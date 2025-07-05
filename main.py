import os
import sys
import argparse
import logging
import threading  # Added for MQ Consumer
import atexit  # Added for graceful shutdown
from sqlalchemy import text
from flask import Flask, jsonify, render_template, redirect, url_for, request, make_response
from flask_socketio import SocketIO
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity, verify_jwt_in_request, get_jwt, decode_token
from functools import wraps
from dotenv import load_dotenv
from app.models import db
from app.utils.logging_config import configure_logging
from app.models.models import Prompt
from app.prompts.default_prompts import DEFAULT_PROMPTS
from app.utils.mq_consumer import RabbitMQConsumer # Added MQ Consumer

# 配置日志
logger = configure_logging()

# 加载环境变量
load_dotenv(override=True)

# 创建Flask应用
app = Flask(__name__, 
            static_folder='app/static',
            template_folder='app/templates')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'deepsoc_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'mysql+pymysql://root:123456@localhost:3306/deepsoc')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# JWT配置
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'deepsoc_jwt_secret_key')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 86400))
app.config['JWT_TOKEN_LOCATION'] = ['headers', 'cookies']
app.config['JWT_COOKIE_CSRF_PROTECT'] = False

# 初始化JWT
jwt = JWTManager(app)

# 初始化数据库
db.init_app(app)

# 初始化迁移
migrate = Migrate(app, db)

# 初始化SocketIO
socketio = SocketIO(
    app, 
    cors_allowed_origins="*",
    async_mode='threading',
    ping_timeout=60,
    ping_interval=25,
    engineio_logger=os.getenv('ENGINEIO_LOGGER', 'False').lower() == 'true', # Control via env var
    logger=os.getenv('SOCKETIO_LOGGER', 'False').lower() == 'true',       # Control via env var
    manage_session=False,
    always_connect=True,
    max_http_buffer_size=int(os.getenv('SOCKETIO_MAX_HTTP_BUFFER_SIZE', 100000000)) # Control via env var (1e8)
)

# 导入路由
from app.controllers.event_controller import event_bp
app.register_blueprint(event_bp, url_prefix='/api/event')

from app.controllers.auth_controller import auth_bp
app.register_blueprint(auth_bp, url_prefix='/api/auth')

from app.controllers.prompt_controller import prompt_bp
app.register_blueprint(prompt_bp, url_prefix='/api/prompt')

from app.controllers.state_controller import state_bp
app.register_blueprint(state_bp, url_prefix='/api/state')

from app.controllers.user_controller import user_bp
app.register_blueprint(user_bp, url_prefix='/api/user')

from app.controllers.engineer_chat_api import engineer_chat_bp
app.register_blueprint(engineer_chat_bp, url_prefix='/api/engineer-chat')

from app.controllers.socket_controller import register_socket_events
register_socket_events(socketio)

# --- RabbitMQ Consumer Setup ---
mq_consumer_thread = None
mq_consumer = None

def handle_mq_message_to_socketio(message_data):
    """Callback function to process messages from RabbitMQ and emit them via SocketIO."""
    event_id = message_data.get('event_id')
    message_type = message_data.get('message_type', 'generic_notification') # Default type if not present
    message_id = message_data.get('message_id', 'N/A')

    if not event_id:
        logger.warning(f"MQ Consumer: Received message (ID: {message_id}) without event_id. Cannot route to SocketIO room. Message: {message_data}")
        return

    # The message_data is already a dict from create_standard_message().to_dict()
    # It should be directly usable by the frontend if it expects the Message model structure.
    
    # Determine the SocketIO event name. 
    # For now, using 'new_message' for all, as previously used by broadcast_message.
    # This could be made more specific based on message_type if frontend handles different events.
    socketio_event_name = 'new_message' 
    
    logger.info(f"MQ Consumer: Relaying message (ID: {message_id}, Type: {message_type}) to SocketIO room '{event_id}' for event '{socketio_event_name}'")
    try:
        # Emit with app.app_context() to ensure context for operations like url_for if used by SocketIO internals
        # although socketio.emit itself is generally thread-safe and handles context for its own operations.
        with app.app_context(): 
            socketio.emit(socketio_event_name, message_data, room=event_id)
        logger.debug(f"MQ Consumer: Successfully emitted message ID {message_id} to room {event_id}.")
    except Exception as e:
        logger.error(f"MQ Consumer: Error emitting message ID {message_id} to SocketIO room '{event_id}': {e}")
        logger.error(traceback.format_exc())

def start_rabbitmq_consumer():
    global mq_consumer, mq_consumer_thread
    logger.info("Initializing RabbitMQ consumer...")
    mq_consumer = RabbitMQConsumer(
        # Uses default connection params from mq_consumer.py which read from .env
        # queue_name can be specific if needed, default is fine
        # routing_key default 'notifications.frontend.#' is also fine
    )
    
    # Start consuming in a separate thread
    # The start_consuming method is blocking, so it needs its own thread.
    mq_consumer_thread = threading.Thread(
        target=mq_consumer.start_consuming, 
        args=(handle_mq_message_to_socketio,),
        name="RabbitMQConsumerThread",
        daemon=True # Daemon thread will exit when the main program exits
    )
    mq_consumer_thread.start()
    logger.info("RabbitMQ consumer thread started.")

def stop_rabbitmq_consumer():
    global mq_consumer, mq_consumer_thread
    if mq_consumer:
        logger.info("Stopping RabbitMQ consumer...")
        mq_consumer.stop_consuming()
        if mq_consumer_thread and mq_consumer_thread.is_alive():
            logger.info("Waiting for RabbitMQ consumer thread to join...")
            mq_consumer_thread.join(timeout=10) # Wait for up to 10 seconds
            if mq_consumer_thread.is_alive():
                logger.warning("RabbitMQ consumer thread did not join in time.")
            else:
                logger.info("RabbitMQ consumer thread joined successfully.")
    logger.info("RabbitMQ consumer stopped.")

# Register the cleanup function to be called on exit
atexit.register(stop_rabbitmq_consumer)
# --- End RabbitMQ Consumer Setup ---

# 定义登录检查装饰器
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 从多个来源获取Token
        token = None
        
        # 1. 尝试从Authorization头部获取
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        
        # 2. 尝试从Cookie获取
        if not token:
            token = request.cookies.get('access_token')
            
        # 3. 尝试从查询参数获取（不推荐，但为了兼容）
        if not token:
            token = request.args.get('access_token')
        
        if token:
            try:
                # 验证令牌有效性
                app.config['JWT_TOKEN_LOCATION'] = ['headers']  # 临时设置为仅从头部获取
                app.config['JWT_HEADER_NAME'] = 'Authorization'
                app.config['JWT_HEADER_TYPE'] = 'Bearer'
                
                # 手动解码Token
                jwt_data = decode_token(token)
                identity = jwt_data['sub']
                
                # 如果到这里没有异常，则用户已登录
                return f(*args, **kwargs)
            except Exception as e:
                logger.error(f"Token验证失败: {str(e)}")
                pass  # Token无效，继续执行重定向逻辑
        
        # Token不存在或无效
        if request.path.startswith('/api/'):
            return jsonify({
                'status': 'error',
                'message': '请先登录',
                'authenticated': False
            }), 401
            
        # 如果是页面请求，重定向到登录页
        return redirect(url_for('login'))
    
    return decorated_function

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/warroom/<event_id>')
@login_required
def warroom(event_id):
    return render_template('warroom.html', event_id=event_id)

@app.route('/settings/prompts')
@login_required
def prompt_settings():
    return render_template('prompt_management.html')

@app.route('/settings/background-security')
@login_required
def background_security():
    return render_template('background_security.html')

@app.route('/settings/soar-playbooks')
@login_required
def soar_playbooks():
    return render_template('soar_playbooks.html')

@app.route('/settings/mcp-tools')
@login_required
def mcp_tools():
    return render_template('mcp_tools.html')

@app.route('/user-management')
@login_required
def user_management():
    return render_template('user_management.html')

@app.route('/change-password')
@login_required
def change_password_page():
    return render_template('change_password.html')

@app.route('/health')
def health():
    return jsonify({
        'status': 'success',
        'message': 'DeepSOC API is healthy'
    })

def create_tables():
    """重新创建数据库表，确保结构最新"""
    with app.app_context():
        db.drop_all()
        db.create_all()
        logger.info("数据库表重新创建成功")

def import_sql_file(sql_path: str = "initial_data.sql"):
    """Import initial data from a SQL file if it exists."""
    if not os.path.exists(sql_path):
        logger.warning(f"SQL file {sql_path} not found, skipping import")
        return
    with app.app_context():
        engine = db.engine
        with engine.begin() as connection:
            sql_content = open(sql_path, "r", encoding="utf-8").read()
            for statement in sql_content.split(";"):
                stmt = statement.strip()
                if stmt:
                    # Use exec_driver_sql to avoid SQLAlchemy interpreting
                    # colon-prefixed values inside JSON as bind parameters.
                    connection.exec_driver_sql(stmt)
        logger.info(f"初始数据 {sql_path} 导入完成")


def create_default_prompts():
    """Load built-in prompt content into the database if not already present."""
    with app.app_context():
        for name, content in DEFAULT_PROMPTS.items():
            prompt = Prompt.query.filter_by(name=name).first()
            if not prompt:
                prompt = Prompt(name=name)
                db.session.add(prompt)
            if not prompt.content:
                prompt.content = content
        db.session.commit()
        logger.info("默认提示词导入完成")

def start_agent(role):
    """启动特定角色的Agent"""
    logger.info(f"启动 {role} Agent")
    if role == '_captain':
        from app.services.captain_service import run_captain
        run_captain()
    elif role == '_manager':
        from app.services.manager_service import run_manager
        run_manager()
    elif role == '_operator':
        from app.services.operator_service import run_operator
        run_operator()
    elif role == '_executor':
        from app.services.executor_service import run_executor
        run_executor()
    elif role == '_expert':
        from app.services.expert_service import run_expert
        run_expert()
    else:
        logger.error(f"未知角色: {role}")
        sys.exit(1)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='DeepSOC - AI驱动的安全运营中心')
    parser.add_argument('-role', type=str, help='Agent角色: _captain, _manager, _operator, _executor, _expert')
    parser.add_argument('-init', action='store_true', help='初始化数据库')
    args = parser.parse_args()
    
    if args.init:
        create_tables()
        import_sql_file()
        # import_sql_file()已经包含提示词初始化，这里不需要再调用create_default_prompts()
        # create_default_prompts()
    
    if args.role:
        # When running as an agent, do not start the MQ consumer or web server.
        start_agent(args.role)
    else:
        # This is the main web server process
        logger.info("Starting DeepSOC Web Server and services...")
        
        # 先检查端口可用性，避免启动后台线程后才发现端口冲突
        host = os.getenv('LISTEN_HOST', '0.0.0.0')
        port = int(os.getenv('LISTEN_PORT', 5007))
        
        try:
            import socket
            # 测试端口是否可用
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            test_socket.bind((host, port))
            test_socket.close()
            logger.info(f"Port {port} is available, starting services...")
        except OSError as e:
            logger.error(f"Port {port} is not available: {e}")
            logger.error("Please stop the existing process or use a different port.")
            sys.exit(1)
        
        # 端口可用后再启动RabbitMQ consumer
        start_rabbitmq_consumer()
        
        # 启动Web服务器
        try:
            socketio.run(
                app, 
                host=host, 
                port=port, 
                debug=(os.getenv('FLASK_DEBUG', 'False').lower() == 'true'), # Control via env var
                use_reloader=False, # Important: reloader can cause issues with threads and SocketIO
                allow_unsafe_werkzeug=True # Allow for development and testing
            )
        except Exception as e:
            logger.error(f"Failed to start web server: {e}")
            stop_rabbitmq_consumer()
            sys.exit(1) 
from flask_socketio import emit, join_room, leave_room
from flask import request
from app.models import Message, db, Event
import json
import traceback
from datetime import datetime
import uuid
import logging

# 获取日志记录器
logger = logging.getLogger(__name__)

def register_socket_events(socketio):
    """注册所有WebSocket事件处理函数"""
    
    @socketio.on('connect')
    def handle_connect():
        """处理客户端连接"""
        try:
            logger.info(f"客户端已连接，SID: {request.sid}")
            emit('status', {'status': 'connected'})
        except Exception as e:
            logger.error(f"处理连接时出错: {str(e)}")
            logger.error(traceback.format_exc())
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """处理客户端断开连接"""
        try:
            logger.info(f"客户端已断开连接，SID: {request.sid}")
        except Exception as e:
            logger.error(f"处理断开连接时出错: {str(e)}")
            logger.error(traceback.format_exc())
    
    @socketio.on('join')
    def handle_join(data):
        """处理客户端加入特定作战室"""
        try:
            room = data.get('event_id')
            if room:
                logger.info(f"客户端 {request.sid} 正在尝试加入房间: {room}")
                
                # 加入房间
                try:
                    join_room(room)
                    logger.info(f"✅ 客户端 {request.sid} 已成功加入房间: {room}")
                except Exception as join_error:
                    logger.error(f"❌ 加入房间失败: {str(join_error)}")
                    emit('error', {'message': f'加入房间失败: {str(join_error)}'})
                    return
                
                # 发送状态更新
                emit('status', {'status': 'joined', 'event_id': room})
                logger.info(f"已发送joined状态到客户端 {request.sid}")
                
                # 发送测试消息验证连接
                try:
                    # 直接发送到当前客户端
                    emit('test_message', {
                        'message': '这是一条测试消息，用于验证WebSocket连接',
                        'timestamp': datetime.now().isoformat()
                    })
                    
                    # 发送到整个房间
                    emit('test_message', {
                        'message': f'客户端 {request.sid} 已加入房间 {room}',
                        'timestamp': datetime.now().isoformat()
                    }, room=room)
                    
                    logger.info(f"测试消息已发送")
                except Exception as e:
                    logger.error(f"发送测试消息时出错: {str(e)}")
            else:
                logger.warning(f"客户端 {request.sid} 尝试加入房间但未提供event_id")
                emit('error', {'message': '缺少event_id参数'})
        except Exception as e:
            logger.error(f"处理加入房间时出错: {str(e)}")
            logger.error(traceback.format_exc())
    
    @socketio.on('leave')
    def handle_leave(data):
        """处理客户端离开特定作战室"""
        try:
            room = data.get('event_id')
            if room:
                leave_room(room)
                logger.info(f"客户端已离开房间: {room}")
                emit('status', {'status': 'left', 'event_id': room}, room=room)
        except Exception as e:
            logger.error(f"处理离开房间时出错: {str(e)}")
            logger.error(traceback.format_exc())
    
    @socketio.on('message')
    def handle_message(data):
        """处理客户端发送的消息"""
        try:
            event_id = data.get('event_id')
            message_content = data.get('message')
            sender = data.get('sender', 'user')
            temp_id = data.get('temp_id')
            
            if not event_id or not message_content:
                emit('error', {'message': '缺少必要参数'})
                return
            
            # 查找事件
            event = Event.query.filter_by(event_id=event_id).first()
            if not event:
                emit('error', {'message': '事件不存在'})
                return
            
            # 创建消息
            user_id = None
            user_nickname = None
            try:
                from flask_jwt_extended import decode_token
                token = request.cookies.get('access_token') or request.headers.get('Authorization', '')
                if token and token.startswith('Bearer '):
                    token = token.split(' ', 1)[1]
                if token:
                    decoded = decode_token(token)
                    username = decoded.get('sub')
                    if username:
                        from app.models.models import User
                        user = User.query.filter_by(username=username).first()
                        if user:
                            user_id = user.user_id
                            user_nickname = user.nickname
            except Exception as auth_error:
                logger.warning(f"解析用户身份失败: {auth_error}")

            message = Message(
                message_id=str(uuid.uuid4()),
                event_id=event_id,
                user_id=user_id,
                message_from=sender,
                message_type='user_message',
                message_content=message_content
            )
            
            # 保存消息
            db.session.add(message)
            db.session.commit()
            
            # 广播消息，并带上临时ID以便前端替换
            msg_dict = message.to_dict()
            if temp_id:
                msg_dict['temp_id'] = temp_id
            if user_nickname:
                msg_dict['user_nickname'] = user_nickname
            else:
                # 如果没有获取到用户昵称，尝试再次获取用户信息
                if user_id:
                    try:
                        from app.models.models import User
                        user = User.query.filter_by(user_id=user_id).first()
                        if user:
                            msg_dict['user_nickname'] = user.nickname or user.username
                            msg_dict['user_username'] = user.username
                    except Exception as e:
                        logger.warning(f"获取用户信息失败: {e}")
            emit('new_message', msg_dict, room=event_id)
        except Exception as e:
            logger.error(f"处理消息时出错: {str(e)}")
            logger.error(traceback.format_exc())
            emit('error', {'message': f'处理消息时出错: {str(e)}'})
    
    @socketio.on('test_connection')
    def handle_test_connection(data):
        """处理客户端发送的测试连接请求"""
        try:
            event_id = data.get('event_id')
            timestamp = data.get('timestamp')
            
            logger.info(f"收到客户端 {request.sid} 的连接测试请求: event_id={event_id}, timestamp={timestamp}")
            
            # 发送响应
            emit('test_connection_response', {
                'message': '连接测试成功',
                'timestamp': datetime.now().isoformat(),
                'request_timestamp': timestamp
            })
            
            # 如果提供了事件ID，还发送一条新消息
            if event_id:
                # 创建测试消息
                test_message = Message(
                    message_id=str(uuid.uuid4()),
                    event_id=event_id,
                    message_from='system',
                    message_type='system_notification',
                    message_content={
                        "type": "system_notification",
                        "timestamp": datetime.now().isoformat(),
                        "data": {
                            "response_text": f"这是一条通过WebSocket发送的测试系统通知 (SID: {request.sid})"
                        }
                    }
                )
                
                # 广播测试消息
                broadcast_message(test_message)
        except Exception as e:
            logger.error(f"处理测试连接请求时出错: {str(e)}")
            logger.error(traceback.format_exc())
            emit('error', {'message': f'处理测试连接请求时出错: {str(e)}'})

def broadcast_message(message, extra_data=None):
    """广播消息到特定作战室
    
    Args:
        message: Message对象
    """
    try:
        from main import socketio
        
        # 通过WebSocket推送消息
        event_id = message.event_id
        message_dict = message.to_dict()
        if extra_data:
            message_dict.update(extra_data)
        
        # 如果是用户消息，添加用户信息
        if message.message_from == 'user' and message.user_id:
            try:
                from app.models.models import User
                user = User.query.filter_by(user_id=message.user_id).first()
                if user:
                    message_dict['user_nickname'] = user.nickname or user.username
                    message_dict['user_username'] = user.username
            except Exception as e:
                logger.warning(f"获取用户信息失败: {e}")
        
        # 保存到数据库（如果尚未保存）
        if message.id is None:
            db.session.add(message)
            db.session.commit()
        
        logger.info(f"广播消息: ID={message.id}, 类型={message.message_type}, 来源={message.message_from}, 事件={event_id}")
        
        # 检查socketio是否可用
        if not socketio:
            logger.error("socketio对象不可用，无法广播消息")
            return
        
        # 广播消息到房间
        socketio.emit('new_message', message_dict, room=event_id)
        logger.info(f"消息已通过WebSocket广播到房间: {event_id}")
        
        # 如果状态发生变化，发送状态更新
        if message.message_type in ['event_summary', 'llm_response']:
            # 获取事件
            event = Event.query.filter_by(event_id=event_id).first()
            if event:
                logger.info(f"发送事件状态更新: 事件={event_id}, 状态={event.status}, 轮次={event.current_round}")
                socketio.emit('status', {
                    'event_status': event.status,
                    'event_round': event.current_round
                }, room=event_id)
    except Exception as e:
        logger.error(f"广播消息时出错: {str(e)}")
        logger.error(traceback.format_exc())

def trigger_ai_response(event_id, user_message):
    """触发AI响应
    
    Args:
        event_id: 事件ID
        user_message: 用户消息对象
    """
    try:
        # 这里可以添加触发AI响应的逻辑
        # 例如，可以将消息放入队列，由AI Agent处理
        logger.info(f"收到用户消息，事件ID: {event_id}, 消息内容: {user_message.message_content}")
        
        # 在实际项目中，这里应该触发AI Agent的处理流程
        # 以下代码仅作为示例，实际应用中应该由AI Agent生成响应
        
        # 创建AI回复消息
        ai_message = Message(
            message_id=str(uuid.uuid4()),
            event_id=event_id,
            message_from='_captain',  # 由安全指挥官回复
            message_type='llm_response',
            message_content={
                "type": "llm_response",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "response_type": "ROGER",
                    "response_text": f"收到您的消息: {user_message.message_content}\n\n我们正在处理中，请稍候..."
                }
            }
        )
        
        # 广播AI回复
        broadcast_message(ai_message)
    except Exception as e:
        logger.error(f"触发AI响应时出错: {str(e)}")
        logger.error(traceback.format_exc()) 

def broadcast_execution_update(execution):
    """广播执行任务状态更新"""
    try:
        # 获取当前socketio实例
        from main import socketio
        
        socketio.emit('execution_update', {
            'execution_id': execution.execution_id,
            'status': execution.execution_status,
            'updated_at': execution.updated_at.isoformat()
        }, room=execution.event_id)
        
        logger.info(f"已广播执行任务状态更新: {execution.execution_id}, 状态: {execution.execution_status}")
    except Exception as e:
        logger.error(f"广播执行任务状态更新时出错: {str(e)}")
        logger.error(traceback.format_exc())
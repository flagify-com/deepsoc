from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.controllers.engineer_chat_controller import engineer_chat_controller
from app.models import db, User, Event
import logging

# 获取日志记录器
logger = logging.getLogger(__name__)

# 创建蓝图
engineer_chat_bp = Blueprint('engineer_chat', __name__)

@engineer_chat_bp.route('/send', methods=['POST'])
@jwt_required()
def send_message():
    """工程师发送消息给AI助手"""
    try:
        # 获取当前用户 - JWT identity返回的是username
        current_username = get_jwt_identity()
        
        # 获取请求数据
        data = request.json
        if not data:
            return jsonify({
                'status': 'error',
                'message': '请求数据不能为空'
            }), 400
        
        # 验证必要字段
        event_id = data.get('event_id')
        message = data.get('message')
        
        if not event_id:
            return jsonify({
                'status': 'error',
                'message': 'event_id不能为空'
            }), 400
        
        if not message or not message.strip():
            return jsonify({
                'status': 'error',
                'message': '消息内容不能为空'
            }), 400
        
        # 验证事件是否存在
        event = db.session.query(Event).filter_by(event_id=event_id).first()
        if not event:
            return jsonify({
                'status': 'error',
                'message': f'事件 {event_id} 不存在'
            }), 404
        
        # 通过username查找用户
        user = db.session.query(User).filter_by(username=current_username).first()
        if not user:
            return jsonify({
                'status': 'error',
                'message': '用户不存在'
            }), 404
        
        # 调用工程师对话控制器
        result = engineer_chat_controller.send_message(
            event_id=event_id,
            user_id=user.user_id,  # 使用用户的user_id
            message=message.strip()
        )
        
        if result['status'] == 'success':
            # 异步模式：只返回用户消息，AI回复通过WebSocket推送
            response_data = {
                'user_message': result.get('user_message'),
                'session_id': result.get('session_id'),
                'summary_updated': result.get('summary_updated', False)
            }
            
            # 添加AI处理状态标识
            if 'ai_processing' in result:
                response_data['ai_processing'] = result['ai_processing']
            
            # 兼容同步模式（如果有ai_response字段）
            if 'ai_response' in result:
                response_data['ai_response'] = result['ai_response']
                
            return jsonify({
                'status': 'success',
                'data': response_data
            }), 200
        elif result['status'] == 'max_rounds_reached':
            return jsonify({
                'status': 'warning',
                'message': result.get('message', '达到最大轮次限制'),
                'data': {
                    'session_id': result.get('session_id'),
                    'action': result.get('action', 'create_new_session')
                }
            }), 200
        else:
            # 处理错误状态
            return jsonify({
                'status': 'error',
                'message': result.get('message', '未知错误')
            }), 500
            
    except Exception as e:
        logger.error(f"处理发送消息请求时出错: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'服务器内部错误: {str(e)}'
        }), 500

@engineer_chat_bp.route('/history', methods=['GET'])
@jwt_required()
def get_chat_history():
    """获取工程师对话历史"""
    try:
        # 获取当前用户
        current_username = get_jwt_identity()
        
        # 获取请求参数
        event_id = request.args.get('event_id')
        
        if not event_id:
            return jsonify({
                'status': 'error',
                'message': 'event_id不能为空'
            }), 400
        
        # 验证事件是否存在
        event = db.session.query(Event).filter_by(event_id=event_id).first()
        if not event:
            return jsonify({
                'status': 'error',
                'message': f'事件 {event_id} 不存在'
            }), 404
        
        # 获取用户
        user = db.session.query(User).filter_by(username=current_username).first()
        if not user:
            return jsonify({
                'status': 'error',
                'message': '用户不存在'
            }), 404
        
        # 调用工程师对话控制器
        result = engineer_chat_controller.get_chat_history(
            event_id=event_id,
            user_id=user.user_id
        )
        
        if result['status'] == 'success':
            return jsonify({
                'status': 'success',
                'data': {
                    'session_id': result['session_id'],
                    'history': result['history'],
                    'current_rounds': result['current_rounds'],
                    'max_rounds': result['max_rounds']
                }
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': result['message']
            }), 500
            
    except Exception as e:
        logger.error(f"获取对话历史时出错: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'服务器内部错误: {str(e)}'
        }), 500

@engineer_chat_bp.route('/new-session', methods=['POST'])
@jwt_required()
def create_new_session():
    """创建新的对话会话（当达到轮次限制时）"""
    try:
        # 获取当前用户
        current_username = get_jwt_identity()
        
        # 获取请求数据
        data = request.json
        if not data:
            return jsonify({
                'status': 'error',
                'message': '请求数据不能为空'
            }), 400
        
        event_id = data.get('event_id')
        if not event_id:
            return jsonify({
                'status': 'error',
                'message': 'event_id不能为空'
            }), 400
        
        # 验证事件是否存在
        event = db.session.query(Event).filter_by(event_id=event_id).first()
        if not event:
            return jsonify({
                'status': 'error',
                'message': f'事件 {event_id} 不存在'
            }), 404
        
        # 获取用户
        user = db.session.query(User).filter_by(username=current_username).first()
        if not user:
            return jsonify({
                'status': 'error',
                'message': '用户不存在'
            }), 404
        
        # 强制创建新会话（通过传递一个新的唯一标识）
        import uuid
        temp_user_id = f"{user.user_id}_{uuid.uuid4().hex[:8]}"
        new_session_id = engineer_chat_controller._get_or_create_session_id(event_id, temp_user_id)
        
        return jsonify({
            'status': 'success',
            'data': {
                'new_session_id': new_session_id,
                'message': '新对话会话已创建'
            }
        }), 200
        
    except Exception as e:
        logger.error(f"创建新会话时出错: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'服务器内部错误: {str(e)}'
        }), 500

@engineer_chat_bp.route('/status', methods=['GET'])
@jwt_required()
def get_chat_status():
    """获取当前对话状态"""
    try:
        # 获取当前用户
        current_username = get_jwt_identity()
        
        # 获取请求参数
        event_id = request.args.get('event_id')
        
        if not event_id:
            return jsonify({
                'status': 'error',
                'message': 'event_id不能为空'
            }), 400
        
        # 验证事件是否存在
        event = db.session.query(Event).filter_by(event_id=event_id).first()
        if not event:
            return jsonify({
                'status': 'error',
                'message': f'事件 {event_id} 不存在'
            }), 404
        
        # 获取用户
        user = db.session.query(User).filter_by(username=current_username).first()
        if not user:
            return jsonify({
                'status': 'error',
                'message': '用户不存在'
            }), 404
        
        # 获取当前会话信息
        session_id = engineer_chat_controller._get_or_create_session_id(event_id, user.user_id)
        chat_history = engineer_chat_controller._get_engineer_chat_history(session_id)
        
        current_rounds = len([msg for msg in chat_history if msg.sender_type == 'user'])
        max_rounds = engineer_chat_controller.max_chat_rounds
        
        # 获取最新的事件概要
        latest_summary = engineer_chat_controller._get_event_summary(event_id)
        summary_info = {
            'has_summary': latest_summary is not None,
            'summary_content': latest_summary.event_summary if latest_summary else None,
            'round_id': latest_summary.round_id if latest_summary else None,
            'updated_at': latest_summary.updated_at.isoformat() if latest_summary and latest_summary.updated_at else None
        }
        
        return jsonify({
            'status': 'success',
            'data': {
                'session_id': session_id,
                'current_rounds': current_rounds,
                'max_rounds': max_rounds,
                'can_chat': current_rounds < max_rounds,
                'event_summary': summary_info,
                'event_info': {
                    'event_id': event.event_id,
                    'event_name': event.event_name,
                    'event_status': event.event_status,
                    'severity': event.severity,
                    'current_round': event.current_round
                }
            }
        }), 200
        
    except Exception as e:
        logger.error(f"获取对话状态时出错: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'服务器内部错误: {str(e)}'
        }), 500
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, Event
from app.utils.message_utils import create_standard_message

event_bp = Blueprint('event', __name__)

@event_bp.route('/create', methods=['POST'])
@jwt_required()
def create_event():
    """创建新的安全事件"""
    data = request.json
    
    # 验证必要字段
    if not data.get('message'):
        return jsonify({
            'status': 'error',
            'message': '事件消息不能为空'
        }), 400
    
    # 生成事件ID（如果未提供）
    event_id = data.get('event_id', str(uuid.uuid4()))
    
    # 创建事件
    event = Event(
        event_id=event_id,
        event_name=data.get('event_name', ''),
        message=data.get('message'),
        context=data.get('context', ''),
        source=data.get('source', 'manual'),
        severity=data.get('severity', 'medium'),
        event_status='pending'
    )
    
    db.session.add(event)
    db.session.commit()
    
    # 创建系统消息，通知事件已创建
    system_message_content = {
        "response_text": f"系统创建了安全事件: {event.event_name or '未命名事件'}"
    }
    
    create_standard_message(
        event_id=event_id,
        message_from="system",
        round_id=1,
        message_type="system_notification",
        content_data=system_message_content
    )
    
    return jsonify({
        'status': 'success',
        'message': '事件创建成功',
        'data': event.to_dict()
    })

@event_bp.route('/list', methods=['GET'])
@jwt_required()
def list_events():
    """获取事件列表"""
    events = Event.query.order_by(Event.created_at.desc()).all()
    return jsonify({
        'status': 'success',
        'data': [event.to_dict() for event in events]
    })

@event_bp.route('/<event_id>', methods=['GET'])
@jwt_required()
def get_event(event_id):
    """获取单个事件详情"""
    event = Event.query.filter_by(event_id=event_id).first()
    if not event:
        return jsonify({
            'status': 'error',
            'message': '事件不存在'
        }), 404
    
    return jsonify({
        'status': 'success',
        'data': event.to_dict()
    })

@event_bp.route('/<event_id>/messages', methods=['GET'])
@jwt_required()
def get_event_messages(event_id):
    """获取事件相关的所有消息"""
    from app.models import Message, User
    
    # 获取 last_message_db_id 参数，用于增量获取消息
    last_message_db_id = request.args.get('last_message_db_id', 0, type=int)
    
    # 获取role参数，用于按角色筛选消息 (此功能保留)
    role = request.args.get('role')
    
    # 构建查询
    query = Message.query.filter_by(event_id=event_id)
    
    # 如果指定了 last_message_db_id，则只获取ID更大的消息
    if last_message_db_id > 0:
        query = query.filter(Message.id > last_message_db_id)
    
    # 如果指定了role，则按角色筛选
    if role:
        query = query.filter_by(message_from=role)
    
    # 获取消息并按数据库ID升序排序
    messages = query.order_by(Message.id.asc()).all()

    result = []
    for message in messages:
        msg_dict = message.to_dict()
        if message.user_id:
            user = User.query.filter_by(user_id=message.user_id).first()
            if user:
                # 优先使用昵称，如果没有昵称则使用用户名
                msg_dict['user_nickname'] = user.nickname or user.username
                msg_dict['user_username'] = user.username  # 同时提供用户名信息
        result.append(msg_dict)

    return jsonify({
        'status': 'success',
        'data': result
    })

@event_bp.route('/<event_id>/tasks', methods=['GET'])
@jwt_required()
def get_event_tasks(event_id):
    """获取事件相关的所有任务"""
    from app.models import Task
    
    tasks = Task.query.filter_by(event_id=event_id).order_by(Task.created_at.asc()).all()
    return jsonify({
        'status': 'success',
        'data': [task.to_dict() for task in tasks]
    })

@event_bp.route('/<event_id>/stats', methods=['GET'])
@jwt_required()
def get_event_stats(event_id):
    """获取事件相关的统计信息"""
    from app.models import Task, Action, Command
    
    # 获取任务数量
    task_count = Task.query.filter_by(event_id=event_id).count()
    
    # 获取动作数量
    action_count = Action.query.filter_by(event_id=event_id).count()
    
    # 获取命令数量
    command_count = Command.query.filter_by(event_id=event_id).count()
    
    return jsonify({
        'status': 'success',
        'data': {
            'task_count': task_count,
            'action_count': action_count,
            'command_count': command_count
        }
    })

@event_bp.route('/<event_id>/summaries', methods=['GET'])
@jwt_required()
def get_event_summaries(event_id):
    """获取事件相关的所有总结"""
    from app.models import Summary
    
    summaries = Summary.query.filter_by(event_id=event_id).order_by(Summary.created_at.desc()).all()
    return jsonify({
        'status': 'success',
        'data': [summary.to_dict() for summary in summaries]
    })

@event_bp.route('/send_message/<event_id>', methods=['POST'])
@jwt_required()
def send_message(event_id):
    """发送消息到事件"""
    from app.models import Message
    from app.controllers.socket_controller import broadcast_message
    
    data = request.json
    
    # 验证必要字段
    if not data.get('message'):
        return jsonify({
            'status': 'error',
            'message': '消息内容不能为空'
        }), 400
    
    # 查找事件
    event = Event.query.filter_by(event_id=event_id).first()
    if not event:
        return jsonify({
            'status': 'error',
            'message': '事件不存在'
        }), 404
    
    # 创建消息，支持扩展不同类型的内容
    content_type = data.get('content_type', 'text')
    message_content = {
        'type': content_type,
        'text': data.get('message')
    }

    temp_id = data.get('temp_id')

    message = Message(
        message_id=str(uuid.uuid4()),
        event_id=event_id,
        message_from=data.get('sender', 'user'),
        message_type='user_message',
        message_content=message_content
    )
    
    # 广播消息
    extra = {'temp_id': temp_id} if temp_id else None
    broadcast_message(message, extra)
    

    
    return jsonify({
        'status': 'success',
        'message': '消息发送成功',
        'data': message.to_dict()
    })

@event_bp.route('/<event_id>/executions', methods=['GET'])
@jwt_required()
def get_event_executions(event_id):
    """获取事件相关的执行任务"""
    from app.models import Execution, Command
    
    # 获取status参数，用于筛选执行任务
    status = request.args.get('status')
    
    # 构建查询
    query = Execution.query.filter_by(event_id=event_id)
    
    # 如果指定了status，则按状态筛选
    if status:
        query = query.filter_by(execution_status=status)
    
    # 获取执行任务并排序
    executions = query.order_by(Execution.created_at.desc()).all()
    
    # 增强执行任务信息，添加命令详情
    enhanced_executions = []
    for execution in executions:
        execution_dict = execution.to_dict()
        
        # 查询关联的命令信息
        if execution.command_id:
            command = Command.query.filter_by(command_id=execution.command_id).first()
            if command:
                # 添加命令相关信息
                execution_dict['command_name'] = command.command_name
                execution_dict['command_type'] = command.command_type
                execution_dict['command_entity'] = command.command_entity
                execution_dict['command_params'] = command.command_params
                execution_dict['description'] = f"执行命令: {command.command_name}"
        
        enhanced_executions.append(execution_dict)
    
    return jsonify({
        'status': 'success',
        'data': enhanced_executions
    })

@event_bp.route('/<event_id>/execution/<execution_id>/complete', methods=['POST'])
def complete_execution(event_id, execution_id):
    """完成执行任务"""
    from app.models import Execution
    from app.controllers.socket_controller import broadcast_execution_update
    
    data = request.json
    
    # 验证必要字段
    if 'result' not in data:
        return jsonify({
            'status': 'error',
            'message': '执行结果不能为空'
        }), 400
    
    # 查找执行任务
    execution = Execution.query.filter_by(
        execution_id=execution_id, 
        event_id=event_id
    ).first()
    
    if not execution:
        return jsonify({
            'status': 'error',
            'message': '执行任务不存在'
        }), 404
    
    # 更新执行任务
    execution.execution_result = data['result']
    execution.execution_status = data.get('status', 'completed')
    execution.updated_at = datetime.utcnow()
    
    db.session.commit()
    
    # 广播执行任务状态更新
    broadcast_execution_update(execution)

    return jsonify({
        'status': 'success',
        'message': '执行任务已完成',
        'data': execution.to_dict()
    })


@event_bp.route('/<event_id>/hierarchy', methods=['GET'])
@jwt_required()
def get_event_hierarchy(event_id):
    """获取事件及其关联实体的树状结构"""
    from collections import defaultdict
    from app.models import Task, Action, Command, Execution, Summary

    event = Event.query.filter_by(event_id=event_id).first()
    if not event:
        return jsonify({'status': 'error', 'message': '事件不存在'}), 404

    tasks = Task.query.filter_by(event_id=event_id).all()
    actions = Action.query.filter_by(event_id=event_id).all()
    commands = Command.query.filter_by(event_id=event_id).all()
    executions = Execution.query.filter_by(event_id=event_id).all()
    summaries = Summary.query.filter_by(event_id=event_id).all()

    # 按ID映射，便于构建关系
    action_map = defaultdict(list)
    for action in actions:
        action_map[action.task_id].append(action)

    command_map = defaultdict(list)
    for command in commands:
        command_map[command.action_id].append(command)

    execution_map = defaultdict(list)
    for exe in executions:
        execution_map[exe.command_id].append(exe)

    summary_map = defaultdict(list)
    for summary in summaries:
        summary_map[summary.round_id].append(summary)

    rounds = defaultdict(lambda: {'round_id': 0, 'tasks': [], 'summaries': []})

    for task in tasks:
        r = task.round_id or 0
        round_data = rounds[r]
        round_data['round_id'] = r
        t_dict = task.to_dict()
        t_dict['actions'] = []
        for act in action_map.get(task.task_id, []):
            a_dict = act.to_dict()
            a_dict['commands'] = []
            for cmd in command_map.get(act.action_id, []):
                c_dict = cmd.to_dict()
                c_dict['executions'] = [e.to_dict() for e in execution_map.get(cmd.command_id, [])]
                a_dict['commands'].append(c_dict)
            t_dict['actions'].append(a_dict)
        round_data['tasks'].append(t_dict)

    for r_id, sum_list in summary_map.items():
        rounds[r_id]['round_id'] = r_id
        rounds[r_id]['summaries'] = [s.to_dict() for s in sum_list]

    # 按round_id排序输出列表
    result = [rounds[r] for r in sorted(rounds.keys())]

    return jsonify({'status': 'success', 'data': result})
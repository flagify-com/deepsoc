import uuid
from datetime import datetime
from app.models import db, Message
# from app.controllers.socket_controller import broadcast_message # Removed

def create_standard_message(event_id, message_from, round_id, message_type, content_data, additional_fields=None):
    """创建标准格式的消息并存入数据库。
       Agent进程调用此函数后，应负责将返回的message对象内容发送到消息队列。
    
    Args:
        event_id: 事件ID
        message_from: 消息来源 (_captain, _manager, _operator, _executor, _expert, system, user)
        round_id: 轮次ID
        message_type: 消息类型 (llm_request, llm_response, execution_summary, event_summary, command_result, system_notification, user_message 等)
        content_data: 消息主体内容 (通常是一个字典)
        additional_fields: 额外字段 (可选, 会合并到 message_content 中)
    
    Returns:
        创建并已存入数据库的 Message 对象
    """
    # 构造标准消息内容
    message_content = {
        # "type": message_type, # message_type 字段已在 Message 模型中有，content里不必重复，除非有特定子类型需求
        "timestamp": datetime.now().isoformat(),
        "data": content_data
    }
    
    # 添加额外字段
    if additional_fields:
        # 如果 content_data 本身就是消息主体，additional_fields 应该合并到 data 内部，
        # 或者如果 content_data 只是 data 的一部分，则可以平级合并。
        # 当前设计: content_data 是 data 字段的值。additional_fields 合并到 message_content 的顶层。
        # 调整为: additional_fields 也放入 data，使得 data 包含所有动态内容。
        if isinstance(message_content['data'], dict) and isinstance(additional_fields, dict):
            message_content['data'].update(additional_fields)
        elif additional_fields: # 如果data不是dict，或者additional_fields不是dict，直接替换或作为新字段
            message_content['additional_info'] = additional_fields # 作为补充信息

    message = Message(
        message_id=str(uuid.uuid4()),
        event_id=event_id,
        message_from=message_from,
        round_id=round_id,
        message_content=message_content, # message_content 现在是 {'timestamp': ..., 'data': {original_content_data + additional_fields}}
        message_type=message_type
    )
    db.session.add(message)
    db.session.commit()
    
    # 广播消息的逻辑已移除，将由Agent通过消息队列处理
    # broadcast_message(message) # Removed
    
    return message 
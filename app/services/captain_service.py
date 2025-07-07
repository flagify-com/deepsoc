import time
import uuid
import json
import traceback
from datetime import datetime
from flask import current_app
from app.models import db, Event, Task, Message, Summary
from app.services.llm_service import call_llm, parse_yaml_response
from app.controllers.socket_controller import broadcast_message
from app.services.prompt_service import PromptService
from app.utils.message_utils import create_standard_message
from app.utils.mq_utils import RabbitMQPublisher
import yaml
import pika

import logging
logger = logging.getLogger(__name__)


def get_events_to_process():
    """获取待处理的安全事件
    
    在新的状态流转设计中，Captain只处理pending状态的事件
    round_finished状态的事件由event_next_round_worker处理并转换为pending
    """
    return Event.query.filter_by(event_status='pending').order_by(Event.created_at.asc()).first()  

def process_event(event, publisher: RabbitMQPublisher):
    """处理单个安全事件
    
    Args:
        event: Event对象
        publisher: RabbitMQPublisher 实例，用于发送消息到队列
    """
    logger.info(f"处理事件: {event.event_id} - {event.event_name}")
    is_first_round = (event.current_round == 1)
    round_id = event.current_round

    # 消息1: LLM 请求通知
    content_for_llm_request_msg = {"text": "Captain on the bridge! 正在请求大模型AI指挥官进行分析决策。"}
    db_message_llm_req = create_standard_message(
        event_id=event.event_id,
        message_from='system', # 或者 '_captain' if captain is initiating
        round_id=round_id,
        message_type='llm_request', # 更具体的类型如 captain_llm_request
        content_data=content_for_llm_request_msg
    )
    if db_message_llm_req and publisher:
        try:
            routing_key = f"notifications.frontend.{db_message_llm_req.event_id}.{db_message_llm_req.message_from}.{db_message_llm_req.message_type}"
            publisher.publish_message(
                message_body=db_message_llm_req.to_dict(),
                routing_key=routing_key
            )
            logger.info(f"消息 [LLM Req] {db_message_llm_req.message_id} 已发布到 RabbitMQ. RK: {routing_key}")
        except Exception as e_pub:
            logger.error(f"发布消息 [LLM Req] {db_message_llm_req.message_id} 到 RabbitMQ 失败: {e_pub}")
            logger.error(traceback.format_exc())
    
    # 更新事件状态为处理中
    event.event_status = 'processing'
    db.session.commit()
    # 通知事件状态变更 (可选，如果需要非常实时的状态更新)
    # TBD: Decide if every status change needs MQ message, or if LLM response message is enough.

    request_data = {
        'type': 'generate_tasks_by_event',
        'req_id': str(uuid.uuid4()),
        'res_id': str(uuid.uuid4()),
        'event_id': event.event_id,
        'round_id': round_id,
        'event_name': event.event_name if event.event_name else '{ 请大模型根据message和context生成 }',
        'message': event.message,
        'context': event.context if event.context else '无',
        'source': event.source if event.source else '无',
        'severity': event.severity if event.severity else '无',
        'created_at': event.created_at.strftime('%Y-%m-%d %H:%M:%S')
    }
    
    tasks_history_list = []
    history_tasks_query = Task.query.filter_by(event_id=event.event_id).order_by(Task.created_at.desc()).all()
    for task_item in history_tasks_query:
        tasks_history_list.append({
            "task_id": task_item.task_id,
            "task_name": task_item.task_name,
            "task_type": task_item.task_type,
            "task_status": task_item.task_status,
            "task_created_at": task_item.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            "task_updated_at": task_item.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        })

    if tasks_history_list:
        request_data['history_tasks'] = tasks_history_list
    
    yaml_data = yaml.dump(request_data, allow_unicode=True, default_flow_style=False, indent=2)
    # logger.info(yaml_data) # Logged later in user_prompt

    last_round_summary_content = ""
    if not is_first_round:
        last_round_summary = Summary.query.filter_by(event_id=event.event_id, round_id=round_id-1).order_by(Summary.created_at.desc()).first()
        if last_round_summary:
            last_round_summary_content = f"""
为了方便你更加全面地分析，这里提供了你上一轮安排的任务和战况同步信息：
<event_progress>
{last_round_summary.event_summary}
</event_progress>
"""
    user_prompt = f"""```yaml
{yaml_data}
```
{last_round_summary_content}
针对当前网络安全事件进行分析决策，并分配适当的任务给安全管理员_manager（_analyst, _operator, _coordinator），如果有必要。
"""
    logger.info(f"User prompt for event {event.event_id}, round {round_id}:\n{user_prompt}")
    logger.info("--------------------------------")
    
    prompt_service = PromptService('_captain')
    system_prompt = prompt_service.get_system_prompt()
    response = call_llm(system_prompt, user_prompt)
    
    logger.info(f"LLM Response for event {event.event_id}, round {round_id}:\n{response}")
    logger.info("--------------------------------")
    
    parsed_response = parse_yaml_response(response)
    if not parsed_response:
        logger.error(f"解析LLM响应失败 for event {event.event_id}: {response}")
        # Create an error message for frontend
        error_content = {"text": "AI指挥官未能正确解析LLM响应数据，请检查日志。", "original_response": response}
        db_message_parse_err = create_standard_message(
            event_id=event.event_id,
            message_from='_captain',
            round_id=round_id,
            message_type='error_internal',
            content_data=error_content
        )
        if db_message_parse_err and publisher:
            try:
                routing_key = f"notifications.frontend.{db_message_parse_err.event_id}.{db_message_parse_err.message_from}.{db_message_parse_err.message_type}"
                publisher.publish_message(message_body=db_message_parse_err.to_dict(), routing_key=routing_key)
                logger.info(f"消息 [LLM Parse Err] {db_message_parse_err.message_id} 已发布到 RabbitMQ. RK: {routing_key}")
            except Exception as e_pub:
                logger.error(f"发布消息 [LLM Parse Err] {db_message_parse_err.message_id} 到 RabbitMQ 失败: {e_pub}")
        event.event_status = 'error_processing' # Set a specific error state
        db.session.commit()
        return
    
    response_type = parsed_response.get('response_type')
    response_round_id = parsed_response.get('round_id', round_id)

    # 消息2: LLM 响应内容通知
    db_message_llm_resp = create_standard_message(
        event_id=event.event_id,
        message_from='_captain',
        round_id=response_round_id,
        message_type='llm_response', # or captain_llm_response
        content_data=parsed_response # parsed_response is already a dict
    )
    if db_message_llm_resp and publisher:
        try:
            routing_key = f"notifications.frontend.{db_message_llm_resp.event_id}.{db_message_llm_resp.message_from}.{db_message_llm_resp.message_type}"
            publisher.publish_message(
                message_body=db_message_llm_resp.to_dict(),
                routing_key=routing_key
            )
            logger.info(f"消息 [LLM Resp] {db_message_llm_resp.message_id} 已发布到 RabbitMQ. RK: {routing_key}")
        except Exception as e_pub:
            logger.error(f"发布消息 [LLM Resp] {db_message_llm_resp.message_id} 到 RabbitMQ 失败: {e_pub}")
            logger.error(traceback.format_exc())

    if response_type == 'TASK':
        tasks_data = parsed_response.get('tasks', [])
        created_task_ids = []
        for task_detail in tasks_data:
            new_task_id = str(uuid.uuid4())
            task = Task(
                task_id=new_task_id,
                event_id=event.event_id,
                task_name=task_detail.get('task_name'),
                task_type=task_detail.get('task_type'),
                task_assignee=task_detail.get('task_assignee'),
                task_status='pending',
                round_id=response_round_id
            )
            db.session.add(task)
            created_task_ids.append(new_task_id)
        
        event_name_from_llm = parsed_response.get('event_name', event.event_name)
        if event_name_from_llm and event_name_from_llm != event.event_name:
            event.event_name = event_name_from_llm
        
        # For tasks, the event might not be 'completed' yet, but perhaps 'tasks_assigned' or remains 'processing'
        # The plan implies Captain might mark event 'completed' if LLM says MISSION_COMPLETE
        # If tasks are assigned, event status should reflect that.
        # For now, we assume no status change here, tasks are just created.
        db.session.commit() # Commit tasks and potential event_name change
        logger.info(f"为事件 {event.event_id} 创建了 {len(created_task_ids)} 个任务: {created_task_ids}")
        
        # Optional: Send a specific message about task creation if llm_response message is not sufficient

    elif response_type == 'MISSION_COMPLETE':
        event.event_status = 'completed' # Captain decides event is completed based on LLM
        db.session.commit()
        logger.info(f"事件 {event.event_id} 已被Captain标记为 'completed' 基于 LLM 响应.")
        # Send a message about event completion
        completion_content = {"text": f"事件 {event.event_id} ({event.event_name}) 已由AI指挥官分析并标记为完成。", "details": parsed_response.get('response_text')}
        db_message_completed = create_standard_message(
            event_id=event.event_id,
            message_from='_captain',
            round_id=response_round_id,
            message_type='event_completed_by_captain',
            content_data=completion_content
        )
        if db_message_completed and publisher:
            try:
                routing_key = f"notifications.frontend.{db_message_completed.event_id}.{db_message_completed.message_from}.{db_message_completed.message_type}"
                publisher.publish_message(message_body=db_message_completed.to_dict(), routing_key=routing_key)
                logger.info(f"消息 [Event Completed] {db_message_completed.message_id} 已发布到 RabbitMQ. RK: {routing_key}")
            except Exception as e_pub:
                logger.error(f"发布消息 [Event Completed] {db_message_completed.message_id} 到 RabbitMQ 失败: {e_pub}")

    elif response_type == 'ROGER': # This seems like an error or simple ack from LLM
        event.event_status = 'error_from_llm' # Or a more specific status
        db.session.commit()
        error_text = parsed_response.get('response_text', 'AI指挥官返回确认信息，但未分配任务或完成事件。')
        logger.error(f"事件 {event.event_id} 处理中，LLM 返回 'ROGER': {error_text}")
        # Send a message about this 'ROGER' state
        roger_content = {"text": f"AI指挥官针对事件 {event.event_id} 的分析响应: {error_text}", "details": parsed_response}
        db_message_roger = create_standard_message(
            event_id=event.event_id,
            message_from='_captain',
            round_id=response_round_id,
            message_type='llm_roger_response',
            content_data=roger_content
        )
        if db_message_roger and publisher:
            try:
                routing_key = f"notifications.frontend.{db_message_roger.event_id}.{db_message_roger.message_from}.{db_message_roger.message_type}"
                publisher.publish_message(message_body=db_message_roger.to_dict(), routing_key=routing_key)
                logger.info(f"消息 [LLM Roger] {db_message_roger.message_id} 已发布到 RabbitMQ. RK: {routing_key}")
            except Exception as e_pub:
                logger.error(f"发布消息 [LLM Roger] {db_message_roger.message_id} 到 RabbitMQ 失败: {e_pub}")
    else:
        logger.warning(f"未知的LLM response_type '{response_type}' for event {event.event_id}")
        # Potentially send a generic notification for unknown response types

def run_captain():
    """运行Captain服务"""
    logger.info("启动Captain服务...")
    
    from main import app # For app_context
    
    publisher = None
    try:
        publisher = RabbitMQPublisher() # Initialize publisher
        logger.info("RabbitMQ Publisher for Captain initialized.")
        
        with app.app_context(): # Ensure DB operations are within app context
            while True:
                try:
                    event = get_events_to_process()
                    if event:
                        process_event(event, publisher) # Pass publisher to process_event
                        # 每处理完一个事件后提交/回滚一次，确保事务结束，释放行锁，下一轮查询能看到最新数据
                        try:
                            db.session.commit()
                        except Exception as loop_commit_err:
                            logger.error(f"Captain 主循环提交事务失败: {loop_commit_err}")
                            db.session.rollback()
                    else:
                        # logger.debug("Captain: 没有待处理事件，等待中...") # reduce noise
                        # 如果本轮没有事件，也显式地回滚事务，避免长事务导致快照不可见
                        db.session.rollback()
                        time.sleep(5)
                except pika.exceptions.AMQPConnectionError as amqp_err:
                    logger.error(f"Captain服务 RabbitMQ连接错误: {amqp_err}. Publisher 会尝试重连。")
                    # Publisher has internal retries for connect and publish, 
                    # so we might just sleep and let the loop continue for it to retry.
                    time.sleep(10) # Wait before next cycle if major MQ error
                except Exception as e:
                    logger.error(f"Captain服务在事件处理循环中发生错误: {e}")
                    logger.error(traceback.format_exc())
                    time.sleep(5) # Wait a bit before retrying the loop
                    
    except pika.exceptions.AMQPConnectionError as amqp_startup_err:
        logger.critical(f"Captain服务启动失败：无法连接到RabbitMQ. 请检查RabbitMQ服务和配置. Error: {amqp_startup_err}")
        logger.critical(traceback.format_exc())
        # Service cannot run without MQ, so exiting or stopping might be an option here
        # For now, it will just log and terminate if __name__ == '__main__' or if called directly.
    except Exception as e_startup:
        logger.critical(f"Captain服务启动时发生未知严重错误: {e_startup}")
        logger.critical(traceback.format_exc())
    finally:
        if publisher:
            logger.info("Captain服务正在关闭RabbitMQ publisher...")
            publisher.close()
        logger.info("Captain服务已停止。")

# This allows running the service independently for testing if needed
# However, typically it's run via main.py -role _captain
# if __name__ == '__main__':
#     # Basic logging config for direct run testing
#     logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
#     run_captain()
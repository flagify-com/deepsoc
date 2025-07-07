import time
import uuid
import json
import traceback
from datetime import datetime
from sqlalchemy import func
from app.models import db, Event, Task, Action, Message
from app.services.llm_service import call_llm, parse_yaml_response
from app.services.prompt_service import PromptService
from app.utils.message_utils import create_standard_message
from app.utils.mq_utils import RabbitMQPublisher
import pika
import yaml
import logging
logger = logging.getLogger(__name__)


def get_pending_tasks():
    """获取待处理的任务，按照event_id和round_id分组
    
    Returns:
        字典，键为(event_id, round_id)元组，值为该组的任务列表
    """
    pending_tasks = Task.query.filter_by(task_status='pending').order_by(Task.created_at.asc()).all()
    grouped_tasks = {}
    for task in pending_tasks:
        key = (task.event_id, task.round_id)
        if key not in grouped_tasks:
            grouped_tasks[key] = []
        grouped_tasks[key].append(task)
    return grouped_tasks

def process_task_group(event_id, round_id, tasks, publisher: RabbitMQPublisher):
    """处理一组任务
    
    Args:
        event_id: 事件ID
        round_id: 轮次ID
        tasks: 任务列表
        publisher: RabbitMQPublisher instance
    """
    logger.info(f"处理事件 {event_id} 轮次 {round_id} 的任务组，共 {len(tasks)} 个任务")
    event = Event.query.filter_by(event_id=event_id).first()
    if not event:
        logger.error(f"事件 {event_id} 不存在，无法处理任务组.")
        # Potentially update task statuses to error or requeue if applicable
        for task_item in tasks:
            task_item.task_status = 'error_event_not_found'
        db.session.commit()
        return

    tasks_data = []
    for task in tasks:
        tasks_data.append({
            'task_id': task.task_id,
            'task_name': task.task_name,
            'task_type': task.task_type
        })

    request_data = {
        'type': 'generate_actions_by_tasks',
        'req_id': str(uuid.uuid4()),
        'res_id': str(uuid.uuid4()),
        'event_id': event_id,
        'event_round': round_id,
        'event_name': event.event_name,
        'event_message': event.message,
        'tasks': tasks_data
    }
    yaml_data = yaml.dump(request_data, allow_unicode=True, default_flow_style=False, indent=2)

    user_prompt = f"""```yaml
{yaml_data}
```

分析来自`_captain`的任务要求，生成可供`_operator`操作的具体的`ACTION`。
"""
    logger.info(f"Manager User prompt for event {event_id}, round {round_id}:\n{user_prompt}")
    logger.info("--------------------------------")
    
    prompt_service = PromptService('_manager')
    system_prompt = prompt_service.get_system_prompt()
    logger.info(f"请求大模型进行任务分解：事件 {event_id} - 轮次 {round_id}")
    
    # 消息1: LLM 请求通知
    llm_req_content = {"text": f"安全经理正在请求大模型分析任务(Event: {event_id}, Round: {round_id})并拆分为具体行动。"}
    db_message_llm_req = create_standard_message(
        event_id=event_id,
        message_from='system', # Or '_manager' if manager initiates
        round_id=round_id,
        message_type='manager_llm_request',
        content_data=llm_req_content
    )
    if db_message_llm_req and publisher:
        try:
            routing_key = f"notifications.frontend.{db_message_llm_req.event_id}.{db_message_llm_req.message_from}.{db_message_llm_req.message_type}"
            publisher.publish_message(message_body=db_message_llm_req.to_dict(), routing_key=routing_key)
            logger.info(f"消息 [Manager LLM Req] {db_message_llm_req.message_id} 已发布到 RabbitMQ. RK: {routing_key}")
        except Exception as e_pub:
            logger.error(f"发布消息 [Manager LLM Req] {db_message_llm_req.message_id} 到 RabbitMQ 失败: {e_pub}")
            logger.error(traceback.format_exc())

    response = call_llm(system_prompt, user_prompt)
    logger.info(f"Manager LLM Response for event {event_id}, round {round_id}:\n{response}")
    logger.info("--------------------------------")
    
    parsed_response = parse_yaml_response(response)
    if not parsed_response:
        logger.error(f"Manager解析LLM响应失败 for event {event_id}: {response}")
        error_content = {"text": "安全经理未能正确解析LLM响应数据，请检查日志。", "original_response": response}
        db_message_parse_err = create_standard_message(
            event_id=event_id, message_from='_manager',
            round_id=round_id, message_type='error_internal',
            content_data=error_content
        )
        if db_message_parse_err and publisher:
            try:
                routing_key = f"notifications.frontend.{db_message_parse_err.event_id}.{db_message_parse_err.message_from}.{db_message_parse_err.message_type}"
                publisher.publish_message(message_body=db_message_parse_err.to_dict(), routing_key=routing_key)
                logger.info(f"消息 [Manager LLM Parse Err] {db_message_parse_err.message_id} 已发布到 RabbitMQ. RK: {routing_key}")
            except Exception as e_pub:
                logger.error(f"发布消息 [Manager LLM Parse Err] {db_message_parse_err.message_id} 到 RabbitMQ 失败: {e_pub}")
        # Update task statuses to error
        for task_item in tasks:
            task_item.task_status = 'error_llm_parse'
        db.session.commit()
        return
    
    # 消息2: LLM 响应内容通知
    db_message_llm_resp = create_standard_message(
        event_id=event_id,
        message_from='_manager',
        round_id=round_id, # Assuming LLM response for manager aligns with current round
        message_type='manager_llm_response',
        content_data=parsed_response
    )
    if db_message_llm_resp and publisher:
        try:
            routing_key = f"notifications.frontend.{db_message_llm_resp.event_id}.{db_message_llm_resp.message_from}.{db_message_llm_resp.message_type}"
            publisher.publish_message(message_body=db_message_llm_resp.to_dict(), routing_key=routing_key)
            logger.info(f"消息 [Manager LLM Resp] {db_message_llm_resp.message_id} 已发布到 RabbitMQ. RK: {routing_key}")
        except Exception as e_pub:
            logger.error(f"发布消息 [Manager LLM Resp] {db_message_llm_resp.message_id} 到 RabbitMQ 失败: {e_pub}")
            logger.error(traceback.format_exc()) # Log full traceback for publish errors
    
    process_manager_response(parsed_response, tasks, publisher, event_id, round_id)

def process_manager_response(response, tasks, publisher: RabbitMQPublisher, event_id: str, round_id: int):
    """处理管理员响应，创建动作，并发送相关通知
    
    Args:
        response: 解析后的响应对象
        tasks: 任务列表
        publisher: RabbitMQPublisher instance
        event_id: current event_id for messaging
        round_id: current round_id for messaging
    """
    response_type = response.get('response_type')
    if response_type == 'ACTION':
        actions_data = response.get('actions', [])
        created_action_ids = []
        for action_detail in actions_data:
            task_id = action_detail.get('task_id')
            task = next((t for t in tasks if t.task_id == task_id), None)
            if not task:
                logger.error(f"任务 {task_id} (来自LLM action) 在提供的任务列表中未找到。跳过此action。LLM Response: {action_detail}")
                # Send an error message to frontend about this mismatch
                error_content = {"text": f"安全经理AI尝试为不存在的任务 {task_id} 创建行动，请检查LLM配置或响应。", "details": action_detail}
                db_message_action_err = create_standard_message(
                    event_id=event_id, message_from='_manager', round_id=round_id,
                    message_type='error_action_creation', content_data=error_content)
                if db_message_action_err and publisher:
                    try:
                        routing_key = f"notifications.frontend.{db_message_action_err.event_id}.{db_message_action_err.message_from}.{db_message_action_err.message_type}"
                        publisher.publish_message(message_body=db_message_action_err.to_dict(), routing_key=routing_key)
                    except Exception as e_pub_err: logger.error(f"发布 Action创建错误消息失败: {e_pub_err}")
                continue
            
            new_action_id = str(uuid.uuid4())
            action = Action(
                action_id=new_action_id,
                task_id=task.task_id,
                event_id=task.event_id,
                round_id=task.round_id,
                action_name=action_detail.get('action_name', ''),
                action_type=action_detail.get('action_type', ''),
                action_assignee=action_detail.get('action_assignee', '_operator'),
                action_status='pending'
            )
            db.session.add(action)
            task.task_status = 'processing' # Mark task as processing since actions are created
            created_action_ids.append(new_action_id)
            
            # 消息3: 新 Action 创建通知
            action_created_content = {"text": f"安全经理已为任务 {task.task_name} (ID: {task.task_id}) 创建新行动: {action.action_name} (ID: {action.action_id})。", "action_details": action.to_dict()}
            db_message_action_new = create_standard_message(
                event_id=action.event_id, message_from='_manager',
                round_id=action.round_id, message_type='action_created',
                content_data=action_created_content
            )
            if db_message_action_new and publisher:
                try:
                    routing_key = f"notifications.frontend.{db_message_action_new.event_id}.{db_message_action_new.message_from}.{db_message_action_new.message_type}"
                    publisher.publish_message(message_body=db_message_action_new.to_dict(), routing_key=routing_key)
                    logger.info(f"消息 [Action Created] {db_message_action_new.message_id} 已发布. RK: {routing_key}")
                except Exception as e_pub_new_action:
                    logger.error(f"发布新Action消息失败 for {db_message_action_new.message_id}: {e_pub_new_action}")
                    logger.error(traceback.format_exc())
        
        if created_action_ids:
            db.session.commit()
            logger.info(f"为事件 {event_id} 轮次 {round_id} 创建了 {len(created_action_ids)} 个动作: {created_action_ids}")
        else:
            logger.warning(f"LLM响应类型为ACTION，但未提供有效actions数据或未能匹配任务。Event: {event_id}, Round: {round_id}")
    else:
        logger.warning(f"Manager LLM未返回预期的ACTION响应类型，而是: {response_type}. Event: {event_id}, Round: {round_id}")
        # Send a message about unexpected LLM response type
        unexpected_resp_content = {"text": f"安全经理AI返回了未知的响应类型: {response_type}。", "llm_response": response}
        db_message_unexpected = create_standard_message(
            event_id=event_id, message_from='_manager', round_id=round_id,
            message_type='llm_unexpected_response', content_data=unexpected_resp_content)
        if db_message_unexpected and publisher:
            try:
                routing_key = f"notifications.frontend.{db_message_unexpected.event_id}.{db_message_unexpected.message_from}.{db_message_unexpected.message_type}"
                publisher.publish_message(message_body=db_message_unexpected.to_dict(), routing_key=routing_key)
            except Exception as e_pub_unexp: logger.error(f"发布LLM意外响应类型消息失败: {e_pub_unexp}")

def run_manager():
    """运行_manager服务"""
    logger.info("启动_manager服务...")
    from main import app # For app_context

    publisher = None
    try:
        publisher = RabbitMQPublisher()
        logger.info("RabbitMQ Publisher for Manager initialized.")

        with app.app_context():
            while True:
                try:
                    grouped_tasks = get_pending_tasks()
                    if grouped_tasks:
                        logger.info(f"Manager发现 {len(grouped_tasks)} 组待处理任务")
                        for (event_id, round_id), tasks in grouped_tasks.items():
                            process_task_group(event_id, round_id, tasks, publisher)
                        # 任务处理完成后提交，以结束事务和释放锁
                        try:
                            db.session.commit()
                        except Exception as loop_commit_err:
                            logger.error(f"Manager 主循环提交事务失败: {loop_commit_err}")
                            db.session.rollback()
                    else:
                        # logger.debug("Manager: 没有待处理任务，等待中...")
                        # 本轮无任务也回滚，避免长事务持有快照
                        db.session.rollback()
                        time.sleep(5)
                except pika.exceptions.AMQPConnectionError as amqp_err:
                    logger.error(f"Manager服务 RabbitMQ连接错误: {amqp_err}. Publisher会尝试重连。")
                    time.sleep(10) 
                except Exception as e:
                    logger.error(f"Manager服务在任务处理循环中发生错误: {e}")
                    logger.error(traceback.format_exc())
                    time.sleep(5)

    except pika.exceptions.AMQPConnectionError as amqp_startup_err:
        logger.critical(f"Manager服务启动失败：无法连接到RabbitMQ. Error: {amqp_startup_err}")
        logger.critical(traceback.format_exc())
    except Exception as e_startup:
        logger.critical(f"Manager服务启动时发生未知严重错误: {e_startup}")
        logger.critical(traceback.format_exc())
    finally:
        if publisher:
            logger.info("Manager服务正在关闭RabbitMQ publisher...")
            publisher.close()
        logger.info("Manager服务已停止。")

# if __name__ == '__main__':
#     logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
#     run_manager() 
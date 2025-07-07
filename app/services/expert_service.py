import time
import uuid
import json
import traceback
import threading
from datetime import datetime
from flask import current_app
from sqlalchemy import func, and_, or_
from app.models import db, Event, Task, Action, Command, Execution, Summary, Message
from app.services.llm_service import call_llm, parse_yaml_response
from app.services.prompt_service import PromptService
from app.config import config
from app.utils.message_utils import create_standard_message
from app.utils.mq_utils import RabbitMQPublisher
import pika
import logging
import yaml

logger = logging.getLogger(__name__)

def get_executions_for_summarization():
    """获取需要生成摘要的执行结果
    
    Returns:
        需要生成摘要的执行结果列表
    """
    # 查询所有completed状态的执行
    # 在新的状态流转逻辑中，completed状态表示执行已完成但尚未生成摘要
    # 生成摘要后状态会更新为summarized
    completed_executions = Execution.query.filter(
        Execution.execution_status.in_(['completed'])
    ).order_by(Execution.created_at.asc()).all()
    
    if completed_executions:
        logger.info(f"找到 {len(completed_executions)} 个completed状态的执行结果需要生成摘要")
    
    return completed_executions

def process_execution_summary(execution: Execution, publisher: RabbitMQPublisher):
    """处理单个执行结果，生成摘要, 并触发后续状态更新检查
    
    Args:
        execution: 执行对象
        publisher: RabbitMQPublisher instance
    """
    logger.info(f"处理执行结果摘要: {execution.execution_id} (Event: {execution.event_id}, Command: {execution.command_id})")
    original_status = execution.execution_status
    
    try:
        # 获取执行结果
        execution_result = execution.execution_result
        if not execution_result:
            logger.warning(f"执行结果为空: {execution.execution_id}")
            execution.ai_summary = "执行结果为空，无法生成AI摘要。"
            execution.execution_status = 'summarized_error' # Consistent error status
            return # Return early, but commit will happen in finally
        
        # 如果执行结果是字符串（JSON字符串），则解析为对象
        if isinstance(execution_result, str):
            try:
                execution_result = json.loads(execution_result)
            except json.JSONDecodeError:
                pass
        
        # 获取关联的命令、动作和任务信息
        command = Command.query.filter_by(command_id=execution.command_id).first()
        action = Action.query.filter_by(action_id=execution.action_id).first() if execution.action_id else None
        task = Task.query.filter_by(task_id=execution.task_id).first() if execution.task_id else None
        
        # 构建上下文信息
        context = {
            "execution_id": execution.execution_id,
            "command_id": execution.command_id,
            "command_name": command.command_name if command else "未知命令",
            "command_type": command.command_type if command else "未知类型",
            "action_id": execution.action_id,
            "action_name": action.action_name if action else "未知动作",
            "task_id": execution.task_id,
            "task_name": task.task_name if task else "未知任务",
            "event_id": execution.event_id,
            "round_id": execution.round_id,
            "execution_status": original_status, # Use original status for context
            "execution_result": execution_result,
            "req_id": str(uuid.uuid4()),
            "res_id": str(uuid.uuid4())
        }
        
        # 将上下文转换为JSON格式
        yaml_context = yaml.dump(context, allow_unicode=True, default_flow_style=False, indent=2)

        # 构建系统提示词
        system_prompt = """
        你是一个经验丰富的安全专家，擅长从执行结果中提取关键信息，并用精炼的文字生成适合人类阅读的文本。
        请不要做总结评论，只保留客观结果。
        """
        
        # 构建用户提示词
        user_prompt = f"""
            ```yaml
            {yaml_context}
            ```
            以上是基于_caption的任务安排，和_manager的动作细化，以及_operator的命令设置，通过SOAR安全之剧本执行的返回结果。
            当然也有可能是，人类工程师在页面手工完成的处置结果。
            请从信息提炼的角度，帮我提取关键信息，作客观结果的保留，不需要做总结评论。
            简单地说，就是告诉我剧本做了什么，得到了什么结果，不窜改，不臆造。
            """
        
        # 调用大模型生成摘要
        prompt_service = PromptService('_expert')
        # 使用自定义系统提示词
        # system_prompt = prompt_service.get_system_prompt()

        logger.info(f"生成摘要: {execution.execution_id}")
        db_msg_llm_req = create_standard_message(
            event_id=execution.event_id,
            message_from='system',
            round_id=execution.round_id,
            message_type='expert_llm_request_exec_summary',
            content_data={"text": f"专家智能正在为执行 {execution.execution_id} 的结果生成摘要..."}
        )
        if db_msg_llm_req and publisher:
            try:
                routing_key = f"notifications.frontend.{db_msg_llm_req.event_id}.system.{db_msg_llm_req.message_type}"
                publisher.publish_message(message_body=db_msg_llm_req.to_dict(), routing_key=routing_key)
            except Exception as e_pub:
                logger.error(f"发布专家LLM请求执行摘要消息失败: {e_pub}")
        
        # 使用长文本模型
        response = call_llm(system_prompt, user_prompt, temperature=0.3, long_text=True)
        
        logger.info(f"生成摘要成功: {execution.execution_id}")
        
        # 更新执行结果的摘要字段
        execution.ai_summary = response
        
        # 更新执行结果状态为已总结
        execution.execution_status = 'summarized'
        
        create_execution_summary_message(execution, response, publisher)
        
    except Exception as e:
        error_msg = f"处理执行结果摘要时出错: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        execution.ai_summary = f"生成AI摘要时出错: {error_msg}"
        execution.execution_status = 'summarized_error' # Consistent error status

        err_summary_content = {
            "execution_id": execution.execution_id,
            "command_id": execution.command_id if execution.command_id else "N/A",
            "error_message": error_msg,
            "text": f"为执行 {execution.execution_id} 生成摘要时失败。"
        }
        db_msg_summary_err = create_standard_message(
            event_id=execution.event_id, message_from='_expert',
            round_id=execution.round_id, message_type='error_execution_summary',
            content_data=err_summary_content
        )
        if db_msg_summary_err and publisher:
            try:
                routing_key = f"notifications.frontend.{db_msg_summary_err.event_id}._expert.{db_msg_summary_err.message_type}"
                publisher.publish_message(message_body=db_msg_summary_err.to_dict(), routing_key=routing_key)
            except Exception as e_pub_err:
                logger.error(f"发布执行摘要错误消息失败: {e_pub_err}")
    finally:
        # Ensure status is committed and then trigger command status update
        try:
            db.session.commit() 
            logger.info(f"Execution {execution.execution_id} status updated to {execution.execution_status}. Triggering command status check.")
            _check_and_update_command_status(execution.command_id, publisher)
        except Exception as e_final:
            logger.error(f"Error in finally block of process_execution_summary for {execution.execution_id}: {e_final}")
            db.session.rollback()

def _check_and_update_command_status(command_id: str, publisher: RabbitMQPublisher):
    """
    Checks all executions for a command. If all are finalized (summarized, summarized_error, failed),
    updates the command's status. If command is finalized, triggers action status check.
    Uses pessimistic locking for command update.
    """
    if not command_id:
        logger.warning("_check_and_update_command_status: command_id is None. Skipping.")
        return

    logger.debug(f"Checking command status for Command ID: {command_id}")
    try:
        db.session.expire_all() # Ensure fresh data
        command = db.session.query(Command).with_for_update().filter_by(command_id=command_id).first()

        if not command:
            logger.warning(f"Command {command_id} not found for status update.")
            return

        if command.command_status in ['completed', 'failed']:
            logger.info(f"Command {command_id} already in a final state: {command.command_status}. Skipping.")
            # Release the row lock before propagating upwards
            db.session.commit()
            if command.action_id:
                 _check_and_update_action_status(command.action_id, publisher)
            return

        executions = Execution.query.filter_by(command_id=command_id).all()
        if not executions:
            logger.warning(f"No executions found for command {command_id}. Cannot determine command status. Setting to 'failed'.")
            command.command_status = 'failed' # Or 'pending' if no executions means it hasn't started. 'failed' if executions were expected.
            # Let's assume 'failed' if it was supposed to have executions.
            # If a command has no executions it implies an issue.
            # Alternatively, could leave as 'pending' or 'processing' if that makes more sense contextually.
            # For now, 'failed' seems a safe default if it's in a state expecting executions.
            # A command should not reach here without executions if it was 'processing'.
        else:
            all_executions_finalized = True
            has_any_execution_failed = False
            for ex in executions:
                if ex.execution_status not in ['summarized', 'summarized_error', 'failed']:
                    all_executions_finalized = False
                    break
                if ex.execution_status in ['summarized_error', 'failed']:
                    has_any_execution_failed = True
            
            if all_executions_finalized:
                if has_any_execution_failed:
                    command.command_status = 'failed'
                else:
                    command.command_status = 'completed'
            else:
                # Still processing, no status change for command yet
                logger.debug(f"Command {command_id} has non-finalized executions. Status remains {command.command_status}.")
                db.session.commit() # Commit any changes from with_for_update even if status doesn't change (e.g. lock release)
                return 

        db.session.commit()
        logger.info(f"Command {command_id} status updated to {command.command_status}.")

        # Propagate to Action
        if command.command_status in ['completed', 'failed'] and command.action_id:
            _check_and_update_action_status(command.action_id, publisher)
        elif not command.action_id:
             logger.warning(f"Command {command_id} does not have an action_id. Cannot propagate status upwards from command.")


    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in _check_and_update_command_status for {command_id}: {e}")
        logger.error(traceback.format_exc())

def _check_and_update_action_status(action_id: str, publisher: RabbitMQPublisher):
    """
    Checks all commands for an action. If all are finalized (completed, failed),
    updates the action's status. If action is finalized, triggers task status check.
    Uses pessimistic locking for action update.
    """
    if not action_id:
        logger.warning("_check_and_update_action_status: action_id is None. Skipping.")
        return

    logger.debug(f"Checking action status for Action ID: {action_id}")
    try:
        db.session.expire_all()
        action = db.session.query(Action).with_for_update().filter_by(action_id=action_id).first()

        if not action:
            logger.warning(f"Action {action_id} not found for status update.")
            return

        if action.action_status in ['completed', 'failed']:
            logger.info(f"Action {action_id} already in a final state: {action.action_status}. Skipping.")
            db.session.commit()  # release lock before propagating
            if action.task_id:  # Ensure task check is still triggered if action is final
                _check_and_update_task_status(action.task_id, publisher)
            return

        commands = Command.query.filter_by(action_id=action_id).all()
        if not commands:
            logger.warning(f"No commands found for action {action_id}. Cannot determine action status. Setting to 'failed'.")
            action.action_status = 'failed' # Similar logic to command with no executions
        else:
            all_commands_finalized = True
            has_any_command_failed = False
            for cmd in commands:
                if cmd.command_status not in ['completed', 'failed']:
                    all_commands_finalized = False
                    break
                if cmd.command_status == 'failed':
                    has_any_command_failed = True
            
            if all_commands_finalized:
                if has_any_command_failed:
                    action.action_status = 'failed'
                else:
                    action.action_status = 'completed'
            else:
                logger.debug(f"Action {action_id} has non-finalized commands. Status remains {action.action_status}.")
                db.session.commit()
                return

        db.session.commit()
        logger.info(f"Action {action_id} status updated to {action.action_status}.")

        # Propagate to Task
        if action.action_status in ['completed', 'failed'] and action.task_id:
            _check_and_update_task_status(action.task_id, publisher)
        elif not action.task_id:
            logger.warning(f"Action {action_id} does not have a task_id. Cannot propagate status upwards from action.")

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in _check_and_update_action_status for {action_id}: {e}")
        logger.error(traceback.format_exc())

def _check_and_update_task_status(task_id: str, publisher: RabbitMQPublisher):
    """
    Checks all actions (or commands if no actions) for a task. If all are finalized,
    updates the task's status. If task is finalized, triggers event round evaluation.
    Uses pessimistic locking for task update.
    """
    if not task_id:
        logger.warning("_check_and_update_task_status: task_id is None. Skipping.")
        return

    logger.debug(f"Checking task status for Task ID: {task_id}")
    try:
        db.session.expire_all()
        task = db.session.query(Task).with_for_update().filter_by(task_id=task_id).first()

        if not task:
            logger.warning(f"Task {task_id} not found for status update.")
            return

        if task.task_status in ['completed', 'failed']:
            logger.info(f"Task {task_id} already in a final state: {task.task_status}. Skipping further event round evaluation trigger from this path.")
            # Previously, we still triggered event round evaluation here.
            # By removing it, we reduce redundant calls to check_and_update_event_tasks_completion,
            # potentially alleviating lock contention. The event_lifecycle_manager_worker
            # should eventually pick up the event if it needs further state changes based on task completion.
            # _trigger_event_round_evaluation(task.event_id, task.round_id, publisher)
            db.session.commit() # Commit to release lock if acquired by with_for_update
            return
        
        actions = Action.query.filter_by(task_id=task_id).all()
        if not actions:
             # This case should ideally not happen if actions are always part of the flow.
             # If it does, means all commands must be checked directly under the task, which is not the current model.
             # For now, if no actions, we assume the task cannot be completed this way.
            logger.warning(f"No actions found for task {task_id}. Cannot determine task status based on actions. Assuming 'failed' or needs review.")
            task.task_status = 'failed' # Or some other indeterminate status
        else:
            all_actions_finalized = True
            has_any_action_failed = False
            for act in actions:
                if act.action_status not in ['completed', 'failed']:
                    all_actions_finalized = False
                    break
                if act.action_status == 'failed':
                    has_any_action_failed = True
            
            if all_actions_finalized:
                if has_any_action_failed:
                    task.task_status = 'failed'
                else:
                    task.task_status = 'completed'
            else:
                logger.debug(f"Task {task_id} has non-finalized actions. Status remains {task.task_status}.")
                db.session.commit()
                return

        db.session.commit()
        logger.info(f"Task {task_id} status updated to {task.task_status}.")

        # Propagate to Event Round Evaluation
        if task.task_status in ['completed', 'failed']:
            _trigger_event_round_evaluation(task.event_id, task.round_id, publisher)

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in _check_and_update_task_status for {task_id}: {e}")
        logger.error(traceback.format_exc())

def _trigger_event_round_evaluation(event_id: str, round_id: int, publisher: RabbitMQPublisher):
    """
    Called when a task's status is finalized. This function will invoke
    check_and_update_event_tasks_completion, which is now responsible for checking
    if all tasks (and their underlying executions) for the current event round are done,
    and then updating the event status to 'tasks_completed' or 'failed'.
    The event_lifecycle_manager_worker will then pick up 'tasks_completed' events.
    """
    if not event_id or round_id is None:
        logger.warning(f"_trigger_event_round_evaluation: Invalid event_id ({event_id}) or round_id ({round_id}). Skipping.")
        return

    logger.info(f"Triggering event round evaluation for Event ID: {event_id}, Round: {round_id}")
    try:
        # check_and_update_event_tasks_completion handles its own db session and locking
        # It will determine if the event round is complete and update event status.
        # The publisher might be needed by check_and_update_event_tasks_completion for notifications.
        status_changed = check_and_update_event_tasks_completion(event_id, round_id, publisher)
        if status_changed:
            logger.info(f"Event {event_id} round {round_id} evaluation resulted in a status change.")
        else:
            logger.info(f"Event {event_id} round {round_id} evaluation did not result in a status change (or event not ready).")

    except Exception as e:
        # db.session.rollback() # check_and_update_event_tasks_completion should manage its own rollback on error
        logger.error(f"Error in _trigger_event_round_evaluation for Event {event_id}, Round {round_id}: {e}")
        logger.error(traceback.format_exc())

def check_and_update_event_tasks_completion(event_id, round_id, publisher: RabbitMQPublisher):
    """
    Checks if all tasks for a given event and round are completed or failed,
    AND all their underlying executions are also finalized (summarized, summarized_error, or failed).
    If so, updates the event status to 'tasks_completed' or 'failed' (if any task/execution failed).
    This function is called by _trigger_event_round_evaluation.
    Uses pessimistic locking for event update.

    Returns:
        bool: True if the event status was changed, False otherwise.
    """
    db.session.expire_all() # Ensure fresh data
    logger.debug(f"check_and_update_event_tasks_completion for Event {event_id}, Round {round_id}")

    # 使用 skip_locked 避免等待已被其他事务锁定的行，减少锁等待超时
    # MySQL 8.0+ 支持 SKIP LOCKED；如果您的 MySQL 版本较低，可改用 NOWAIT 并捕获异常重试
    try:
        event = db.session.query(Event).with_for_update(skip_locked=True).filter_by(event_id=event_id).first()
    except Exception as lock_err:
        # 如果数据库不支持 skip_locked 或出现其他问题，则记录并返回 False，等待下一轮处理
        logger.warning(f"check_and_update_event_tasks_completion: 获取 Event 行锁失败 (event_id={event_id}): {lock_err}")
        db.session.rollback()
        return False

    if not event:
        logger.warning(f"check_and_update_event_tasks_completion: Event {event_id} not found.")
        return False
    
    # Only proceed if the event is currently in 'processing' state.
    if event.event_status != 'processing':
        logger.info(f"check_and_update_event_tasks_completion: Event {event_id} status is '{event.event_status}', not 'processing'. Skipping update.")
        db.session.commit()  # release lock obtained by with_for_update
        return False

    # Fetch all tasks for the current event and round.
    tasks_for_round = Task.query.filter_by(event_id=event_id, round_id=round_id).all()

    if not tasks_for_round:
        logger.warning(f"check_and_update_event_tasks_completion: No tasks found for Event {event_id}, Round {round_id}. Cannot determine completion. Assuming round is not completable if tasks were expected.")
        db.session.commit()  # release lock
        return False

    all_tasks_finalized = True
    any_task_failed = False
    for task in tasks_for_round:
        if task.task_status not in ['completed', 'failed']:
            all_tasks_finalized = False
            logger.debug(f"Event {event_id} R{round_id}: Task {task.task_id} is {task.task_status}. Tasks not all finalized.")
            break
        if task.task_status == 'failed':
            any_task_failed = True
    
    if not all_tasks_finalized:
        db.session.commit()  # release lock
        return False  # Not all tasks are done yet.

    # All tasks are finalized (completed or failed).
    # Now, we need to ensure all EXECUTIONS under these tasks (via commands and actions) are also finalized.
    # The chained status updates (_check_and_update_command_status -> _check_and_update_action_status -> _check_and_update_task_status)
    # should mean that if a task is 'completed' or 'failed', its underlying commands/executions are already final.
    # So, an additional check for execution statuses here might be redundant if the chain is working correctly.
    # However, for defense, a quick check can be done.

    # Let's assume for now the task status accurately reflects the finality of its children.
    # The more critical check was done at each level of the chain.

    original_event_status = event.event_status
    new_event_status = ''

    if any_task_failed:
        new_event_status = 'failed' # If any task in the round failed, the event round (or event itself) might be considered failed.
                                   # The `event_lifecycle_manager_worker` should handle this 'failed' state appropriately.
    else:
        # All tasks completed successfully
        new_event_status = 'tasks_completed'

    changed = False
    if event.event_status != new_event_status:
        event.event_status = new_event_status
        changed = True
        logger.info(f"check_and_update_event_tasks_completion: Event {event_id} R{round_id} status updated from '{original_event_status}' to '{event.event_status}'.")
    else:
        logger.debug(f"check_and_update_event_tasks_completion: Event {event_id} R{round_id} status '{original_event_status}' remains unchanged (new status was also '{new_event_status}').")
    
    db.session.commit() # Commit changes and release lock
    return changed

def create_execution_summary_message(execution, summary_text, publisher: RabbitMQPublisher):
    """创建执行结果摘要消息"""
    content_data = {
        "execution_id": execution.execution_id,
        "command_id": execution.command_id,
        "action_id": execution.action_id,
        "task_id": execution.task_id,
        "ai_summary": summary_text
    }
    db_message = create_standard_message(
        event_id=execution.event_id,
        message_from='_expert',
        round_id=execution.round_id,
        message_type='execution_summary_generated', # Keep type specific
        content_data=content_data
    )
    if db_message and publisher:
        try:
            routing_key = f"notifications.frontend.{db_message.event_id}._expert.{db_message.message_type}"
            publisher.publish_message(message_body=db_message.to_dict(), routing_key=routing_key)
            logger.info(f"消息 [Exec Summary Gen] {db_message.message_id} 已发布. RK: {routing_key}")
        except Exception as e_pub:
            logger.error(f"发布执行摘要生成消息失败: {e_pub}")

def create_event_summary_message(event, summary_obj, publisher: RabbitMQPublisher):
    """创建事件总结消息"""
    content_data = {
        "event_id": event.event_id,
        "event_name": event.event_name,
        "event_status": event.event_status, # Reflects current status (e.g., 'summarized')
        "round_id": event.current_round,
        "summary_id": summary_obj.summary_id,
        "event_summary": summary_obj.event_summary,
        "event_suggestion": summary_obj.event_suggestion
    }
    db_message = create_standard_message(
        event_id=event.event_id,
        message_from='_expert',
        round_id=event.current_round,
        message_type='event_summary_generated', # Keep type specific
        content_data=content_data
    )
    if db_message and publisher:
        try:
            routing_key = f"notifications.frontend.{db_message.event_id}._expert.{db_message.message_type}"
            publisher.publish_message(message_body=db_message.to_dict(), routing_key=routing_key)
            logger.info(f"消息 [Event Summary Gen] {db_message.message_id} 已发布. RK: {routing_key}")
        except Exception as e_pub:
            logger.error(f"发布事件总结生成消息失败: {e_pub}")

# --- Worker thread for processing execution summaries ---
def execution_summary_worker(app, publisher: RabbitMQPublisher):
    """处理执行结果摘要的工作线程"""
    with app.app_context():
        logger.info("启动执行结果摘要处理线程 (execution_summary_worker)")
        while True:
            try:
                # 开始循环先回滚，确保使用最新快照，避免长事务
                db.session.rollback()
                db.session.expire_all() # Ensure fresh data if worker sleeps for long
                pending_executions = get_executions_for_summarization()
                if pending_executions:
                    # logger.info(f"ExecutionSummaryWorker: 发现 {len(pending_executions)} 个待处理的执行结果") # Reduced verbosity from get_executions... itself
                    for execution in pending_executions:
                        # Re-fetch execution inside the loop to ensure it's still 'completed'
                        # This helps avoid race conditions if another process/thread modifies it.
                        fresh_execution = Execution.query.filter_by(execution_id=execution.execution_id, execution_status='completed').first()
                        if fresh_execution:
                            process_execution_summary(fresh_execution, publisher)
                        else:
                            logger.info(f"ExecutionSummaryWorker: Execution {execution.execution_id} no longer 'completed' or not found. Skipping.")
                    time.sleep(1) # Shorter sleep if there was work
                else:
                    # Use configured interval, default if not set
                    sleep_duration = getattr(config, 'EXPERT_EXECUTION_SUMMARY_INTERVAL', 5)
                    time.sleep(sleep_duration)
            except pika.exceptions.AMQPConnectionError as amqp_err:
                logger.error(f"ExecutionSummaryWorker: RabbitMQ连接错误: {amqp_err}. Retrying in 10s.")
                time.sleep(10)
            except Exception as e:
                logger.error(f"ExecutionSummaryWorker: 处理执行结果摘要时出错: {str(e)}")
                logger.error(traceback.format_exc())
                sleep_duration_error = getattr(config, 'EXPERT_EXECUTION_SUMMARY_INTERVAL_ERROR', 15)
                time.sleep(sleep_duration_error) # Sleep on other errors

def event_lifecycle_manager_worker(app, publisher: RabbitMQPublisher):
    with app.app_context():
        logger.info("Starting Event Lifecycle Manager Worker...")
        sleep_interval = config.EXPERT_LIFECYCLE_INTERVAL or 7 
        max_sleep_interval = sleep_interval * 4 
        current_sleep = sleep_interval

        while True:
            try:
                # 先回滚，避免长事务快照
                db.session.rollback()
                db.session.expire_all() 
                did_work_in_cycle = False

                # 0. Check for 'processing' events whose tasks might be complete
                # This step ensures that if _trigger_event_round_evaluation was missed or if an event
                # is stuck in 'processing', we can re-evaluate it.
                # This is a more proactive check in the lifecycle manager itself.
                processing_events = Event.query.filter_by(event_status='processing').order_by(Event.updated_at.asc()).all()
                if processing_events:
                    logger.debug(f"LifecycleManager: Found {len(processing_events)} 'processing' events to check for task completion.")
                    for event in processing_events:
                        # Re-check if tasks are completed. check_and_update_event_tasks_completion handles locking.
                        status_changed = check_and_update_event_tasks_completion(event.event_id, event.current_round, publisher)
                        if status_changed:
                            logger.info(f"LifecycleManager: Proactive check for Event {event.event_id} R{event.current_round} resulted in status change (likely to 'tasks_completed' or 'failed').")
                            did_work_in_cycle = True
                            # After status change, re-fetch the event to get its new status for subsequent steps in this same cycle
                            # This avoids waiting for the next loop iteration if it moved to tasks_completed.
                            # db.session.expire(event) # Expire the specific event object
                            # event = Event.query.filter_by(event_id=event.event_id).first() # Re-fetch
                            # if not event: continue # Should not happen

                # 1. Process events where tasks are completed (status: 'tasks_completed')
                #    Action: Mark for summarization (status: 'to_be_summarized')
                # Re-query after the potential changes from step 0
                db.session.expire_all()
                events_tasks_completed = Event.query.filter_by(event_status='tasks_completed').order_by(Event.updated_at.asc()).all()
                if events_tasks_completed:
                    logger.info(f"LifecycleManager: Found {len(events_tasks_completed)} events with 'tasks_completed'.")
                    for event_tc in events_tasks_completed: # Use different var name
                        # Re-fetch with lock to prevent race condition before update
                        fresh_event_tc = db.session.query(Event).with_for_update().filter_by(event_id=event_tc.event_id, event_status='tasks_completed').first()
                        if fresh_event_tc:
                            fresh_event_tc.event_status = 'to_be_summarized'
                            db.session.commit()
                            logger.info(f"LifecycleManager: Event {fresh_event_tc.event_id} ({fresh_event_tc.event_name}) status updated 'tasks_completed' -> 'to_be_summarized'.")
                            did_work_in_cycle = True
                        else:
                            logger.debug(f"LifecycleManager: Event {event_tc.event_id} no longer 'tasks_completed' or disappeared before 'to_be_summarized' update.")
                
                # 2. Process events marked for summarization (status: 'to_be_summarized' or 'resolved')
                #    'resolved' also leads to a final summary.
                #    Action: Call generate_event_summary (which sets status to 'summarized' or 'summary_failed')
                db.session.expire_all()
                events_to_be_summarized = Event.query.filter(
                    or_(Event.event_status == 'to_be_summarized', Event.event_status == 'resolved')
                ).order_by(Event.updated_at.asc()).all()
                if events_to_be_summarized:
                    logger.info(f"LifecycleManager: Found {len(events_to_be_summarized)} events 'to_be_summarized' or 'resolved'.")
                    for event_tbs in events_to_be_summarized: # Use different var name
                        # generate_event_summary handles its own concurrency for LLM call and DB updates for summary object
                        # It also re-fetches event before final status update to 'summarized' or 'summary_failed'.
                        # It expects event status 'to_be_summarized'. For 'resolved', generate_event_summary should perhaps handle it.
                        # For now, generate_event_summary is called. It internally checks for 'to_be_summarized'.
                        # If event is 'resolved', generate_event_summary will log "事件状态不是to_be_summarized" and return.
                        # We need to ensure generate_event_summary can handle 'resolved' or we adjust logic here.

                        # Let's make generate_event_summary accept 'resolved' as a trigger for final summary.
                        # For now, assume generate_event_summary is robust or will be adapted.
                        
                        # Check status before calling to avoid unnecessary calls if it changed.
                        checked_event_tbs = Event.query.filter_by(event_id=event_tbs.event_id).filter(
                            or_(Event.event_status == 'to_be_summarized', Event.event_status == 'resolved')
                        ).first()

                        if checked_event_tbs:
                            logger.info(f"LifecycleManager: Event {checked_event_tbs.event_id} ({checked_event_tbs.event_name}, Status: {checked_event_tbs.event_status}) calling generate_event_summary.")
                            generate_event_summary(checked_event_tbs.event_id, publisher) # generate_event_summary needs to handle 'resolved' state properly
                            did_work_in_cycle = True 
                        else:
                            logger.debug(f"LifecycleManager: Event {event_tbs.event_id} no longer 'to_be_summarized'/'resolved' before calling generate_event_summary.")

                # 3. Process summarized events (status: 'summarized') or summary_failed events
                #    Action for 'summarized': Mark 'round_finished' or 'completed' (if max rounds)
                #    Action for 'summary_failed': Mark 'failed' (event failed)
                db.session.expire_all()
                events_summary_done_or_failed = Event.query.filter(
                    or_(Event.event_status == 'summarized', Event.event_status == 'summary_failed')
                ).order_by(Event.updated_at.asc()).all()

                if events_summary_done_or_failed:
                    logger.info(f"LifecycleManager: Found {len(events_summary_done_or_failed)} events 'summarized' or 'summary_failed'.")
                    for event_s_or_sf in events_summary_done_or_failed: # Use different var name
                        fresh_event_s_or_sf = db.session.query(Event).with_for_update().filter_by(event_id=event_s_or_sf.event_id).filter(
                             or_(Event.event_status == 'summarized', Event.event_status == 'summary_failed')
                        ).first()

                        if fresh_event_s_or_sf:
                            original_status_for_log = fresh_event_s_or_sf.event_status
                            if original_status_for_log == 'summarized':
                                if fresh_event_s_or_sf.current_round >= config.EVENT_MAX_ROUND:
                                    fresh_event_s_or_sf.event_status = 'completed'
                                else:
                                    # 安全解析 context 判断是否为人工解决
                                    context_dict = {}
                                    if fresh_event_s_or_sf.context:
                                        if isinstance(fresh_event_s_or_sf.context, dict):
                                            context_dict = fresh_event_s_or_sf.context
                                        elif isinstance(fresh_event_s_or_sf.context, str):
                                            try:
                                                context_dict = json.loads(fresh_event_s_or_sf.context)
                                            except Exception as ctx_err:
                                                logger.warning(f"LifecycleManager: 解析事件 context JSON 失败 (event={fresh_event_s_or_sf.event_id}): {ctx_err}")
                                    is_resolved_event = 'resolution_note' in context_dict
                                    
                                    if is_resolved_event:
                                        fresh_event_s_or_sf.event_status = 'completed'
                                        logger.info(f"LifecycleManager: Event {fresh_event_s_or_sf.event_id} was resolved and now summarized, setting to 'completed'.")
                                    else:
                                        fresh_event_s_or_sf.event_status = 'round_finished'

                            elif original_status_for_log == 'summary_failed':
                                fresh_event_s_or_sf.event_status = 'failed' # Event processing failed overall due to summary failure.
                            
                            db.session.commit()
                            logger.info(f"LifecycleManager: Event {fresh_event_s_or_sf.event_id} ({fresh_event_s_or_sf.event_name}) status updated '{original_status_for_log}' -> '{fresh_event_s_or_sf.event_status}' (Round: {fresh_event_s_or_sf.current_round}).")
                            did_work_in_cycle = True
                        else:
                            logger.debug(f"LifecycleManager: Event {event_s_or_sf.event_id} no longer 'summarized'/'summary_failed' or disappeared.")

                # 4. Process round_finished events (status: 'round_finished')
                #    Action: Call advance_event_to_next_round (sets to 'pending' or 'completed')
                db.session.expire_all()
                events_round_finished = Event.query.filter_by(event_status='round_finished').order_by(Event.updated_at.asc()).all()
                if events_round_finished:
                    logger.info(f"LifecycleManager: Found {len(events_round_finished)} events 'round_finished'.")
                    for event_rf in events_round_finished: # Use different var name
                        # advance_event_to_next_round handles its own concurrency and status updates.
                        checked_event_rf = Event.query.filter_by(event_id=event_rf.event_id, event_status='round_finished').first()
                        if checked_event_rf:
                            logger.info(f"LifecycleManager: Event {checked_event_rf.event_id} ({checked_event_rf.event_name}, Round {checked_event_rf.current_round}) calling advance_event_to_next_round.")
                            advanced = advance_event_to_next_round(checked_event_rf.event_id, publisher)
                            # Log current status after advance_event_to_next_round for clarity
                            db.session.expire(checked_event_rf) # Expire to re-fetch
                            final_event_state = Event.query.filter_by(event_id=checked_event_rf.event_id).first()
                            if final_event_state:
                                logger.info(f"LifecycleManager: Event {final_event_state.event_id} after advance call. Advanced: {advanced}. New Status: {final_event_state.event_status}, New Round: {final_event_state.current_round}")
                            else:
                                logger.warning(f"LifecycleManager: Event {checked_event_rf.event_id} disappeared after advance_event_to_next_round call.")
                            did_work_in_cycle = True 
                        else:
                            logger.debug(f"LifecycleManager: Event {event_rf.event_id} no longer 'round_finished' before calling advance_event_to_next_round.")
                
                # Adjust sleep time based on whether work was done in this cycle
                if did_work_in_cycle:
                    current_sleep = sleep_interval # Reset to base interval if work was done
                else:
                    current_sleep = min(current_sleep * 1.5, max_sleep_interval)
                    logger.debug(f"Event Lifecycle Manager: No actionable events in this cycle, sleeping for {current_sleep:.2f}s.")
                
                time.sleep(current_sleep)

            except pika.exceptions.AMQPConnectionError as amqp_err:
                logger.error(f"EventLifecycleManager: RabbitMQ connection error: {amqp_err}. Retrying in 15s.")
                db.session.rollback() # Rollback any transaction due to AMQP error
                time.sleep(15)
                current_sleep = sleep_interval # Reset sleep on presumed recovery
            except Exception as e:
                logger.error(f"EventLifecycleManager: Unhandled error: {str(e)}")
                logger.error(traceback.format_exc())
                db.session.rollback() # Rollback potentially problematic transaction
                time.sleep(max_sleep_interval) # Longer sleep on unknown error
                current_sleep = sleep_interval # Reset sleep on presumed recovery

def run_expert():
    logger.info("启动_expert服务...")
    from main import app

    publisher = None
    try:
        publisher = RabbitMQPublisher()
        logger.info("RabbitMQ Publisher for Expert Service initialized.")

        threads = []
        
        # --- Updated worker map with the new EventLifecycleManager and ExecutionSummaryWorker ---
        workers_map = {
            "ExecutionSummaryWorker": (execution_summary_worker, app, publisher),
            "EventLifecycleManagerWorker": (event_lifecycle_manager_worker, app, publisher)
        }

        logger.info(f"Starting Expert worker threads: {list(workers_map.keys())}")

        for name, worker_config in workers_map.items():
            target_func, *args = worker_config
            thread = threading.Thread(target=target_func, args=args, name=name)
            thread.daemon = True
            threads.append(thread)
            thread.start()
            logger.info(f"{name} 线程已启动.")

        if not threads:
            logger.critical("CRITICAL: No worker threads were configured or started for Expert Service. Exiting.")
            if publisher: publisher.close()
            return # Exit if no threads started

        while True:
            alive_threads = [t for t in threads if t.is_alive()]
            if not alive_threads:
                logger.error("All expert worker threads seem to have died. Shutting down expert service.")
                break
            time.sleep(60)  # Check every minute

    except pika.exceptions.AMQPConnectionError as amqp_startup_err:
        logger.critical(f"Expert服务启动失败：无法连接到RabbitMQ. Error: {amqp_startup_err}")
        logger.critical(traceback.format_exc())
    except KeyboardInterrupt:
        logger.info("Expert服务被用户中断...")
    except Exception as e_startup:
        logger.critical(f"Expert服务启动时发生未知严重错误: {e_startup}")
        logger.critical(traceback.format_exc())
    finally:
        if publisher:
            logger.info("Expert服务正在关闭RabbitMQ publisher...")
            publisher.close()
        logger.info("Expert服务已停止或启动失败。")

def advance_event_to_next_round(event_id, publisher: RabbitMQPublisher):
    db.session.expire_all()
    event = Event.query.filter_by(event_id=event_id).first()
    if not event:
        logger.warning(f"事件不存在: {event_id}")
        return False
    
    # Ensure event is in 'round_finished' state before advancing
    if event.event_status != 'round_finished':
        logger.warning(f"事件 {event_id} 状态不是 'round_finished' (is {event.event_status})，无法推进到下一轮.")
        return False
    
    current_round = event.current_round or 1 
    if current_round >= config.EVENT_MAX_ROUND:
        logger.warning(f"事件 {event_id} 已达到最大轮次 ({current_round}), 无法推进. 事件状态将设置为 'completed'.")
        if event.event_status != 'completed': # Ensure it's not already completed
            event.event_status = 'completed'
            db.session.commit()
            logger.info(f"事件 {event_id} 在最大轮次时状态已设置为 'completed'.")
        return False # Cannot advance further, already handled.
    
    previous_round_id = event.current_round
    event.current_round = current_round + 1
    event.event_status = 'pending' # New round starts as pending
    db.session.commit()
    logger.info(f"事件 {event_id} 从轮次 {previous_round_id} 推进到新轮次: {event.current_round}, 状态: 'pending'.")

    next_round_content = {
        "event_id": event.event_id, "event_name": event.event_name,
        "previous_round_id": previous_round_id, "new_round_id": event.current_round,
        "text": f"事件 '{event.event_name}' (ID: {event.event_id}) 已进入第 {event.current_round} 轮处理。"
    }
    db_msg_next_round = create_standard_message(
        event_id=event.event_id, message_from='system', round_id=event.current_round, 
        message_type='event_next_round_initiated', content_data=next_round_content
    )
    if db_msg_next_round and publisher:
        try:
            routing_key = f"notifications.frontend.{event.event_id}.system.{db_msg_next_round.message_type}"
            publisher.publish_message(message_body=db_msg_next_round.to_dict(), routing_key=routing_key)
            logger.info(f"消息 [Event Next Round] {db_msg_next_round.message_id} 已发布. RK: {routing_key}")
        except Exception as e_pub: 
            logger.error(f"发布事件进入下一轮消息失败: {e_pub}")
    return True

def resolve_event(event_id, publisher: RabbitMQPublisher, resolution_note=None):
    """人工解决事件, 并准备最终总结"""
    db.session.expire_all()
    event = Event.query.filter_by(event_id=event_id).first()
    if not event:
        logger.warning(f"手动解决事件：事件不存在: {event_id}")
        return False
    
    original_event_status = event.event_status
    logger.info(f"手动解决事件: {event_id}. 当前状态: {original_event_status}. 解决备注: {resolution_note}")

    # Update context with resolution note
    current_context = {}
    if event.context:
        try:
            current_context = json.loads(event.context) if isinstance(event.context, str) else event.context
        except json.JSONDecodeError:
            logger.warning(f"无法解析事件 {event_id} 的现有上下文 JSON，将覆盖。上下文: {event.context}")
            current_context = {} # Reset if invalid JSON
    current_context['resolution_note'] = resolution_note or "事件已由人工操作解决。"
    current_context['resolved_by'] = "manual_user_action" # Could be enhanced with actual user
    current_context['resolved_at_utc'] = datetime.utcnow().isoformat()
    event.context = json.dumps(current_context)

    # Set status to indicate resolution, then to 'to_be_summarized' for final report
    event.event_status = 'resolved' 
    # if hasattr(event, 'resolved_at'): # Assuming 'resolved_at' is a field on the model
    #     event.resolved_at = datetime.utcnow()
    db.session.commit()
    logger.info(f"事件 {event_id} 状态更新为 'resolved'.")

    resolved_content = {
        "event_id": event.event_id, "event_name": event.event_name,
        "resolution_note": resolution_note or "事件已解决",
        "resolved_at": current_context['resolved_at_utc'],
        "text": f"事件 '{event.event_name}' (ID: {event.event_id}) 已解决。备注: {resolution_note or '无'}"
    }
    db_msg_resolved = create_standard_message(
        event_id=event.event_id, message_from='system', round_id=event.current_round,
        message_type='event_resolved_manual', content_data=resolved_content
    )
    if db_msg_resolved and publisher:
        try:
            routing_key = f"notifications.frontend.{event.event_id}.system.{db_msg_resolved.message_type}"
            publisher.publish_message(message_body=db_msg_resolved.to_dict(), routing_key=routing_key)
        except Exception as e_pub: 
            logger.error(f"发布事件解决消息失败: {e_pub}")

    # Now, mark for final summarization
    event.event_status = 'to_be_summarized'
    db.session.commit()
    logger.info(f"事件 {event_id} 解决后，标记为 'to_be_summarized' 以生成最终总结。")
    
    # Explicitly trigger summary generation. In a fully refactored model,
    # the event_lifecycle_manager_worker would pick this up.
    # For now, direct call after setting status.
    # generate_event_summary(event_id, publisher) # This will be handled by the worker that polls 'to_be_summarized'
    
    return True

def debug_event_status(event_id):
    db.session.expire_all()
    event = Event.query.filter_by(event_id=event_id).first()
    if not event:
        logger.warning(f"调试事件状态：事件不存在: {event_id}")
        return
    
    logger.info(f"【事件诊断】事件ID: {event_id}, 状态: {event.event_status}, 轮次: {event.current_round}")
    tasks = Task.query.filter_by(event_id=event_id).all()
    logger.info(f"  当前轮次任务 ({len(tasks)}):")
    for t in tasks:
        logger.info(f"    Task ID: {t.task_id}, Status: {t.task_status}")
        commands = Command.query.filter_by(task_id=t.task_id).all()
        logger.info(f"      命令 ({len(commands)}):")
        for c in commands:
            logger.info(f"        Cmd ID: {c.command_id}, Status: {c.command_status}")
            executions = Execution.query.filter_by(command_id=c.command_id).all()
            logger.info(f"          执行 ({len(executions)}):")
            for ex in executions:
                logger.info(f"            Exec ID: {ex.execution_id}, Status: {ex.execution_status}")
    summaries = Summary.query.filter_by(event_id=event_id).all()
    logger.info(f"  总结 ({len(summaries)}):")
    for s in summaries:
        logger.info(f"    Summary ID: {s.summary_id}, Round: {s.round_id}")

# ------------- 生成事件总结核心函数（恢复）-------------

def generate_event_summary(event_id: str, publisher: RabbitMQPublisher):
    """根据当前事件的所有数据生成总结，并更新事件状态

    仅在 Event.event_status 为 'to_be_summarized' 或 'resolved' 时执行。
    生成完成后将事件状态更新为 'summarized'（正常流程）或 'completed'（若已解决或达到最大轮次）。
    失败时将事件状态置为 'summary_failed'。
    """
    db.session.expire_all()
    event = Event.query.filter_by(event_id=event_id).first()
    if not event:
        logger.warning(f"generate_event_summary: 事件不存在: {event_id}")
        return

    if event.event_status not in ['to_be_summarized', 'resolved']:
        logger.info(f"generate_event_summary: 事件 {event_id} 状态 {event.event_status} 不在可总结范围，跳过。")
        return

    try:
        logger.info(f"generate_event_summary: 开始生成事件 {event_id} 第 {event.current_round} 轮总结，状态 {event.event_status}")
        # 收集上下文
        tasks = Task.query.filter_by(event_id=event_id).all()
        actions = Action.query.filter_by(event_id=event_id).all()
        commands = Command.query.filter_by(event_id=event_id).all()
        executions = Execution.query.filter_by(event_id=event_id).all()

        ctx = {
            "event_id": event.event_id,
            "event_name": event.event_name,
            "event_message": event.message,
            "round_id": event.current_round,
            "event_status": event.event_status,
            "tasks": [{"id": t.task_id, "name": t.task_name, "status": t.task_status} for t in tasks],
            "actions": [{"id": a.action_id, "name": a.action_name, "status": a.action_status} for a in actions],
            "commands": [{"id": c.command_id, "name": c.command_name, "status": c.command_status} for c in commands],
            "executions": [{"id": e.execution_id, "status": e.execution_status, "ai_summary": e.ai_summary} for e in executions]
        }
        yaml_ctx = yaml.dump(ctx, allow_unicode=True, default_flow_style=False, indent=2)

        system_prompt = """你是经验丰富的安全专家，请根据给定 YAML 信息生成仅包含客观事实的事件战况概述。"""
        user_prompt = f"""```yaml\n{yaml_ctx}\n```\n请生成事件战况概述。"""

        # 通知前端开始 LLM
        start_msg = create_standard_message(event_id=event_id, message_from='system', round_id=event.current_round, message_type='expert_llm_request_event_summary', content_data={"text": f"_expert 正在为事件 {event_id} 生成总结"})
        if start_msg and publisher:
            try:
                rk = f"notifications.frontend.{event_id}.system.{start_msg.message_type}"
                publisher.publish_message(message_body=start_msg.to_dict(), routing_key=rk)
            except Exception as mq_err:
                logger.error(f"generate_event_summary: 发布开始消息失败: {mq_err}")

        summary_text = call_llm(system_prompt, user_prompt, temperature=0.3, long_text=True).strip()
        logger.info(f"generate_event_summary: LLM 返回完成。长度 {len(summary_text)} 字")

        summary_obj = Summary(summary_id=str(uuid.uuid4()), event_id=event_id, round_id=event.current_round, event_summary=summary_text, event_suggestion="")
        db.session.add(summary_obj)

        # 更新事件状态
        if event.event_status == 'resolved' or event.current_round >= config.EVENT_MAX_ROUND:
            event.event_status = 'completed'
        else:
            event.event_status = 'summarized'
        db.session.commit()
        logger.info(f"generate_event_summary: 事件 {event_id} 状态更新为 {event.event_status}")

        create_event_summary_message(event, summary_obj, publisher)

    except Exception as err:
        logger.error(f"generate_event_summary: 生成事件 {event_id} 总结失败: {err}")
        logger.error(traceback.format_exc())
        db.session.rollback()
        evt = Event.query.filter_by(event_id=event_id).first()
        if evt and evt.event_status in ['to_be_summarized', 'resolved']:
            evt.event_status = 'summary_failed'
            db.session.commit() 
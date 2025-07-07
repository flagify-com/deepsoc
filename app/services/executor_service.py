import time
import uuid
import json
from datetime import datetime
from flask import current_app
from sqlalchemy import func
from app.models import db, Event, Task, Action, Command, Execution, Message
from app.controllers.socket_controller import broadcast_message
from app.services.playbook_service import PlaybookService
from app.utils.message_utils import create_standard_message
import logging

logger = logging.getLogger(__name__)

def get_pending_commands():
    """获取待处理的命令
    
    Returns:
        待处理的命令列表
    """
    # 查询所有pending状态的命令
    pending_commands = Command.query.filter_by(command_status='pending').order_by(Command.created_at.asc()).all()
    return pending_commands

def process_command(command):
    """处理单个命令
    
    Args:
        command: 命令对象
    """
    logger.info(f"处理命令: {command.command_id}, 类型: {command.command_type}")
    
    # 更新命令状态为处理中
    command.command_status = 'processing'
    db.session.commit()
    
    result = None
    
    try:
        # 根据命令类型执行不同的处理逻辑
        if command.command_type == 'playbook':
            # 执行SOAR剧本
            result = execute_playbook_command(command)
        elif command.command_type == 'manual':
            # 人工命令，需要前端用户处理
            result = handle_manual_command(command)
        else:
            # 未知命令类型
            error_msg = f"未知命令类型: {command.command_type}"
            logger.error(error_msg)
            result = {
                "status": "failed",
                "message": error_msg
            }
        
        # 更新命令状态和结果
        if result and result.get('status') == 'success':
            command.command_status = 'completed'
            command.command_result = result.get('data', {})
            
            # 更新关联的动作状态
            update_action_status(command.action_id, 'completed')
        else:
            command.command_status = 'failed'
            command.command_result = {
                "error": result.get('message') if result else "未知错误"
            }
            
            # 更新关联的动作状态
            update_action_status(command.action_id, 'failed')
        
        db.session.commit()
        
        # 创建消息记录
        create_command_message(command, result)
        
    except Exception as e:
        error_msg = f"处理命令时出错: {str(e)}"
        logger.error(error_msg)
        
        # 更新命令状态为失败
        command.command_status = 'failed'
        command.command_result = {"error": str(e)}
        
        # 更新关联的动作状态
        update_action_status(command.action_id, 'failed')
        
        db.session.commit()
        
        # 创建错误消息记录
        create_command_message(command, {
            "status": "failed",
            "message": error_msg
        })

def execute_playbook_command(command):
    """执行SOAR剧本命令
    
    Args:
        command: 命令对象
    
    Returns:
        执行结果
    """
    logger.info(f"执行SOAR剧本命令: {command.command_id}")
    
    # 创建PlaybookService实例
    playbook_service = PlaybookService()
    
    # 执行剧本
    result = playbook_service.execute_playbook(command)
    
    return result

def handle_manual_command(command):
    """处理人工命令
    
    Args:
        command: 命令对象
    
    Returns:
        处理结果
    """
    logger.info(f"处理人工命令: {command.command_id}")
    
    # 人工命令需要前端用户处理，这里只是标记为等待处理
    # 实际的处理逻辑会在前端用户完成后通过API更新
    
    # 创建执行记录
    execution = Execution(
        execution_id=str(uuid.uuid4()),
        command_id=command.command_id,
        action_id=command.action_id,
        task_id=command.task_id,
        event_id=command.event_id,
        round_id=command.round_id,
        execution_summary="等待人工处理",
        execution_status="waiting"
    )
    db.session.add(execution)
    db.session.commit()
    
    return {
        "status": "success",
        "message": "命令已提交，等待人工处理",
        "data": {
            "execution_id": execution.execution_id,
            "status": "waiting"
        }
    }

def update_action_status(action_id, status):
    """更新动作状态
    
    Args:
        action_id: 动作ID
        status: 新状态
    """
    action = Action.query.filter_by(action_id=action_id).first()
    if action:
        action.action_status = status
        db.session.commit()

def create_command_message(command, result):
    """创建命令执行消息
    
    Args:
        command: 命令对象
        result: 执行结果
    """
    # 构造消息内容
    content_data = {
        "command_id": command.command_id,
        "command_type": command.command_type,
        "command_name": command.command_name,
        "action_id": command.action_id,
        "task_id": command.task_id,
        "status": command.command_status,
        "result": command.command_result
    }
    
    # 创建标准消息
    create_standard_message(
        event_id=command.event_id,
        message_from='_executor',
        round_id=command.round_id,
        message_type='command_result',
        content_data=content_data
    )

def run_executor():
    """运行_executor服务"""
    logger.info("启动_executor服务...")
    
    # 导入Flask应用
    from main import app
    
    # 使用应用上下文
    with app.app_context():
        while True:
            try:
                # 获取待处理命令
                pending_commands = get_pending_commands()
                
                if pending_commands:
                    logger.info(f"发现 {len(pending_commands)} 个待处理命令")
                    
                    # 处理每个命令
                    for command in pending_commands:
                        process_command(command)
                    # 命令处理完后提交，释放锁
                    try:
                        db.session.commit()
                    except Exception as loop_commit_err:
                        logger.error(f"Executor 主循环提交事务失败: {loop_commit_err}")
                        db.session.rollback()
                else:
                    logger.info("没有待处理命令，等待中...")
                    # 回滚事务，避免长事务
                    db.session.rollback()
                    time.sleep(5)
            except Exception as e:
                logger.error(f"处理命令时出错: {str(e)}")
                time.sleep(5) 
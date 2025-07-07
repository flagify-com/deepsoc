from flask import request, jsonify
from app.models import Message, db, Event, Summary, User
from app.services.llm_service import call_llm
from app.utils.mq_utils import RabbitMQPublisher
import json
import traceback
from datetime import datetime
import uuid
import logging
import hashlib

# 获取日志记录器
logger = logging.getLogger(__name__)

class EngineerChatController:
    """工程师对话控制器 - 与Agent系统完全隔离"""
    
    def __init__(self):
        self.max_chat_rounds = 10  # 最大对话轮次
    
    def send_message(self, event_id, user_id, message):
        """
        处理工程师消息 - 异步模式，立即返回用户消息，AI回复通过WebSocket推送
        """
        try:
            # 1. 生成或获取会话ID
            session_id = self._get_or_create_session_id(event_id, user_id)
            
            # 2. 获取最新事件概要
            latest_summary = self._get_event_summary(event_id)
            
            # 3. 从Message表中获取工程师对话历史
            chat_history = self._get_engineer_chat_history(session_id)
            
            # 4. 检查轮次限制
            current_rounds = len([msg for msg in chat_history if msg.sender_type == 'user'])
            if current_rounds >= self.max_chat_rounds:
                return self._handle_max_rounds_reached(session_id)
            
            # 5. 检查概要更新
            summary_updated = self._check_summary_update(chat_history, latest_summary)
            
            # 6. 立即保存用户消息到Message表
            user_message = self._save_message_to_unified_table(
                event_id=event_id,
                sender_id=user_id,
                sender_type='user',
                content=message,
                message_category='engineer_chat',
                session_id=session_id,
                summary_version=self._get_summary_hash(latest_summary)
            )
            
            # 7. 立即通过WebSocket广播用户消息
            self._broadcast_message_via_websocket(user_message)
            
            # 8. 启动异步AI处理任务
            import threading
            # 传递简单数据而不是SQLAlchemy对象到异步线程
            summary_data = None
            if latest_summary:
                summary_data = {
                    'event_id': latest_summary.event_id,
                    'round_id': latest_summary.round_id,
                    'event_summary': latest_summary.event_summary,
                    'event_suggestion': latest_summary.event_suggestion,
                    'updated_at': latest_summary.updated_at.isoformat() if latest_summary.updated_at else None
                }
            
            ai_thread = threading.Thread(
                target=self._process_ai_response_async,
                args=(event_id, session_id, message, summary_data, summary_updated),
                daemon=True
            )
            ai_thread.start()
            
            # 9. 立即返回用户消息，不等待AI回复
            return {
                'status': 'success',
                'user_message': user_message.to_dict(),
                'session_id': session_id,
                'summary_updated': summary_updated,
                'ai_processing': True  # 表示AI正在后台处理
            }
            
        except Exception as e:
            logger.error(f"处理工程师消息时出错: {str(e)}")
            logger.error(traceback.format_exc())
            return {
                'status': 'error',
                'message': f"处理消息时出错: {str(e)}"
            }
    
    def _process_ai_response_async(self, event_id, session_id, user_message, summary_data, summary_updated):
        """
        异步处理AI回复 - 在独立线程中运行，需要创建应用上下文
        """
        # 获取Flask应用实例
        from main import app
        
        # 在异步线程中创建应用上下文
        with app.app_context():
            try:
                logger.info(f"开始异步处理AI回复，会话ID: {session_id}")
                
                # 1. 重新获取对话历史（在应用上下文中）
                chat_history = self._get_engineer_chat_history(session_id)
                
                # 2. 构建对话上下文
                context = self._build_context_from_data(chat_history, user_message, summary_data, summary_updated)
                
                # 3. 调用AI服务
                ai_response = self._call_ai_service(context)
                
                # 4. 保存AI回复到Message表
                summary_hash = self._get_summary_hash_from_data(summary_data) if summary_data else None
                ai_message = self._save_message_to_unified_table(
                    event_id=event_id,
                    sender_id='ai_assistant',
                    sender_type='ai',
                    content=ai_response,
                    message_category='engineer_chat',
                    session_id=session_id,
                    summary_version=summary_hash
                )
                
                # 5. 通过WebSocket广播AI回复
                self._broadcast_message_via_websocket(ai_message)
                
                logger.info(f"AI回复处理完成，消息ID: {ai_message.message_id}")
                
            except Exception as e:
                logger.error(f"异步AI处理失败: {str(e)}")
                logger.error(traceback.format_exc())
                
                # 发送错误消息到前端
                try:
                    summary_hash = self._get_summary_hash_from_data(summary_data) if summary_data else None
                    error_message = self._save_message_to_unified_table(
                        event_id=event_id,
                        sender_id='system',
                        sender_type='ai',
                        content=f"AI助手暂时无法回复，请稍后重试。错误信息：{str(e)}",
                        message_category='engineer_chat',
                        session_id=session_id,
                        summary_version=summary_hash
                    )
                    self._broadcast_message_via_websocket(error_message)
                except Exception as broadcast_error:
                    logger.error(f"发送错误消息失败: {str(broadcast_error)}")
                    logger.error(traceback.format_exc())
    
    def _get_or_create_session_id(self, event_id, user_id):
        """生成或获取会话ID"""
        # 查找是否有现有的活跃会话
        existing_message = db.session.query(Message).filter_by(
            event_id=event_id,
            user_id=user_id,
            message_category='engineer_chat'
        ).order_by(Message.created_at.desc()).first()
        
        if existing_message and existing_message.chat_session_id:
            # 检查该会话是否未达到轮次限制
            chat_history = self._get_engineer_chat_history(existing_message.chat_session_id)
            current_rounds = len([msg for msg in chat_history if msg.sender_type == 'user'])
            
            if current_rounds < self.max_chat_rounds:
                return existing_message.chat_session_id
        
        # 创建新的会话ID（使用更短的格式）
        import hashlib
        combined = f"{event_id}_{user_id}"
        hash_suffix = hashlib.md5(combined.encode()).hexdigest()[:8]
        return f"chat_{hash_suffix}_{uuid.uuid4().hex[:8]}"
    
    def _get_event_summary(self, event_id):
        """获取最新事件概要"""
        return db.session.query(Summary).filter_by(
            event_id=event_id
        ).order_by(Summary.created_at.desc()).first()
    
    def _get_engineer_chat_history(self, session_id):
        """从Message表中获取工程师对话历史"""
        return db.session.query(Message).filter_by(
            message_category='engineer_chat',
            chat_session_id=session_id
        ).order_by(Message.created_at.asc()).all()
    
    def _check_summary_update(self, chat_history, latest_summary):
        """检查概要是否有更新"""
        if not chat_history or not latest_summary:
            return False
        
        # 获取最后一条消息的概要版本
        last_message = chat_history[-1] if chat_history else None
        if not last_message or not last_message.event_summary_version:
            return True  # 如果没有版本信息，认为有更新
        
        latest_hash = self._get_summary_hash(latest_summary)
        return last_message.event_summary_version != latest_hash
    
    def _get_summary_hash(self, summary):
        """生成概要内容的哈希值"""
        if not summary or not summary.event_summary:
            return None
        
        content = f"{summary.event_summary}_{summary.round_id}_{summary.updated_at}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _build_context(self, chat_history, current_message, latest_summary, summary_updated):
        """基于Message表中的历史记录构建对话上下文"""
        # 1. 格式化历史对话（最近10轮对话，即20条消息）
        formatted_history = []
        recent_history = chat_history[-20:] if len(chat_history) > 20 else chat_history
        
        for msg in recent_history:
            if msg.sender_type == 'user':
                role = "工程师"
            elif msg.sender_type == 'ai':
                role = "AI助手"
            else:
                continue
            
            # 提取消息内容
            content = msg.message_content
            if isinstance(content, dict):
                content = content.get('content', content.get('message', str(content)))
            elif isinstance(content, str):
                try:
                    parsed = json.loads(content)
                    content = parsed.get('content', parsed.get('message', content))
                except json.JSONDecodeError:
                    pass
            
            formatted_history.append(f"{role}: {content}")
        
        # 2. 构建事件概要信息
        summary_info = "暂无事件概要"
        if latest_summary and latest_summary.event_summary:
            summary_info = latest_summary.event_summary
        
        update_status = "本次对话中事件概要有更新" if summary_updated else "事件概要无更新"
        
        # 3. 构建完整上下文
        context = f"""
# 安全事件概要信息
事件ID: {latest_summary.event_id if latest_summary else '未知'}
概要信息: {summary_info}
概要更新状态: {update_status}

# 历史对话记录
{chr(10).join(formatted_history) if formatted_history else '暂无历史对话'}

# 当前问题
工程师问题: {current_message}

请基于以上信息回答工程师的问题。你是一个专业的安全运营AI助手，请提供准确、有用的建议和信息。
如果事件概要有更新，请特别关注新的变化并在回答中体现出来。
"""
        return context
    
    def _build_context_from_data(self, chat_history, current_message, summary_data, summary_updated):
        """基于简单数据结构构建对话上下文（用于异步线程）"""
        # 1. 格式化历史对话（最近10轮对话，即20条消息）
        formatted_history = []
        recent_history = chat_history[-20:] if len(chat_history) > 20 else chat_history
        
        for msg in recent_history:
            if msg.sender_type == 'user':
                role = "工程师"
            elif msg.sender_type == 'ai':
                role = "AI助手"
            else:
                continue
            
            # 提取消息内容
            content = msg.message_content
            if isinstance(content, dict):
                content = content.get('content', content.get('message', str(content)))
            elif isinstance(content, str):
                try:
                    parsed = json.loads(content)
                    content = parsed.get('content', parsed.get('message', content))
                except json.JSONDecodeError:
                    pass
            
            formatted_history.append(f"{role}: {content}")
        
        # 2. 构建事件概要信息
        summary_info = "暂无事件概要"
        event_id_display = "未知"
        
        if summary_data:
            event_id_display = summary_data.get('event_id', '未知')
            if summary_data.get('event_summary'):
                summary_info = summary_data['event_summary']
        
        update_status = "本次对话中事件概要有更新" if summary_updated else "事件概要无更新"
        
        # 3. 构建完整上下文
        context = f"""
# 安全事件概要信息
事件ID: {event_id_display}
概要信息: {summary_info}
概要更新状态: {update_status}

# 历史对话记录
{chr(10).join(formatted_history) if formatted_history else '暂无历史对话'}

# 当前问题
工程师问题: {current_message}

请基于以上信息回答工程师的问题。你是一个专业的安全运营AI助手，请提供准确、有用的建议和信息。
如果事件概要有更新，请特别关注新的变化并在回答中体现出来。
"""
        return context
    
    def _get_summary_hash_from_data(self, summary_data):
        """从简单数据结构计算概要哈希"""
        if not summary_data or not summary_data.get('event_summary'):
            return None
        
        import hashlib
        summary_content = summary_data.get('event_summary', '')
        round_id = summary_data.get('round_id', 0)
        content_to_hash = f"{summary_content}_{round_id}"
        return hashlib.md5(content_to_hash.encode()).hexdigest()[:16]
    
    def _call_ai_service(self, context):
        """独立的AI调用"""
        try:
            # 使用现有的call_llm函数
            system_prompt = "你是DeepSOC安全运营中心的AI助手，专门协助安全工程师处理安全事件。请基于提供的事件信息和对话历史，为工程师提供专业的安全建议和协助。"
            user_prompt = context
            
            # 调用LLM服务
            response = call_llm(system_prompt, user_prompt)
            return response
            
        except Exception as e:
            logger.error(f"AI调用失败: {str(e)}")
            return f"抱歉，AI助手暂时不可用。错误信息: {str(e)}"
    
    def _save_message_to_unified_table(self, event_id, sender_id, sender_type, 
                                      content, message_category, session_id, summary_version):
        """保存消息到统一的Message表"""
        try:
            # 构建消息内容
            message_content = {
                'content': content,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            message = Message(
                message_id=str(uuid.uuid4()),
                event_id=event_id,
                user_id=sender_id,
                message_from=sender_id,
                message_content=message_content,
                message_type='chat',
                message_category=message_category,
                chat_session_id=session_id,
                sender_type=sender_type,
                event_summary_version=summary_version,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.session.add(message)
            db.session.commit()
            
            return message
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"保存消息到数据库失败: {str(e)}")
            raise e
    
    def _broadcast_message_via_websocket(self, message):
        """通过RabbitMQ广播工程师对话消息 - 与Agent系统统一架构"""
        try:
            # 使用RabbitMQ Publisher，与Agent系统完全一致的架构
            publisher = RabbitMQPublisher()
            
            # 构建与Agent系统相同的routing key格式
            routing_key = f"notifications.frontend.{message.event_id}.{message.message_from}.{message.message_type}"
            
            logger.info(f"🚀 [工程师对话] 使用RabbitMQ发送消息: {message.message_id}")
            logger.info(f"📮 Routing Key: {routing_key}")
            
            # 发布消息到RabbitMQ，与Agent系统使用相同的方法
            publisher.publish_message(
                message_body=message.to_dict(),
                routing_key=routing_key
            )
            
            logger.info(f"✅ [工程师对话] 消息已通过RabbitMQ发布: {message.message_id}")
            
            # 关闭publisher连接
            publisher.close()
            
        except Exception as e:
            logger.error(f"❌ [工程师对话] RabbitMQ广播失败: {str(e)}")
            logger.error(traceback.format_exc())
            
            # 备用方案：使用socket_controller的broadcast_message
            try:
                logger.info(f"🔄 [工程师对话] 使用备用方案: socket_controller广播")
                from app.controllers.socket_controller import broadcast_message
                broadcast_message(message)
                logger.info(f"✅ [工程师对话] 备用广播成功: {message.message_id}")
            except Exception as backup_error:
                logger.error(f"❌ [工程师对话] 备用广播也失败: {str(backup_error)}")
                logger.error(traceback.format_exc())
    
    def _handle_max_rounds_reached(self, session_id):
        """处理达到最大轮次的情况"""
        return {
            'status': 'max_rounds_reached',
            'message': f'对话轮次已达上限({self.max_chat_rounds}轮)，建议开始新的对话会话。',
            'session_id': session_id,
            'action': 'create_new_session'
        }
    
    def get_chat_history(self, event_id, user_id):
        """获取工程师对话历史"""
        try:
            session_id = self._get_or_create_session_id(event_id, user_id)
            chat_history = self._get_engineer_chat_history(session_id)
            
            # 格式化历史记录
            formatted_history = []
            for msg in chat_history:
                formatted_msg = {
                    'id': msg.id,
                    'sender_type': msg.sender_type,
                    'content': msg.message_content,
                    'created_at': msg.created_at.isoformat() if msg.created_at else None
                }
                formatted_history.append(formatted_msg)
            
            return {
                'status': 'success',
                'session_id': session_id,
                'history': formatted_history,
                'current_rounds': len([msg for msg in chat_history if msg.sender_type == 'user']),
                'max_rounds': self.max_chat_rounds
            }
            
        except Exception as e:
            logger.error(f"获取对话历史失败: {str(e)}")
            return {
                'status': 'error',
                'message': f"获取对话历史失败: {str(e)}"
            }

# 创建全局实例
engineer_chat_controller = EngineerChatController()
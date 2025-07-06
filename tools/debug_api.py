#!/usr/bin/env python3
"""
调试工程师对话API
"""
import os
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import app
from app.models.models import User, Event
from flask_jwt_extended import create_access_token

def test_api_logic():
    with app.app_context():
        # 1. 查找用户
        print("=== 查找用户 ===")
        user = User.query.filter_by(username='admin').first()
        if user:
            print(f"✅ 找到用户: {user.username}, user_id: {user.user_id}")
        else:
            print("❌ 未找到admin用户")
            return
        
        # 2. 查找事件
        print("\n=== 查找事件 ===")
        event_id = "1d0528af-6071-4495-a3e9-21fea33da178"
        event = Event.query.filter_by(event_id=event_id).first()
        if event:
            print(f"✅ 找到事件: {event.event_name}, 状态: {event.event_status}")
        else:
            print(f"❌ 未找到事件: {event_id}")
            return
        
        # 3. 测试工程师对话控制器
        print("\n=== 测试工程师对话控制器 ===")
        from app.controllers.engineer_chat_controller import engineer_chat_controller
        
        try:
            result = engineer_chat_controller.send_message(
                event_id=event_id,
                user_id=user.user_id,
                message="测试消息：这个安全事件的风险等级如何？"
            )
            print(f"✅ 控制器调用成功")
            print(f"   状态: {result.get('status')}")
            if result.get('status') == 'success':
                print(f"   用户消息ID: {result['user_message']['message_id']}")
                print(f"   AI回复ID: {result['ai_response']['message_id']}")
            else:
                print(f"   错误: {result.get('message')}")
        except Exception as e:
            print(f"❌ 控制器调用失败: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    test_api_logic()
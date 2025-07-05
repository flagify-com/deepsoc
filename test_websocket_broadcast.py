#!/usr/bin/env python3
"""
测试工程师对话WebSocket广播功能
"""

import json
import requests
import socketio
import threading
import time
import sys

# 服务器配置
BASE_URL = "http://localhost:5007"
EVENT_ID = "test_event_123"

class WebSocketTestClient:
    def __init__(self):
        self.sio = socketio.Client()
        self.received_messages = []
        self.connected = False
        
        # 注册事件处理器
        @self.sio.event
        def connect():
            print("✅ WebSocket连接成功")
            self.connected = True
            # 加入事件房间
            self.sio.emit('join', {'event_id': EVENT_ID})
            print(f"📍 已发送加入房间请求: {EVENT_ID}")
        
        @self.sio.event
        def disconnect():
            print("❌ WebSocket连接断开")
            self.connected = False
        
        @self.sio.on('new_message')
        def on_new_message(data):
            print(f"🔔 收到WebSocket消息: {json.dumps(data, indent=2, ensure_ascii=False)}")
            # 记录所有new_message事件
            self.received_messages.append(data)
            if data.get('message_category') == 'engineer_chat':
                print(f"🎯 工程师对话消息: {data.get('sender_type')} - {data.get('message_content')}")
            else:
                print(f"📝 其他消息: 类型={data.get('message_type')}, 来源={data.get('message_from')}")
        
        @self.sio.on('status')
        def on_status(data):
            print(f"📊 状态更新: {data}")
            if data.get('status') == 'joined':
                print(f"✅ 成功加入房间: {data.get('event_id')}")
        
        @self.sio.on('test_message')
        def on_test_message(data):
            print(f"🧪 测试消息: {data}")
        
        @self.sio.on('*')
        def catch_all(event, *args):
            print(f"🌐 WebSocket事件: {event}, 数据: {args}")
    
    def connect_websocket(self):
        try:
            self.sio.connect(BASE_URL)
            return True
        except Exception as e:
            print(f"❌ WebSocket连接失败: {e}")
            return False
    
    def disconnect_websocket(self):
        if self.connected:
            self.sio.disconnect()

def test_api_and_websocket():
    """测试API发送消息和WebSocket接收"""
    
    print("🚀 开始测试工程师对话WebSocket广播功能")
    
    # 1. 创建WebSocket客户端
    ws_client = WebSocketTestClient()
    
    # 2. 连接WebSocket
    if not ws_client.connect_websocket():
        print("❌ 无法连接WebSocket，测试终止")
        return False
    
    # 等待连接稳定
    time.sleep(2)
    
    # 3. 模拟用户登录（获取JWT token）
    print("🔐 尝试用户登录...")
    login_data = {
        "username": "admin",
        "password": "admin123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/auth/login", json=login_data)
        if response.status_code == 200:
            token = response.json().get('access_token')
            print(f"✅ 登录成功，获得token: {token[:20]}...")
        else:
            print(f"❌ 登录失败: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 登录请求失败: {e}")
        return False
    
    # 4. 创建测试事件（如果不存在）
    print("📝 创建测试事件...")
    headers = {"Authorization": f"Bearer {token}"}
    event_data = {
        "event_id": EVENT_ID,
        "event_name": "WebSocket测试事件",
        "message": "这是一个用于测试WebSocket广播的测试事件",
        "source": "test",
        "severity": "low"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/event/create", json=event_data, headers=headers)
        if response.status_code in [200, 201]:
            print("✅ 测试事件创建成功")
        else:
            print(f"⚠️ 事件创建响应: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ 创建事件失败: {e}")
    
    # 5. 发送工程师对话消息
    print("💬 发送工程师对话消息...")
    headers = {"Authorization": f"Bearer {token}"}
    message_data = {
        "event_id": EVENT_ID,
        "message": "@AI 这是一条测试消息，用于验证WebSocket广播功能是否正常工作"
    }
    
    initial_message_count = len(ws_client.received_messages)
    
    try:
        response = requests.post(f"{BASE_URL}/api/engineer-chat/send", 
                               json=message_data, headers=headers)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 消息发送成功: {json.dumps(result, indent=2, ensure_ascii=False)}")
        else:
            print(f"❌ 消息发送失败: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ 发送消息请求失败: {e}")
        return False
    
    # 6. 等待并检查WebSocket消息
    print("⏰ 等待WebSocket消息...")
    
    # 等待用户消息
    timeout = 5
    start_time = time.time()
    while time.time() - start_time < timeout:
        if len(ws_client.received_messages) > initial_message_count:
            break
        time.sleep(0.1)
    
    user_message_received = len(ws_client.received_messages) > initial_message_count
    
    # 等待AI回复消息  
    timeout = 30  # AI回复可能需要更长时间
    start_time = time.time()
    ai_message_received = False
    
    while time.time() - start_time < timeout:
        for msg in ws_client.received_messages[initial_message_count:]:
            if msg.get('sender_type') == 'ai':
                ai_message_received = True
                break
        if ai_message_received:
            break
        time.sleep(0.5)
    
    # 7. 分析结果
    print("\n📊 测试结果分析:")
    new_messages = ws_client.received_messages[initial_message_count:]
    engineer_messages = [msg for msg in new_messages if msg.get('message_category') == 'engineer_chat']
    user_messages = [msg for msg in engineer_messages if msg.get('sender_type') == 'user']
    ai_messages = [msg for msg in engineer_messages if msg.get('sender_type') == 'ai']
    
    print(f"📨 总共接收到的WebSocket消息数: {len(new_messages)}")
    print(f"🎯 其中工程师对话消息数: {len(engineer_messages)}")
    print(f"👤 用户消息通过WebSocket接收: {'✅' if len(user_messages) > 0 else '❌'} (数量: {len(user_messages)})")
    print(f"🤖 AI回复通过WebSocket接收: {'✅' if len(ai_messages) > 0 else '❌'} (数量: {len(ai_messages)})")
    
    if new_messages:
        print("\n📝 收到的所有消息详情:")
        for i, msg in enumerate(new_messages, 1):
            category = msg.get('message_category', 'unknown')
            sender = msg.get('sender_type', msg.get('message_from', 'unknown'))
            msg_type = msg.get('message_type', 'unknown')
            content = msg.get('message_content', {})
            if isinstance(content, dict):
                text = content.get('content', str(content))
            else:
                text = str(content)
            print(f"  {i}. [类型:{category}] [发送者:{sender}] [消息类型:{msg_type}]: {text[:100]}...")
    else:
        print("\n❌ 没有收到任何WebSocket消息")
    
    # 8. 清理
    ws_client.disconnect_websocket()
    
    # 判断测试是否成功
    success = user_message_received and ai_message_received
    print(f"\n🎯 测试{'成功' if success else '失败'}: WebSocket实时广播功能{'正常' if success else '存在问题'}")
    
    return success

if __name__ == "__main__":
    test_api_and_websocket()
#!/usr/bin/env python3
"""
WebSocket Engineer Chat Testing Script

This script tests the WebSocket broadcasting fix for engineer chat messages
to verify they are delivered immediately rather than through 30-second polling.
"""

import sys
import time
import json
import requests
import threading
from datetime import datetime
import socketio

# Configuration
SERVER_BASE_URL = "http://localhost:5007"
WS_URL = "http://localhost:5007"
TEST_EVENT_ID = "test_event_20250704_websocket"
TEST_USER_ID = "test_engineer"
TEST_USERNAME = "test_engineer"

class WebSocketTester:
    def __init__(self):
        self.sio = socketio.Client()
        self.messages_received = []
        self.connected = False
        self.room_joined = False
        
        # Setup event handlers
        self.sio.on('connect', self.on_connect)
        self.sio.on('disconnect', self.on_disconnect)
        self.sio.on('new_message', self.on_new_message)
        self.sio.on('status', self.on_status)
        self.sio.on('test_message', self.on_test_message)
        
    def on_connect(self):
        print(f"✅ WebSocket连接成功 at {datetime.now()}")
        self.connected = True
        
    def on_disconnect(self):
        print(f"❌ WebSocket连接断开 at {datetime.now()}")
        self.connected = False
        
    def on_new_message(self, data):
        timestamp = datetime.now()
        print(f"📨 收到WebSocket消息 at {timestamp}: {json.dumps(data, indent=2, ensure_ascii=False)}")
        self.messages_received.append({
            'timestamp': timestamp,
            'data': data
        })
        
    def on_status(self, data):
        print(f"📊 收到状态消息: {data}")
        if data.get('status') == 'joined':
            print(f"🏠 成功加入房间: {data.get('event_id')}")
            self.room_joined = True
    
    def on_test_message(self, data):
        print(f"🧪 收到测试消息: {data}")
        
    def connect_and_join_room(self, event_id, access_token):
        """连接WebSocket并加入事件房间"""
        try:
            # 连接WebSocket
            self.sio.connect(WS_URL, headers={'Authorization': f'Bearer {access_token}'})
            
            # 等待连接建立
            timeout = 10
            start_time = time.time()
            while not self.connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)
                
            if not self.connected:
                raise Exception("WebSocket连接超时")
                
            # 加入事件房间
            self.sio.emit('join', {'event_id': event_id})
            
            # 等待加入房间成功
            start_time = time.time()
            while not self.room_joined and (time.time() - start_time) < timeout:
                time.sleep(0.1)
                
            if not self.room_joined:
                print("⚠️ 警告: 未收到加入房间成功确认，但继续测试...")
                
            return True
            
        except Exception as e:
            print(f"❌ WebSocket连接失败: {e}")
            return False
    
    def disconnect(self):
        """断开WebSocket连接"""
        if self.connected:
            self.sio.disconnect()

def get_test_token():
    """获取测试用的JWT token"""
    login_data = {
        "username": TEST_USERNAME,
        "password": "test123"  # Assuming test user exists
    }
    
    try:
        response = requests.post(f"{SERVER_BASE_URL}/api/auth/login", json=login_data)
        if response.status_code == 200:
            data = response.json()
            return data.get('access_token')
        else:
            print(f"❌ 登录失败: {response.text}")
            return None
    except Exception as e:
        print(f"❌ 登录请求失败: {e}")
        return None

def send_engineer_chat_message(event_id, message, access_token):
    """发送工程师对话消息"""
    chat_data = {
        "event_id": event_id,
        "message": message
    }
    
    headers = {'Authorization': f'Bearer {access_token}'}
    
    try:
        print(f"📤 发送工程师对话消息: {message}")
        response = requests.post(
            f"{SERVER_BASE_URL}/api/engineer-chat/send", 
            json=chat_data,
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 消息发送成功: {json.dumps(data, indent=2, ensure_ascii=False)}")
            return data
        else:
            print(f"❌ 消息发送失败: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 发送消息请求失败: {e}")
        return None

def main():
    print("🧪 开始WebSocket工程师对话测试")
    print("=" * 60)
    
    # 1. 获取访问令牌
    print("1. 获取访问令牌...")
    access_token = get_test_token()
    if not access_token:
        print("❌ 无法获取访问令牌，跳过WebSocket测试")
        return False
    
    print(f"✅ 成功获取访问令牌: {access_token[:20]}...")
    
    # 2. 建立WebSocket连接
    print("\n2. 建立WebSocket连接...")
    ws_tester = WebSocketTester()
    
    if not ws_tester.connect_and_join_room(TEST_EVENT_ID, access_token):
        print("❌ WebSocket连接失败")
        return False
    
    print("✅ WebSocket连接建立成功")
    
    # 3. 发送测试消息并验证实时接收
    print("\n3. 测试实时消息传递...")
    
    test_messages = [
        "@AI 这是第一条测试消息",
        "@AI 请检查WebSocket是否工作正常", 
        "@AI 验证消息是否立即传递而不是通过轮询"
    ]
    
    all_tests_passed = True
    
    for i, test_message in enumerate(test_messages, 1):
        print(f"\n📝 测试 {i}/3: 发送消息并验证即时接收")
        
        # 记录发送前的消息数量
        messages_before = len(ws_tester.messages_received)
        send_time = datetime.now()
        
        # 发送消息
        result = send_engineer_chat_message(TEST_EVENT_ID, test_message, access_token)
        if not result:
            print(f"❌ 测试 {i} 失败: 消息发送失败")
            all_tests_passed = False
            continue
        
        # 等待WebSocket消息（应该在3秒内收到）
        print("⏰ 等待WebSocket消息接收...")
        timeout = 5  # 5秒超时
        start_wait = time.time()
        
        while (time.time() - start_wait) < timeout:
            if len(ws_tester.messages_received) > messages_before:
                # 检查是否收到了用户消息
                new_messages = ws_tester.messages_received[messages_before:]
                user_message_received = any(
                    msg['data'].get('sender_type') == 'user' 
                    for msg in new_messages
                )
                
                if user_message_received:
                    receive_time = datetime.now()
                    latency = (receive_time - send_time).total_seconds()
                    print(f"✅ 测试 {i} 成功: 用户消息在 {latency:.2f} 秒内通过WebSocket接收")
                    
                    # 等待AI回复（额外10秒）
                    print("⏰ 等待AI回复...")
                    ai_wait_start = time.time()
                    while (time.time() - ai_wait_start) < 10:
                        ai_messages = [
                            msg for msg in ws_tester.messages_received[messages_before:]
                            if msg['data'].get('sender_type') == 'ai'
                        ]
                        if ai_messages:
                            ai_receive_time = datetime.now()
                            ai_latency = (ai_receive_time - send_time).total_seconds()
                            print(f"✅ AI回复在 {ai_latency:.2f} 秒内通过WebSocket接收")
                            break
                        time.sleep(0.5)
                    else:
                        print("⚠️ 未在10秒内收到AI回复")
                    
                    break
                    
            time.sleep(0.2)
        else:
            print(f"❌ 测试 {i} 失败: 在 {timeout} 秒内未收到WebSocket消息")
            all_tests_passed = False
        
        # 测试间隔
        time.sleep(2)
    
    # 4. 断开连接并总结
    print("\n4. 断开连接...")
    ws_tester.disconnect()
    
    print("\n" + "=" * 60)
    print("📊 测试总结:")
    print(f"总共收到 {len(ws_tester.messages_received)} 条WebSocket消息")
    
    if all_tests_passed:
        print("🎉 所有测试通过! WebSocket实时消息传递工作正常")
        print("✅ 修复成功: 工程师对话消息现在通过WebSocket立即传递")
    else:
        print("❌ 部分测试失败，可能仍存在WebSocket传递问题")
    
    return all_tests_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
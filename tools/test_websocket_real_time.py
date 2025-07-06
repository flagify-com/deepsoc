#!/usr/bin/env python3
"""
WebSocket实时推送验证测试
验证工程师对话消息是否通过WebSocket实时推送而不是轮询
"""

import sys
import time
import json
import requests
import threading
from datetime import datetime
import socketio

# 配置
SERVER_BASE_URL = "http://localhost:5007"
WS_URL = "http://localhost:5007"
TEST_EVENT_ID = "test_event_20250704_websocket"
TEST_USERNAME = "test_engineer"

class RealTimeWebSocketTester:
    def __init__(self):
        self.sio = socketio.Client()
        self.messages_received = []
        self.connected = False
        self.room_joined = False
        self.engineer_messages_received = 0
        
        # Setup event handlers
        self.sio.on('connect', self.on_connect)
        self.sio.on('disconnect', self.on_disconnect)
        self.sio.on('new_message', self.on_new_message)
        self.sio.on('status', self.on_status)
        
    def on_connect(self):
        print(f"✅ WebSocket连接成功 at {datetime.now()}")
        self.connected = True
        
    def on_disconnect(self):
        print(f"❌ WebSocket连接断开 at {datetime.now()}")
        self.connected = False
        
    def on_new_message(self, data):
        timestamp = datetime.now()
        print(f"📨 收到WebSocket消息 at {timestamp}")
        
        # 检查是否是工程师对话消息
        if isinstance(data, dict) and data.get('message_category') == 'engineer_chat':
            self.engineer_messages_received += 1
            print(f"🎯 工程师对话消息#{self.engineer_messages_received}: {data.get('sender_type')} - {data.get('message_id', 'no_id')}")
        else:
            print(f"📄 其他消息: {data.get('message_category', 'unknown')} - {data.get('test', False)}")
        
        self.messages_received.append({
            'timestamp': timestamp,
            'data': data
        })
        
    def on_status(self, data):
        print(f"📊 收到状态消息: {data}")
        if data.get('status') == 'joined':
            print(f"🏠 成功加入房间: {data.get('event_id')}")
            self.room_joined = True
        
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
                
            print(f"✅ WebSocket连接和房间加入完成")
            return True
            
        except Exception as e:
            print(f"❌ WebSocket连接失败: {e}")
            return False
    
    def disconnect(self):
        """断开WebSocket连接"""
        if self.connected:
            self.sio.disconnect()

def get_test_token():
    """获取测试token"""
    login_data = {
        "username": TEST_USERNAME,
        "password": "test123"
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
            print(f"✅ 消息发送成功")
            return data
        else:
            print(f"❌ 消息发送失败: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 发送消息请求失败: {e}")
        return None

def main():
    print("🧪 WebSocket实时推送验证测试")
    print("=" * 60)
    
    # 1. 获取访问令牌
    print("1. 获取访问令牌...")
    access_token = get_test_token()
    if not access_token:
        print("❌ 无法获取访问令牌")
        return False
    
    print(f"✅ 成功获取访问令牌")
    
    # 2. 建立WebSocket连接
    print("\n2. 建立WebSocket连接...")
    ws_tester = RealTimeWebSocketTester()
    
    if not ws_tester.connect_and_join_room(TEST_EVENT_ID, access_token):
        print("❌ WebSocket连接失败")
        return False
    
    # 3. 实时消息测试
    print("\n3. 开始实时消息测试...")
    print("📡 等待5秒以确保连接稳定...")
    time.sleep(5)
    
    # 发送消息并监控实时接收
    test_message = "@AI 实时推送测试 - 这条消息应该立即通过WebSocket推送"
    
    print(f"\n📤 发送测试消息: {test_message}")
    send_time = datetime.now()
    
    # 记录发送前收到的消息数量
    messages_before = len(ws_tester.messages_received)
    engineer_messages_before = ws_tester.engineer_messages_received
    
    # 发送消息
    result = send_engineer_chat_message(TEST_EVENT_ID, test_message, access_token)
    if not result:
        print("❌ 消息发送失败")
        ws_tester.disconnect()
        return False
    
    print(f"⏰ 监控WebSocket消息接收...")
    
    # 监控15秒内的消息接收情况
    monitoring_duration = 15
    last_check = datetime.now()
    
    for i in range(monitoring_duration):
        time.sleep(1)
        current_time = datetime.now()
        
        # 检查是否收到新的工程师对话消息
        new_engineer_messages = ws_tester.engineer_messages_received - engineer_messages_before
        
        if new_engineer_messages > 0:
            latency = (current_time - send_time).total_seconds()
            print(f"🎉 在 {latency:.2f} 秒内收到 {new_engineer_messages} 条工程师对话消息！")
            
            if latency <= 3.0:
                print(f"✅ 实时推送成功！延迟: {latency:.2f}秒 (≤3秒)")
                break
            else:
                print(f"⚠️ 延迟较高: {latency:.2f}秒 (>3秒)")
        
        # 每5秒报告一次状态
        if i > 0 and i % 5 == 0:
            elapsed = (current_time - send_time).total_seconds()
            print(f"⏰ 已等待 {elapsed:.0f} 秒，收到 {new_engineer_messages} 条工程师对话消息")
    
    # 4. 等待AI回复
    print(f"\n4. 等待AI回复...")
    ai_wait_start = datetime.now()
    initial_engineer_messages = ws_tester.engineer_messages_received
    
    for i in range(15):  # 等待15秒AI回复
        time.sleep(1)
        ai_messages = ws_tester.engineer_messages_received - initial_engineer_messages
        
        if ai_messages > 1:  # 用户消息 + AI回复
            ai_latency = (datetime.now() - ai_wait_start).total_seconds()
            print(f"🤖 AI回复在 {ai_latency:.2f} 秒内通过WebSocket接收")
            break
    else:
        print("⚠️ 未在15秒内收到AI回复")
    
    # 5. 断开连接并总结
    print("\n5. 断开连接...")
    ws_tester.disconnect()
    
    print("\n" + "=" * 60)
    print("📊 测试总结:")
    print(f"总共收到 {len(ws_tester.messages_received)} 条WebSocket消息")
    print(f"工程师对话消息: {ws_tester.engineer_messages_received} 条")
    
    if ws_tester.engineer_messages_received >= 2:  # 用户 + AI回复
        print("🎉 WebSocket实时推送测试成功!")
        print("✅ 工程师对话消息通过WebSocket立即传递")
        return True
    elif ws_tester.engineer_messages_received == 1:
        print("⚠️ 只收到用户消息，AI回复可能未通过WebSocket推送")
        return False
    else:
        print("❌ 未收到任何工程师对话消息，WebSocket推送失败")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
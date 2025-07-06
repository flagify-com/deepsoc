#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试工程师对话修复
"""

import requests
import json
import time

def test_engineer_chat():
    base_url = "http://localhost:5007"
    
    # 1. 登录获取token
    login_data = {
        "username": "admin",
        "password": "admin123"
    }
    
    print("=== 登录获取Token ===")
    login_response = requests.post(f"{base_url}/api/auth/login", json=login_data)
    if login_response.status_code != 200:
        print(f"❌ 登录失败: {login_response.status_code}")
        return
    
    token_data = login_response.json()
    if token_data['status'] != 'success':
        print(f"❌ 登录失败: {token_data}")
        return
    
    access_token = token_data['access_token']
    print(f"✅ 登录成功，获取token: {access_token[:20]}...")
    
    # 2. 测试工程师对话API
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    chat_data = {
        "event_id": "1d0528af-6071-4495-a3e9-21fea33da178",
        "message": "测试异步消息发送"
    }
    
    print("\n=== 测试工程师对话发送 ===")
    start_time = time.time()
    
    chat_response = requests.post(f"{base_url}/api/engineer-chat/send", 
                                 json=chat_data, headers=headers)
    
    end_time = time.time()
    response_time = (end_time - start_time) * 1000  # 转换为毫秒
    
    print(f"响应时间: {response_time:.1f}ms")
    print(f"状态码: {chat_response.status_code}")
    
    if chat_response.status_code == 200:
        result = chat_response.json()
        print(f"✅ API调用成功")
        print(f"状态: {result.get('status')}")
        
        # 检查关键字段
        if result.get('status') == 'success':
            data = result.get('data', {})
            print(f"用户消息ID: {data.get('user_message', {}).get('message_id', 'None')}")
            print(f"AI处理中: {data.get('ai_processing', False)}")
            print(f"会话ID: {data.get('session_id', 'None')}")
            
            # 验证响应时间 - 应该小于500ms (异步模式)
            if response_time < 500:
                print(f"✅ 响应时间优秀: {response_time:.1f}ms < 500ms")
            else:
                print(f"⚠️ 响应时间较慢: {response_time:.1f}ms")
        else:
            print(f"⚠️ API返回状态: {result}")
    else:
        print(f"❌ API调用失败: {chat_response.status_code}")
        try:
            error_data = chat_response.json()
            print(f"错误信息: {error_data}")
        except:
            print(f"响应内容: {chat_response.text}")

if __name__ == "__main__":
    test_engineer_chat()
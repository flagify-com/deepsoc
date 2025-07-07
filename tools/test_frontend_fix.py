#!/usr/bin/env python3
"""
前端修复测试脚本
测试发送工程师对话消息，检查console是否还有undefined错误
"""

import requests
import json
import sys

# 配置
SERVER_BASE_URL = "http://localhost:5007"
TEST_EVENT_ID = "test_event_20250704_websocket"
TEST_USERNAME = "test_engineer"

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

def send_test_message(access_token):
    """发送测试工程师对话消息"""
    chat_data = {
        "event_id": TEST_EVENT_ID,
        "message": "@AI 测试前端修复"
    }
    
    headers = {'Authorization': f'Bearer {access_token}'}
    
    try:
        print("📤 发送工程师对话消息...")
        response = requests.post(
            f"{SERVER_BASE_URL}/api/engineer-chat/send", 
            json=chat_data,
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 消息发送成功")
            print(f"会话ID: {data['data']['session_id']}")
            return True
        else:
            print(f"❌ 消息发送失败: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 发送消息请求失败: {e}")
        return False

def main():
    print("🧪 测试前端JavaScript修复")
    print("=" * 50)
    
    # 1. 获取访问令牌
    print("1. 获取访问令牌...")
    access_token = get_test_token()
    if not access_token:
        print("❌ 无法获取访问令牌")
        return False
    
    print(f"✅ 成功获取访问令牌")
    
    # 2. 发送测试消息
    print("\n2. 发送测试消息...")
    if send_test_message(access_token):
        print("\n✅ 测试完成")
        print("🔍 请在浏览器控制台检查：")
        print("   - 不应该有 'Cannot read properties of undefined' 错误")
        print("   - 应该看到 '[addMessage] 消息详情:' 日志")
        print("   - 消息应该正常显示")
        return True
    else:
        print("\n❌ 测试失败")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
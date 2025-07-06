#!/usr/bin/env python3
"""
全局广播测试脚本
直接测试socketio.emit全局广播是否能到达客户端
"""

import requests
import time
import threading

def trigger_global_broadcast():
    """触发一个全局广播测试"""
    print("🚀 触发全局广播测试...")
    
    # 获取访问令牌
    login_data = {"username": "test_engineer", "password": "test123"}
    try:
        response = requests.post("http://localhost:5007/api/auth/login", json=login_data)
        if response.status_code == 200:
            access_token = response.json().get('access_token')
            print(f"✅ 获取访问令牌成功")
            
            # 发送工程师对话消息
            chat_data = {
                "event_id": "test_event_20250704_websocket",
                "message": "@AI 全局广播测试 - 验证socketio.emit能否到达客户端"
            }
            headers = {'Authorization': f'Bearer {access_token}'}
            
            response = requests.post(
                "http://localhost:5007/api/engineer-chat/send", 
                json=chat_data,
                headers=headers
            )
            
            if response.status_code == 200:
                print(f"✅ 消息发送成功，检查客户端是否收到")
                return True
            else:
                print(f"❌ 消息发送失败: {response.text}")
                return False
        else:
            print(f"❌ 登录失败: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return False

if __name__ == "__main__":
    print("🧪 全局广播测试")
    print("=" * 50)
    print("请在另一个终端运行以下命令来监听WebSocket消息:")
    print("python test_websocket_real_time.py")
    print("")
    input("按回车键开始触发全局广播...")
    
    if trigger_global_broadcast():
        print("✅ 全局广播已触发，请检查客户端终端")
    else:
        print("❌ 全局广播触发失败")
#!/usr/bin/env python3
"""
工程师对话功能测试工具
用于验证工程师对话系统的集成和隔离性
"""

import os
import sys
import requests
import json
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.models import db, Event, Message, Summary, User
from app.controllers.engineer_chat_controller import engineer_chat_controller

class EngineerChatTester:
    def __init__(self, base_url='http://127.0.0.1:5007'):
        self.base_url = base_url
        self.access_token = None
        self.test_event_id = None
        self.test_user_id = None
        
    def authenticate(self, username='admin', password='admin123'):
        """认证并获取访问令牌"""
        try:
            response = requests.post(f'{self.base_url}/api/auth/login', 
                json={'username': username, 'password': password})
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    self.access_token = data['data']['access_token']
                    self.test_user_id = data['data']['user']['user_id']
                    print(f"✅ 认证成功: {username}")
                    return True
                else:
                    print(f"❌ 认证失败: {data.get('message')}")
                    return False
            else:
                print(f"❌ 认证请求失败: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ 认证异常: {str(e)}")
            return False
    
    def get_headers(self):
        """获取认证头"""
        return {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.access_token}' if self.access_token else ''
        }
    
    def create_test_event(self):
        """创建测试事件"""
        try:
            event_data = {
                'message': '测试工程师对话功能的安全事件',
                'context': '这是一个用于测试工程师对话功能的模拟安全事件',
                'severity': 'medium',
                'source': 'test_tool'
            }
            
            response = requests.post(f'{self.base_url}/api/event/create', 
                json=event_data, headers=self.get_headers())
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    self.test_event_id = data['data']['event_id']
                    print(f"✅ 测试事件创建成功: {self.test_event_id}")
                    return True
                else:
                    print(f"❌ 创建事件失败: {data.get('message')}")
                    return False
            else:
                print(f"❌ 创建事件请求失败: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ 创建事件异常: {str(e)}")
            return False
    
    def test_engineer_chat_api(self):
        """测试工程师对话API"""
        print("\n📋 测试工程师对话API...")
        
        # 测试发送消息
        test_messages = [
            "你好，AI助手，请介绍一下这个安全事件",
            "这个事件的严重程度是什么？",
            "你建议采取什么措施？"
        ]
        
        for i, message in enumerate(test_messages, 1):
            print(f"\n🔸 测试消息 {i}: {message}")
            
            try:
                response = requests.post(f'{self.base_url}/api/engineer-chat/send',
                    json={'event_id': self.test_event_id, 'message': message},
                    headers=self.get_headers())
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('status') == 'success':
                        print(f"✅ 消息发送成功")
                        print(f"   用户消息ID: {data['data']['user_message']['message_id']}")
                        print(f"   AI回复ID: {data['data']['ai_response']['message_id']}")
                        print(f"   会话ID: {data['data']['session_id']}")
                        print(f"   概要更新: {data['data']['summary_updated']}")
                    else:
                        print(f"❌ 消息发送失败: {data.get('message')}")
                        return False
                else:
                    print(f"❌ 消息发送请求失败: {response.status_code}")
                    print(f"   响应: {response.text}")
                    return False
                    
            except Exception as e:
                print(f"❌ 消息发送异常: {str(e)}")
                return False
        
        return True
    
    def test_chat_history(self):
        """测试对话历史功能"""
        print("\n📋 测试对话历史...")
        
        try:
            response = requests.get(f'{self.base_url}/api/engineer-chat/history',
                params={'event_id': self.test_event_id},
                headers=self.get_headers())
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    history = data['data']['history']
                    print(f"✅ 对话历史获取成功")
                    print(f"   会话ID: {data['data']['session_id']}")
                    print(f"   当前轮次: {data['data']['current_rounds']}")
                    print(f"   最大轮次: {data['data']['max_rounds']}")
                    print(f"   历史消息数: {len(history)}")
                    
                    for i, msg in enumerate(history[-4:], 1):  # 显示最后4条消息
                        sender = "工程师" if msg['sender_type'] == 'user' else "AI助手"
                        content = msg['content']['content'] if isinstance(msg['content'], dict) else str(msg['content'])
                        print(f"   消息{i} [{sender}]: {content[:50]}...")
                    
                    return True
                else:
                    print(f"❌ 获取历史失败: {data.get('message')}")
                    return False
            else:
                print(f"❌ 获取历史请求失败: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ 获取历史异常: {str(e)}")
            return False
    
    def test_chat_status(self):
        """测试对话状态"""
        print("\n📋 测试对话状态...")
        
        try:
            response = requests.get(f'{self.base_url}/api/engineer-chat/status',
                params={'event_id': self.test_event_id},
                headers=self.get_headers())
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    status_data = data['data']
                    print(f"✅ 对话状态获取成功")
                    print(f"   会话ID: {status_data['session_id']}")
                    print(f"   当前轮次: {status_data['current_rounds']}")
                    print(f"   最大轮次: {status_data['max_rounds']}")
                    print(f"   可以对话: {status_data['can_chat']}")
                    print(f"   事件状态: {status_data['event_info']['event_status']}")
                    
                    if status_data['event_summary']['has_summary']:
                        print(f"   有事件概要: 轮次{status_data['event_summary']['round_id']}")
                    else:
                        print(f"   无事件概要")
                    
                    return True
                else:
                    print(f"❌ 获取状态失败: {data.get('message')}")
                    return False
            else:
                print(f"❌ 获取状态请求失败: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ 获取状态异常: {str(e)}")
            return False
    
    def verify_message_isolation(self):
        """验证消息隔离性"""
        print("\n📋 验证消息隔离性...")
        
        try:
            # 获取事件的所有消息
            response = requests.get(f'{self.base_url}/api/event/{self.test_event_id}/messages',
                headers=self.get_headers())
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    messages = data['data']
                    
                    # 统计不同类型的消息
                    agent_messages = [msg for msg in messages if msg.get('message_category') == 'agent']
                    engineer_chat_messages = [msg for msg in messages if msg.get('message_category') == 'engineer_chat']
                    
                    print(f"✅ 消息统计完成")
                    print(f"   总消息数: {len(messages)}")
                    print(f"   Agent消息数: {len(agent_messages)}")
                    print(f"   工程师对话消息数: {len(engineer_chat_messages)}")
                    
                    # 验证工程师对话消息的属性
                    for msg in engineer_chat_messages:
                        if not msg.get('chat_session_id'):
                            print(f"❌ 工程师对话消息缺少会话ID: {msg['message_id']}")
                            return False
                        if not msg.get('sender_type'):
                            print(f"❌ 工程师对话消息缺少发送者类型: {msg['message_id']}")
                            return False
                    
                    print(f"✅ 消息隔离性验证通过")
                    return True
                else:
                    print(f"❌ 获取消息失败: {data.get('message')}")
                    return False
            else:
                print(f"❌ 获取消息请求失败: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ 验证隔离性异常: {str(e)}")
            return False
    
    def run_full_test(self):
        """运行完整测试"""
        print("🚀 开始工程师对话功能测试")
        print("=" * 50)
        
        # 认证
        if not self.authenticate():
            print("❌ 测试失败：无法认证")
            return False
        
        # 创建测试事件
        if not self.create_test_event():
            print("❌ 测试失败：无法创建测试事件")
            return False
        
        # 测试API功能
        if not self.test_engineer_chat_api():
            print("❌ 测试失败：API测试失败")
            return False
        
        # 测试对话历史
        if not self.test_chat_history():
            print("❌ 测试失败：对话历史测试失败")
            return False
        
        # 测试对话状态
        if not self.test_chat_status():
            print("❌ 测试失败：对话状态测试失败")
            return False
        
        # 验证消息隔离性
        if not self.verify_message_isolation():
            print("❌ 测试失败：消息隔离性验证失败")
            return False
        
        print("\n" + "=" * 50)
        print("✅ 工程师对话功能测试全部通过！")
        print(f"   测试事件ID: {self.test_event_id}")
        print(f"   测试时间: {datetime.now().isoformat()}")
        
        return True

def main():
    """主函数"""
    tester = EngineerChatTester()
    
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
        tester.base_url = base_url
        print(f"使用指定的服务地址: {base_url}")
    
    success = tester.run_full_test()
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
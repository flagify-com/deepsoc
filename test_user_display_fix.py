#!/usr/bin/env python3
"""
测试用户名显示修复效果
"""
import sys
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(override=True)

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 创建Flask应用
app = Flask(__name__, 
            static_folder='app/static',
            template_folder='app/templates')

# 配置数据库
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///deepsoc.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 初始化数据库
from app.models import db
db.init_app(app)

from app.models.models import User, Message

def test_user_display_fix():
    """测试用户名显示修复效果"""
    
    with app.app_context():
        print("=== 测试用户名显示修复效果 ===\n")
        
        # 1. 查看现有用户信息
        print("1. 查看现有用户信息:")
        users = User.query.all()
        for user in users:
            print(f"   - 用户ID: {user.user_id}")
            print(f"     用户名: {user.username}")
            print(f"     昵称: {user.nickname}")
            print(f"     角色: {user.role}")
            print()
        
        # 2. 模拟消息显示逻辑
        print("2. 模拟消息显示逻辑:")
        
        # 查找admin用户
        admin_user = User.query.filter_by(username='admin').first()
        if admin_user:
            print(f"   Admin用户消息显示:")
            print(f"     - 昵称存在: {admin_user.nickname}")
            print(f"     - 显示名称: {admin_user.nickname or admin_user.username}")
            print()
        
        # 查找test_engineer用户
        test_user = User.query.filter_by(username='test_engineer').first()
        if test_user:
            print(f"   Test_engineer用户消息显示:")
            print(f"     - 昵称存在: {test_user.nickname}")
            print(f"     - 显示名称: {test_user.nickname or test_user.username}")
            print()
        
        # 3. 测试消息结构
        print("3. 测试消息结构:")
        sample_message = {
            "id": 131,
            "message_id": "1221e171-a927-4c65-ad48-a3fb4dc5800e",
            "event_id": "f82d503b-3984-4134-9561-bc43ad5567b9",
            "user_id": "b0c34a6d-3bc8-4a29-b379-6c53e0decc50",
            "message_from": "user",
            "message_type": "user_message",
            "message_category": "agent"
        }
        
        # 根据user_id查找用户
        user = User.query.filter_by(user_id=sample_message["user_id"]).first()
        if user:
            print(f"   消息中的用户ID对应的用户:")
            print(f"     - 用户名: {user.username}")
            print(f"     - 昵称: {user.nickname}")
            print(f"     - 应该显示: {user.nickname or user.username}")
            print()
        
        # 4. 测试修复后的API响应
        print("4. 测试修复后的API响应结构:")
        if admin_user:
            enhanced_message = {
                **sample_message,
                "user_nickname": admin_user.nickname or admin_user.username,
                "user_username": admin_user.username
            }
            print(f"   Admin用户消息:")
            print(f"     - user_nickname: {enhanced_message.get('user_nickname')}")
            print(f"     - user_username: {enhanced_message.get('user_username')}")
            print()
        
        if test_user:
            enhanced_message = {
                **sample_message,
                "user_id": test_user.user_id,
                "user_nickname": test_user.nickname or test_user.username,
                "user_username": test_user.username
            }
            print(f"   Test_engineer用户消息:")
            print(f"     - user_nickname: {enhanced_message.get('user_nickname')}")
            print(f"     - user_username: {enhanced_message.get('user_username')}")
            print()
        
        print("=== 测试完成 ===")

if __name__ == "__main__":
    test_user_display_fix()
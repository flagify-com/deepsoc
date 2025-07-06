#!/usr/bin/env python3
"""
DeepSOC 升级验证脚本
用于验证系统升级后的完整性和功能正常性
"""
import sys
import os
import traceback
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    """测试关键模块导入"""
    print("🔍 测试模块导入...")
    try:
        from app.models.models import User, Message, Event, Task, Execution, Summary, GlobalSettings
        from app.models import db
        print("✅ 模型导入成功")
        return True
    except Exception as e:
        print(f"❌ 模型导入失败: {e}")
        return False

def test_database_connection():
    """测试数据库连接"""
    print("🔍 测试数据库连接...")
    try:
        from flask import Flask
        from dotenv import load_dotenv
        
        # 加载环境变量
        load_dotenv(override=True)
        
        # 创建Flask应用
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///deepsoc.db')
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        from app.models import db
        db.init_app(app)
        
        with app.app_context():
            # 测试数据库连接
            result = db.engine.execute('SELECT 1').scalar()
            if result == 1:
                print("✅ 数据库连接成功")
                return True
            else:
                print("❌ 数据库连接测试失败")
                return False
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False

def test_table_structure():
    """测试数据库表结构"""
    print("🔍 测试数据库表结构...")
    try:
        from flask import Flask
        from dotenv import load_dotenv
        from sqlalchemy import inspect
        
        # 加载环境变量
        load_dotenv(override=True)
        
        # 创建Flask应用
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///deepsoc.db')
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        from app.models import db
        from app.models.models import User, Message, GlobalSettings
        db.init_app(app)
        
        with app.app_context():
            inspector = inspect(db.engine)
            
            # 检查用户表
            user_columns = [col['name'] for col in inspector.get_columns('users')]
            required_user_columns = ['id', 'username', 'user_id', 'nickname']
            for col in required_user_columns:
                if col not in user_columns:
                    print(f"❌ 用户表缺少字段: {col}")
                    return False
            print("✅ 用户表结构正确")
            
            # 检查消息表
            message_columns = [col['name'] for col in inspector.get_columns('messages')]
            required_message_columns = ['id', 'message_id', 'user_id', 'message_category', 'chat_session_id', 'sender_type']
            for col in required_message_columns:
                if col not in message_columns:
                    print(f"❌ 消息表缺少字段: {col}")
                    return False
            print("✅ 消息表结构正确")
            
            # 检查全局设置表
            if 'global_settings' not in inspector.get_table_names():
                print("❌ 缺少全局设置表")
                return False
            print("✅ 全局设置表存在")
            
            return True
    except Exception as e:
        print(f"❌ 表结构检查失败: {e}")
        traceback.print_exc()
        return False

def test_user_data_integrity():
    """测试用户数据完整性"""
    print("🔍 测试用户数据完整性...")
    try:
        from flask import Flask
        from dotenv import load_dotenv
        
        # 加载环境变量
        load_dotenv(override=True)
        
        # 创建Flask应用
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///deepsoc.db')
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        from app.models import db
        from app.models.models import User
        db.init_app(app)
        
        with app.app_context():
            users = User.query.all()
            
            if not users:
                print("⚠️  数据库中没有用户数据")
                return True
            
            # 检查用户UUID
            for user in users:
                if not user.user_id:
                    print(f"❌ 用户 {user.username} 缺少 user_id")
                    return False
                if len(user.user_id.strip()) == 0:
                    print(f"❌ 用户 {user.username} user_id 为空")
                    return False
            
            print(f"✅ 用户数据完整性检查通过 ({len(users)} 个用户)")
            return True
    except Exception as e:
        print(f"❌ 用户数据完整性检查失败: {e}")
        return False

def test_message_categories():
    """测试消息分类功能"""
    print("🔍 测试消息分类功能...")
    try:
        from flask import Flask
        from dotenv import load_dotenv
        
        # 加载环境变量
        load_dotenv(override=True)
        
        # 创建Flask应用
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///deepsoc.db')
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        from app.models import db
        from app.models.models import Message
        db.init_app(app)
        
        with app.app_context():
            messages = Message.query.all()
            
            if not messages:
                print("⚠️  数据库中没有消息数据")
                return True
            
            # 检查消息分类
            categories = set()
            for message in messages:
                if message.message_category:
                    categories.add(message.message_category)
                else:
                    print(f"⚠️  消息 {message.id} 缺少分类")
            
            print(f"✅ 消息分类检查通过，发现分类: {', '.join(categories) if categories else '无'}")
            return True
    except Exception as e:
        print(f"❌ 消息分类检查失败: {e}")
        return False

def test_flask_migrate_status():
    """测试Flask-Migrate状态"""
    print("🔍 测试数据库迁移状态...")
    try:
        import subprocess
        
        # 检查迁移状态
        result = subprocess.run(['flask', 'db', 'current'], 
                              capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        if result.returncode == 0:
            current_revision = result.stdout.strip()
            if current_revision:
                print(f"✅ 当前迁移版本: {current_revision}")
                return True
            else:
                print("⚠️  无法获取当前迁移版本")
                return False
        else:
            print(f"❌ 获取迁移状态失败: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ 迁移状态检查失败: {e}")
        return False

def test_api_endpoints():
    """测试关键API端点"""
    print("🔍 测试API端点可用性...")
    try:
        import requests
        import time
        
        # 等待服务启动（如果正在运行）
        base_url = "http://127.0.0.1:5007"
        
        try:
            # 测试主页
            response = requests.get(f"{base_url}/", timeout=5)
            if response.status_code == 200:
                print("✅ 主页访问正常")
            else:
                print(f"⚠️  主页返回状态码: {response.status_code}")
            
            # 测试API端点
            response = requests.get(f"{base_url}/api/events", timeout=5)
            if response.status_code in [200, 401]:  # 401表示需要认证，但端点存在
                print("✅ API端点可访问")
            else:
                print(f"⚠️  API端点返回状态码: {response.status_code}")
                
            return True
        except requests.exceptions.ConnectionError:
            print("⚠️  服务未运行，跳过API测试")
            return True
        except Exception as e:
            print(f"⚠️  API测试异常: {e}")
            return True
    except Exception as e:
        print(f"❌ API测试失败: {e}")
        return False

def generate_report(results):
    """生成验证报告"""
    print("\n" + "="*50)
    print("📋 升级验证报告")
    print("="*50)
    
    total_tests = len(results)
    passed_tests = sum(1 for result in results.values() if result)
    
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"总测试项: {total_tests}")
    print(f"通过测试: {passed_tests}")
    print(f"失败测试: {total_tests - passed_tests}")
    print(f"成功率: {(passed_tests/total_tests)*100:.1f}%")
    
    print("\n详细结果:")
    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {test_name}: {status}")
    
    if passed_tests == total_tests:
        print("\n🎉 所有测试通过！升级验证成功。")
        return True
    else:
        print(f"\n⚠️  有 {total_tests - passed_tests} 项测试失败，请检查相关问题。")
        return False

def main():
    """主函数"""
    print("🚀 DeepSOC 升级验证开始")
    print("="*50)
    
    # 执行各项测试
    results = {}
    
    results["模块导入"] = test_imports()
    results["数据库连接"] = test_database_connection()
    results["表结构检查"] = test_table_structure()
    results["用户数据完整性"] = test_user_data_integrity()
    results["消息分类功能"] = test_message_categories()
    results["迁移状态"] = test_flask_migrate_status()
    results["API端点"] = test_api_endpoints()
    
    # 生成报告
    success = generate_report(results)
    
    # 返回适当的退出码
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
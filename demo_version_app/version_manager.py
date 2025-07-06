#!/usr/bin/env python3
"""
简化版本管理工具
"""
import re
import argparse
import sys
import os
from datetime import datetime

def get_current_version():
    """获取当前版本"""
    if not os.path.exists('version.py'):
        print("错误: 找不到 version.py 文件")
        sys.exit(1)
        
    with open('version.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    match = re.search(r'__version__ = ["\']([^"\']+)["\']', content)
    if match:
        return match.group(1)
    raise ValueError("无法找到版本号")

def update_version(new_version):
    """更新版本文件"""
    try:
        major, minor, patch = map(int, new_version.split('.'))
    except ValueError:
        print(f"错误: 版本号格式不正确: {{new_version}}")
        print("正确格式: major.minor.patch (例如: 1.2.3)")
        sys.exit(1)
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    with open('version.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 更新版本信息
    content = re.sub(r'__version__ = ["\'][^"\']+["\']', f'__version__ = "{{new_version}}"', content)
    content = re.sub(r'__version_info__ = \([^)]+\)', f'__version_info__ = ({{major}}, {{minor}}, {{patch}})', content)
    content = re.sub(r'VERSION_MAJOR = \d+', f'VERSION_MAJOR = {{major}}', content)
    content = re.sub(r'VERSION_MINOR = \d+', f'VERSION_MINOR = {{minor}}', content)
    content = re.sub(r'VERSION_PATCH = \d+', f'VERSION_PATCH = {{patch}}', content)
    content = re.sub(r'"build_date": "[^"]*"', f'"build_date": "{{today}}"', content)
    
    with open('version.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ 版本已更新为: {{new_version}}")

def bump_version(bump_type):
    """升级版本号"""
    current = get_current_version()
    major, minor, patch = map(int, current.split('.'))
    
    if bump_type == 'major':
        major += 1
        minor = 0
        patch = 0
    elif bump_type == 'minor':
        minor += 1
        patch = 0
    elif bump_type == 'patch':
        patch += 1
    else:
        print(f"错误: 不支持的升级类型: {{bump_type}}")
        print("支持的类型: major, minor, patch")
        sys.exit(1)
    
    new_version = f"{{major}}.{{minor}}.{{patch}}"
    update_version(new_version)
    return new_version

def show_version():
    """显示版本信息"""
    try:
        # 导入version模块
        if 'version' in sys.modules:
            del sys.modules['version']
        
        import version
        info = version.get_version_info()
        
        print("📋 当前版本信息")
        print("=" * 40)
        for key, value in info.items():
            print(f"{{key}}: {{value}}")
            
    except ImportError:
        current = get_current_version()
        print(f"当前版本: {{current}}")

def create_git_tag(version, message=None):
    """创建Git标签"""
    try:
        import subprocess
        
        tag_name = f"v{{version}}"
        tag_message = message or f"Release {{version}}"
        
        # 检查是否在git仓库中
        result = subprocess.run(['git', 'rev-parse', '--git-dir'], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            print("⚠️  不在Git仓库中，跳过标签创建")
            return
        
        # 创建标签
        subprocess.check_call(['git', 'tag', '-a', tag_name, '-m', tag_message])
        print(f"✅ Git标签已创建: {{tag_name}}")
        
        # 提示推送标签
        print(f"💡 运行以下命令推送标签到远程仓库:")
        print(f"   git push origin {{tag_name}}")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ 创建Git标签失败: {{e}}")
    except FileNotFoundError:
        print("⚠️  Git未安装，跳过标签创建")

def main():
    parser = argparse.ArgumentParser(description='简化版本管理工具')
    parser.add_argument('action', choices=['show', 'patch', 'minor', 'major', 'set', 'tag'], 
                       help='操作类型')
    parser.add_argument('version', nargs='?', help='版本号 (用于set命令)')
    parser.add_argument('--tag', action='store_true', help='自动创建Git标签')
    parser.add_argument('--message', help='Git标签信息')
    
    args = parser.parse_args()
    
    if args.action == 'show':
        show_version()
    elif args.action == 'set':
        if not args.version:
            print("错误: set命令需要提供版本号")
            print("示例: python version_manager.py set 1.2.3")
            return
        update_version(args.version)
        if args.tag:
            create_git_tag(args.version, args.message)
    elif args.action == 'tag':
        current = get_current_version()
        create_git_tag(current, args.message)
    else:
        old_version = get_current_version()
        new_version = bump_version(args.action)
        print(f"版本已升级: {{old_version}} → {{new_version}}")
        if args.tag:
            create_git_tag(new_version, args.message)

if __name__ == '__main__':
    main()

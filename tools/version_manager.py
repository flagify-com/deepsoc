#!/usr/bin/env python3
"""
DeepSOC 版本管理工具
用于更新版本号、生成版本信息等
"""
import os
import sys
import re
import argparse
import datetime
from typing import Tuple

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_current_version() -> str:
    """获取当前版本号"""
    version_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'app', '_version.py')
    with open(version_file, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # 查找版本号
    match = re.search(r'__version__ = ["\']([^"\']+)["\']', content)
    if match:
        return match.group(1)
    else:
        raise ValueError("无法找到版本号")

def parse_version(version: str) -> Tuple[int, int, int]:
    """解析版本号"""
    parts = version.split('.')
    if len(parts) != 3:
        raise ValueError(f"版本号格式错误: {version}")
    
    try:
        return tuple(int(part) for part in parts)
    except ValueError:
        raise ValueError(f"版本号格式错误: {version}")

def bump_version(version: str, bump_type: str) -> str:
    """升级版本号"""
    major, minor, patch = parse_version(version)
    
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
        raise ValueError(f"不支持的升级类型: {bump_type}")
    
    return f"{major}.{minor}.{patch}"

def update_version_file(new_version: str, release_name: str = None):
    """更新版本文件"""
    version_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'app', '_version.py')
    
    # 读取当前文件内容
    with open(version_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 解析版本号
    major, minor, patch = parse_version(new_version)
    build_date = datetime.datetime.now().strftime('%Y-%m-%d')
    
    # 更新版本信息
    content = re.sub(r'__version__ = ["\'][^"\']+["\']', f'__version__ = "{new_version}"', content)
    content = re.sub(r'__version_info__ = \([^)]+\)', f'__version_info__ = ({major}, {minor}, {patch})', content)
    content = re.sub(r'VERSION_MAJOR = \d+', f'VERSION_MAJOR = {major}', content)
    content = re.sub(r'VERSION_MINOR = \d+', f'VERSION_MINOR = {minor}', content)
    content = re.sub(r'VERSION_PATCH = \d+', f'VERSION_PATCH = {patch}', content)
    content = re.sub(r'"build_date": "[^"]*"', f'"build_date": "{build_date}"', content)
    
    if release_name:
        content = re.sub(r'"release_name": "[^"]*"', f'"release_name": "{release_name}"', content)
    
    # 写入文件
    with open(version_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ 版本文件已更新: {new_version}")


def update_changelog(new_version: str, release_name: str = None):
    """更新changelog.md"""
    changelog_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'changelog.md')
    
    if not os.path.exists(changelog_file):
        print("⚠️  changelog.md 不存在，跳过更新")
        return
    
    with open(changelog_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 准备新的版本条目
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    version_header = f"## [{new_version}] - {today}"
    if release_name:
        version_header += f" - {release_name}"
    
    # 在"## [未发布]"后面添加新版本
    if "## [未发布]" in content:
        content = content.replace("## [未发布]", f"## [未发布]\n\n{version_header}\n\n### 更新内容\n- TODO: 添加更新内容\n")
    else:
        # 如果没有"未发布"部分，在开头添加
        lines = content.split('\n')
        header_index = -1
        for i, line in enumerate(lines):
            if line.startswith('## '):
                header_index = i
                break
        
        if header_index >= 0:
            lines.insert(header_index, f"{version_header}\n")
            lines.insert(header_index + 1, "### 更新内容")
            lines.insert(header_index + 2, "- TODO: 添加更新内容\n")
            content = '\n'.join(lines)
    
    with open(changelog_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ changelog.md 已更新")

def get_git_info():
    """获取Git信息"""
    try:
        import subprocess
        
        # 获取当前提交哈希
        commit_hash = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode().strip()[:8]
        
        # 获取当前分支
        branch = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD']).decode().strip()
        
        # 检查是否有未提交的更改
        status = subprocess.check_output(['git', 'status', '--porcelain']).decode().strip()
        dirty = len(status) > 0
        
        return {
            'commit_hash': commit_hash,
            'branch': branch,
            'dirty': dirty
        }
    except Exception as e:
        print(f"⚠️  无法获取Git信息: {e}")
        return None

def show_version_info():
    """显示版本信息"""
    try:
        from app._version import get_version_info
        from app import __version__
        
        print("📋 当前版本信息")
        print("=" * 40)
        
        version_info = get_version_info()
        for key, value in version_info.items():
            print(f"{key}: {value}")
        
        git_info = get_git_info()
        if git_info:
            print(f"git_branch: {git_info['branch']}")
            print(f"git_commit: {git_info['commit_hash']}")
            print(f"git_dirty: {git_info['dirty']}")
            
    except Exception as e:
        print(f"❌ 无法获取版本信息: {e}")

def create_git_tag(version: str, message: str = None):
    """创建Git标签"""
    try:
        import subprocess
        
        tag_name = f"v{version}"
        tag_message = message or f"Release {version}"
        
        # 创建标签
        subprocess.check_call(['git', 'tag', '-a', tag_name, '-m', tag_message])
        print(f"✅ Git标签已创建: {tag_name}")
        
        # 提示推送标签
        print(f"💡 运行以下命令推送标签到远程仓库:")
        print(f"   git push origin {tag_name}")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ 创建Git标签失败: {e}")
    except Exception as e:
        print(f"❌ 创建Git标签时出错: {e}")

def main():
    parser = argparse.ArgumentParser(description='DeepSOC 版本管理工具')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 显示版本信息
    subparsers.add_parser('show', help='显示当前版本信息')
    
    # 升级版本
    bump_parser = subparsers.add_parser('bump', help='升级版本号')
    bump_parser.add_argument('type', choices=['major', 'minor', 'patch'], help='升级类型')
    bump_parser.add_argument('--release-name', help='发布名称')
    bump_parser.add_argument('--no-changelog', action='store_true', help='不更新changelog')
    bump_parser.add_argument('--no-tag', action='store_true', help='不创建Git标签')
    
    # 设置版本
    set_parser = subparsers.add_parser('set', help='设置特定版本号')
    set_parser.add_argument('version', help='版本号 (例如: 1.2.3)')
    set_parser.add_argument('--release-name', help='发布名称')
    set_parser.add_argument('--no-changelog', action='store_true', help='不更新changelog')
    set_parser.add_argument('--no-tag', action='store_true', help='不创建Git标签')
    
    # 创建标签
    tag_parser = subparsers.add_parser('tag', help='为当前版本创建Git标签')
    tag_parser.add_argument('--message', help='标签信息')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == 'show':
        show_version_info()
        
    elif args.command == 'bump':
        current_version = get_current_version()
        new_version = bump_version(current_version, args.type)
        
        print(f"🔄 升级版本: {current_version} → {new_version}")
        
        # 更新版本文件
        update_version_file(new_version, args.release_name)
        
        # 更新changelog
        if not args.no_changelog:
            update_changelog(new_version, args.release_name)
        
        # 创建Git标签
        if not args.no_tag:
            create_git_tag(new_version, args.release_name)
        
        print(f"🎉 版本升级完成: {new_version}")
        
    elif args.command == 'set':
        # 验证版本号格式
        parse_version(args.version)
        
        current_version = get_current_version()
        print(f"🔄 设置版本: {current_version} → {args.version}")
        
        # 更新版本文件
        update_version_file(args.version, args.release_name)
        
        # 更新changelog
        if not args.no_changelog:
            update_changelog(args.version, args.release_name)
        
        # 创建Git标签
        if not args.no_tag:
            create_git_tag(args.version, args.release_name)
        
        print(f"🎉 版本设置完成: {args.version}")
        
    elif args.command == 'tag':
        current_version = get_current_version()
        create_git_tag(current_version, args.message)

if __name__ == '__main__':
    main()
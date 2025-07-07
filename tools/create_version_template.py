#!/usr/bin/env python3
"""
创建简化版本管理模板
为任何Python项目快速生成版本管理文件
"""
import os
import argparse
from pathlib import Path

# 版本文件模板
VERSION_PY_TEMPLATE = '''"""
{project_name} 版本信息
"""

__version__ = "{initial_version}"
__version_info__ = {version_tuple}

# 版本元数据
VERSION_MAJOR = {major}
VERSION_MINOR = {minor}
VERSION_PATCH = {patch}

def get_version():
    """获取版本字符串"""
    return f"{{VERSION_MAJOR}}.{{VERSION_MINOR}}.{{VERSION_PATCH}}"

def get_version_info():
    """获取版本详细信息"""
    import datetime
    import platform
    import sys
    
    return {{
        "version": get_version(),
        "version_tuple": (VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH),
        "build_date": "{build_date}",
        "python_version": platform.python_version(),
        "platform": platform.system(),
        "description": "{description}",
        "project_name": "{project_name}"
    }}

def print_version():
    """打印版本信息"""
    info = get_version_info()
    print("=" * 50)
    print(f"🚀 {{info['project_name']}} - {{info['description']}}")
    print("=" * 50)
    print(f"版本: {{info['version']}}")
    print(f"构建日期: {{info['build_date']}}")
    print(f"Python版本: {{info['python_version']}}")
    print(f"运行平台: {{info['platform']}}")
    print("=" * 50)

# 版本比较函数
def version_compare(version1, version2):
    """比较两个版本号"""
    def normalize(v):
        return [int(x) for x in v.split('.')]
    
    v1_parts = normalize(version1)
    v2_parts = normalize(version2)
    
    # 补齐长度
    max_len = max(len(v1_parts), len(v2_parts))
    v1_parts.extend([0] * (max_len - len(v1_parts)))
    v2_parts.extend([0] * (max_len - len(v2_parts)))
    
    if v1_parts < v2_parts:
        return -1
    elif v1_parts > v2_parts:
        return 1
    else:
        return 0
'''

# 版本管理器模板
VERSION_MANAGER_TEMPLATE = '''#!/usr/bin/env python3
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
    
    match = re.search(r'__version__ = ["\\\']([^"\\\']+)["\\\']', content)
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
    content = re.sub(r'__version__ = ["\\\'][^"\\\']+["\\\']', f'__version__ = "{{new_version}}"', content)
    content = re.sub(r'__version_info__ = \\([^)]+\\)', f'__version_info__ = ({{major}}, {{minor}}, {{patch}})', content)
    content = re.sub(r'VERSION_MAJOR = \\d+', f'VERSION_MAJOR = {{major}}', content)
    content = re.sub(r'VERSION_MINOR = \\d+', f'VERSION_MINOR = {{minor}}', content)
    content = re.sub(r'VERSION_PATCH = \\d+', f'VERSION_PATCH = {{patch}}', content)
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
'''

# 主程序示例模板
MAIN_PY_TEMPLATE = '''#!/usr/bin/env python3
"""
{project_name} 主程序
"""
import argparse
import sys
from version import __version__, print_version

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='{description}')
    parser.add_argument('--version', action='store_true', help='显示版本信息')
    
    args = parser.parse_args()
    
    if args.version:
        print_version()
        return
    
    # 启动时显示版本
    print(f"🚀 {project_name} v{{__version__}} 启动")
    
    # 你的应用逻辑在这里
    print("应用运行中...")
    print("使用 --version 查看版本信息")

if __name__ == '__main__':
    main()
'''

# README模板
README_TEMPLATE = '''# {project_name}

{description}

## 版本信息

当前版本: {initial_version}

## 安装和运行

```bash
# 运行应用
python main.py

# 查看版本信息
python main.py --version
```

## 版本管理

```bash
# 查看当前版本
python version_manager.py show

# 升级版本
python version_manager.py patch   # 1.0.0 → 1.0.1
python version_manager.py minor   # 1.0.0 → 1.1.0
python version_manager.py major   # 1.0.0 → 2.0.0

# 设置特定版本
python version_manager.py set 1.5.0

# 创建Git标签
python version_manager.py tag
```

## 更新日志

### [{initial_version}] - {build_date}
- 初始版本
'''

def create_template(target_dir, project_name, description, initial_version):
    """创建版本管理模板"""
    
    # 解析版本号
    try:
        major, minor, patch = map(int, initial_version.split('.'))
    except ValueError:
        print(f"错误: 版本号格式不正确: {initial_version}")
        return False
    
    # 创建目标目录
    target_path = Path(target_dir)
    target_path.mkdir(parents=True, exist_ok=True)
    
    # 获取当前日期
    build_date = datetime.now().strftime('%Y-%m-%d')
    
    # 模板变量
    template_vars = {
        'project_name': project_name,
        'description': description,
        'initial_version': initial_version,
        'version_tuple': f"({major}, {minor}, {patch})",
        'major': major,
        'minor': minor,
        'patch': patch,
        'build_date': build_date
    }
    
    # 创建文件
    files = {
        'version.py': VERSION_PY_TEMPLATE.format(**template_vars),
        'version_manager.py': VERSION_MANAGER_TEMPLATE,
        'main.py': MAIN_PY_TEMPLATE.format(**template_vars),
        'README.md': README_TEMPLATE.format(**template_vars)
    }
    
    created_files = []
    for filename, content in files.items():
        file_path = target_path / filename
        
        if file_path.exists():
            response = input(f"文件 {filename} 已存在，是否覆盖？ (y/N): ")
            if response.lower() != 'y':
                print(f"⏭️  跳过 {filename}")
                continue
        
        file_path.write_text(content, encoding='utf-8')
        created_files.append(filename)
        
        # 为Python脚本添加执行权限
        if filename.endswith('.py') and filename != 'version.py':
            os.chmod(file_path, 0o755)
    
    print(f"\n✅ 版本管理模板创建完成！")
    print(f"📁 目标目录: {target_path.absolute()}")
    print(f"📄 创建的文件: {', '.join(created_files)}")
    
    print(f"\n🚀 快速开始:")
    print(f"   cd {target_dir}")
    print(f"   python main.py --version")
    print(f"   python version_manager.py show")
    
    return True

def main():
    parser = argparse.ArgumentParser(description='创建简化版本管理模板')
    parser.add_argument('target_dir', help='目标目录')
    parser.add_argument('--name', required=True, help='项目名称')
    parser.add_argument('--description', default='A Python application', help='项目描述')
    parser.add_argument('--version', default='1.0.0', help='初始版本号')
    
    args = parser.parse_args()
    
    print(f"🛠️  正在创建版本管理模板...")
    print(f"   项目名称: {args.name}")
    print(f"   项目描述: {args.description}")
    print(f"   初始版本: {args.version}")
    print(f"   目标目录: {args.target_dir}")
    
    success = create_template(args.target_dir, args.name, args.description, args.version)
    
    if success:
        print(f"\n🎉 模板创建成功！现在你可以：")
        print(f"   1. 开发你的应用功能")
        print(f"   2. 使用 version_manager.py 管理版本")
        print(f"   3. 在应用中导入 version 模块获取版本信息")

if __name__ == '__main__':
    from datetime import datetime
    main()
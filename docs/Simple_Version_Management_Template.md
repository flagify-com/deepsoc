# 简化版本管理模板

## 适用场景

这套模板适用于：
- Web应用
- 桌面应用
- 微服务
- 内部工具
- API服务
- 任何需要版本追踪的软件项目

## 最小化实现

### 1. 创建版本文件 `version.py`

```python
"""
应用版本信息
"""

__version__ = "1.0.0"
__version_info__ = (1, 0, 0)

# 版本元数据
VERSION_MAJOR = 1
VERSION_MINOR = 0
VERSION_PATCH = 0

def get_version():
    """获取版本字符串"""
    return f"{VERSION_MAJOR}.{VERSION_MINOR}.{VERSION_PATCH}"

def get_version_info():
    """获取版本详细信息"""
    import datetime
    import platform
    
    return {
        "version": get_version(),
        "version_tuple": (VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH),
        "build_date": "2025-07-06",  # 可以通过CI自动设置
        "python_version": platform.python_version(),
        "platform": platform.system(),
        "description": "Your Application Description"
    }

def print_version():
    """打印版本信息"""
    info = get_version_info()
    print(f"应用版本: {info['version']}")
    print(f"构建日期: {info['build_date']}")
    print(f"Python版本: {info['python_version']}")
    print(f"运行平台: {info['platform']}")
```

### 2. 在主程序中使用

```python
# main.py 或 app.py
from version import __version__, get_version_info, print_version
import argparse

def main():
    parser = argparse.ArgumentParser(description='Your Application')
    parser.add_argument('--version', action='store_true', help='显示版本信息')
    args = parser.parse_args()
    
    if args.version:
        print_version()
        return
    
    # 启动时显示版本
    print(f"🚀 Your Application v{__version__} 启动")
    
    # 你的应用逻辑
    print("应用运行中...")

if __name__ == '__main__':
    main()
```

### 3. Web应用中显示版本

```python
# Flask示例
from flask import Flask, jsonify, render_template
from version import __version__, get_version_info

app = Flask(__name__)

@app.route('/api/version')
def api_version():
    return jsonify({
        'status': 'success',
        'data': get_version_info()
    })

@app.route('/')
def index():
    return render_template('index.html', version=__version__)

# 在HTML模板中显示
# <footer>Your App v{{ version }}</footer>
```

### 4. 简化版本管理脚本

```python
#!/usr/bin/env python3
"""
简化版本管理工具
"""
import re
import argparse
from datetime import datetime

def get_current_version():
    """获取当前版本"""
    with open('version.py', 'r') as f:
        content = f.read()
    
    match = re.search(r'__version__ = ["\']([^"\']+)["\']', content)
    if match:
        return match.group(1)
    raise ValueError("无法找到版本号")

def update_version(new_version):
    """更新版本文件"""
    major, minor, patch = map(int, new_version.split('.'))
    today = datetime.now().strftime('%Y-%m-%d')
    
    with open('version.py', 'r') as f:
        content = f.read()
    
    # 更新版本信息
    content = re.sub(r'__version__ = ["\'][^"\']+["\']', f'__version__ = "{new_version}"', content)
    content = re.sub(r'__version_info__ = \([^)]+\)', f'__version_info__ = ({major}, {minor}, {patch})', content)
    content = re.sub(r'VERSION_MAJOR = \d+', f'VERSION_MAJOR = {major}', content)
    content = re.sub(r'VERSION_MINOR = \d+', f'VERSION_MINOR = {minor}', content)
    content = re.sub(r'VERSION_PATCH = \d+', f'VERSION_PATCH = {patch}', content)
    content = re.sub(r'"build_date": "[^"]*"', f'"build_date": "{today}"', content)
    
    with open('version.py', 'w') as f:
        f.write(content)
    
    print(f"✅ 版本已更新为: {new_version}")

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
    
    new_version = f"{major}.{minor}.{patch}"
    update_version(new_version)
    return new_version

def main():
    parser = argparse.ArgumentParser(description='版本管理工具')
    parser.add_argument('action', choices=['show', 'patch', 'minor', 'major', 'set'])
    parser.add_argument('version', nargs='?', help='版本号 (用于set命令)')
    
    args = parser.parse_args()
    
    if args.action == 'show':
        print(f"当前版本: {get_current_version()}")
    elif args.action == 'set':
        if not args.version:
            print("错误: set命令需要提供版本号")
            return
        update_version(args.version)
    else:
        new_version = bump_version(args.action)
        print(f"版本已升级为: {new_version}")

if __name__ == '__main__':
    main()
```

## 实际使用方法

### 日常开发流程

```bash
# 1. 查看当前版本
python version_manager.py show

# 2. 开发功能...

# 3. 发布时升级版本
python version_manager.py patch   # 1.0.0 → 1.0.1 (bug修复)
python version_manager.py minor   # 1.0.0 → 1.1.0 (新功能)
python version_manager.py major   # 1.0.0 → 2.0.0 (重大变更)

# 4. 或直接设置版本
python version_manager.py set 1.5.0

# 5. 运行应用检查版本
python main.py --version
```

### Git集成

```bash
# 提交代码
git add .
git commit -m "feat: 添加新功能"

# 升级版本
python version_manager.py minor

# 创建标签
git tag v$(python version_manager.py show | cut -d' ' -f3)

# 推送
git push origin main --tags
```

### CI/CD集成

```yaml
# .github/workflows/release.yml
name: Release
on:
  push:
    tags: ['v*']

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    
    - name: Get version
      id: version
      run: echo "::set-output name=version::$(python version_manager.py show)"
    
    - name: Build application
      run: |
        # 构建步骤
        echo "Building version ${{ steps.version.outputs.version }}"
    
    - name: Create Release
      uses: actions/create-release@v1
      with:
        tag_name: ${{ github.ref }}
        release_name: Release ${{ steps.version.outputs.version }}
```

## 不同类型应用的适配

### Web应用
```html
<!-- 在页面底部显示版本 -->
<footer>
    <small>MyApp v<span id="version">1.0.0</span></small>
</footer>

<script>
fetch('/api/version')
    .then(r => r.json())
    .then(data => {
        document.getElementById('version').textContent = data.data.version;
    });
</script>
```

### API服务
```python
@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'version': __version__,
        'timestamp': datetime.now().isoformat()
    })
```

### 桌面应用 (tkinter/PyQt)
```python
import tkinter as tk
from version import __version__

class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"MyApp v{__version__}")
        
        # 在帮助菜单中显示版本
        menubar = tk.Menu(self.root)
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="关于", command=self.show_about)
        menubar.add_cascade(label="帮助", menu=help_menu)
        self.root.config(menu=menubar)
    
    def show_about(self):
        from version import get_version_info
        info = get_version_info()
        message = f"MyApp\n版本: {info['version']}\n构建日期: {info['build_date']}"
        tk.messagebox.showinfo("关于", message)
```

### 微服务
```python
# 在日志中记录版本
import logging
from version import __version__

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    logger.info(f"微服务启动 - 版本: {__version__}")
    # 服务逻辑
```

## 团队协作建议

### 1. 版本命名约定
- **补丁版本**：bug修复，向下兼容
- **次版本**：新功能，向下兼容  
- **主版本**：重大变更，可能不兼容

### 2. 发布流程
1. 功能开发完成
2. 运行测试
3. 升级版本号
4. 更新CHANGELOG.md
5. 创建Git标签
6. 部署发布

### 3. 版本策略
- **开发环境**：可以使用开发版本号 (如 1.1.0-dev)
- **测试环境**：使用预发布版本号 (如 1.1.0-beta.1)
- **生产环境**：只使用正式版本号 (如 1.1.0)

## 监控和维护

### 版本使用统计
```python
# 在应用启动时记录版本信息
import logging
from version import __version__

def log_startup():
    logging.info(f"应用启动 - 版本: {__version__}")
    
    # 可选：发送到监控系统
    # send_to_monitoring("app_start", {"version": __version__})
```

### 版本兼容性检查
```python
def check_compatibility():
    """检查配置文件或数据库版本兼容性"""
    current_version = get_version()
    config_version = load_config_version()
    
    if not is_compatible(current_version, config_version):
        print("警告：配置版本与应用版本不兼容")
        print(f"应用版本: {current_version}")
        print(f"配置版本: {config_version}")
```

这套简化的版本管理方案可以轻松适配到任何Python项目中，提供基本但完整的版本管理功能。
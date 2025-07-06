# DeepSOC 版本管理指南

## 概述

DeepSOC 采用语义化版本管理（Semantic Versioning），提供完整的版本信息系统，包括命令行显示、Web界面显示、API接口等多种方式来查看和管理版本信息。

## 版本号规范

DeepSOC 遵循 [语义化版本](https://semver.org/lang/zh-CN/) 规范：

```
主版本号.次版本号.修订号 (MAJOR.MINOR.PATCH)
```

- **主版本号 (MAJOR)**：不兼容的API修改
- **次版本号 (MINOR)**：向下兼容的功能性新增
- **修订号 (PATCH)**：向下兼容的问题修正

### 版本示例

- `1.0.0` - 初始发布版本
- `1.1.0` - 增加工程师聊天功能
- `1.1.1` - 修复消息显示问题
- `2.0.0` - 重大架构调整

## 版本信息架构

### 1. 核心版本文件

#### `app/_version.py`

这是版本信息的核心文件，包含：

```python
__version__ = "1.1.0"
__version_info__ = (1, 1, 0)

VERSION_MAJOR = 1
VERSION_MINOR = 1
VERSION_PATCH = 0
VERSION_BUILD = None
```

#### `app/__init__.py`

向外暴露版本信息：

```python
from ._version import (
    __version__,
    __version_info__,
    get_version,
    get_version_info
)
```

### 2. 版本信息获取

#### 编程方式获取

```python
from app import __version__, get_version_info

# 获取版本号
print(__version__)  # "1.1.0"

# 获取详细版本信息
info = get_version_info()
print(info['version'])      # "1.1.0"
print(info['release_name']) # "Enhanced User Experience"
print(info['build_date'])   # "2025-07-06"
```

#### 命令行获取

```bash
# 显示详细版本信息
python main.py -version

# 使用版本管理工具
python tools/version_manager.py show
```

#### API接口获取

```bash
# GET请求获取版本信息
curl http://127.0.0.1:5007/api/version
```

响应格式：
```json
{
  "status": "success",
  "data": {
    "version": "1.1.0",
    "version_info": [1, 1, 0],
    "build_date": "2025-07-06",
    "python_version": "3.9.7",
    "release_name": "Enhanced User Experience",
    "description": "AI-Powered Security Operations Center with Multi-Agent Architecture"
  }
}
```

### 3. 运行时版本显示

#### 命令行启动时

启动DeepSOC时会显示版本信息：

```
============================================================
🚀 DeepSOC - AI-Powered Security Operations Center
============================================================
版本: 1.1.0
发布名称: Enhanced User Experience
构建日期: 2025-07-06
Python 版本: 3.9.7
描述: AI-Powered Security Operations Center with Multi-Agent Architecture
============================================================
```

#### Web界面显示

- **首页底部**：显示版本号和项目描述
- **作战室右下角**：固定显示当前版本号
- **动态加载**：通过JavaScript调用API获取最新版本信息

## 版本管理工具

### `tools/version_manager.py`

专门的版本管理工具，提供以下功能：

#### 查看版本信息

```bash
python tools/version_manager.py show
```

#### 升级版本号

```bash
# 升级补丁版本 (1.1.0 → 1.1.1)
python tools/version_manager.py bump patch

# 升级次版本 (1.1.0 → 1.2.0)
python tools/version_manager.py bump minor

# 升级主版本 (1.1.0 → 2.0.0)
python tools/version_manager.py bump major --release-name "Major Rewrite"
```

#### 设置特定版本

```bash
python tools/version_manager.py set 1.5.0 --release-name "New Features"
```

#### 创建Git标签

```bash
python tools/version_manager.py tag --message "Release v1.1.0"
```

### 版本管理工具特性

- **自动更新**：同时更新所有版本相关文件
- **变更日志**：自动更新 `changelog.md`
- **Git集成**：自动创建版本标签
- **格式验证**：确保版本号格式正确
- **安全检查**：防止版本号回退

## 版本发布流程

### 1. 开发阶段

在开发过程中，版本号保持不变，通过Git提交跟踪更改。

### 2. 准备发布

```bash
# 检查当前版本状态
python tools/version_manager.py show

# 更新版本号（根据更改类型选择）
python tools/version_manager.py bump minor --release-name "New Chat Features"
```

### 3. 更新变更日志

版本管理工具会自动在 `changelog.md` 中创建新的版本条目：

```markdown
## [1.2.0] - 2025-07-06 - New Chat Features

### 更新内容
- 新增工程师聊天功能
- 优化用户消息显示
- 修复WebSocket连接问题
```

### 4. 提交和标签

```bash
# 提交版本更改
git add .
git commit -m "chore: bump version to 1.2.0"

# 推送到远程仓库
git push origin main

# 推送标签
git push origin v1.2.0
```

### 5. 发布验证

```bash
# 验证版本显示
python main.py -version

# 验证API端点
curl http://127.0.0.1:5007/api/version

# 检查Web界面版本显示
```

## 最佳实践

### 版本号管理

1. **开发分支**：保持版本号不变，通过Git跟踪
2. **功能分支**：不修改版本号
3. **发布分支**：统一升级版本号
4. **主分支**：只包含已发布的稳定版本

### 发布命名

使用有意义的发布名称：

- `"Initial Release"` - 首次发布
- `"Enhanced User Experience"` - 用户体验改进
- `"Performance Boost"` - 性能优化
- `"Security Update"` - 安全更新
- `"Bug Fixes"` - 错误修复

### 变更日志

每个版本都应该包含：

- **新增功能**：`### 新增`
- **改进优化**：`### 改进`
- **错误修复**：`### 修复`
- **破坏性变更**：`### 破坏性变更`
- **安全更新**：`### 安全`

### Git标签策略

- 使用 `v` 前缀：`v1.1.0`
- 包含发布说明作为标签信息
- 为重要版本创建GitHub Release

## 集成和自动化

### CI/CD集成

在CI/CD管道中集成版本管理：

```yaml
# .github/workflows/release.yml
- name: Bump version
  run: python tools/version_manager.py bump ${{ github.event.inputs.bump_type }}

- name: Build package
  run: python setup.py sdist bdist_wheel

- name: Create release
  uses: actions/create-release@v1
  with:
    tag_name: v${{ env.VERSION }}
```

### 自动化脚本

创建发布脚本 `scripts/release.sh`：

```bash
#!/bin/bash
set -e

# 检查工作目录是否干净
if [ -n "$(git status --porcelain)" ]; then
    echo "Working directory is not clean"
    exit 1
fi

# 升级版本
python tools/version_manager.py bump $1

# 构建包
python setup.py sdist bdist_wheel

# 运行测试
python -m pytest

echo "Release prepared successfully"
```

## 版本兼容性

### API版本控制

对于重大API变更，考虑版本化API：

```python
# v1 API
@app.route('/api/v1/events')

# v2 API  
@app.route('/api/v2/events')
```

### 数据库迁移

版本升级可能涉及数据库变更：

```python
# migrations/versions/xxx_version_1_2_0.py
def upgrade():
    # 升级到1.2.0的数据库变更
    pass

def downgrade():
    # 回滚变更
    pass
```

### 配置兼容性

保持配置文件的向下兼容性：

```python
def load_config():
    # 加载配置
    config = load_base_config()
    
    # 处理版本特定的配置
    version = get_version()
    if version_compare(version, "1.2.0") >= 0:
        config.update(load_v1_2_config())
    
    return config
```

## 故障排除

### 常见问题

1. **版本号不一致**
   ```bash
   # 检查所有版本引用
   grep -r "1\." . --include="*.py" --include="*.md"
   ```

2. **Git标签冲突**
   ```bash
   # 删除本地标签
   git tag -d v1.1.0
   
   # 删除远程标签
   git push origin :refs/tags/v1.1.0
   ```

3. **导入错误**
   ```bash
   # 检查Python路径
   python -c "from app import __version__; print(__version__)"
   ```

### 版本回滚

如需回滚版本：

```bash
# 设置为之前的版本
python tools/version_manager.py set 1.0.9 --no-tag

# 重置Git状态
git reset --hard HEAD~1
```

## 监控和日志

### 版本使用统计

在应用启动时记录版本信息：

```python
logger.info(f"DeepSOC v{__version__} started")
logger.info(f"Python version: {sys.version}")
logger.info(f"Build date: {get_version_info()['build_date']}")
```

### 版本检查

定期检查是否有新版本：

```python
def check_updates():
    current = get_version()
    # 检查远程版本
    # 提醒用户更新
```

---

**文档版本**: 1.0  
**创建日期**: 2025-07-06  
**适用版本**: v1.1.0+  
**维护团队**: DeepSOC开发团队
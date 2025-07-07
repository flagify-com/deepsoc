# DeepSOC 开发指导手册

## 概述

本手册为DeepSOC开发团队提供标准化的开发流程指导，包括版本管理、代码提交、发布流程等最佳实践。

## 版本管理工作流

### 🚀 快速开始

DeepSOC使用语义化版本管理（Semantic Versioning），格式为：`主版本号.次版本号.修订号`

```bash
# 查看当前版本信息
python tools/version_manager.py show

# 查看项目启动版本信息
python main.py -version
```

### 📋 日常开发流程

#### 1. 功能开发阶段

**不修改版本号**，专注功能开发：

```bash
# 检查当前状态
git status
python tools/version_manager.py show

# 创建功能分支（推荐）
git checkout -b feature/新功能名称

# 开发过程中的常规提交
git add .
git commit -m "feat: 添加XXX功能"
git commit -m "fix: 修复XXX问题"
git commit -m "docs: 更新XXX文档"
```

#### 2. 功能完成准备发布

```bash
# 1. 检查工作区状态
git status --porcelain

# 2. 合并到开发分支
git checkout dev
git merge feature/新功能名称

# 3. 提交最终功能代码
git add .
git commit -m "feat: 完成XXX功能实现

- 具体功能点1
- 具体功能点2
- 相关文档更新

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# 4. 预先编辑changelog.md ⭐ 重要步骤
# 在 "## [未发布]" 下面添加新版本的详细内容：
#
# ## [1.3.0] - 2025-07-06 - 功能名称
#
# ### 新增功能
# - **功能模块**: 详细的功能描述
#   - 具体特性1，说明用户价值
#   - 具体特性2，说明技术实现
#   - 具体特性3，说明解决的问题

# 5. 提交changelog预编辑
git add changelog.md
git commit -m "docs: 预先完善v1.X.0版本更新内容

- 详细记录新增功能特性
- 包含用户价值和技术要点

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

#### 3. 版本发布

根据功能类型选择合适的版本升级：

```bash
# 修复bug - 补丁版本 (1.2.0 → 1.2.1)
python tools/version_manager.py bump patch --release-name "Bug Fixes"

# 新功能 - 次版本 (1.2.0 → 1.3.0)
python tools/version_manager.py bump minor --release-name "New Features"

# 重大变更 - 主版本 (1.2.0 → 2.0.0)
python tools/version_manager.py bump major --release-name "Major Update"
```

**版本管理工具自动完成：**
- ✅ 版本号升级
- ✅ 更新版本文件 (`app/_version.py`)
- ✅ 更新发布名称和构建日期
- ✅ 自动更新 `changelog.md`（合并预编辑内容）
- ✅ 创建Git标签 (`v1.x.x`) **包含完整changelog**

**🎯 关键优势：** Git标签现在包含完整的changelog内容，确保版本归属准确！

#### 5. 验证发布结果

```bash
# 验证版本信息
python tools/version_manager.py show

# 测试启动显示
python main.py -version

# 检查Git标签
git tag --list "v*" | tail -5

# 查看最近提交
git log --oneline -5
```

## 版本升级决策指南

### 版本号规范

| 版本类型 | 使用场景 | 示例 | 命令 |
|----------|----------|------|------|
| **主版本** (MAJOR) | 重大架构变更，不兼容的API修改 | 1.0.0 → 2.0.0 | `bump major` |
| **次版本** (MINOR) | 新功能，向下兼容的功能性新增 | 1.2.0 → 1.3.0 | `bump minor` |
| **修订版** (PATCH) | Bug修复，向下兼容的问题修正 | 1.2.3 → 1.2.4 | `bump patch` |

### 具体场景示例

#### 🔧 补丁版本 (PATCH)
```bash
# 适用场景：
# - 修复已知bug
# - 性能优化
# - 文档修正
# - 依赖版本更新

python tools/version_manager.py bump patch --release-name "Bug Fixes"
```

#### ⭐ 次版本 (MINOR)
```bash
# 适用场景：
# - 新增功能
# - API扩展
# - 用户界面改进
# - 新增配置选项

python tools/version_manager.py bump minor --release-name "Enhanced Features"
```

#### 🚀 主版本 (MAJOR)
```bash
# 适用场景：
# - 架构重构
# - 不兼容的API变更
# - 重大功能重写
# - 依赖版本重大升级

python tools/version_manager.py bump major --release-name "Major Rewrite"
```

## Git工作流集成

### 分支管理策略

```bash
# 主分支
main    # 生产环境，只包含已发布的稳定版本
dev     # 开发分支，集成所有开发完成的功能

# 功能分支
feature/功能名称    # 具体功能开发
bugfix/问题描述     # bug修复
hotfix/紧急修复     # 生产环境紧急修复
```

### 标准提交消息格式

```bash
# 格式：<类型>: <描述>
#
# <详细说明>
#
# 🤖 Generated with [Claude Code](https://claude.ai/code)
# Co-Authored-By: Claude <noreply@anthropic.com>

# 类型说明：
feat:     # 新功能
fix:      # bug修复
docs:     # 文档更新
style:    # 代码格式调整
refactor: # 重构
test:     # 测试相关
chore:    # 构建/工具相关
```

### 发布到远程仓库

```bash
# 推送代码
git push origin dev

# 推送标签
git push origin v1.2.0

# 推送所有标签
git push origin --tags
```

## 版本管理工具使用

### 基本命令

```bash
# 查看版本信息
python tools/version_manager.py show

# 升级版本
python tools/version_manager.py bump [patch|minor|major]

# 设置特定版本
python tools/version_manager.py set 1.5.0

# 创建Git标签
python tools/version_manager.py tag --message "Release note"
```

### 高级选项

```bash
# 升级版本并设置发布名称
python tools/version_manager.py bump minor --release-name "New Features"

# 升级版本但不自动创建Git标签
python tools/version_manager.py bump patch --no-tag

# 升级版本但不自动更新changelog
python tools/version_manager.py bump minor --no-changelog
```

### 版本信息获取

```bash
# 命令行方式
python main.py -version

# 程序化方式
python -c "from app import __version__; print(__version__)"

# API方式
curl http://127.0.0.1:5007/api/version

# 详细信息
python tools/version_manager.py show
```

## 发布检查清单

### 发布前检查 ✓

- [ ] 所有功能开发完成并测试通过
- [ ] 代码已合并到dev分支
- [ ] 运行测试套件（如果有）
- [ ] 更新相关文档
- [ ] 检查Git工作区干净（`git status`）
- [ ] 确认版本升级类型（patch/minor/major）

### 发布操作 ✓

- [ ] 提交最终功能代码
- [ ] **⭐ 预先编辑changelog.md更新内容**
- [ ] **⭐ 提交changelog预编辑**
- [ ] 使用版本管理工具升级版本
- [ ] 验证版本信息正确性

### 发布后验证 ✓

- [ ] 验证启动版本显示正确
- [ ] 检查Web界面版本显示
- [ ] 验证API版本端点
- [ ] 确认Git标签创建成功
- [ ] 推送标签到远程仓库（可选）

## 团队协作规范

### 版本发布责任

| 角色 | 职责 |
|------|------|
| **开发者** | 功能开发，功能分支管理，提交规范 |
| **发布负责人** | 版本升级决策，发布操作，文档维护 |
| **测试人员** | 版本验证，功能测试，问题反馈 |

### 发布周期建议

```bash
# 日常开发
每日提交  → 功能开发，bug修复
每周合并  → 功能分支合并到dev

# 版本发布
补丁版本  → 根据需要（bug修复）
次版本    → 每2-4周（新功能积累）
主版本    → 每季度或半年（重大更新）
```

### 紧急发布流程

```bash
# 生产环境紧急修复
git checkout main
git checkout -b hotfix/紧急问题描述

# 修复问题
git commit -m "fix: 紧急修复XXX问题"

# 合并到main和dev
git checkout main
git merge hotfix/紧急问题描述

# 立即发布补丁版本
python tools/version_manager.py bump patch --release-name "Hotfix"

# 同步到dev分支
git checkout dev
git merge main
```

## 常见问题和解决方案

### Q1: 版本号设置错误怎么办？

```bash
# 重新设置正确的版本号
python tools/version_manager.py set 1.2.3

# 如果已经创建了错误的Git标签
git tag -d v1.2.2  # 删除本地标签
git push origin :refs/tags/v1.2.2  # 删除远程标签
```

### Q2: 忘记更新changelog怎么办？

```bash
# 手动编辑 changelog.md
# 然后提交更新
git add changelog.md
git commit -m "docs: 补充vX.X.X版本更新日志"
```

### Q3: 需要回滚版本怎么办？

```bash
# 回滚到指定版本
python tools/version_manager.py set 1.1.0

# 或者回滚到指定Git提交
git reset --hard <commit-hash>
```

### Q4: 版本工具出错怎么办？

```bash
# 检查version.py文件格式
cat app/_version.py

# 手动修复版本文件
# 然后重新运行版本工具
python tools/version_manager.py show
```

## 版本发布示例

### 示例1: Bug修复发布

```bash
# 1. 修复完成后
git add .
git commit -m "fix: 修复用户登录问题

- 解决session超时问题
- 优化错误提示信息

🤖 Generated with [Claude Code](https://claude.ai/code)
Co-Authored-By: Claude <noreply@anthropic.com>"

# 2. ⭐ 预先编辑changelog.md
# 在 "## [未发布]" 下面添加：
# ## [1.2.1] - 2025-07-06 - Bug Fixes
# 
# ### 修复
# - **用户登录**: 修复用户登录问题
#   - 解决session超时问题
#   - 优化错误提示信息

# 3. ⭐ 提交changelog预编辑
git add changelog.md
git commit -m "docs: 预先完善v1.2.1版本更新内容

- 详细记录bug修复内容
- 包含具体解决的技术问题

🤖 Generated with [Claude Code](https://claude.ai/code)
Co-Authored-By: Claude <noreply@anthropic.com>"

# 4. 发布补丁版本
python tools/version_manager.py bump patch --release-name "Bug Fixes"
```

### 示例2: 新功能发布

```bash
# 1. 功能开发完成
git add .
git commit -m "feat: 添加数据导出功能

- 支持CSV格式导出
- 支持自定义字段选择
- 添加导出历史记录

🤖 Generated with [Claude Code](https://claude.ai/code)
Co-Authored-By: Claude <noreply@anthropic.com>"

# 2. ⭐ 预先编辑changelog.md
# 在 "## [未发布]" 下面添加：
# ## [1.3.0] - 2025-07-06 - Data Export Feature
# 
# ### 新增功能
# - **数据导出**: 新增数据导出功能
#   - 支持CSV格式导出，方便数据分析
#   - 支持自定义字段选择，灵活导出
#   - 添加导出历史记录，便于追踪

# 3. ⭐ 提交changelog预编辑
git add changelog.md
git commit -m "docs: 预先完善v1.3.0版本更新内容

- 详细记录数据导出功能特性
- 包含用户价值和技术实现点

🤖 Generated with [Claude Code](https://claude.ai/code)
Co-Authored-By: Claude <noreply@anthropic.com>"

# 4. 发布次版本
python tools/version_manager.py bump minor --release-name "Data Export Feature"
```

## 自动化和CI/CD集成

### GitHub Actions示例

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
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.8'
    
    - name: Get version
      id: version
      run: |
        VERSION=$(python tools/version_manager.py show | grep "version:" | cut -d' ' -f2)
        echo "version=$VERSION" >> $GITHUB_OUTPUT
    
    - name: Create Release
      uses: actions/create-release@v1
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      with:
        tag_name: ${{ github.ref }}
        release_name: Release ${{ steps.version.outputs.version }}
        draft: false
        prerelease: false
```

## 版本监控和统计

### 版本使用统计

```bash
# 检查当前运行版本
python -c "from app import __version__; print(f'当前版本: {__version__}')"

# 在日志中记录版本信息
# main.py 启动时会自动记录版本信息
```

### 版本历史查看

```bash
# 查看Git标签历史
git tag --sort=-version:refname

# 查看版本间的变更
git log v1.1.0..v1.2.0 --oneline

# 查看changelog历史
head -50 changelog.md
```

---

## 📞 支持和联系

如果在版本管理过程中遇到问题：

1. 检查本手册的常见问题部分
2. 查看技术文档 `docs/Version_Management.md`
3. 联系开发团队技术负责人

**记住：规范的版本管理是团队协作和项目维护的基础！** 🚀

---

**文档版本**: 1.0  
**创建日期**: 2025-07-06  
**适用版本**: DeepSOC v1.2.0+  
**维护团队**: DeepSOC开发团队
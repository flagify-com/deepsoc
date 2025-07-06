# DeepSOC 开发快速参考

## 🚀 版本管理快速命令

### 常用命令
```bash
# 查看版本
python tools/version_manager.py show
python main.py -version

# 升级版本
python tools/version_manager.py bump patch    # bug修复
python tools/version_manager.py bump minor    # 新功能
python tools/version_manager.py bump major    # 重大变更

# 设置版本
python tools/version_manager.py set 1.5.0
```

### 标准发布流程
```bash
# 1. 提交代码
git add .
git commit -m "feat: 功能描述"

# 2. 升级版本
python tools/version_manager.py bump minor --release-name "功能名称"

# 3. 完善文档
# 编辑 changelog.md
git add changelog.md
git commit -m "docs: 完善版本文档"

# 4. 推送标签（可选）
git push origin v1.x.x
```

## 📋 Git提交规范

| 类型 | 说明 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat: 添加数据导出功能` |
| `fix` | Bug修复 | `fix: 修复登录超时问题` |
| `docs` | 文档更新 | `docs: 更新API文档` |
| `style` | 代码格式 | `style: 统一代码缩进` |
| `refactor` | 重构 | `refactor: 优化数据处理逻辑` |
| `test` | 测试 | `test: 添加单元测试` |
| `chore` | 构建/工具 | `chore: 更新依赖包` |

## 🔢 版本号规则

```
主版本.次版本.修订版
  ↓      ↓      ↓
 2  .   1   .   3

主版本: 不兼容的API修改
次版本: 向下兼容的功能性新增  
修订版: 向下兼容的问题修正
```

## 📁 重要文件位置

```
DeepSOC/
├── app/_version.py              # 版本核心文件
├── tools/version_manager.py     # 版本管理工具
├── changelog.md                 # 更新日志
├── docs/Development_Guide.md    # 开发指南
└── docs/Version_Management.md   # 版本管理详解
```

## 🔍 常用检查命令

```bash
# 检查状态
git status
git log --oneline -5
git tag --list "v*" | tail -5

# 版本验证
python main.py -version
curl http://127.0.0.1:5007/api/version

# 启动应用
python main.py
python tools/run_all_agents.py
```

## 🆘 紧急修复流程

```bash
# 1. 创建hotfix分支
git checkout main
git checkout -b hotfix/问题描述

# 2. 修复并提交
git commit -m "fix: 紧急修复XXX"

# 3. 合并并发版
git checkout main
git merge hotfix/问题描述
python tools/version_manager.py bump patch --release-name "Hotfix"

# 4. 同步dev分支
git checkout dev && git merge main
```

## 📞 获取帮助

- 查看完整开发指南：`docs/Development_Guide.md`
- 版本管理详解：`docs/Version_Management.md` 
- 工具帮助：`python tools/version_manager.py --help`
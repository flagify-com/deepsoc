# DeepSOC 升级指南

## 概述

本文档提供 DeepSOC 系统的详细升级指南，包括快速重置、数据保留升级、故障排除等内容。

## 升级方式概览

### 推荐方式：快速重置（适合95%的用户）
**适用场景**：开发环境、测试环境、想要体验最新功能的用户

**优势**：
- 操作简单，不会出现兼容性问题
- 获得最新的演示数据和功能
- 避免老版本遗留的数据结构问题

### 保留数据升级（适合生产环境）
**适用场景**：生产环境、有重要历史数据需要保留的用户

**注意事项**：
- 需要手动处理数据库迁移
- 可能遇到版本兼容性问题
- 需要更多的故障排除经验

## 版本兼容性

### 当前版本特性
- **版本号**：v1.6.x
- **重大变化**：已与旧版本完全切割
- **初始化方式**：提供三种初始化模式（`-init`、`-init-with-demo`、`-load_demo`）
- **演示数据**：包含完整的邮件网关暴力破解攻击事件处理案例

### 支持的升级路径
- **v1.0.x → v1.6.x**：建议使用快速重置
- **v1.1.x → v1.6.x**：建议使用快速重置
- **开发版本 → v1.6.x**：必须使用快速重置

## 方式一：快速重置升级（推荐）

### 适用场景
- 开发环境和测试环境
- 想要体验最新功能和演示数据
- 不需要保留历史数据
- 从旧版本迁移遇到困难

### 升级步骤

#### 1. 准备工作
```bash
# 检查 Python 版本
python --version  # 需要 3.8+

# 检查正在运行的进程
ps aux | grep "python main.py"

# 停止所有 DeepSOC 进程
pkill -f "python main.py"
```

#### 2. 备份重要数据（可选）
```bash
# 创建备份目录
mkdir -p backups/$(date +%Y%m%d)

# 备份环境配置
cp .env backups/$(date +%Y%m%d)/.env.backup

# 备份数据库（如果需要）
mysqldump -u your_username -p deepsoc > backups/$(date +%Y%m%d)/deepsoc_backup.sql
```

#### 3. 更新代码和依赖
```bash
# 拉取最新代码
git pull origin main

# 更新依赖包
pip install -r requirements.txt
```

#### 4. 快速重置初始化
```bash
# 使用演示数据完整初始化（推荐）
python main.py -init-with-demo

# 或者仅基础初始化
python main.py -init
```

#### 5. 验证升级
```bash
# 启动主服务
python main.py

# 访问 Web 界面验证
curl http://127.0.0.1:5007/

# 检查演示数据是否正确加载
# 登录后查看是否有演示事件
```

#### 6. 启动所有服务
```bash
# 一键启动所有服务
python tools/run_all_agents.py

# 或者单独启动各服务
python main.py -role _captain &
python main.py -role _manager &
python main.py -role _operator &
python main.py -role _executor &
python main.py -role _expert &
```

## 方式二：保留数据升级（高级用户）

### 前提条件
- 有 Flask-Migrate 使用经验
- 有数据库管理经验
- 能够处理迁移过程中的问题

#### 1. 完整数据备份
```bash
# 创建备份目录
mkdir -p backups/$(date +%Y%m%d)

# MySQL 完整备份
mysqldump -u your_username -p \
  --single-transaction \
  --routines \
  --triggers \
  deepsoc > backups/$(date +%Y%m%d)/deepsoc_full_backup.sql

# 备份环境配置
cp .env backups/$(date +%Y%m%d)/.env.backup
```

#### 2. 停止服务
```bash
# 停止所有 DeepSOC 进程
pkill -f "python main.py"

# 验证进程已停止
ps aux | grep "python main.py"
```

#### 3. 更新代码
```bash
# 拉取最新代码
git pull origin main
pip install -r requirements.txt
```

#### 4. 数据库迁移
```bash
# 检查当前迁移状态
flask db current

# 执行数据库迁移
flask db upgrade

# 验证迁移结果
flask db current
```

#### 5. 配置更新
```bash
# 检查配置文件差异
diff .env sample.env

# 更新必要的配置项
# 重点检查：RabbitMQ、OpenAI API、SOAR 配置
```

#### 6. 启动验证
```bash
# 启动主服务
python main.py

# 访问界面验证
curl http://127.0.0.1:5007/

# 启动所有代理
python tools/run_all_agents.py
```

### 常见迁移问题

#### 迁移失败处理
```bash
# 如果迁移失败，回滚到备份
mysql -u your_username -p -e "DROP DATABASE IF EXISTS deepsoc;"
mysql -u your_username -p -e "CREATE DATABASE deepsoc CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -u your_username -p deepsoc < backups/$(date +%Y%m%d)/deepsoc_full_backup.sql

# 然后使用快速重置方式
python main.py -init-with-demo
```

## 初始化模式详解

### 三种初始化模式对比

| 模式 | 命令 | 包含内容 | 适用场景 |
|------|------|----------|----------|
| 完整初始化 | `python main.py -init-with-demo` | 数据库表 + 提示词 + 管理员 + 演示数据 | 新用户快速体验 |
| 基础初始化 | `python main.py -init` | 数据库表 + 提示词 + 管理员 | 生产环境或自定义数据 |
| 仅导入演示数据 | `python main.py -load_demo` | 仅演示数据 | 已有数据库，想要演示案例 |

### 演示数据内容

当前演示数据包含一个完整的**邮件网关暴力破解攻击事件**，包括：

- **事件信息**：外部IP 66.240.205.34 对邮件网关服务器 192.168.22.251 的暴力破解攻击
- **处理流程**：完整的多Agent协作处理过程
- **执行结果**：包含SOAR平台的实际返回数据
- **用户账户**：管理员账户（admin/admin123）

## 升级后验证清单

### 功能验证步骤

1. **基础功能验证**
```bash
# 访问 Web 界面
curl http://127.0.0.1:5007/

# 检查登录功能
# 使用 admin/admin123 登录
```

2. **演示数据验证**
```bash
# 登录后检查是否有演示事件
# 查看事件ID为1的邮件网关攻击事件
```

3. **多Agent系统验证**
```bash
# 检查所有代理是否正常运行
ps aux | grep "python main.py"

# 应该看到6个进程：main + 5个agent角色
```

4. **工程师聊天验证**
```bash
# 在作战室发送 @AI 消息
# 检查是否有AI响应
```

### 常见问题处理

#### 1. 演示数据未正确加载
```bash
# 重新导入演示数据
python main.py -load_demo

# 检查数据库中是否有数据
mysql -u your_username -p deepsoc -e "SELECT COUNT(*) FROM events;"
```

#### 2. 用户无法登录
```bash
# 重新创建管理员用户
python tools/create_admin.py

# 或者重置密码
python tools/reset_admin_password.py
```

#### 3. Agent服务无法启动
```bash
# 检查依赖是否正确安装
pip install -r requirements.txt

# 检查配置文件
cat .env | grep -v "^#" | grep -v "^$"
```

## 故障排除

### 快速诊断脚本

创建诊断脚本快速检查系统状态：

```bash
#!/bin/bash
# diagnosis.sh - DeepSOC 系统诊断脚本

echo "=== DeepSOC 系统诊断 ==="

# 检查Python版本
echo "Python版本:"
python --version

# 检查进程状态
echo "DeepSOC进程状态:"
ps aux | grep "python main.py" | grep -v grep

# 检查数据库连接
echo "数据库连接测试:"
python -c "from app.models import db; from main import app; app.app_context().push(); print('数据库连接:', 'OK' if db.engine.execute('SELECT 1').scalar() else 'FAILED')" 2>/dev/null || echo "数据库连接: FAILED"

# 检查演示数据
echo "演示数据检查:"
python -c "from app.models.models import Event; from main import app; app.app_context().push(); print('事件数量:', Event.query.count())" 2>/dev/null || echo "演示数据: FAILED"

# 检查Web服务
echo "Web服务检查:"
curl -s http://127.0.0.1:5007/ >/dev/null && echo "Web服务: OK" || echo "Web服务: FAILED"

echo "=== 诊断完成 ==="
```

### 升级建议

#### 为什么推荐快速重置？

1. **避免兼容性问题**：新版本数据结构变化较大
2. **获得最新功能**：演示数据包含最新的功能展示
3. **简化升级流程**：减少手动处理步骤
4. **更好的体验**：完整的演示案例帮助理解系统功能

#### 何时使用保留数据升级？

- 生产环境运行，有重要历史数据
- 有专业的数据库管理经验
- 有足够的时间处理潜在问题
- 已经制定了详细的回滚计划

---

**文档版本**: 2.0  
**更新日期**: 2025-07-07  
**适用版本**: v1.6.x  
**维护团队**: DeepSOC开发团队
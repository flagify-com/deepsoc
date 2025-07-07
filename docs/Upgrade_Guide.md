# DeepSOC 升级指南

## 概述

本文档提供 DeepSOC 系统的详细升级指南，包括数据库迁移、配置更新、故障排除等内容。

## 支持的升级路径

- **v1.0.x → v1.1.x**：完整支持，包含数据库迁移
- **开发版本 → 正式版本**：需要完整数据库重建

## 准备工作

### 1. 系统环境检查

升级前请确认系统环境：

```bash
# 检查 Python 版本
python --version  # 需要 3.8+

# 检查数据库连接
mysql -u your_username -p -e "SELECT VERSION();"

# 检查磁盘空间
df -h

# 检查正在运行的进程
ps aux | grep "python main.py"
```

### 2. 创建升级检查点

```bash
# 记录当前版本信息
git branch
git log -1 --oneline

# 记录当前数据库状态
flask db current
mysql -u your_username -p deepsoc -e "SHOW TABLES;"
```

## 完整升级流程

### 步骤 1：数据备份

#### MySQL 数据库备份

```bash
# 创建备份目录
mkdir -p backups/$(date +%Y%m%d)

# 完整数据库备份
mysqldump -u your_username -p \
  --single-transaction \
  --routines \
  --triggers \
  deepsoc > backups/$(date +%Y%m%d)/deepsoc_full_backup.sql

# 仅结构备份（用于快速恢复测试）
mysqldump -u your_username -p \
  --no-data \
  deepsoc > backups/$(date +%Y%m%d)/deepsoc_schema_backup.sql

# 验证备份文件
ls -la backups/$(date +%Y%m%d)/
```

#### SQLite 数据库备份

```bash
# 备份 SQLite 数据库
cp instance/deepsoc.db backups/$(date +%Y%m%d)/deepsoc_backup.db

# 导出为 SQL 格式（可选）
sqlite3 instance/deepsoc.db .dump > backups/$(date +%Y%m%d)/deepsoc_dump.sql
```

#### 配置文件备份

```bash
# 备份环境配置
cp .env backups/$(date +%Y%m%d)/.env.backup
cp sample.env backups/$(date +%Y%m%d)/sample.env.backup

# 备份自定义配置
cp -r app/config.py backups/$(date +%Y%m%d)/
```

### 步骤 2：停止服务

```bash
# 优雅停止所有 DeepSOC 进程
pkill -TERM -f "python main.py"

# 等待进程完全停止
sleep 5

# 强制停止（如果需要）
pkill -KILL -f "python main.py"

# 验证进程已停止
ps aux | grep "python main.py"
```

### 步骤 3：代码更新

```bash
# 保存本地修改（如果有）
git stash

# 拉取最新代码
git fetch origin
git checkout main
git pull origin main

# 检查是否有冲突
git status

# 如果有本地修改，合并回来
# git stash pop
```

### 步骤 4：依赖更新

```bash
# 激活虚拟环境
source venv/bin/activate  # Linux/Mac
# .\venv\Scripts\activate  # Windows

# 更新 pip
pip install --upgrade pip

# 安装新依赖
pip install -r requirements.txt

# 检查关键包版本
pip show flask flask-sqlalchemy flask-migrate
```

### 步骤 5：数据库迁移

#### 自动迁移（推荐）

```bash
# 检查当前迁移状态
flask db current

# 查看待执行的迁移
flask db show

# 执行数据库迁移
flask db upgrade

# 验证迁移结果
flask db current
```

#### 手动迁移（故障恢复）

如果自动迁移失败，按以下步骤手动处理：

```bash
# 检查迁移历史
flask db history

# 手动执行特定迁移文件
mysql -u your_username -p deepsoc < add_user_uuid.sql

# 标记迁移为已完成
flask db stamp head
```

### 步骤 6：配置更新

#### 环境变量检查

```bash
# 对比配置文件
diff .env sample.env

# 检查新增的配置项
grep -v "^#" sample.env | grep -v "^$"
```

#### 重要配置项

检查并更新以下配置：

```env
# 数据库连接（如果有变更）
DATABASE_URL=mysql+pymysql://user:pass@localhost:3306/deepsoc

# 新增的 RabbitMQ 配置
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASS=guest

# OpenAI API 配置
OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=https://api.openai.com/v1

# SOAR 集成配置（如果使用）
SOAR_BASE_URL=your_soar_url
SOAR_API_KEY=your_soar_key
```

### 步骤 7：启动验证

#### 启动主服务

```bash
# 启动主 Web 服务
python main.py

# 检查启动日志
tail -f error.log
```

#### 启动多代理服务

```bash
# 使用脚本启动所有代理
python tools/run_all_agents.py

# 或者手动启动各个代理
python main.py -role _captain &
python main.py -role _manager &
python main.py -role _operator &
python main.py -role _executor &
python main.py -role _expert &
```

#### 功能验证

```bash
# 访问 Web 界面
curl http://127.0.0.1:5007/

# 测试 API 端点
curl -X GET http://127.0.0.1:5007/api/events

# 测试数据库连接
python -c "from app.models import db; from main import app; app.app_context().push(); print('Database connected:', db.engine.execute('SELECT 1').scalar())"
```

## 数据库迁移详解

### 迁移文件说明

#### 用户系统增强迁移

```python
# f68b4187b0dc_add_user_id_to_message_model.py
# 新增用户 UUID 字段，支持更好的用户识别
```

#### 工程师聊天功能迁移

```python
# add_engineer_chat_fields_to_message.py
# 新增聊天相关字段，支持 @AI 对话功能
```

#### 全局设置系统迁移

```python
# eb3b587c55f1_add_global_settings_table.py
# 新增全局配置表，支持系统级设置
```

### 迁移验证脚本

创建验证脚本检查迁移结果：

```python
#!/usr/bin/env python3
# scripts/verify_migration.py
import sys
from app.models.models import User, Message, GlobalSettings
from main import app

def verify_user_migration():
    with app.app_context():
        # 检查用户表结构
        users = User.query.all()
        for user in users:
            assert user.user_id is not None, f"用户 {user.username} 缺少 user_id"
            assert len(user.user_id) > 0, f"用户 {user.username} user_id 为空"
        print(f"✓ 用户迁移验证通过：{len(users)} 个用户")

def verify_message_migration():
    with app.app_context():
        # 检查消息表结构
        from sqlalchemy import inspect
        inspector = inspect(Message.__table__.bind)
        columns = [col['name'] for col in inspector.get_columns('messages')]
        
        required_columns = ['message_category', 'chat_session_id', 'sender_type', 'event_summary_version']
        for col in required_columns:
            assert col in columns, f"消息表缺少字段：{col}"
        print(f"✓ 消息表迁移验证通过：包含所有必需字段")

def verify_global_settings():
    with app.app_context():
        # 检查全局设置表
        settings = GlobalSettings.query.all()
        print(f"✓ 全局设置表创建成功：{len(settings)} 个设置项")

if __name__ == "__main__":
    try:
        verify_user_migration()
        verify_message_migration()
        verify_global_settings()
        print("🎉 所有迁移验证通过！")
    except Exception as e:
        print(f"❌ 迁移验证失败：{e}")
        sys.exit(1)
```

## 故障排除

### 常见问题

#### 1. 迁移失败：外键约束错误

```bash
# 问题：外键约束导致迁移失败
# 解决：临时禁用外键检查

mysql -u your_username -p deepsoc -e "
SET FOREIGN_KEY_CHECKS = 0;
-- 执行迁移操作
SET FOREIGN_KEY_CHECKS = 1;
"
```

#### 2. 用户 UUID 字段冲突

```sql
-- 问题：user_id 字段已存在但格式不正确
-- 解决：清理并重新生成

-- 检查现有数据
SELECT username, user_id FROM users WHERE user_id IS NULL OR user_id = '';

-- 为空值用户生成 UUID
UPDATE users SET user_id = UUID() WHERE user_id IS NULL OR user_id = '';

-- 验证结果
SELECT COUNT(*) FROM users WHERE user_id IS NOT NULL;
```

#### 3. 工程师聊天字段缺失

```sql
-- 问题：消息表缺少聊天相关字段
-- 解决：手动添加字段

ALTER TABLE messages ADD COLUMN message_category VARCHAR(32) DEFAULT 'agent';
ALTER TABLE messages ADD COLUMN chat_session_id VARCHAR(64);
ALTER TABLE messages ADD COLUMN sender_type VARCHAR(32);
ALTER TABLE messages ADD COLUMN event_summary_version VARCHAR(64);

-- 更新现有数据
UPDATE messages SET message_category = 'agent' WHERE message_category IS NULL;
```

#### 4. 权限不足错误

```bash
# 问题：数据库用户权限不足
# 解决：授予必要权限

mysql -u root -p -e "
GRANT ALL PRIVILEGES ON deepsoc.* TO 'deepsoc_user'@'localhost';
GRANT CREATE, ALTER, DROP, INDEX ON deepsoc.* TO 'deepsoc_user'@'localhost';
FLUSH PRIVILEGES;
"
```

### 回滚操作

如果升级出现严重问题，可以回滚到备份状态：

#### 数据库回滚

```bash
# MySQL 回滚
mysql -u your_username -p -e "DROP DATABASE IF EXISTS deepsoc;"
mysql -u your_username -p -e "CREATE DATABASE deepsoc CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -u your_username -p deepsoc < backups/$(date +%Y%m%d)/deepsoc_full_backup.sql

# SQLite 回滚
cp backups/$(date +%Y%m%d)/deepsoc_backup.db instance/deepsoc.db
```

#### 代码回滚

```bash
# 回滚到之前的版本
git log --oneline -10  # 查看最近提交
git checkout previous_version_tag

# 或者回滚到特定提交
git reset --hard commit_hash
```

## 升级后优化

### 性能调优

#### 数据库索引优化

```sql
-- 为新字段添加索引
CREATE INDEX idx_messages_user_id ON messages(user_id);
CREATE INDEX idx_messages_category ON messages(message_category);
CREATE INDEX idx_messages_session_id ON messages(chat_session_id);
CREATE INDEX idx_users_user_id ON users(user_id);

-- 检查索引使用情况
SHOW INDEX FROM messages;
SHOW INDEX FROM users;
```

#### 清理过期数据

```sql
-- 清理超过 30 天的旧消息（可选）
DELETE FROM messages 
WHERE created_at < DATE_SUB(NOW(), INTERVAL 30 DAY) 
AND message_category = 'agent';

-- 清理无效的聊天会话
DELETE FROM messages 
WHERE message_category = 'engineer_chat' 
AND chat_session_id IN (
    SELECT chat_session_id FROM (
        SELECT chat_session_id 
        FROM messages 
        WHERE message_category = 'engineer_chat'
        GROUP BY chat_session_id 
        HAVING MAX(created_at) < DATE_SUB(NOW(), INTERVAL 7 DAY)
    ) AS old_sessions
);
```

### 监控设置

```bash
# 设置日志轮转
echo "*/10 * * * * find /path/to/deepsoc -name '*.log' -size +100M -exec truncate -s 50M {} \;" | crontab -

# 监控数据库大小
echo "0 1 * * * mysql -u your_username -p -e \"SELECT table_name, round(((data_length + index_length) / 1024 / 1024), 2) 'DB Size in MB' FROM information_schema.tables WHERE table_schema = 'deepsoc';\"" | crontab -
```

## 版本历史

### v1.1.x 主要变更

- 用户系统增强：UUID 用户标识
- 工程师聊天系统：实时 AI 对话
- 全局设置系统：系统级配置管理
- 消息显示优化：多用户身份识别
- 性能优化：数据库索引和查询优化

### v1.0.x 基础功能

- 多代理系统架构
- 安全事件处理流程
- SOAR 平台集成
- Web 界面和 API

---

**文档版本**: 1.0  
**创建日期**: 2025-07-06  
**适用版本**: v1.1.x  
**维护团队**: DeepSOC开发团队
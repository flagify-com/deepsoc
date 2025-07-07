# DeepSOC 🚀

<p align="center">
  <strong>AI驱动的新一代安全运营中心 | AI-Powered Security Operations Center</strong>
</p>

<p align="center">
  <a href="https://github.com/flagify-com/deepsoc/stargazers">
    <img src="https://img.shields.io/github/stars/flagify-com/deepsoc" alt="Stars">
  </a>
  <a href="https://github.com/flagify-com/deepsoc/network/members">
    <img src="https://img.shields.io/github/forks/flagify-com/deepsoc" alt="Forks">
  </a>
  <a href="https://github.com/flagify-com/deepsoc/issues">
    <img src="https://img.shields.io/github/issues/flagify-com/deepsoc" alt="Issues">
  </a>
  <a href="https://github.com/flagify-com/deepsoc/blob/main/LICENSE">
    <img src="https://img.shields.io/github/license/flagify-com/deepsoc" alt="License">
  </a>
</p>

## 📖 项目简介

DeepSOC 是一个革命性的安全运营解决方案，它将先进的 AI 技术与传统的安全运营工具完美结合，通过多智能体（Multi-Agent）架构，DeepSOC 能够自动化处理安全事件，显著提升安全运营效率。

DeepSOC产品工作逻辑图

![DeepSOC产品工作逻辑图](app/static/images/deepsoc-work-logic.jpg)

### ✨ 核心特性

- 🤖 **智能多Agent架构**
  - 指挥官：统筹全局决策
  - 经理：任务分配协调
  - 操作员：执行具体操作
  - 执行器：连接外部工具
  - 专家：提供专业建议

- 🔄 **自动化处理流程**
  - 自动分析安全告警
  - 智能决策响应方案
  - 自动化执行处置
  - 实时反馈处理结果

- 🛠 **丰富的工具集成**
  - 支持 SOAR 自动化编排
  - 可扩展 Function Calling Tools
  - 可扩展 MCP Tools
  - 支持人工参与事件处置

- 💬 **工程师AI助手**
  - 实时对话式AI支持，使用 `@AI` 指令交互
  - 事件上下文感知回答，自动获取事件详情和处理历史
  - 异步处理，即时响应，支持连续对话
  - 独立于自动化工作流，提供专业安全分析建议

- 🌐 **开放式架构**
  - 支持自定义 AI 参数
  - 可自定义处理流程
  - 灵活的 API 接口
  - WebSocket 实时通信

## 🚀 快速开始

### 环境要求

- Python 3.8+
- MySQL（推荐运行时使用）
- RabbitMQ（消息队列，用于多Agent通信）
- 自动化系统（支持SOAR编排自动化系统，推荐[OctoMation社区免费版](https://github.com/flagify-com/OctoMation)）
  - [剧本配置信息](docs/soar-config-help.md)


### 安装步骤

1. 克隆项目
```bash
git clone https://github.com/flagify-com/deepsoc.git
cd deepsoc
```

2. 安装依赖

2.1 Python环境及安装包

```bash
virtualenv venv
source venv/bin/activate
# Windows
# .\venv\Scripts\activate
pip install -r requirements.txt
# pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com 
# pip install -r requirements.txt -i https://mirrors.cloud.tencent.com/pypi/simple --trusted-host mirrors.cloud.tencent.com

```

2.2 MySQL准备

使用MySQL方式连接数据库，直接修改.env文件即可。

**请修改密码**
> MySQL连接密码中的特殊字符串需要通过URL编码替代
```sql
CREATE DATABASE IF NOT EXISTS deepsoc DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'deepsoc_user'@'localhost' IDENTIFIED BY 'deepsoc_password';
GRANT ALL PRIVILEGES ON deepsoc.* TO 'deepsoc_user'@'localhost';
FLUSH PRIVILEGES;
-- DATABASE_URL="mysql+pymysql://deepsoc_user:deepsoc_password@localhost:3306/deepsoc"
```

2.3 RabbitMQ 准备

安装并启动 RabbitMQ，用于多 Agent 之间的消息传递。

可通过 Docker 快速启动一个用于测试的RabbitMQ服务：

```bash
# 生产环境建议修改为强壮密码
docker run -d --name rabbitmq \
  -p 5672:5672 \
  -p 15672:15672 \
  -e RABBITMQ_DEFAULT_USER=guest \
  -e RABBITMQ_DEFAULT_PASS=guest \
  rabbitmq:3-management
```

启动后，在 `.env` 中配置 `RABBITMQ_HOST`、`RABBITMQ_USER` 等连接参数。

3. 配置环境变量
```bash
cp sample.env .env
# 编辑 .env 文件，配置必要的环境变量
```

4. 启动服务

为了方便管理，调试和优化改进，我们为每个角色启动了单独的进程。

### 4.1 数据库初始化

我们提供了三种初始化方式，满足不同的使用场景：

```bash
# 方式一：完整初始化（推荐新用户）
# 包含数据库表 + 提示词 + 管理员用户 + 演示数据
python main.py -init-with-demo

# 方式二：基础初始化（仅框架）
# 仅包含数据库表 + 提示词 + 管理员用户
python main.py -init

# 方式三：仅导入演示数据（已有数据库）
# 在现有数据库基础上导入演示事件
python main.py -load_demo
```

**说明：**
- 所有方式都会**删除现有数据库中的所有历史数据**
- 推荐新用户使用 `-init-with-demo` 快速体验完整功能
- 演示数据包含一个完整的邮件网关暴力破解攻击事件处理案例

### 4.2 启动多Agent服务

```bash
# 使用单独的窗口，启动独立进程
# 启动前记得激活venv环境

# 主服务（Web、API）
python main.py
# 指挥官
python main.py -role _captain
# 安全管理员（经理）
python main.py -role _manager
# 安全工程师（操作员）
python main.py -role _operator
# 执行器
python main.py -role _executor
# 安全专家
python main.py -role _expert
```

### 4.3 一键启动所有服务

如果想在一个命令中启动全部服务，可以运行脚本：

```bash
python tools/run_all_agents.py
```

该脚本会自动从项目根目录加载`.env`文件，并在收到`Ctrl+C`或终止信号时清理所有子进程。

## 🔄 系统升级

### 升级方式选择

我们提供两种升级方式：

#### 推荐：快速重置（适合大多数用户）
```bash
# 1. 备份重要数据（如有需要）
# 2. 拉取最新代码
git pull origin main
pip install -r requirements.txt

# 3. 使用演示数据重新初始化
python main.py -init-with-demo
```

#### 保留数据升级（适合生产环境）
如果您需要保留现有数据，请参考详细的 **[升级指南](docs/Upgrade_Guide.md)**

### 版本兼容性
- **当前版本**：v1.6.x（已与旧版本完全切割）
- **推荐做法**：使用演示数据重新开始，体验完整功能
- **详细升级**：查看 [docs/Upgrade_Guide.md](docs/Upgrade_Guide.md) 获取完整升级指南

## 📚 使用示例

### Web界面创建安全事件

登录`http://127.0.0.1:5007/`,创建安全事件。

![](app/static/images/deepsoc-home.jpg)

### 查看多Agent运行状态

![](app/static/images/deepsoc-warroom.jpg)

### 在作战室发送消息

作战室页面支持用户输入文本指令。发送的消息会通过 WebSocket 实时广播给所有在线用户，并以蓝色背景靠右显示，便于区分。

### 🤖 工程师AI助手交互

DeepSOC 提供了智能AI助手，帮助安全工程师分析和处理安全事件。在作战室中，您可以使用 `@AI` 指令与AI助手进行实时对话。

#### 基本使用方法

在作战室消息框中输入以 `@AI` 开头的消息，AI助手会基于当前事件上下文提供专业建议：

```
@AI 如何用nmap对本次事件中的邮件服务服务器做端口扫描？
@AI 这个暴力破解攻击的风险等级如何？
@AI 请分析攻击源IP的威胁情报
@AI 建议采取哪些防护措施？
@AI 这种攻击模式常见吗？有什么特征？
```

#### 上下文感知能力

AI助手具备强大的上下文感知能力，会自动获取完整的事件信息：

- **事件基本信息**（始终提供）：
  - 事件名称、描述、上下文
  - 严重程度、来源、状态
  - 创建时间等基础数据
- **AI分析概要**（第一轮完成后）：
  - 事件的详细分析结果
  - AI生成的处置建议
  - 概要更新状态提示
- **处理历史**：事件的处理进度、已执行的操作和结果
- **对话记录**：最近的工程师与AI的对话历史

通过同时提供事件基本信息和AI分析概要，确保AI助手能够全面理解事件背景并提供精准建议。

#### 交互特性

- **实时响应**：消息发送后立即显示，AI处理完成后自动推送回复
- **异步处理**：不阻塞界面操作，可以连续发送多条消息
- **智能分析**：基于事件上下文提供专业的安全分析和建议
- **持续对话**：支持多轮对话，AI会记住对话历史

#### 使用示例

假设当前处理的是邮件网关暴力破解攻击事件，您可以这样与AI助手交互：

```
用户: @AI 66.240.205.34这个IP的威胁等级如何？
AI助手: 根据威胁情报查询结果，IP 66.240.205.34 被标记为高风险地址，
        关联多个僵尸网络活动。建议立即实施IP封禁措施。

用户: @AI 除了封禁IP，还应该做哪些加固措施？
AI助手: 建议采取以下加固措施：
        1. 启用多因素认证(MFA)
        2. 实施IP白名单策略
        3. 加强密码策略和账户锁定机制
        4. 部署入侵检测系统监控异常登录
        5. 定期进行安全审计和漏洞扫描
```

#### 注意事项

- AI助手的建议基于当前事件上下文，但最终决策应结合实际环境
- 建议在执行重要操作前进行人工确认


### 查看消息原始数据结构

![](app/static/images/deepsoc-warroom-message-structure.jpg)


### 工程师AI助手快速上手

#### 1. 进入作战室
登录系统后，点击任意事件进入作战室页面。

#### 2. 开始AI对话
在消息输入框中输入以 `@AI` 开头的消息：

```
@AI 请帮我分析这个安全事件的风险等级
```

#### 3. AI助手响应
AI助手会基于当前事件的完整上下文信息提供专业建议：
- **始终包含**事件基本信息（名称、描述、上下文等）
- **自动整合**AI分析概要（如果已生成）
- **智能识别**概要更新状态，关注最新变化

#### 4. 持续对话
可以继续提问，AI助手会记住对话历史：

```
@AI 基于你的分析，我应该优先处理哪些方面？
@AI 这种攻击模式有什么预防措施？
```

#### 5. AI对话截图

指令发送：

![](app/static/images/deepsoc-warroom-ask-ai.jpg)

AI返回：

![](app/static/images/deepsoc-warroom-ask-ai-response.jpg)




### API创建安全事件

```bash
curl -X POST http://127.0.0.1:5007/api/event/create \
  -H "Content-Type: application/json" \
  -d '{
    "message": "SIEM告警外部IP 66.240.205.34正在对邮件网关服务器进行暴力破解攻击", 
    "context": "邮件网关服务器的内网IP地址192.168.22.251", 
    "severity": "medium",
    "source": "SIEM"
  }'
```

## 🤝 参与贡献

我们欢迎任何形式的贡献！

1. Fork 本项目
2. 创建您的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交您的改动 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启一个 Pull Request

## 📜 相关项目

- [DeepSec](https://deepsec.top) - 中文网络安全运营领域开源语料库
- [OctoMation](https://github.com/flagify-com/OctoMation) - 社区免费版编排自动化产品

## 🌟 加入社区

- 微信社区：扫码加入（备注：deepsoc）
- 技术讨论：每周直播分享
- 项目动态：实时更新



DeepSOC群助手微信二维码

<img src="app/static/images/deepsoc-wechat-assistant.jpg" width="100" alt="DeepSOC群助手微信二维码">

## 📚 技术文档

详细的技术文档和开发指南请参考：

- **[🚀 开发指导手册](docs/Development_Guide.md)** - **开发团队必读**：版本管理和开发流程
- **[技术文档目录](docs/README.md)** - 完整的技术文档索引
- **[系统架构](docs/Architecture.md)** - 系统整体架构设计
- **[多代理系统](docs/Agents.md)** - 多代理系统详细说明
- **[工程师聊天系统](docs/Engineer_Chat_Architecture.md)** - 工程师聊天功能架构
- **[SOAR配置指南](docs/soar-config-help.md)** - SOAR平台配置说明
- **[系统升级指南](docs/Upgrade_Guide.md)** - 版本升级和数据库迁移
- **[版本管理详解](docs/Version_Management.md)** - 版本管理技术细节
- **[开发指南](CLAUDE.md)** - AI助手开发指南
- **[更新日志](changelog.md)** - 项目更新记录

## 📄 开源协议

本项目采用 [MIT](LICENSE) 协议开源。

---

<p align="center">用AI重新定义安全运营 | Redefining Security Operations with AI</p>

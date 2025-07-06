# DeepSOC 更新日志

## [未发布]

## [1.6.1] - 2025-07-06 - 暴力移除add_user_uuid.sql的说明

### 更新内容
- 移除了add_user_uuid.sql的说明，暴力移除，不兼容模式，以后从这版本开始使用标准迁移工具完成。


## [1.6.0] - 2025-07-06 - 项目清理

### 更新内容
- **根目录整理**: 清理项目根目录，移除不必要的临时文件和调试文件
  - 删除所有日志文件（*.log）- 15个临时日志文件
  - 移动调试文件到tools目录：debug_api.py 等
  - 移动测试文件到tools目录：test_*.py 等（8个文件）
  - 删除重复文件：soar_client.py（app/utils/已有）
  - 删除临时SQL文件：add_user_uuid.sql, truncate_table.sql
  - 恢复重要文件：initial_data.sql（包含示例数据，初始化时需要）
  - 删除demo目录：demo_version_app/, cursor_chat/
  - 删除临时文件：debug_frontend.html, plan.md
  - 项目根目录现在更加整洁，便于维护和开发

## [1.5.1] - 2025-07-06 - 移除作战室版本信息显示，优化作战室检查逻辑
### 更新内容
- 移除了作战室版本信息显示，现在版本信息仅在首页底部显示
- 优化main.py启动时候的调试信息，去除之前开发阶段预留的调试日志（消息队列）
- 修复控制台报错：Error - 方法3检查失败: module 'flask_socketio' has no attribute '__version__'
  - 修复Flask-SocketIO版本检查错误，使用安全的getattr方法
  - 简化WebSocket房间加入验证逻辑，移除冗余的检查方法
  - 优化日志输出，减少不必要的调试信息，提高代码可读性


## [1.5.0] - 2025-07-06 - 调整了版本管理工具的使用流程

- 调整了版本管理工具的使用流程，现在需要先编辑changelog.md，再使用版本管理工具升级版本

## [1.4.0] - 2025-07-06

### 更新内容
- TODO: 添加更新内容


## [1.3.0] - 2025-07-06

### 更新内容
- TODO: 添加更新内容


## [1.2.1] - 2025-07-06 - Documentation Enhancement

### 文档完善
- **开发指导手册**: 新增 `docs/Development_Guide.md` 开发团队标准化流程指南
  - 完整的版本管理工作流程
  - Git分支管理和提交规范
  - 发布检查清单和团队协作规范
  - 常见问题解决方案和最佳实践
- **快速参考**: 新增 `docs/Quick_Reference.md` 版本管理快速参考卡片
  - 常用命令速查表
  - 标准发布流程
  - 紧急修复流程
- **文档结构优化**: 更新文档索引，突出开发指导手册重要性
- **README改进**: 完善项目主页文档链接结构，便于开发者快速找到所需文档


## [1.2.0] - 2025-07-06 - Version Management System

### 新增功能
- **完整版本管理系统**: 为DeepSOC添加了专业的版本管理能力
  - 新增核心版本文件 `app/_version.py`，支持语义化版本控制
  - 新增 `app/__init__.py` 统一暴露版本信息接口
  - 启动时显示版本信息横幅，包含版本号、发布名称、构建日期等
  - 新增 `/api/version` API端点，支持程序化获取版本信息
  - Web界面集成版本显示：首页底部和作战室右下角实时显示当前版本
  - 新增 `tools/version_manager.py` 专业版本管理工具
    - 支持查看、升级（patch/minor/major）和设置版本号
    - 自动更新changelog.md和创建Git标签
    - 集成Git工作流，支持版本标签管理
  - 新增 `tools/create_version_template.py` 版本管理模板生成器
    - 为任何Python项目快速生成版本管理骨架
    - 包含示例主程序、版本管理工具和使用文档
  - 新增包管理配置 `setup.py` 和 `MANIFEST.in`
  - 完善技术文档
    - `docs/Version_Management.md` - 详细版本管理指南
    - `docs/Simple_Version_Management_Template.md` - 简化版本管理模板说明
    - 更新项目文档索引，改进文档导航结构


### 新增
- **用户消息显示优化**: 修复多用户作战室中消息发送者显示不正确的问题
  - 后端API增强：在消息创建和广播时正确关联用户信息（user_id、user_nickname、user_username）
  - 前端显示逻辑优化：建立用户名称显示优先级机制（昵称 > 用户名 > localStorage > 默认）
  - 数据结构完善：消息对象包含完整的用户身份信息，支持多用户身份识别
  - 实时传递机制：通过WebSocket实时传递包含用户信息的消息
  - 创建专门的技术文档：`docs/User_Message_Display_Logic.md`，详细记录实现逻辑和测试验证
- **工程师对话系统**: 为安全工程师提供实时AI助手，支持异步消息处理和上下文感知对话
  - 统一Message表架构，支持Agent通信和工程师对话的数据隔离
  - 异步处理模式：用户消息立即显示（~10ms响应），AI回复后台处理（3-5秒）
  - WebSocket实时通信：用户消息和AI回复通过WebSocket实时推送
  - 会话管理：每个事件-用户组合创建独立对话会话，支持轮次限制（10轮/会话）
  - 上下文构建：基于事件概要和对话历史构建AI上下文，完全独立于Agent工作流
  - 前端集成：`@AI`触发模式，可视化思考指示器，即时用户体验优化
  - API端点：`/api/engineer-chat/*` 系列接口支持发送消息、获取历史、会话管理
  - 错误恢复：AI服务失败时的优雅降级和用户友好的错误提示
- 全局状态表 `global_settings`，支持存储并持久化系统级设置，如作战室的驾驶模式
- 创建 `DeepSOC状态流转设计文档.md`，详细设计了系统中Event、Task、Action、Command、Execution等实体的状态定义与流转规则
- 引入更加完善的状态流转设计，包括引入新增中间状态如`tasks_completed`、`to_be_summarized`、`summarized`等
- 优化事件处理流程，明确状态依赖关系与状态更新机制
- 新增`event_summarizing_worker`线程，专门负责处理从`tasks_completed`到`to_be_summarized`的状态转换
- 新增`event_next_round_worker`线程，专门负责处理从`round_finished`到下一轮`pending`的状态转换
- 实现worker线程的自适应睡眠时间调整机制，根据任务负载动态调整查询频率
- 添加`debug_event_status`功能，用于诊断事件状态和流转过程中的问题
- **引入 RabbitMQ 作为核心消息队列**：重构后端 Agent 服务与主 Web 服务之间的消息通知机制，实现异步化和解耦。
- **`RabbitMQPublisher` 工具类 (`app/utils/mq_utils.py`)**: 为各 Agent 服务提供统一的消息发布接口，支持连接重试和持久化消息。
- **`RabbitMQConsumer` 工具类 (`app/utils/mq_consumer.py`)**: 在主 Web 服务中实现，负责从 RabbitMQ 消费消息，支持连接重试和回调处理。
- 新增提示词管理页面及相关 API，可在“设置”菜单下编辑各角色提示词
- 新增 `prompts` 数据表，用于存储所有提示词和背景信息，前端可在线修改
- 初始化脚本现会自动导入内置的提示词，并移除相应 Markdown 模板文件
- 初始化脚本支持从 `initial_data.sql` 导入示例数据，安装后即可体验
- 用户表和消息表新增 `user_id`(UUID) 字段，用于标识消息发送者
- 作战室消息列表显示发送者昵称，并在服务端确认后替换临时消息
- 作战室支持用户发送文本消息，并通过 WebSocket 广播给其他在线用户，用户消息在界面右侧以蓝色高亮显示
- 发送消息现在通过 WebSocket 完成，前端在本地立即展示待确认的消息，收到服务端推送后自动替换
- **Agent 服务消息发布集成**: 
    - `captain_service.py`、`manager_service.py`、`operator_service.py`、`executor_service.py`、`expert_service.py`（包括其多线程worker）均已集成 `RabbitMQPublisher`，在生成业务消息（如LLM请求/响应、任务/动作/命令创建、执行结果、摘要生成、事件状态变更等）后，将消息发布到 RabbitMQ。
- **主 Web 服务消息消费与 WebSocket 推送**: 
    - `main.py` 集成 `RabbitMQConsumer`，在单独的后台线程中运行。
    - 消费者接收到消息后，通过 `handle_mq_message_to_socketio` 回调函数，使用 Flask-SocketIO (`new_message` 事件) 将消息推送到对应 `event_id` 的前端作战室。
    - 实现应用退出时对消费者的优雅关闭逻辑 (`atexit`注册)。
- **统一消息路由键前缀**: Agent 发布的消息使用 `notifications.frontend.{event_id}.{source}.{type}` 格式的路由键，消费者据此订阅 (`notifications.frontend.#`)。

### 优化
- 提供了状态流转流程图与状态转换说明
- 提出了优化建议，包括状态检查与更新机制、日志与监控、容错与恢复等
- 重构了`expert_service.py`中事件状态流转逻辑，将原本混合的逻辑拆分为更细粒度的步骤
- 明确了各个worker线程的职责，避免了状态更新的重叠和冲突
- 调整了`generate_event_summary`函数，使其只处理`to_be_summarized`状态的事件
- 合并`check_event_round_completion`和`update_event_round_status`为更清晰的`check_and_update_event_tasks_completion`函数
- 将状态名称`summarizing`改为更直观的`to_be_summarized`，更好地表达其意义
- 优化worker线程睡眠时间策略，采用指数退避算法，减少无效查询和日志输出
- 优化了event_next_round_worker线程的日志输出，增加【轮次推进】前缀，使轮次状态变化更加清晰可见
- 减小event_next_round_worker线程的初始睡眠时间（45s→20s）和最大睡眠时间（150s→90s），提高轮次推进的响应速度
- 修改了`captain_service.py`中的`get_events_to_process`函数，移除对`round_finished`状态事件的处理，确保与新的状态流转设计保持一致
- 重构`process_event`函数中轮次判断逻辑，使用`current_round`字段来确定是否为第一轮，而不是依赖事件状态
- 增强了事件状态的诊断功能，在worker线程中添加状态统计和详细日志，方便排查状态流转问题
- 改进数据库会话管理，在每次查询前调用`db.session.expire_all()`刷新会话，确保获取最新数据，避免缓存导致的状态不一致问题
- 在关键函数中添加状态二次验证，避免在长耗时操作后状态已被其他进程更改
- **解决前端消息重复问题与优化加载**: 
    - 后端确保每条消息的数据库ID (`message.id`) 在通过消息队列传递并在WebSocket推送时均包含在内。
    - `Message` 模型的 `to_dict()` 方法已确认包含数据库自增 `id`。
    - `main.py` 中 `handle_mq_message_to_socketio` 函数在通过WebSocket推送消息时，已确认将包含数据库 `id` 的完整消息对象发出。
    - 优化了事件消息拉取API (`GET /api/event/<event_id>/messages`)：
        - 支持 `last_message_db_id` 查询参数，用于获取该ID之后的新消息。

        - 查询结果按消息的数据库ID (`Message.id`) 升序排列，确保增量加载的准确性。
        - (指导前端) 前端应利用消息中的数据库 `id` 进行去重处理，并在轮询拉取时携带 `last_message_db_id` 参数，实现高效的增量加载，避免消息重复展示。

- 作战室事件关系树新增层级连接线，并在状态文本中加入 Emoji，提升可读性

### 修复
- 修复作战室退出功能，恢复WebSocket断开连接、停止自动刷新和调用后端登出接口的完整流程
- 解决了事件状态更新中可能存在的竞态条件问题
- 修正了`resolve_event`函数，使其符合新的状态流转逻辑
- 解决了worker线程过于频繁查询导致日志过多的问题
- 修复轮次更新的重复增加问题，确保事件轮次只在`advance_event_to_next_round`函数中递增 
- 修复了`captain_service.py`中处理轮次更新的逻辑错误，确保状态流转的连贯性和正确性
- 修复了`task_status_worker`中调用已删除函数的问题，将`check_event_round_completion`替换为新的`check_and_update_event_tasks_completion`函数
- 修复了多线程并发导致的数据库会话状态不一致问题，通过添加`db.session.expire_all()`确保每次查询都获取最新数据
- 修复允许修改初始管理员账号角色的漏洞，禁止更改`ADMIN_USERNAME`指定账户的角色
- 修复事件消息接口导入 `User` 模型失败的问题，确保正确返回发送者昵称

### 变更 (本次消息机制重大更新)
- **消息传递流程重构**: 
    - Agent 服务不再直接通过 `socket_controller.broadcast_message` 或其他方式与 WebSocket 交互。
    - 所有后端到前端的通知均通过 RabbitMQ 的 Topic Exchange (`deepsoc_notifications_exchange`) 进行路由和传递。
- **`create_standard_message` (`app/utils/message_utils.py`)**: 移除内部对 `broadcast_message` 的直接调用。Agent 调用此函数创建并保存消息到数据库后，自行负责将消息内容发送到 RabbitMQ。
- **`broadcast_message` (`app/controllers/socket_controller.py`)**: 此函数不再被 Agent 服务直接调用。其功能（向特定房间广播消息）现在由主进程中 MQ 消费者的回调函数 `handle_mq_message_to_socketio` 在 `main.py` 中实现。
- **数据库持久化**: 消息在 Agent 服务中通过 `create_standard_message` 创建时即存入数据库。主 Web 服务的 MQ 消费者收到消息后不再重复写入数据库，仅负责通过 WebSocket 推送。
- **`main.py` 启动逻辑**: MQ 消费者仅在主 Web 服务模式下启动，Agent 角色启动时则不启动。
- **配置项**: `main.py` 中的部分 Flask 和 SocketIO 配置（如日志开关、缓冲区大小）改为通过环境变量控制。

### 移除 (本次消息机制重大更新)
- Agent 服务 (`captain`, `manager`, `operator`, `executor`, `expert`) 中对 `app.controllers.socket_controller.broadcast_message` 的直接调用及相关导入。
- 作战室用户发送的消息不再自动转发给指挥官进行大模型请求，仅在房间内广播。

### 修复
- 前端无法正确显示事件状态，因 `Event.to_dict()` 返回的字段名与前端期望不一致，现统一为 `event_status`，并保留 `status` 兼容旧代码。
- 系统通知等消息内容显示 `undefined`，更新前端 `warroom.js` 使用统一的 `extractMessageData` 函数解析消息内容。
- 作战室仍然显示原始 JSON 的 AI 响应，前端 `warroom.js` 现统一处理 `*_llm_request` 与 `*_llm_response` 类型。

### 新增
- 提示词管理页面改为左侧导航布局，支持切换各角色及背景信息编辑。
- 新增API `GET/PUT /api/prompt/background/<name>` 用于管理背景文件。
- `PromptService` 采用 `generate_prompt` 动态生成提示词。
- 作战室事件详情模态框支持 Markdown 渲染，展示原始信息、上下文和事件总结时格式更友好。
- 新增修改密码页面及 `/api/auth/change-password` 接口，用户可在登录后通过右上角菜单修改密码。
- 作战室 system 消息统一右侧对齐，展示更清晰。
- 消息源码弹窗新增 "复制源码" 按钮，便于快速复制原始信息。
- 设置页面顶部导航现会显示登录用户名。


- 新增管理员用户管理功能，可在导航栏进入用户管理界面创建、修改和删除用户。

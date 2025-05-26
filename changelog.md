# DeepSOC 更新日志

## [未发布]

### 新增
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

### 修复
- 前端无法正确显示事件状态，因 `Event.to_dict()` 返回的字段名与前端期望不一致，现统一为 `event_status`，并保留 `status` 兼容旧代码。
- 系统通知等消息内容显示 `undefined`，更新前端 `warroom.js` 使用统一的 `extractMessageData` 函数解析消息内容。
- 作战室仍然显示原始 JSON 的 AI 响应，前端 `warroom.js` 现统一处理 `*_llm_request` 与 `*_llm_response` 类型。

### 新增
- 提示词管理页面改为左侧导航布局，支持切换各角色及背景信息编辑。
- 新增API `GET/PUT /api/prompt/background/<name>` 用于管理背景文件。
- `PromptService` 采用 `generate_prompt` 动态生成提示词。
- 新增修改密码页面及 `/api/auth/change-password` 接口，用户可在登录后通过右上角菜单修改密码。


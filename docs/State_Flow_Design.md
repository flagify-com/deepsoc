# DeepSOC系统状态流转设计文档

## 1. 概述

本文档详细描述了DeepSOC系统中各核心实体（Event、Task、Action、Command、Execution）的状态流转设计，包括每个状态的定义、状态之间的转换条件和转换过程，以及状态流转中的注意事项和优化设计。

未来建议：
1. 将事件、任务等状态变更的动作放到独立的进程中，避免在主线程中进行状态变更，导致主线程阻塞。
2. 处理好数据库状态和锁的问题，避免在并发情况下，状态更新不一致的问题。

## 2. 核心实体状态定义

### 2.1 Event（事件）状态

| 状态 | 描述 | 触发条件 |
| --- | --- | --- |
| `pending` | 初始状态，事件已创建但尚未开始处理 | 事件创建时自动设置 |
| `processing` | 事件正在处理中 | Captain开始处理事件时设置 |
| `tasks_completed` | 事件当前轮次的所有任务已完成 | Expert检测到所有任务和执行都完成时设置 |
| `to_be_summarized` | 事件已标记为待生成总结 | Expert标记事件准备生成总结时设置 |
| `summarized` | 事件总结已生成 | Expert完成事件总结生成时设置 |
| `summary_failed` | 总结生成失败 | 调用LLM或生成总结过程中出错时设置 |
| `round_finished` | 当前轮次处理完成 | Expert在总结生成后设置 |
| `failed` | 事件处理失败 | 任务执行过程中出现不可恢复的错误时设置 |
| `completed` | 事件全部处理完成 | 达到最大轮次或解决方案有效时设置 |
| `resolved` | 事件已人工解决 | 人工干预解决事件时设置 |

### 2.2 Task（任务）状态

| 状态 | 描述 | 触发条件 |
| --- | --- | --- |
| `pending` | 初始状态，任务已创建但尚未开始处理 | 任务创建时自动设置 |
| `processing` | 任务正在处理中 | Manager开始处理任务时设置 |
| `completed` | 任务处理完成 | 所有相关命令都完成时设置 |
| `failed` | 任务处理失败 | 任意相关命令失败时设置 |

### 2.3 Action（动作）状态

| 状态 | 描述 | 触发条件 |
| --- | --- | --- |
| `pending` | 初始状态，动作已创建但尚未开始处理 | 动作创建时自动设置 |
| `processing` | 动作正在处理中 | Operator开始处理动作时设置 |
| `completed` | 动作处理完成 | 所有相关命令都完成时设置 |
| `failed` | 动作处理失败 | 任意相关命令失败时设置 |

### 2.4 Command（命令）状态

| 状态 | 描述 | 触发条件 |
| --- | --- | --- |
| `pending` | 初始状态，命令已创建但尚未开始处理 | 命令创建时自动设置 |
| `processing` | 命令正在处理中 | Executor开始处理命令时设置 |
| `completed` | 命令处理完成 | 所有相关执行都完成时设置 |
| `failed` | 命令处理失败 | 任意相关执行失败时设置 |

### 2.5 Execution（执行）状态

| 状态 | 描述 | 触发条件 |
| --- | --- | --- |
| `pending` | 初始状态，执行已创建但尚未开始处理 | 执行创建时自动设置 |
| `waiting` | 等待人工干预 | 手动操作类型命令创建执行时设置 |
| `processing` | 执行正在处理中 | 开始执行命令时设置 |
| `completed` | 执行完成但尚未生成摘要 | 命令执行完成但尚未生成摘要时设置 |
| `summarized` | 执行结果已生成摘要 | Expert生成执行结果摘要后设置 |
| `summarized_error` | 摘要生成失败 | 生成执行结果摘要过程中出现错误时设置 |
| `failed` | 执行失败 | 命令执行过程中出现错误时设置 |

## 3. 状态流转流程

### 3.1 Event状态流转

```
[创建] -> pending -> processing -> tasks_completed -> to_be_summarized -> summarized -> round_finished -> pending(下一轮) -> ... -> completed/resolved
                                                                                                                             |
                                                                                                                             v
                                                                                                                           failed
```

状态转换说明：
1. `pending` → `processing`: Captain服务开始处理事件
2. `processing` → `tasks_completed`: 当前轮次所有任务及其执行都完成
3. `tasks_completed` → `to_be_summarized`: Expert标记事件为待生成总结
4. `to_be_summarized` → `summarized`: 事件总结生成完成
5. `summarized` → `round_finished`: Expert将事件标记为当前轮次完成
6. `round_finished` → `pending`: 推进到下一轮次
7. `round_finished` → `completed`: 达到最大轮次
8. 任何状态 → `resolved`: 人工干预解决事件
9. 任何状态 → `failed`: 处理过程中出现不可恢复的错误

### 3.2 Task状态流转

```
[创建] -> pending -> processing -> completed
                        |
                        v
                      failed
```

状态转换说明：
1. `pending` → `processing`: Manager服务开始处理任务
2. `processing` → `completed`: 所有相关命令都完成
3. `processing` → `failed`: 任意相关命令失败

### 3.3 Action状态流转

```
[创建] -> pending -> processing -> completed
                        |
                        v
                      failed
```

状态转换说明：
1. `pending` → `processing`: Operator服务开始处理动作
2. `processing` → `completed`: 所有相关命令都完成
3. `processing` → `failed`: 任意相关命令失败

### 3.4 Command状态流转

```
[创建] -> pending -> processing -> completed
                        |
                        v
                      failed
```

状态转换说明：
1. `pending` → `processing`: Executor服务开始处理命令
2. `processing` → `completed`: 所有相关执行都完成
3. `processing` → `failed`: 任意相关执行失败

### 3.5 Execution状态流转

```
[创建] -> pending -> processing -> completed -> summarized
            |            |
            v            v
         waiting       failed
```

状态转换说明：
1. `pending` → `processing`: 开始执行命令
2. `pending` → `waiting`: 对于需要人工干预的命令
3. `processing`/`waiting` → `completed`: 执行完成但尚未生成摘要
4. `completed` → `summarized`: Expert生成执行结果摘要
5. `processing`/`waiting` → `failed`: 执行过程中出现错误

### 3.6 事件到执行的状态递进及轮次逻辑

1. 新事件创建后处于 `pending` 状态，`current_round` 默认为 1。
2. Captain 服务拉取 `pending` 事件，设置为 `processing` 并调用大模型生成任务（Task）。
3. 任务创建后为 `pending`，由 Manager 服务取出后标记为 `processing`，并根据任务内容生成动作（Action）。
4. Operator 服务处理 `pending` 动作，生成具体命令（Command），命令随后被 Executor 服务拉取执行，状态从 `pending` → `processing`。
5. 执行过程中会创建 Execution，状态依次经历 `pending`、`processing`/`waiting`、`completed`。Expert 服务为 `completed` 的执行生成摘要，状态更新为 `summarized` 或 `summarized_error`。
6. 当命令的所有执行都进入终态后，命令状态更新为 `completed`/`failed`，并依次向上触发动作、任务状态更新。
7. 当前轮次所有任务完成后，事件状态变为 `tasks_completed`，随后在生命周期管理器中依次流转至 `to_be_summarized`、`summarized`、`round_finished`。
8. 若事件未结束且未达到最大轮次，`advance_event_to_next_round` 会将 `current_round` 加一，并把事件状态重新置为 `pending`，开始下一轮处理。
9. 当事件被人工 `resolved` 或达到设定最大轮次后，会生成最终总结，事件状态置为 `completed`。

## 4. 优化设计与实现建议

### 4.1 Event处理流程优化

当前系统中存在两个可能导致冲突的事件状态更新路径：
1. `event_round_status_worker`: 检测任务完成，更新事件状态为`round_finished`，并直接调用`generate_event_summary`
2. `event_summary_worker`: 对`round_finished`状态的事件生成总结，并推进到下一轮

建议优化为：
1. `event_round_status_worker`: 仅负责将事件从`processing`状态更新为`tasks_completed`
2. 新增`event_summarizing_worker`: 处理`tasks_completed`状态的事件，将状态更新为`to_be_summarized`
3. `event_summary_worker`: 负责将`to_be_summarized`状态的事件更新为`summarized`，然后是`round_finished`
4. 新增`event_next_round_worker`: 负责将`round_finished`状态的事件推进到下一轮

### 4.2 状态检查与更新机制

为避免状态检查和更新过程中的竞态条件，建议：
1. 使用数据库事务确保状态更新的原子性
2. 添加状态前置条件检查，确保状态只能按预定义的流程转换
3. 对状态更新操作添加适当的锁机制，防止并发更新冲突

### 4.3 日志与监控

为方便故障排查和系统监控，建议：
1. 记录每次状态变更的详细日志，包括时间、原状态、新状态、触发原因
2. 实现状态转换超时监控机制，及时发现状态流转异常
3. 提供状态统计视图，方便管理员了解系统中各实体的状态分布

### 4.4 容错与恢复

为提高系统健壮性，建议：
1. 实现状态自修复机制，定期检查长时间停留在中间状态的实体
2. 提供手动干预接口，允许管理员强制修改实体状态
3. 设计状态回滚机制，支持在特定条件下回退到上一状态

## 5. 状态依赖关系

各实体之间的状态依赖关系如下：

1. Event → Task: 事件创建并开始处理后，才会创建并处理相关任务
2. Task → Action: 任务创建并开始处理后，才会创建并处理相关动作
3. Action → Command: 动作创建并开始处理后，才会创建并处理相关命令
4. Command → Execution: 命令创建并开始处理后，才会创建并处理相关执行

状态更新的上行传递机制：
1. 所有Execution变为终态(summarized/failed)时，触发Command状态更新
2. 所有Command变为终态(completed/failed)时，触发Action状态更新
3. 所有Action变为终态(completed/failed)时，触发Task状态更新
4. 所有Task变为终态(completed/failed)时，触发Event状态更新

## 6. 结论

本设计文档详细定义了DeepSOC系统中各实体的状态及其流转规则，通过明确的状态定义和转换条件，可以确保系统运行过程中的状态一致性和可追踪性。优化后的状态流转设计将减少潜在的竞态条件和状态冲突，提高系统的稳定性和可靠性。 
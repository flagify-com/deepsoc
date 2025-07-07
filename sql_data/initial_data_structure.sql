-- ============================================================
-- DeepSOC 演示数据结构文件 (精简版)
-- ============================================================
-- 文件描述: 包含基本数据结构，所有text字段为空字符串，仅用于测试数据库结构
-- 版本: 1.0.0
-- 创建日期: 2025-07-07
-- 修改日期: 2025-07-07
-- 兼容版本: DeepSOC v1.6.1+
-- 说明: 此文件为结构测试版本，实际演示请使用 initial_data.sql
-- ============================================================

-- 插入事件数据 (结构测试)
INSERT INTO events (id, event_id, event_name, message, context, source, severity, event_status, current_round, created_at, updated_at)
VALUES (1, 'test-event-001', 'test event', 'test message', 'test context', 'manual', 'medium', 'completed', 2, '2025-07-07 00:00:00', '2025-07-07 00:00:00');

-- 插入任务数据 (结构测试)
INSERT INTO tasks (id, task_id, event_id, task_name, task_type, task_assignee, task_status, round_id, result, created_at, updated_at)
VALUES 
(1, 'test-task-001', 'test-event-001', 'test task 1', 'query', '_operator', 'completed', 1, '{}', '2025-07-07 00:00:00', '2025-07-07 00:00:00'),
(2, 'test-task-002', 'test-event-001', 'test task 2', 'query', '_operator', 'completed', 1, '{}', '2025-07-07 00:00:00', '2025-07-07 00:00:00'),
(3, 'test-task-003', 'test-event-001', 'test task 3', 'mitigation', '_operator', 'completed', 2, '{}', '2025-07-07 00:00:00', '2025-07-07 00:00:00');

-- 插入动作数据 (结构测试)
INSERT INTO actions (id, action_id, task_id, round_id, event_id, action_name, action_type, action_assignee, action_status, action_result, created_at, updated_at)
VALUES 
(1, 'test-action-001', 'test-task-001', 1, 'test-event-001', 'test action 1', 'query', '_operator', 'completed', NULL, '2025-07-07 00:00:00', '2025-07-07 00:00:00'),
(2, 'test-action-002', 'test-task-002', 1, 'test-event-001', 'test action 2', 'query', '_operator', 'completed', NULL, '2025-07-07 00:00:00', '2025-07-07 00:00:00'),
(3, 'test-action-003', 'test-task-003', 2, 'test-event-001', 'test action 3', 'mitigation', '_operator', 'completed', NULL, '2025-07-07 00:00:00', '2025-07-07 00:00:00');

-- 插入命令数据 (结构测试)
INSERT INTO commands (id, command_id, action_id, task_id, event_id, round_id, command_name, command_type, command_assignee, command_entity, command_params, command_status, command_result, created_at, updated_at)
VALUES 
(1, 'test-command-001', 'test-action-001', 'test-task-001', 'test-event-001', 1, 'test command 1', 'playbook', '_executor', '{}', '{}', 'completed', '{}', '2025-07-07 00:00:00', '2025-07-07 00:00:00'),
(2, 'test-command-002', 'test-action-002', 'test-task-002', 'test-event-001', 1, 'test command 2', 'playbook', '_executor', '{}', '{}', 'completed', '{}', '2025-07-07 00:00:00', '2025-07-07 00:00:00');

-- 插入执行记录数据 (结构测试)
INSERT INTO executions (id, execution_id, command_id, action_id, task_id, event_id, round_id, execution_result, execution_summary, ai_summary, execution_status, created_at, updated_at)
VALUES 
(1, 'test-execution-001', 'test-command-001', 'test-action-001', 'test-task-001', 'test-event-001', 1, '{}', 'test summary 1', 'test ai summary 1', 'completed', '2025-07-07 00:00:00', '2025-07-07 00:00:00'),
(2, 'test-execution-002', 'test-command-002', 'test-action-002', 'test-task-002', 'test-event-001', 1, '{}', 'test summary 2', 'test ai summary 2', 'completed', '2025-07-07 00:00:00', '2025-07-07 00:00:00');

-- 插入消息数据 (结构测试)
INSERT INTO messages (id, message_id, event_id, user_id, message_from, round_id, message_content, message_type, message_category, chat_session_id, sender_type, event_summary_version, created_at, updated_at)
VALUES 
(1, 'test-message-001', 'test-event-001', NULL, '_captain', 1, '{}', 'task_assignment', 'agent', NULL, NULL, NULL, '2025-07-07 00:00:00', '2025-07-07 00:00:00'),
(2, 'test-message-002', 'test-event-001', NULL, '_manager', 1, '{}', 'task_assignment', 'agent', NULL, NULL, NULL, '2025-07-07 00:00:00', '2025-07-07 00:00:00');

-- 插入总结数据 (结构测试)
INSERT INTO summaries (id, summary_id, event_id, round_id, event_summary, event_suggestion, created_at, updated_at)
VALUES 
(1, 'test-summary-001', 'test-event-001', 1, 'test summary 1', 'test suggestion 1', '2025-07-07 00:00:00', '2025-07-07 00:00:00'),
(2, 'test-summary-002', 'test-event-001', 2, 'test summary 2', 'test suggestion 2', '2025-07-07 00:00:00', '2025-07-07 00:00:00');

-- 插入LLM记录数据 (结构测试) - 如果表存在
INSERT INTO llm_records (id, request_id, model_name, created_at) 
VALUES (1, 'test-llm-001', 'test_model', '2025-07-07 00:00:00');


-- 用户由系统初始化时自动创建，无需插入
-- 提示词数据由系统初始化时自动创建，无需插入


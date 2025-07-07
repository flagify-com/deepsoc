// DeepSOC 作战室页面脚本

// 获取事件ID
const eventId = document.getElementById('event-id-data').getAttribute('data-event-id');

// API基础URL
const API_BASE_URL = '/api';

// 全局变量
let isAutoMode = true;
let lastMessageId = 0;
let displayedMessages = new Set();
let eventData = null;
let taskCount = 0;
let actionCount = 0;
let commandCount = 0;
let socketReconnectAttempts = 0;
let maxReconnectAttempts = 10;
let reconnectInterval = 2000; // 初始重连间隔2秒
let isManuallyDisconnected = false;
let refreshIntervalId = null; // 定时刷新ID
let refreshInterval = 30000; // 默认30秒刷新一次
let lastRefreshTime = 0; // 上次刷新时间
let isRefreshing = false; // 是否正在刷新
let waitingExecutions = []; // 等待处理的执行任务列表
let currentExecution = null; // 当前正在处理的执行任务
let messagesData = []; // 存储所有消息数据的数组

// WebSocket连接
const socket = io({
    transports: ['websocket', 'polling'], // 优先使用WebSocket
    upgrade: true,
    reconnection: true,
    reconnectionAttempts: maxReconnectAttempts,
    reconnectionDelay: reconnectInterval,
    reconnectionDelayMax: 10000, // 最大重连延迟10秒
    timeout: 20000,
    forceNew: true, // 强制创建新连接
    autoConnect: false // 手动控制连接时机
});

// DOM元素引用
const elements = {
    chatMessages: document.getElementById('chat-messages'),
    userInput: document.getElementById('user-input'),
    sendButton: document.getElementById('send-button'),
    eventName: document.getElementById('event-name'),
    eventStatus: document.getElementById('event-status'),
    eventIdDisplay: document.getElementById('event-id-display'),
    eventRound: document.getElementById('event-round'),
    eventSource: document.getElementById('event-source'),
    eventSeverity: document.getElementById('event-severity'),
    eventCreated: document.getElementById('event-created'),
    currentRound: document.getElementById('current-round'),
    taskCount: document.getElementById('task-count'),
    actionCount: document.getElementById('action-count'),
    commandCount: document.getElementById('command-count'),
    modeSwitch: document.getElementById('mode-switch'),
    eventDetailsBtn: document.getElementById('event-details-btn'),
    eventTreeBtn: document.getElementById('event-tree-btn'),
    eventTreeModal: document.getElementById('event-tree-modal'),
    eventTreeContainer: document.getElementById('event-tree-container'),
    eventDetailsModal: document.getElementById('event-details-modal'),
    roleHistoryModal: document.getElementById('role-history-modal'),
    messageSourceModal: document.getElementById('message-source-modal'),
    messageSourceContent: document.getElementById('message-source-content'),
    roleItems: document.querySelectorAll('.role-item'),
    settingsBtn: document.getElementById('settings-btn'),
    logoutBtn: document.getElementById('logout-btn'),
    connectionStatus: document.getElementById('connection-status'),
    // 执行任务相关元素
    executionIndicator: document.getElementById('execution-indicator'),
    executionCount: document.querySelector('.execution-count'),
    executionPanel: document.getElementById('execution-panel'),
    executionList: document.getElementById('execution-list'),
    executionEmpty: document.getElementById('execution-empty'),
    executionCountDisplay: document.getElementById('execution-count-display'),
    executionModal: document.getElementById('execution-modal'),
    executionId: document.getElementById('execution-id'),
    executionCommand: document.getElementById('execution-command'),
    executionTime: document.getElementById('execution-time'),
    contextContent: document.getElementById('context-content'),
    contextToggle: document.getElementById('context-toggle'),
    executionResult: document.getElementById('execution-result'),
    submitExecution: document.getElementById('submit-execution'),
    laterExecution: document.getElementById('later-execution')
};

// 存储所有消息的映射，用于源码查看
const messagesMap = new Map();
let currentSourceMessageId = null;

// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // 检查用户是否已登录
    checkAuth();
    
    // 初始化事件
    initWarRoom();
});

// 检查用户是否已登录
function checkAuth() {
    const token = localStorage.getItem('access_token') || getCookie('access_token');
    
    if (!token) {
        // 未登录，显示提示并重定向
        showLoginRequired();
        return;
    }
    
    // 验证token有效性
    fetch('/api/auth/check-auth', {
        headers: getAuthHeaders(),
        credentials: 'include'  // 包含凭证
    })
    .then(response => response.json())
    .then(data => {
        if (!data.authenticated) {
            // token无效，显示提示并重定向
            localStorage.removeItem('access_token');
            localStorage.removeItem('user_info');
            document.cookie = 'access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
            showLoginRequired();
        }
    })
    .catch(error => {
        console.error('验证认证状态错误:', error);
        localStorage.removeItem('access_token');
        localStorage.removeItem('user_info');
        document.cookie = 'access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
        showLoginRequired();
    });
}

// 显示登录提示并重定向
function showLoginRequired() {
    const warRoomContainer = document.getElementById('war-room-container');
    
    if (warRoomContainer) {
        warRoomContainer.innerHTML = `
            <div class="text-center py-5">
                <div class="alert alert-warning" role="alert">
                    <h4 class="alert-heading">需要登录</h4>
                    <p>您需要登录后才能访问作战室</p>
                    <hr>
                    <p class="mb-0">即将跳转到登录页面...</p>
                </div>
            </div>
        `;
    }
    
    // 延迟跳转到登录页
    setTimeout(() => {
        window.location.href = '/login';
    }, 2000);
}

// 初始化作战室
function initWarRoom() {
    console.log('%c[页面] 页面加载完成，初始化作战室...', 'background: #E91E63; color: white; padding: 2px 5px; border-radius: 3px;');
    
    // 初始化事件监听器
    initEventListeners();
    
    // 加载事件详情
    fetchEventDetails();
    
    // 加载事件消息
    fetchEventMessages();
    
    // 加载事件统计
    fetchEventStats();

    // 获取当前驾驶模式
    fetchDrivingMode();
    
    // 加载等待处理的执行任务
    fetchWaitingExecutions();
    
    // 初始化WebSocket
    initializeSocket();
    
    // 启动定时刷新
    startAutoRefresh();
    
    // 页面关闭前断开连接
    window.addEventListener('beforeunload', () => {
        console.log('%c[页面] 页面即将关闭，断开连接', 'color: #E91E63;');
        isManuallyDisconnected = true;
        socket.disconnect();
        stopAutoRefresh();
    });
    
    // 页面可见性变化时处理
    document.addEventListener('visibilitychange', handleVisibilityChange);
    
    console.log('%c[页面] 作战室初始化完成', 'color: #E91E63; font-weight: bold;');
}

// 处理页面可见性变化
function handleVisibilityChange() {
    if (document.visibilityState === 'visible') {
        // 页面变为可见时，立即刷新数据并重启定时器
        console.log('%c[页面] 页面变为可见，立即刷新数据', 'background: #E91E63; color: white; padding: 2px 5px; border-radius: 3px;');
        refreshData(true);
        startAutoRefresh();
    } else {
        // 页面变为不可见时，停止定时刷新
        console.log('%c[页面] 页面变为不可见，暂停定时刷新', 'color: #E91E63;');
        stopAutoRefresh();
    }
}

// 启动定时刷新
function startAutoRefresh() {
    // 如果已经有定时器，先清除
    stopAutoRefresh();
    
    console.log(`%c[定时刷新] 启动定时刷新，间隔: ${refreshInterval}ms`, 'background: #795548; color: white; padding: 2px 5px; border-radius: 3px;');
    
    // 创建新的定时器
    refreshIntervalId = setInterval(() => {
        console.log('%c[定时刷新] 触发定时刷新', 'color: #795548;');
        refreshData();
    }, refreshInterval);
    
    // 记录启动时间
    lastRefreshTime = Date.now();
}

// 停止定时刷新
function stopAutoRefresh() {
    if (refreshIntervalId) {
        clearInterval(refreshIntervalId);
        refreshIntervalId = null;
        console.log('%c[定时刷新] 停止定时刷新', 'color: #795548;');
    }
}

// 刷新数据
async function refreshData(force = false) {
    if (isRefreshing && !force) return;
    
    isRefreshing = true;
    
    try {
        const eventDetailsResponse = await fetch(`/api/event/${eventId}`, {
            headers: getAuthHeaders(),
            credentials: 'include'
        });
        
        if (eventDetailsResponse.status === 401) {
            // 认证失败，跳转到登录页
            localStorage.removeItem('access_token');
            localStorage.removeItem('user_info');
            document.cookie = 'access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
            window.location.href = '/login';
            return;
        }
        
        const eventData = await eventDetailsResponse.json();
        
        if (eventData.status === 'success') {
            displayEventDetails(eventData.data);
        }
        
        // 获取最新消息
        fetchEventMessages();
        
        // 获取执行中任务
        fetchWaitingExecutions();
        
        // 获取统计数据
        fetchEventStats();
    } catch (error) {
        console.error('刷新数据错误:', error);
    } finally {
        isRefreshing = false;
    }
}

// 初始化WebSocket连接
function initializeSocket() {
    // 设置所有事件监听器
    setupSocketEventListeners();
    
    // 开始连接
    socket.connect();
    
    // 显示连接状态
    updateConnectionStatus('connecting');
}

// 设置Socket事件监听器
function setupSocketEventListeners() {
    // 连接成功
    socket.on('connect', () => {
        console.log('%c[WebSocket] 连接成功，Socket ID:', 'background: #4CAF50; color: white; padding: 2px 5px; border-radius: 3px;', socket.id);
        socketReconnectAttempts = 0;
        updateConnectionStatus('connected');
        
        // 加入房间
        joinWarroom();
    });
    
    // 连接错误
    socket.on('connect_error', (error) => {
        console.error('WebSocket连接错误:', error);
        updateConnectionStatus('error');
        showToast('WebSocket连接失败: ' + error.message, 'error');
        
        // 如果不是手动断开，尝试重连
        if (!isManuallyDisconnected) {
            attemptReconnect();
        }
    });
    
    // 连接超时
    socket.on('connect_timeout', () => {
        console.error('WebSocket连接超时');
        updateConnectionStatus('timeout');
        showToast('WebSocket连接超时，正在重试...', 'error');
        
        // 如果不是手动断开，尝试重连
        if (!isManuallyDisconnected) {
            attemptReconnect();
        }
    });
    
    // 断开连接
    socket.on('disconnect', (reason) => {
        console.log('WebSocket断开连接，原因:', reason);
        updateConnectionStatus('disconnected');
        
        // 如果不是手动断开且不是正常关闭，尝试重连
        if (!isManuallyDisconnected && reason !== 'io client disconnect') {
            showToast('WebSocket连接断开: ' + reason + '，正在重试...', 'warning');
            attemptReconnect();
        }
    });
    
    // 重连尝试
    socket.on('reconnect_attempt', (attemptNumber) => {
        console.log(`WebSocket重连尝试 ${attemptNumber}/${maxReconnectAttempts}`);
        updateConnectionStatus('reconnecting');
        showToast(`正在尝试重新连接 (${attemptNumber}/${maxReconnectAttempts})`, 'info');
    });
    
    // 重连成功
    socket.on('reconnect', (attemptNumber) => {
        console.log(`WebSocket重连成功，尝试次数: ${attemptNumber}`);
        updateConnectionStatus('connected');
        showToast('WebSocket重连成功', 'success');
        socketReconnectAttempts = 0;
    });
    
    // 重连失败
    socket.on('reconnect_failed', () => {
        console.error('WebSocket重连失败，已达到最大尝试次数');
        updateConnectionStatus('failed');
        showToast('WebSocket重连失败，请刷新页面重试', 'error');
    });
    
    // 错误事件
    socket.on('error', (error) => {
        console.error('WebSocket错误:', error);
        showToast('WebSocket发生错误: ' + error, 'error');
    });
    
    // 新消息
    socket.on('new_message', (message) => {
        console.log('%c[WebSocket] 收到新消息:', 'background: #4CAF50; color: white; padding: 2px 5px; border-radius: 3px;', message);
        
        // 工程师对话消息的特殊处理
        if (message.message_category === 'engineer_chat') {
            console.log('%c[工程师对话] 收到工程师对话消息', 'background: #FF9800; color: white; padding: 2px 5px; border-radius: 3px;', {
                sender_type: message.sender_type,
                message_id: message.message_id,
                content_preview: typeof message.message_content === 'object' ? 
                    message.message_content.content?.substring(0, 50) + '...' : 
                    message.message_content?.substring(0, 50) + '...'
            });
            
            // 如果是AI回复，隐藏思考指示器
            if (message.sender_type === 'ai') {
                hideAIThinkingIndicator();
                console.log('%c[工程师对话] 收到AI回复，隐藏思考指示器', 'color: #4CAF50;');
            }
        }
        
        // 直接调用新的 addMessage 函数，它会处理去重和状态更新
        const added = addMessage(message);
        console.log(`%c[WebSocket] 消息添加结果: ${added ? '成功' : '失败/重复'}`, added ? 'color: #4CAF50;' : 'color: #FFA500;');
        
        if (added) {
            scrollToBottom();
            
            // 如果有新任务或状态变化，刷新统计和事件详情 (此逻辑保留)
            if (message.message_type === 'llm_response' ||
                message.message_type === 'command_result' ||
                message.message_type === 'execution_summary' ||
                message.message_type === 'execution_summary_generated' ||
                message.message_type === 'event_summary' ||
                message.message_type === 'event_summary_generated') {
                fetchEventStats();
                fetchEventDetails();
            }
        }
    });
    
    // 状态变化
    socket.on('status', (data) => {
        console.log('%c[WebSocket] 收到状态更新:', 'background: #9C27B0; color: white; padding: 2px 5px; border-radius: 3px;', data);
        
        // 如果事件状态发生变化，刷新事件详情和统计
        if (data.event_status) {
            console.log(`%c[WebSocket] 事件状态变化为: ${data.event_status}`, 'color: #9C27B0;');
            fetchEventDetails();
            fetchEventStats();
        }
        
        // 如果收到joined状态，表示成功加入房间
        if (data.status === 'joined') {
            console.log(`%c[WebSocket] 成功加入作战室: ${data.event_id}`, 'color: #9C27B0; font-weight: bold;');
        }
    });
    
    // 添加调试事件监听
    socket.onAny((event, ...args) => {
        console.log(`%c[WebSocket] 收到事件: ${event}`, 'background: #607D8B; color: white; padding: 2px 5px; border-radius: 3px;', args);
    });
    
    // 测试消息
    socket.on('test_message', (data) => {
        console.log('%c[WebSocket] 收到测试消息:', 'background: #FF9800; color: white; padding: 2px 5px; border-radius: 3px;', data);
        showToast(`WebSocket测试消息: ${data.message}`, 'info');
    });
    
    // 连接测试响应
    socket.on('test_connection_response', (data) => {
        console.log('%c[WebSocket] 收到连接测试响应:', 'background: #FF9800; color: white; padding: 2px 5px; border-radius: 3px;', data);
        showToast(`WebSocket连接测试成功: ${data.message}`, 'success');
    });
    
    // 新执行任务
    socket.on('new_execution', (execution) => {
        console.log('%c[WebSocket] 收到新执行任务:', 'background: #FF9800; color: white; padding: 2px 5px; border-radius: 3px;', execution);
        
        // 检查执行任务格式
        if (!execution || !execution.id) {
            console.error('%c[WebSocket] 收到的执行任务格式无效:', 'color: #F44336;', execution);
            return;
        }
        
        // 检查是否已存在
        const existingIndex = waitingExecutions.findIndex(e => e.id === execution.id);
        if (existingIndex === -1 && execution.status === 'waiting') {
            // 添加到等待列表
            waitingExecutions.push(execution);
            
            // 更新UI
            updateExecutionIndicator();
            updateExecutionList();
            
            // 显示通知
            showExecutionNotification(execution);
        }
    });
    
    // 执行任务状态更新
    socket.on('execution_update', (data) => {
        console.log('%c[WebSocket] 收到执行任务状态更新:', 'background: #FF9800; color: white; padding: 2px 5px; border-radius: 3px;', data);
        
        // 检查数据格式
        if (!data || !data.execution_id) {
            console.error('%c[WebSocket] 收到的执行任务状态更新格式无效:', 'color: #F44336;', data);
            return;
        }
        
        // 更新等待列表
        const executionIndex = waitingExecutions.findIndex(e => e.id === data.execution_id);
        if (executionIndex !== -1) {
            if (data.status !== 'waiting') {
                // 如果状态不再是waiting，从列表中移除
                waitingExecutions.splice(executionIndex, 1);
            } else {
                // 更新执行任务信息
                waitingExecutions[executionIndex] = { ...waitingExecutions[executionIndex], ...data };
            }
            
            // 更新UI
            updateExecutionIndicator();
            updateExecutionList();
        }
    });
}

// 尝试重新连接
function attemptReconnect() {
    socketReconnectAttempts++;
    
    if (socketReconnectAttempts <= maxReconnectAttempts) {
        // 使用指数退避策略增加重连间隔
        const delay = Math.min(reconnectInterval * Math.pow(1.5, socketReconnectAttempts - 1), 30000);
        
        console.log(`将在 ${delay}ms 后尝试第 ${socketReconnectAttempts} 次重连`);
        
        setTimeout(() => {
            if (!socket.connected && !isManuallyDisconnected) {
                console.log(`执行第 ${socketReconnectAttempts} 次重连`);
                socket.connect();
            }
        }, delay);
    } else {
        updateConnectionStatus('failed');
        showToast('已达到最大重连次数，请刷新页面重试', 'error');
    }
}

// 更新连接状态显示
function updateConnectionStatus(status) {
    if (!elements.connectionStatus) return;
    
    // 移除所有状态类
    elements.connectionStatus.classList.remove(
        'status-connected', 
        'status-connecting', 
        'status-disconnected', 
        'status-error', 
        'status-timeout', 
        'status-failed', 
        'status-reconnecting'
    );
    
    // 添加当前状态类
    elements.connectionStatus.classList.add(`status-${status}`);
    
    // 更新状态文本
    let statusText = '';
    switch (status) {
        case 'connected':
            statusText = '已连接';
            break;
        case 'connecting':
            statusText = '连接中...';
            break;
        case 'disconnected':
            statusText = '已断开';
            break;
        case 'error':
            statusText = '连接错误';
            break;
        case 'timeout':
            statusText = '连接超时';
            break;
        case 'failed':
            statusText = '连接失败';
            break;
        case 'reconnecting':
            statusText = '重连中...';
            break;
        default:
            statusText = status;
    }
    
    elements.connectionStatus.textContent = statusText;
}

// 初始化事件监听器
function initEventListeners() {
    // 发送按钮点击事件
    elements.sendButton.addEventListener('click', sendMessage);
    
    // 输入框回车事件
    elements.userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
    
    // 模式切换事件
    elements.modeSwitch.addEventListener('click', toggleMode);
    
    // 事件详情按钮点击事件
    if (elements.eventDetailsBtn) {
        elements.eventDetailsBtn.addEventListener('click', showEventDetailsModal);
    }

    if (elements.eventTreeBtn) {
        elements.eventTreeBtn.addEventListener('click', showEventTreeModal);
    }
    
    // 关闭模态框按钮点击事件
    document.querySelectorAll('.cyber-modal-close').forEach(btn => {
        btn.addEventListener('click', closeAllModals);
    });
    
    // 角色项点击事件
    elements.roleItems.forEach(item => {
        item.addEventListener('click', (e) => {
            const role = e.currentTarget.getAttribute('data-role');
            showRoleHistoryModal(role);
        });
    });
    
    // 设置按钮点击事件
    elements.settingsBtn.addEventListener('click', () => {
        showToast('设置功能即将推出', 'info');
    });
    
    // 退出按钮点击事件
    elements.logoutBtn.addEventListener('click', () => {
        // 设置手动断开标志
        isManuallyDisconnected = true;
        
        // 断开WebSocket连接
        if (socket.connected) {
            console.log('%c[退出] 断开WebSocket连接', 'background: #E91E63; color: white; padding: 2px 5px; border-radius: 3px;');
            socket.disconnect();
        }
        
        // 停止自动刷新
        stopAutoRefresh();
        
        // 通知用户
        showToast('正在退出作战室...', 'info');
        
        // 调用后端登出接口
        fetch('/api/auth/logout', {
            method: 'POST',
            headers: getAuthHeaders(),
            credentials: 'include'
        })
        .then(response => {
            // 无论成功失败都清理本地状态
            localStorage.removeItem('access_token');
            localStorage.removeItem('user_info');
            document.cookie = 'access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
            
            console.log('%c[退出] 登出接口调用完成，即将跳转到首页', 'background: #E91E63; color: white; padding: 2px 5px; border-radius: 3px;');
            window.location.href = '/';
        })
        .catch(error => {
            console.error('登出接口调用失败:', error);
            // 即使API调用失败，也清理本地状态并跳转
            localStorage.removeItem('access_token');
            localStorage.removeItem('user_info');
            document.cookie = 'access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
            window.location.href = '/';
        });
    });
    
    // 点击模态框背景关闭模态框
    document.querySelectorAll('.cyber-modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeAllModals();
            }
        });
    });
    
    // 添加连接状态点击事件（用于测试WebSocket）
    if (elements.connectionStatus) {
        elements.connectionStatus.addEventListener('click', () => {
            // 只有在已连接状态下才能测试
            if (socket.connected) {
                testWebSocketConnection();
            } else {
                showToast('WebSocket未连接，请等待连接成功后再测试', 'warning');
            }
        });
    }
    
    // 执行任务指示器点击事件
    elements.executionIndicator.addEventListener('click', toggleExecutionPanel);
    
    // 执行任务面板关闭按钮点击事件
    elements.executionPanel.querySelector('.execution-panel-close').addEventListener('click', toggleExecutionPanel);
    
    // 提交执行结果按钮点击事件
    elements.submitExecution.addEventListener('click', submitExecutionResult);
    
    // 稍后处理按钮点击事件
    elements.laterExecution.addEventListener('click', closeAllModals);
}

// 加入作战室
function joinWarroom() {
    if (socket.connected) {
        console.log(`%c[WebSocket] 尝试加入作战室: ${eventId}`, 'background: #9C27B0; color: white; padding: 2px 5px; border-radius: 3px;');
        socket.emit('join', { event_id: eventId });
        console.log(`%c[WebSocket] 已发送加入作战室请求: ${eventId}`, 'color: #9C27B0;');
    } else {
        console.error('%c[WebSocket] 未连接，无法加入作战室', 'color: #F44336;');
        showToast('WebSocket未连接，无法加入作战室', 'error');
    }
}

// 添加认证头的辅助函数
function getAuthHeaders() {
    const token = localStorage.getItem('access_token') || getCookie('access_token');
    return {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : ''
    };
}

// 获取cookie的辅助函数
function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
}

// 获取事件详情
async function fetchEventDetails() {
    try {
        updateLoadingState('event-details', true);
        
        const response = await fetch(`/api/event/${eventId}`, {
            headers: getAuthHeaders()
        });
        
        if (response.status === 401) {
            // 认证失败，跳转到登录页
            localStorage.removeItem('access_token');
            localStorage.removeItem('user_info');
            window.location.href = '/login';
            return;
        }
        
        const data = await response.json();
        
        if (data.status === 'success') {
            // 保存事件数据到全局变量
            eventData = data.data;
            displayEventDetails(data.data);
        } else {
            console.error('获取事件详情失败:', data.message);
        }
    } catch (error) {
        console.error('获取事件详情错误:', error);
    } finally {
        updateLoadingState('event-details', false);
    }
}

// 显示事件详情
function displayEventDetails(event) {
    elements.eventName.textContent = event.event_name || '未命名事件';
    elements.eventIdDisplay.textContent = `ID: ${event.event_id}`;
    elements.eventRound.textContent = `轮次: ${event.current_round || 1}`;
    elements.eventSource.textContent = `来源: ${event.source || '未知'}`;
    elements.eventSeverity.textContent = `严重程度: ${getSeverityText(event.severity)}`;
    elements.eventCreated.textContent = `创建时间: ${formatDateTime(event.created_at)}`;
    
    // 更新事件状态
    const statusElement = elements.eventStatus;
    const statusText = statusElement.querySelector('.status-text');
    
    statusElement.className = `event-status ${event.event_status}`;
    statusText.textContent = getStatusText(event.event_status);
    
    // 更新当前轮次
    elements.currentRound.textContent = event.current_round || 1;
}

// 获取事件消息列表
async function fetchEventMessages() {
    try {
        updateLoadingState('messages', true);
        
        const lastId = messagesData.length > 0 ? Math.max(...messagesData.map(m => m.id)) : 0;
        
        const response = await fetch(`/api/event/${eventId}/messages?last_message_db_id=${lastId}`, {
            headers: getAuthHeaders(),
            credentials: 'include'
        });
        
        if (response.status === 401) {
            return;
        }
        
        const data = await response.json();
        
        if (data.status === 'success') {
            let newMessagesAdded = false;
            if (data.data.length > 0) {
                for (const message of data.data) {
                    // 直接调用新的 addMessage 函数，它会处理去重和状态更新
                    if (addMessage(message)) {
                        newMessagesAdded = true;
                    }
                }
            }
            if (newMessagesAdded) {
                scrollToBottom();
            }
        }
    } catch (error) {
        console.error('获取消息错误:', error);
    } finally {
        updateLoadingState('messages', false);
    }
}

// 获取事件统计信息
async function fetchEventStats() {
    try {
        const response = await fetch(`/api/event/${eventId}/stats`, {
            headers: getAuthHeaders(),
            credentials: 'include'
        });
        
        if (response.status === 401) return;
        
        const data = await response.json();
        
        if (data.status === 'success') {
            updateEventStats(data.data);
        }
    } catch (error) {
        console.error('获取统计信息错误:', error);
    }
}

// 更新事件统计
function updateEventStats(stats) {
    taskCount = stats.task_count || 0;
    actionCount = stats.action_count || 0;
    commandCount = stats.command_count || 0;
    
    elements.taskCount.textContent = taskCount;
    elements.actionCount.textContent = actionCount;
    elements.commandCount.textContent = commandCount;
}

// 添加消息
function addMessage(message) {
    if (!message) {
        console.error('[addMessage] 消息对象无效:', message);
        return false;
    }

    const uniqueKey = message.temp_id ? `tmp_${message.temp_id}` : `id_${message.message_id || message.id}`;

    // 如果存在同temp_id的待确认消息，先移除
    if (message.temp_id) {
        const pendingEl = document.getElementById(`msg-${message.temp_id}`);
        if (pendingEl) {
            pendingEl.remove();
            displayedMessages.delete(`tmp_${message.temp_id}`);
            const idx = messagesData.findIndex(m => m.temp_id === message.temp_id);
            if (idx !== -1) messagesData.splice(idx, 1);
        }
    }

    if (displayedMessages.has(uniqueKey)) {
        console.log(`%c[addMessage] 忽略重复消息 ${uniqueKey}`, 'color: #FFA500;');
        return false;
    }

    console.log(`%c[addMessage] 添加新消息 ${uniqueKey}, 类型:${message.message_type || 'undefined'}, 来源:${message.message_from || 'undefined'}`, 'color: #4CAF50;');
    console.log('[addMessage] 消息详情:', message);

    displayedMessages.add(uniqueKey);
    messagesData.push(message);
    if (message.message_id) {
        messagesMap.set(message.message_id, message);
    }

    // 2. 更新 lastMessageId (虽然其直接用途可能需要重新评估，但为保持一致性暂时保留)
    // lastMessageId = Math.max(lastMessageId, message.id);
    // 注意: fetchEventMessages 中计算 lastId 的方式 (从 messagesData 获取最大值) 更可靠

    // 3. 创建DOM元素并追加 (以下为原 addMessage 中的渲染逻辑)
    const messageElement = document.createElement('div');
    
    // 设置消息样式
    let messageClass = 'message';
    if (message.message_from === '_captain') {
        messageClass += ' message-captain';
    } else if (message.message_from === '_manager') {
        messageClass += ' message-manager';
    } else if (message.message_from === '_operator') {
        messageClass += ' message-operator';
    } else if (message.message_from === '_executor') {
        messageClass += ' message-executor';
    } else if (message.message_from === '_expert') {
        messageClass += ' message-expert';
    } else if (message.message_from === 'system') {
        messageClass += ' message-system';
        if (message.message_type === 'llm_request') {
            messageClass += ' message-llm-request';
        }
    } else if (message.message_category === 'engineer_chat') {
        // 工程师对话消息
        if (message.sender_type === 'user') {
            messageClass += ' message-engineer-question';
        } else if (message.sender_type === 'ai') {
            messageClass += ' message-ai-assistant';
        }
    } else {
        messageClass += ' message-user';
    }
    if (message.pending) {
        messageClass += ' message-pending';
    }
    messageElement.className = messageClass;
    
    // 为思考指示器设置特殊的data属性
    if (message.message_type === 'thinking') {
        messageElement.setAttribute('data-message-type', 'thinking');
    }
    
    let messageContent = '';
    messageContent += `
        <div class="message-header">
            <span class="message-sender">${getSenderName(message)}</span>
            <div class="message-time-container">
                <span class="message-source-btn" onclick="showMessageSourceModal('${message.message_id}')">
                    <i class="fas fa-code" title="查看源码"></i>
                </span>
                <span class="message-time">${formatDateTime(message.created_at)}</span>
            </div>
        </div>
    `;
    messageContent += '<div class="message-content">';

    // 防御性检查消息类型
    if (!message.message_type) {
        console.warn('[addMessage] 消息缺少message_type字段，设置默认值');
        message.message_type = 'chat'; // 默认类型
    }
    
    // 处理消息内容逻辑
    if (message.message_type === 'llm_request' || (message.message_type && message.message_type.includes('_llm_request'))) {
        let requestContent = '';
        let data = extractMessageData(message.message_content);
        if (typeof data === 'object' && data !== null) {
            if (typeof data.text === 'string') {
                requestContent = data.text;
            } else {
                requestContent = JSON.stringify(data);
            }
        } else {
            requestContent = data;
        }
        messageContent += `<div class="llm-request-notification"><p>${requestContent}</p></div>`;
    } else if (message.message_type === 'llm_response' || (message.message_type && message.message_type.includes('_llm_response'))) {
        const content = message.message_content;
        let data = extractMessageData(content);
        if (message.message_from === '_captain') {
            if (data.response_type === 'TASK') {
                messageContent += `<p>${data.response_text || '分配任务'}</p>`;
                if (data.tasks && data.tasks.length > 0) {
                    messageContent += '<div class="task-list">';
                    data.tasks.forEach(task => {
                        const taskType = getTaskTypeText(task.task_type);
                        let assignee_name = '未指定';
                        let assignee_role = '';
                        if (task.task_assignee === '_manager') { assignee_name = '安全管理员'; assignee_role = 'manager'; }
                        else if (task.task_assignee === '_operator') { assignee_name = '安全工程师'; assignee_role = 'operator'; }
                        else if (task.task_assignee === '_executor') { assignee_name = '执行器'; assignee_role = 'executor'; }
                        else if (task.task_assignee === '_expert') { assignee_name = '安全专家'; assignee_role = 'expert'; }
                        else if (task.task_assignee === '_coordinator') { assignee_name = '协调员'; assignee_role = 'coordinator'; }
                        else if (task.task_assignee === '_analyst') { assignee_name = '分析员'; assignee_role = 'analyst'; }
                        else if (task.task_assignee === '_responder') { assignee_name = '处置员'; assignee_role = 'responder'; }
                        const shortTaskId = task.task_id ? String(task.task_id).substring(0, 8) : '';
                        messageContent += `<div class="task-item task-type-${task.task_type}"><span class="task-assignee role-${assignee_role}">@${assignee_name}</span> <span class="task-name">${task.task_name}</span> <span class="task-type">${taskType}</span> <span class="task-id">${shortTaskId}</span></div>`;
                    });
                    messageContent += '</div>';
                }
            } else {
                messageContent += `<p>${data.response_text || JSON.stringify(data)}</p>`;
            }
        } else if (message.message_from === '_manager') {
            if (data.response_type === 'ACTION') {
                messageContent += `<p>${data.response_text || '安排动作'}</p>`;
                if (data.actions && data.actions.length > 0) {
                    messageContent += '<div class="action-list">';
                    data.actions.forEach(action => {
                        const actionType = action.action_type || 'default';
                        let assignee_name = '未指定';
                        let assignee_role = '';
                        if (action.action_assignee === '_manager') { assignee_name = '安全管理员'; assignee_role = 'manager'; }
                        else if (action.action_assignee === '_operator') { assignee_name = '安全工程师'; assignee_role = 'operator'; }
                        else if (action.action_assignee === '_executor') { assignee_name = '执行器'; assignee_role = 'executor'; }
                        else if (action.action_assignee === '_expert') { assignee_name = '安全专家'; assignee_role = 'expert'; }
                        else if (action.action_assignee === '_analyst') { assignee_name = '分析员'; assignee_role = 'analyst'; }
                        else if (action.action_assignee === '_responder') { assignee_name = '处置员'; assignee_role = 'responder'; }
                        else if (action.action_assignee === '_coordinator') { assignee_name = '协调员'; assignee_role = 'coordinator'; }
                        const shortTaskId = action.task_id ? String(action.task_id).substring(0, 8) : '';
                        const shortActionId = action.action_id ? String(action.action_id).substring(0, 8) : '';
                        const idInfo = `${shortTaskId}->${shortActionId}`;
                        messageContent += `<div class="action-item action-type-${actionType}"><span class="action-assignee role-${assignee_role}">@${assignee_name}</span> <span class="action-name">${action.action_name}</span> <span class="action-id">${idInfo}</span></div>`;
                    });
                    messageContent += '</div>';
                }
            } else {
                messageContent += `<p>${data.response_text || JSON.stringify(data)}</p>`;
            }
        } else { // Other roles llm_response
            if (data.response_type === 'TASK') {
                messageContent += `<p>${data.response_text || '分配任务'}</p>`;
                if (data.tasks && data.tasks.length > 0) {
                    messageContent += '<pre>';
                    data.tasks.forEach(task => { messageContent += `- ${task.task_name} (${getTaskTypeText(task.task_type)})\n`; });
                    messageContent += '</pre>';
                }
            } else if (data.response_type === 'ACTION') {
                messageContent += `<p>${data.response_text || '安排动作'}</p>`;
                if (data.actions && data.actions.length > 0) {
                    messageContent += '<pre>';
                    data.actions.forEach(action => { messageContent += `- ${action.action_name} (任务: ${action.task_id})\n`; });
                    messageContent += '</pre>';
                }
            } else if (data.response_type === 'COMMAND') {
                messageContent += `<p>${data.response_text || '准备命令'}</p>`;
                if (data.commands && data.commands.length > 0) {
                    messageContent += '<div class="command-list">';
                    data.commands.forEach(command => {
                        const shortTaskId = command.task_id ? String(command.task_id).substring(0, 8) : '';
                        const shortActionId = command.action_id ? String(command.action_id).substring(0, 8) : '';
                        const shortCommandId = command.command_id ? String(command.command_id).substring(0, 8) : '';
                        const idInfo = `${shortTaskId}->${shortActionId}->${shortCommandId}`;
                        let assignee_name = '未指定';
                        let assignee_role = '';
                        if (command.command_assignee === '_manager') { assignee_name = '安全管理员'; assignee_role = 'manager'; }
                        else if (command.command_assignee === '_operator') { assignee_name = '安全工程师'; assignee_role = 'operator'; }
                        else if (command.command_assignee === '_executor') { assignee_name = '执行器'; assignee_role = 'executor'; }
                        else if (command.command_assignee === '_expert') { assignee_name = '安全专家'; assignee_role = 'expert'; }
                        else if (command.command_assignee === '_analyst') { assignee_name = '分析员'; assignee_role = 'analyst'; }
                        else if (command.command_assignee === '_responder') { assignee_name = '处置员'; assignee_role = 'responder'; }
                        else if (command.command_assignee === '_coordinator') { assignee_name = '协调员'; assignee_role = 'coordinator'; }
                        messageContent += `<div class="command-item command-type-${command.command_type || 'default'}"><span class="command-assignee role-${assignee_role}">@${assignee_name}</span> <span class="command-name">${command.command_name}</span> <span class="command-type">${command.command_type || ''}</span> <span class="command-id">${idInfo}</span></div>`;
                    });
                    messageContent += '</div>';
                }
            } else {
                messageContent += `<p>${data.response_text || JSON.stringify(data)}</p>`;
            }
        }
    } else if (message.message_type === 'command_result') {
        const content = message.message_content;
        let data = extractMessageData(content);
        if (message.message_from === '_executor') {
            messageContent += `<p>命令 "${data.command_name}" 执行${data.status === 'completed' ? '成功' : '失败'}</p>`;
            if (data.ai_summary) {
                messageContent += `<div class="ai-summary markdown-content">${marked.parse(data.ai_summary)}</div>`;
            }
            if (data.result) {
                const resultId = `result-${Date.now()}-${Math.floor(Math.random() * 1000)}`;
                messageContent += `<div class="collapsible-result"><div class="collapsible-header" onclick="toggleCollapsible('${resultId}')"><span class="collapse-icon">▶</span> 查看详细结果</div><div id="${resultId}" class="collapsible-content collapsed"><pre>${JSON.stringify(data.result, null, 2)}</pre></div></div>`;
            }
        } else {
            messageContent += `<p>命令 "${data.command_name}" 执行${data.status === 'completed' ? '成功' : '失败'}</p>`;
            if (data.result) {
                messageContent += `<pre>${JSON.stringify(data.result, null, 2)}</pre>`;
            }
        }
    } else if (message.message_type === 'execution_summary' || message.message_type === 'execution_summary_generated') {
        const content = message.message_content;
        let data = extractMessageData(content);
        if (message.message_from === '_expert' && data.ai_summary) {
            messageContent += `<p>执行结果摘要:</p><div class="ai-summary markdown-content">${marked.parse(data.ai_summary)}</div>`;
        } else {
            messageContent += `<p>执行结果摘要:</p><p>${data.ai_summary}</p>`;
        }
    } else if (message.message_type === 'event_summary' || message.message_type === 'event_summary_generated') {
        const content = message.message_content;
        let data = extractMessageData(content);
        if (message.message_from === '_expert') {
            messageContent += `<p>事件总结 (轮次 ${data.round_id}):</p><div class="event-summary markdown-content">${marked.parse(data.event_summary)}</div>`;
        } else {
            messageContent += `<p>事件总结 (轮次 ${data.round_id}):</p><p>${data.event_summary}</p>`;
        }
    } else if (message.message_type === 'system_notification') {
        const content = message.message_content;
        let data = extractMessageData(content);
        messageContent += `<div class="system-notification"><p>${data.response_text}</p></div>`;
    } else if (message.message_category === 'engineer_chat') {
        // 处理工程师对话消息
        const content = message.message_content;
        let data = extractMessageData(content);
        let chatContent = '';
        
        if (typeof data === 'object' && data !== null) {
            chatContent = data.content || data.text || JSON.stringify(data);
        } else {
            chatContent = data || '';
        }
        
        if (message.sender_type === 'user') {
            messageContent += `<div class="engineer-question"><p>${chatContent}</p></div>`;
        } else if (message.sender_type === 'ai') {
            // AI助手回复支持Markdown渲染
            messageContent += `<div class="ai-response markdown-content">${marked.parse(chatContent)}</div>`;
        }
    } else {
        // 普通消息，确保 message.message_content 不是对象。如果是对象，尝试提取 data.text 或 stringify
        let plainTextContent = message.message_content;
        if (typeof plainTextContent === 'object' && plainTextContent !== null) {
            if (plainTextContent.data && typeof plainTextContent.data.text === 'string') {
                plainTextContent = plainTextContent.data.text;
            } else if (typeof plainTextContent.text === 'string') {
                 plainTextContent = plainTextContent.text;
            } else {
                plainTextContent = JSON.stringify(plainTextContent);
            }
        }
        messageContent += `<p>${plainTextContent}</p>`;
    }
    // End of placeholder for detailed message content rendering logic

    messageContent += '</div>';
    messageElement.innerHTML = messageContent;
    messageElement.id = `msg-${message.temp_id || message.message_id || message.id}`;
    elements.chatMessages.appendChild(messageElement);

    return true; // 表示消息已成功添加并渲染
}

// 添加折叠/展开功能
function toggleCollapsible(id) {
    const content = document.getElementById(id);
    const header = content.previousElementSibling;
    const icon = header.querySelector('.collapse-icon');
    
    if (content.classList.contains('collapsed')) {
        content.classList.remove('collapsed');
        icon.textContent = '▼';
    } else {
        content.classList.add('collapsed');
        icon.textContent = '▶';
    }
}

// 发送消息
async function sendMessage() {
    // 使用统一的输入框，预留扩展空间
    const messageInput = elements.userInput;
    const text = messageInput.value.trim();

    if (!text) return;

    // 检查是否是AI助手对话模式（以@AI开头的消息）
    if (text.startsWith('@AI') || text.startsWith('@ai')) {
        await sendEngineerChatMessage(text.replace(/^@AI\s*|^@ai\s*/i, '').trim());
        return;
    }
    
    // 检查是否是普通@消息（未来可扩展给其他用户或Agent）
    if (text.startsWith('@') && !text.startsWith('@AI') && !text.startsWith('@ai')) {
        showToast('请使用 @AI 来与AI助手对话，或输入普通消息', 'info');
        return;
    }

    if (!socket.connected) {
        showToast('WebSocket未连接，无法发送消息', 'error');
        return;
    }

    // 生成临时ID用于本地展示和与服务器回应匹配
    const tempId = `tmp_${Date.now()}_${Math.floor(Math.random() * 1000)}`;

    // 构造待显示的本地消息对象
    const pendingMessage = {
        temp_id: tempId,
        message_id: tempId,
        event_id: eventId,
        message_from: 'user',
        message_type: 'user_message',
        message_content: { type: 'text', text: text },
        created_at: new Date().toISOString(),
        pending: true,
        user_nickname: (() => {
            try {
                const info = JSON.parse(localStorage.getItem('user_info') || '{}');
                return info.nickname || info.username || '用户';
            } catch (e) {
                return '用户';
            }
        })()
    };

    // 在界面上立即显示待确认的消息
    addMessage(pendingMessage);
    scrollToBottom();

    // 通过WebSocket发送到服务器
    socket.emit('message', {
        event_id: eventId,
        message: pendingMessage.message_content,
        sender: 'user',
        temp_id: tempId
    });

    // 清空输入框并重新聚焦
    messageInput.value = '';
    messageInput.focus();
}

// 工程师对话相关函数
async function sendEngineerChatMessage(message) {
    if (!message.trim()) return;

    // 显示发送中状态
    const sendButton = elements.sendButton;
    const originalText = sendButton.querySelector('.cyber-btn-text').textContent;
    
    // 立即清空输入框和恢复按钮（优化用户体验）
    elements.userInput.value = '';
    
    try {
        sendButton.querySelector('.cyber-btn-text').textContent = '发送中...';
        sendButton.disabled = true;

        const response = await fetch('/api/engineer-chat/send', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                event_id: eventId,
                message: message
            })
        });

        const data = await response.json();

        if (response.ok && data.status === 'success') {
            // 立即显示用户消息（不等待WebSocket广播）
            if (data.data && data.data.user_message) {
                addMessage(data.data.user_message);
                scrollToBottom();
            }
            
            // 立即恢复按钮状态 - 异步模式下不等待AI回复
            sendButton.querySelector('.cyber-btn-text').textContent = originalText;
            sendButton.disabled = false;
            elements.userInput.focus();
            
            // 显示AI正在思考的状态指示器
            if (data.data && data.data.ai_processing) {
                showAIThinkingIndicator();
            }
            
            // 如果概要有更新，提示用户
            if (data.data && data.data.summary_updated) {
                showToast('事件概要已更新', 'info');
            }
            
            console.log('%c[工程师对话] 用户消息已显示，AI正在后台处理', 'color: #4CAF50;');
            return; // 立即返回，不在finally块中重复处理
            
        } else if (data.status === 'warning') {
            // 达到轮次限制
            showToast(data.message, 'warning');
            
            // 可以在这里添加创建新会话的逻辑
            if (confirm('是否创建新的对话会话？')) {
                await createNewChatSession();
            }
            
        } else {
            showToast(data.message || '发送失败', 'error');
        }

    } catch (error) {
        console.error('发送工程师对话消息失败:', error);
        showToast('发送失败: ' + error.message, 'error');
    } finally {
        // 恢复按钮状态（仅在出错时执行）
        sendButton.querySelector('.cyber-btn-text').textContent = originalText;
        sendButton.disabled = false;
        elements.userInput.focus();
    }
}

// 创建新的工程师对话会话
async function createNewChatSession() {
    try {
        const response = await fetch('/api/engineer-chat/new-session', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                event_id: eventId
            })
        });

        const data = await response.json();

        if (response.ok && data.status === 'success') {
            showToast('新对话会话已创建', 'success');
            return data.data.new_session_id;
        } else {
            showToast(data.message || '创建新会话失败', 'error');
            return null;
        }

    } catch (error) {
        console.error('创建新会话失败:', error);
        showToast('创建新会话失败: ' + error.message, 'error');
        return null;
    }
}

// AI思考状态指示器相关函数
let aiThinkingIndicatorId = null;

function showAIThinkingIndicator() {
    // 如果已经有思考指示器，不重复添加
    if (aiThinkingIndicatorId) return;
    
    // 创建思考指示器消息
    const thinkingMessage = {
        id: `ai_thinking_${Date.now()}`,
        message_id: `ai_thinking_${Date.now()}`,
        event_id: eventId,
        message_from: 'ai_assistant',
        message_content: 'AI助手正在思考中...',
        message_type: 'thinking',
        message_category: 'engineer_chat',
        sender_type: 'ai',
        created_at: new Date().toISOString(),
        temp_indicator: true // 标记为临时指示器
    };
    
    // 添加到界面
    if (addMessage(thinkingMessage)) {
        aiThinkingIndicatorId = thinkingMessage.id;
        console.log('%c[AI思考指示器] 显示思考状态', 'color: #FF9800;');
        
        // 滚动到底部
        scrollToBottom();
    }
}

function hideAIThinkingIndicator() {
    if (aiThinkingIndicatorId) {
        // 移除思考指示器元素
        const indicatorElement = document.getElementById(`msg-${aiThinkingIndicatorId}`);
        if (indicatorElement) {
            indicatorElement.remove();
            console.log('%c[AI思考指示器] 隐藏思考状态', 'color: #FF9800;');
        }
        
        // 从数据结构中移除
        const uniqueKey = `id_${aiThinkingIndicatorId}`;
        displayedMessages.delete(uniqueKey);
        const idx = messagesData.findIndex(m => m.id === aiThinkingIndicatorId);
        if (idx !== -1) messagesData.splice(idx, 1);
        
        aiThinkingIndicatorId = null;
    }
}

// 获取当前驾驶模式
async function fetchDrivingMode() {
    try {
        const response = await fetch('/api/state/driving-mode', {
            headers: getAuthHeaders()
        });
        if (response.ok) {
            const data = await response.json();
            isAutoMode = (data.data.mode === 'auto');
            updateModeUI(false);
        }
    } catch (err) {
        console.error('获取驾驶模式失败:', err);
    }
}

function updateModeUI(showTip = true) {
    if (isAutoMode) {
        elements.modeSwitch.classList.remove('manual-mode');
        elements.modeSwitch.classList.add('auto-mode');
        elements.modeSwitch.querySelector('.switch-label').textContent = 'AI自动驾驶';
        if (showTip) showToast('已切换到AI自动驾驶模式', 'info');
    } else {
        elements.modeSwitch.classList.remove('auto-mode');
        elements.modeSwitch.classList.add('manual-mode');
        elements.modeSwitch.querySelector('.switch-label').textContent = '人工操控';
        if (showTip) showToast('已切换到人工操控模式', 'info');
    }
}

// 切换模式
function toggleMode() {
    isAutoMode = !isAutoMode;
    updateModeUI();

    const mode = isAutoMode ? 'auto' : 'manual';
    fetch('/api/state/driving-mode', {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify({ mode })
    }).catch(err => console.error('更新驾驶模式失败:', err));
}

// 显示事件详情模态框
function showEventDetailsModal() {
    console.log('%c[事件详情] 尝试显示事件详情模态框', 'background: #3F51B5; color: white; padding: 2px 5px; border-radius: 3px;');
    console.log('%c[事件详情] 当前事件数据:', 'color: #3F51B5;', eventData);
    
    if (!eventData) {
        console.error('%c[事件详情] 事件数据为空，尝试重新获取', 'color: #F44336;');
        showToast('事件数据加载中，请稍后再试', 'warning');
        
        // 重新获取事件数据
        fetchEventDetails().then(() => {
            if (eventData) {
                console.log('%c[事件详情] 重新获取事件数据成功，显示模态框', 'color: #4CAF50;');
                showEventDetailsModal();
            } else {
                console.error('%c[事件详情] 重新获取事件数据失败', 'color: #F44336;');
            }
        });
        return;
    }
    
    const messageDetailElement = document.getElementById('event-message-detail');
    const contextDetailElement = document.getElementById('event-context-detail');
    const summaryListElement = document.getElementById('event-summary-list');
    
    if (!messageDetailElement || !contextDetailElement || !summaryListElement) {
        console.error('%c[事件详情] 模态框元素不存在', 'color: #F44336;', {
            messageDetailElement,
            contextDetailElement,
            summaryListElement
        });
        showToast('模态框元素不存在，请联系管理员', 'error');
        return;
    }
    
    console.log('%c[事件详情] 填充事件详情数据', 'color: #3F51B5;');
    
    // 显示事件原始信息，支持Markdown渲染
    if (eventData.message) {
        messageDetailElement.innerHTML = marked.parse(eventData.message);
    } else {
        messageDetailElement.innerHTML = '<p>无原始信息</p>';
    }

    // 显示事件上下文，支持Markdown渲染
    if (eventData.context) {
        contextDetailElement.innerHTML = marked.parse(eventData.context);
    } else {
        contextDetailElement.innerHTML = '<p>无上下文信息</p>';
    }
    
    // 获取并显示事件总结
    fetchEventSummaries(summaryListElement);
    
    // 显示模态框
    console.log('%c[事件详情] 显示模态框', 'color: #4CAF50;');
    
    if (elements.eventDetailsModal) {
        elements.eventDetailsModal.style.display = 'flex';
    } else {
        console.error('%c[事件详情] eventDetailsModal元素不存在', 'color: #F44336;');
        const modal = document.getElementById('event-details-modal');
        if (modal) {
            console.log('%c[事件详情] 通过ID找到模态框元素，显示模态框', 'color: #4CAF50;');
            modal.style.display = 'flex';
        } else {
            console.error('%c[事件详情] 无法找到事件详情模态框元素', 'color: #F44336;');
            showToast('无法找到事件详情模态框，请联系管理员', 'error');
        }
    }
}

// 获取事件总结
async function fetchEventSummaries(container) {
    try {
        const response = await fetch(`${API_BASE_URL}/event/${eventId}/summaries`, {
            headers: getAuthHeaders(),
            credentials: 'include'
        });
        
        if (response.status === 401) {
            // 认证失败，显示提示并重定向
            showToast('登录已过期，请重新登录', 'error');
            setTimeout(() => {
                window.location.href = '/login';
            }, 1500);
            return;
        }
        
        const data = await response.json();
        
        if (data.status === 'success') {
            displayEventSummaries(data.data, container);
        } else {
            container.innerHTML = '<div class="text-center">获取事件总结失败</div>';
        }
    } catch (error) {
        console.error('获取事件总结出错:', error);
        container.innerHTML = '<div class="text-center">获取事件总结出错</div>';
    }
}

// 显示事件总结
function displayEventSummaries(summaries, container) {
    if (!summaries || summaries.length === 0) {
        container.innerHTML = '<div class="text-center">暂无事件总结</div>';
        return;
    }
    
    let html = '';
    
    // 按轮次倒序排列
    summaries.sort((a, b) => b.round_id - a.round_id);
    
    summaries.forEach(summary => {
        const content = summary.event_summary ? marked.parse(summary.event_summary) : '';
        html += `
            <div class="event-summary-item">
                <div class="event-summary-header">
                    <span class="event-summary-round">轮次 ${summary.round_id}</span>
                    <span class="event-summary-time">${formatDateTime(summary.created_at)}</span>
                </div>
                <div class="event-summary-content markdown-content">${content}</div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

// 显示角色历史模态框
function showRoleHistoryModal(role) {
    const titleElement = document.getElementById('role-history-title');
    const listElement = document.getElementById('role-history-list');
    
    titleElement.textContent = `${getRoleName(role)} 历史记录`;
    
    // 设置模态框的角色属性
    elements.roleHistoryModal.setAttribute('data-role', role);
    
    // 获取并显示角色历史
    fetchRoleHistory(role, listElement);
    
    // 显示模态框
    elements.roleHistoryModal.style.display = 'flex';
}

// 获取角色历史
async function fetchRoleHistory(role, container) {
    try {
        const response = await fetch(`${API_BASE_URL}/event/${eventId}/messages?role=${role}`, {
            headers: getAuthHeaders(),
            credentials: 'include'
        });
        
        if (response.status === 401) {
            // 认证失败，显示提示并重定向
            showToast('登录已过期，请重新登录', 'error');
            setTimeout(() => {
                window.location.href = '/login';
            }, 1500);
            return;
        }
        
        const data = await response.json();
        
        if (data.status === 'success') {
            displayRoleHistory(data.data, container);
        } else {
            container.innerHTML = '<div class="text-center">获取角色历史失败</div>';
        }
    } catch (error) {
        console.error('获取角色历史出错:', error);
        container.innerHTML = '<div class="text-center">获取角色历史出错</div>';
    }
}

// 显示角色历史
function displayRoleHistory(messages, container) {
    if (!messages || messages.length === 0) {
        container.innerHTML = '<div class="text-center">暂无历史记录</div>';
        return;
    }
    
    let html = '';
    
    // 按时间倒序排列
    messages.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    
    messages.forEach(message => {
        let content = '';
        
        if (message.message_type === 'llm_response') {
            const messageContent = message.message_content;
            let responseText = '';
            
            if (messageContent.type === 'llm_response') {
                // 新的标准化消息格式
                responseText = messageContent.data.response_text || JSON.stringify(messageContent.data, null, 2);
            } else {
                // 旧的消息格式
                responseText = messageContent.response_text || JSON.stringify(messageContent, null, 2);
            }
            
            // 使用markdown渲染响应文本
            content = `<div class="role-history-markdown">${marked.parse(responseText)}</div>`;
        } else if (message.message_type === 'command_result') {
            // 命令执行结果，格式化JSON
            const resultData = typeof message.message_content === 'object' 
                ? message.message_content 
                : { result: '无结果数据' };
            
            content = `
                <p>命令执行结果:</p>
                <pre><code>${JSON.stringify(resultData, null, 2)}</code></pre>
            `;
        } else if (message.message_type === 'execution_summary' || message.message_type === 'execution_summary_generated') {
            // 执行结果摘要，尝试提取AI摘要并用markdown渲染
            const summaryData = typeof message.message_content === 'object' 
                ? message.message_content 
                : { summary: '无摘要数据' };
            
            let aiSummary = '';
            
            if (summaryData.type === 'execution_summary' && summaryData.data && summaryData.data.ai_summary) {
                aiSummary = summaryData.data.ai_summary;
            } else if (summaryData.ai_summary) {
                aiSummary = summaryData.ai_summary;
            } else {
                aiSummary = JSON.stringify(summaryData, null, 2);
            }
            
            content = `
                <p>执行结果摘要:</p>
                <div class="role-history-markdown">${marked.parse(aiSummary)}</div>
            `;
        } else if (message.message_type === 'event_summary' || message.message_type === 'event_summary_generated') {
            // 事件总结，用markdown渲染
            const summaryData = typeof message.message_content === 'object' 
                ? message.message_content 
                : { summary: '无总结数据' };
            
            let eventSummary = '';
            
            if (summaryData.type === 'event_summary' && summaryData.data && summaryData.data.summary) {
                eventSummary = summaryData.data.summary;
            } else if (summaryData.summary) {
                eventSummary = summaryData.summary;
            } else {
                eventSummary = JSON.stringify(summaryData, null, 2);
            }
            
            content = `
                <p>事件总结:</p>
                <div class="role-history-markdown">${marked.parse(eventSummary)}</div>
            `;
        } else {
            // 其他类型的消息，尝试格式化JSON或直接显示
            if (typeof message.message_content === 'object') {
                content = `<pre><code>${JSON.stringify(message.message_content, null, 2)}</code></pre>`;
            } else {
                content = message.message_content;
            }
        }
        
        html += `
            <div class="role-history-item">
                <div class="role-history-header">
                    <span class="role-history-type">${getMessageTypeText(message.message_type)}</span>
                    <span class="role-history-time">${formatDateTime(message.created_at)}</span>
                </div>
                <div class="role-history-content">${content}</div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

// 显示事件关系树模态框
function showEventTreeModal() {
    fetchEventTree();
    elements.eventTreeModal.style.display = 'flex';
}

// 获取事件关系树数据
async function fetchEventTree() {
    try {
        const response = await fetch(`${API_BASE_URL}/event/${eventId}/hierarchy`, {
            headers: getAuthHeaders(),
            credentials: 'include'
        });

        if (response.status === 401) return;

        const data = await response.json();

        if (data.status === 'success') {
            displayEventTree(data.data);
        } else {
            elements.eventTreeContainer.innerHTML = '<div class="text-center">获取失败</div>';
        }
    } catch (error) {
        console.error('获取事件关系树出错:', error);
        elements.eventTreeContainer.innerHTML = '<div class="text-center">获取关系树失败</div>';
    }
}

function displayEventTree(rounds) {
    if (!rounds || rounds.length === 0) {
        elements.eventTreeContainer.innerHTML = '<div class="text-center">暂无数据</div>';
        return;
    }

    let html = '';
    rounds.forEach(round => {
        html += `<div class="event-tree-round">`;
        html += `<div class="event-tree-round-title"># round ${round.round_id}</div>`;
        html += buildTaskList(round.tasks);
        html += `</div>`;
    });

    elements.eventTreeContainer.innerHTML = html;
}

function buildTaskList(tasks) {
    let html = '<ul>';
    tasks.forEach(task => {
        html += `<li>${task.task_name || task.task_id}<span class="event-tree-status">[${getStatusText(task.task_status)}]</span>`;
        if (task.actions && task.actions.length > 0) {
            html += buildActionList(task.actions);
        }
        html += '</li>';
    });
    html += '</ul>';
    return html;
}

function buildActionList(actions) {
    let html = '<ul>';
    actions.forEach(action => {
        html += `<li>${action.action_name || action.action_id}<span class="event-tree-status">[${getStatusText(action.action_status)}]</span>`;
        if (action.commands && action.commands.length > 0) {
            html += buildCommandList(action.commands);
        }
        html += '</li>';
    });
    html += '</ul>';
    return html;
}

function buildCommandList(commands) {
    let html = '<ul>';
    commands.forEach(cmd => {
        html += `<li>${cmd.command_name || cmd.command_id}<span class="event-tree-status">[${getStatusText(cmd.command_status)}]</span>`;
        if (cmd.executions && cmd.executions.length > 0) {
            html += buildExecutionList(cmd.executions);
        }
        html += '</li>';
    });
    html += '</ul>';
    return html;
}

function buildExecutionList(executions) {
    let html = '<ul>';
    executions.forEach(exe => {
        html += `<li>${exe.execution_id}<span class="event-tree-status">[${getStatusText(exe.execution_status)}]</span></li>`;
    });
    html += '</ul>';
    return html;
}

// 关闭所有模态框
function closeAllModals() {
    document.querySelectorAll('.cyber-modal').forEach(modal => {
        modal.style.display = 'none';
        // 清除角色属性
        if (modal.hasAttribute('data-role')) {
            modal.removeAttribute('data-role');
        }
    });
    
    // 重置当前执行任务
    currentExecution = null;
}

// 显示消息源码模态框
function showMessageSourceModal(messageId) {
    // 从映射中获取消息
    const message = messagesMap.get(messageId);
    
    if (!message) {
        showToast('无法找到消息数据', 'error');
        return;
    }
    
    // 记录当前查看的消息ID
    currentSourceMessageId = messageId;

    // 格式化JSON
    const formattedJson = JSON.stringify(message, null, 2);

    // 使用markdown渲染
    elements.messageSourceContent.innerHTML = marked.parse('```json\n' + formattedJson + '\n```');
    
    // 显示模态框
    elements.messageSourceModal.style.display = 'flex';
}

// 复制消息源码到剪贴板
function copyMessageSource() {
    if (!currentSourceMessageId) return;
    const message = messagesMap.get(currentSourceMessageId);
    if (!message) {
        showToast('无法找到消息数据', 'error');
        return;
    }
    const text = JSON.stringify(message, null, 2);
    navigator.clipboard.writeText(text)
        .then(() => {
            showToast('已复制到剪贴板', 'success');
        })
        .catch(() => {
            showToast('复制失败', 'error');
        });
}
// 滚动到底部
function scrollToBottom() {
    // 使用requestAnimationFrame确保DOM更新后再滚动
    requestAnimationFrame(() => {
        elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
        
        // 再次确认滚动到底部（有时单次滚动可能不够）
        setTimeout(() => {
            elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
        }, 100);
    });
}

// 显示Toast通知
function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toast-container');
    const toast = document.createElement('div');
    
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    
    toastContainer.appendChild(toast);
    
    // 3秒后自动移除
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => {
            toast.remove();
        }, 300);
    }, 3000);
}

// 辅助函数
function formatDateTime(dateString) {
    if (!dateString) return '未知时间';
    
    const date = new Date(dateString);
    return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
    });
}

function getRoleName(role) {
    const roleMap = {
        '_captain': '安全指挥官',
        '_manager': '安全管理员',
        '_operator': '安全工程师',
        '_executor': '执行器',
        '_expert': '安全专家',
        'user': '用户',
        'system': '系统'
    };
    
    return roleMap[role] || role;
}

function getSenderName(message) {
    // 处理工程师对话消息
    if (message.message_category === 'engineer_chat') {
        if (message.sender_type === 'user') {
            if (message.user_nickname) {
                return message.user_nickname;
            }
            try {
                const info = JSON.parse(localStorage.getItem('user_info') || '{}');
                return info.nickname || info.username || '工程师';
            } catch (e) {
                return '工程师';
            }
        } else if (message.sender_type === 'ai') {
            return 'AI助手';
        }
    }
    
    if (message.message_from === 'user') {
        // 优先使用消息中的user_nickname字段
        if (message.user_nickname) {
            return message.user_nickname;
        }
        
        // 如果消息中有user_username，使用它
        if (message.user_username) {
            return message.user_username;
        }
        
        // 如果消息中没有用户信息，尝试从localStorage获取
        try {
            const info = JSON.parse(localStorage.getItem('user_info') || '{}');
            // 检查当前登录用户的ID是否与消息的user_id匹配
            if (message.user_id && info.user_id && message.user_id === info.user_id) {
                // 如果是当前用户的消息，使用localStorage中的信息
                return info.nickname || info.username || '用户';
            } else if (message.user_id && info.user_id && message.user_id !== info.user_id) {
                // 如果是其他用户的消息，但没有用户信息，显示为"其他用户"
                return '其他用户';
            } else {
                // 无法确定用户身份时的默认显示
                return info.nickname || info.username || '用户';
            }
        } catch (e) {
            return '用户';
        }
    }
    return getRoleName(message.message_from);
}

function getTaskTypeText(type) {
    const typeMap = {
        'analysis': '分析',
        'response': '响应',
        'coordination': '协调',
        'investigation': '调查',
        'remediation': '修复'
    };
    
    return typeMap[type] || type;
}

function getStatusText(status) {
    const statusMap = {
        'pending': '⏳ 待处理',
        'processing': '🔄 处理中',
        'completed': '✅ 已完成',
        'failed': '❌ 失败',
        'round_finished': '🎯 轮次完成',
        'summarized': '📄 已总结',
        'resolved': '✔️ 已解决'
    };

    return statusMap[status] || status;
}

function getSeverityText(severity) {
    const severityMap = {
        'high': '高',
        'medium': '中',
        'low': '低'
    };
    
    return severityMap[severity] || severity || '未知';
}

function extractMessageData(content) {
    if (!content) {
        return content;
    }
    if (typeof content === 'string') {
        try {
            const parsed = JSON.parse(content);
            if (parsed && typeof parsed === 'object') {
                return (parsed.data !== undefined) ? parsed.data : parsed;
            }
        } catch (e) {
            return content;
        }
    } else if (typeof content === 'object') {
        return (content.data !== undefined) ? content.data : content;
    }
    return content;
}

function getMessageTypeText(type) {
    const typeMap = {
        'llm_request': 'AI请求',
        'llm_response': 'AI响应',
        'command_result': '命令结果',
        'execution_summary': '执行摘要',
        'execution_summary_generated': '执行摘要',
        'event_summary': '事件总结',
        'event_summary_generated': '事件总结',
        'user_message': '用户消息',
        'system_notification': '系统通知'
    };

    if (type && type.includes('_llm_request')) return 'AI请求';
    if (type && type.includes('_llm_response')) return 'AI响应';
    return typeMap[type] || type;
}

// 更新加载状态
function updateLoadingState(section, isLoading) {
    // 根据不同区域更新加载状态
    switch (section) {
        case 'event-details':
            // 可以添加加载指示器
            break;
        case 'messages':
            // 可以添加消息加载指示器
            break;
        case 'stats':
            // 可以添加统计加载指示器
            break;
    }
}

// 测试WebSocket连接
function testWebSocketConnection() {
    if (!socket.connected) {
        showToast('WebSocket未连接，无法发送测试消息', 'error');
        return;
    }
    
    console.log('%c[WebSocket] 发送测试消息请求', 'background: #FF9800; color: white; padding: 2px 5px; border-radius: 3px;');
    
    // 发送测试消息请求
    socket.emit('test_connection', {
        event_id: eventId,
        timestamp: new Date().toISOString()
    });
    
    showToast('已发送WebSocket测试请求', 'info');
}

// 获取等待处理的执行任务
async function fetchWaitingExecutions() {
    let retryCount = 0;
    const maxRetries = 3;
    
    while (retryCount < maxRetries) {
        try {
            console.log('%c[HTTP] 请求等待处理的执行任务', 'background: #FF9800; color: white; padding: 2px 5px; border-radius: 3px;');
            
            const response = await fetch(`${API_BASE_URL}/event/${eventId}/executions?status=waiting`, {
                headers: getAuthHeaders(),
                credentials: 'include',
                signal: AbortSignal.timeout(5000) // 5秒超时
            });
            
            if (!response.ok) {
                if (response.status === 401) {
                    // 认证失败，清除token并跳转登录
                    localStorage.removeItem('access_token');
                    localStorage.removeItem('user_info');
                    document.cookie = 'access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
                    window.location.href = '/login';
                    return;
                }
                throw new Error(`HTTP错误: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.status === 'success') {
                console.log(`%c[HTTP] 收到${data.data.length}个等待处理的执行任务`, 'color: #FF9800;');
                
                // 更新等待执行任务列表
                waitingExecutions = data.data;
                
                // 更新UI
                updateExecutionIndicator();
                updateExecutionList();
                
                return; // 成功获取数据，退出循环
            } else {
                throw new Error(data.message || '获取等待处理的执行任务失败');
            }
        } catch (error) {
            retryCount++;
            console.error(`%c[HTTP] 获取等待处理的执行任务出错 (尝试 ${retryCount}/${maxRetries}):`, 'color: #F44336;', error);
            
            if (retryCount >= maxRetries) {
                showToast(`获取等待处理的执行任务失败: ${error.message || '未知错误'}`, 'error');
            } else {
                // 指数退避重试
                const delay = Math.min(1000 * Math.pow(2, retryCount - 1), 5000);
                await new Promise(resolve => setTimeout(resolve, delay));
            }
        }
    }
}

// 更新执行任务指示器
function updateExecutionIndicator() {
    const count = waitingExecutions.length;
    
    // 更新计数
    elements.executionCount.textContent = count;
    elements.executionCountDisplay.textContent = count;
    
    // 更新样式
    if (count > 0) {
        elements.executionIndicator.classList.add('has-waiting');
    } else {
        elements.executionIndicator.classList.remove('has-waiting');
    }
}

// 更新执行任务列表
function updateExecutionList() {
    // 清空列表
    elements.executionList.innerHTML = '';
    
    // 显示空状态或列表
    if (waitingExecutions.length === 0) {
        elements.executionEmpty.style.display = 'flex';
        elements.executionList.style.display = 'none';
    } else {
        elements.executionEmpty.style.display = 'none';
        elements.executionList.style.display = 'flex';
        
        // 按创建时间排序（最新的在前面）
        const sortedExecutions = [...waitingExecutions].sort((a, b) => 
            new Date(b.created_at) - new Date(a.created_at)
        );
        
        // 添加执行任务项
        sortedExecutions.forEach(execution => {
            const executionItem = createExecutionItem(execution);
            elements.executionList.appendChild(executionItem);
        });
    }
}

// 创建执行任务项
function createExecutionItem(execution) {
    const item = document.createElement('div');
    item.className = 'execution-item';
    item.setAttribute('data-id', execution.execution_id || execution.id);
    
    // 计算等待时间
    const waitingTime = getWaitingTimeText(execution.created_at);
    
    // 获取命令名称
    const commandName = execution.command_name || '未知命令';
    
    // 获取描述
    const description = execution.description || '无描述';
    
    // 创建HTML
    item.innerHTML = `
        <div class="execution-item-header">
            <span class="execution-item-id">${getShortId(execution.execution_id || execution.id)}</span>
            <span class="execution-item-time">${waitingTime}</span>
        </div>
        <div class="execution-item-command">${commandName}</div>
        <div class="execution-item-desc">${description}</div>
        <div class="execution-item-action">
            <button class="execution-item-btn">处理</button>
        </div>
    `;
    
    // 添加点击事件
    item.querySelector('.execution-item-btn').addEventListener('click', (e) => {
        e.stopPropagation();
        showExecutionModal(execution);
    });
    
    item.addEventListener('click', () => {
        showExecutionModal(execution);
    });
    
    return item;
}

// 获取短ID（前6位）
function getShortId(id) {
    if (!id) return '无ID';
    return String(id).substring(0, 8);
}

// 获取等待时间文本
function getWaitingTimeText(createdAt) {
    if (!createdAt) return '未知时间';
    
    const created = new Date(createdAt);
    const now = new Date();
    const diffMs = now - created;
    
    // 转换为分钟
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) {
        return '刚刚';
    } else if (diffMins < 60) {
        return `${diffMins}分钟前`;
    } else {
        const hours = Math.floor(diffMins / 60);
        if (hours < 24) {
            return `${hours}小时前`;
        } else {
            const days = Math.floor(hours / 24);
            return `${days}天前`;
        }
    }
}

// 切换执行任务面板
function toggleExecutionPanel() {
    elements.executionPanel.classList.toggle('active');
}

// 显示执行任务模态框
function showExecutionModal(execution) {
    // 保存当前执行任务
    currentExecution = execution;
    
    // 填充执行任务信息
    elements.executionId.textContent = execution.execution_id || execution.id;
    elements.executionCommand.textContent = execution.command_name || '未知命令';
    elements.executionTime.textContent = formatDateTime(execution.created_at);
    
    // 填充上下文信息
    let contextHtml = '';
    
    if (execution.command_id) {
        contextHtml += `<div class="context-item"><span class="label">命令ID:</span> ${execution.command_id}</div>`;
    }
    
    if (execution.command_name) {
        contextHtml += `<div class="context-item"><span class="label">命令名称:</span> ${execution.command_name}</div>`;
    }
    
    if (execution.command_type) {
        contextHtml += `<div class="context-item"><span class="label">命令类型:</span> ${execution.command_type}</div>`;
    }
    
    if (execution.action_id) {
        contextHtml += `<div class="context-item"><span class="label">动作ID:</span> ${execution.action_id}</div>`;
    }
    
    if (execution.task_id) {
        contextHtml += `<div class="context-item"><span class="label">任务ID:</span> ${execution.task_id}</div>`;
    }
    
    // 显示命令实体信息
    if (execution.command_entity) {
        let entityHtml = '';
        try {
            const entityData = typeof execution.command_entity === 'string' 
                ? JSON.parse(execution.command_entity) 
                : execution.command_entity;
                
            if (entityData) {
                entityHtml = `<pre>${JSON.stringify(entityData, null, 2)}</pre>`;
            }
        } catch (e) {
            entityHtml = String(execution.command_entity);
        }
        
        if (entityHtml) {
            contextHtml += `<div class="context-item"><span class="label">命令实体:</span> ${entityHtml}</div>`;
        }
    }
    
    // 显示命令参数信息
    if (execution.command_params) {
        let paramsHtml = '';
        try {
            const paramsData = typeof execution.command_params === 'string' 
                ? JSON.parse(execution.command_params) 
                : execution.command_params;
                
            if (paramsData) {
                paramsHtml = `<pre>${JSON.stringify(paramsData, null, 2)}</pre>`;
            }
        } catch (e) {
            paramsHtml = String(execution.command_params);
        }
        
        if (paramsHtml) {
            contextHtml += `<div class="context-item"><span class="label">命令参数:</span> ${paramsHtml}</div>`;
        }
    }
    
    // 兼容旧版参数字段
    if (execution.parameters && !execution.command_params) {
        contextHtml += `<div class="context-item"><span class="label">参数:</span> <pre>${JSON.stringify(execution.parameters, null, 2)}</pre></div>`;
    }
    
    if (execution.description) {
        contextHtml += `<div class="context-item"><span class="label">描述:</span> ${execution.description}</div>`;
    }
    
    elements.contextContent.innerHTML = contextHtml;
    
    // 清空结果输入
    elements.executionResult.value = '';
    
    // 重置状态选项
    document.querySelector('input[name="execution-status"][value="success"]').checked = true;
    
    // 显示模态框
    elements.executionModal.style.display = 'flex';
}

// 切换上下文内容显示/隐藏
function toggleExecutionContext() {
    elements.contextContent.classList.toggle('collapsed');
    
    if (elements.contextContent.classList.contains('collapsed')) {
        elements.contextToggle.className = 'fas fa-chevron-right';
    } else {
        elements.contextToggle.className = 'fas fa-chevron-down';
    }
}

// 提交执行结果
async function submitExecutionResult() {
    if (!currentExecution) {
        showToast('无法提交执行结果：未找到当前执行任务', 'error');
        return;
    }
    
    const result = elements.executionResult.value.trim();
    if (!result) {
        showToast('请输入执行结果', 'warning');
        return;
    }
    
    // 获取执行状态
    const status = document.querySelector('input[name="execution-status"]:checked').value;
    const isSuccess = status === 'success';
    
    // 禁用按钮，防止重复提交
    elements.submitExecution.disabled = true;
    elements.laterExecution.disabled = true;
    
    try {
        // 显示提交中状态
        const originalButtonText = elements.submitExecution.querySelector('.cyber-btn-text').textContent;
        elements.submitExecution.querySelector('.cyber-btn-text').textContent = '提交中...';
        
        // 提交执行结果
        const response = await fetch(`${API_BASE_URL}/event/${eventId}/execution/${currentExecution.execution_id || currentExecution.id}/complete`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...getAuthHeaders()
            },
            credentials: 'include',
            body: JSON.stringify({
                result: result,
                status: isSuccess ? 'completed' : 'failed'
            }),
            signal: AbortSignal.timeout(10000) // 10秒超时
        });
        
        // 检查响应状态
        if (!response.ok) {
            if (response.status === 401) {
                // 认证失败，清除token并跳转登录
                localStorage.removeItem('access_token');
                localStorage.removeItem('user_info');
                document.cookie = 'access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
                window.location.href = '/login';
                return;
            }
            const errorText = await response.text();
            throw new Error(`服务器响应错误 (${response.status}): ${errorText}`);
        }
        
        // 尝试解析JSON响应
        let data;
        try {
            data = await response.json();
        } catch (jsonError) {
            throw new Error(`解析响应失败: ${jsonError.message}`);
        }
        
        if (data.status === 'success') {
            // 从等待列表中移除
            const index = waitingExecutions.findIndex(e => (e.execution_id || e.id) === (currentExecution.execution_id || currentExecution.id));
            if (index !== -1) {
                waitingExecutions.splice(index, 1);
            }
            
            // 更新UI
            updateExecutionIndicator();
            updateExecutionList();
            
            // 关闭模态框
            closeAllModals();
            
            // 显示成功提示
            showToast('执行结果提交成功', 'success');
        } else {
            throw new Error(data.message || '提交执行结果失败');
        }
    } catch (error) {
        console.error('提交执行结果出错:', error);
        showToast(`提交执行结果失败: ${error.message || '未知错误'}`, 'error');
    } finally {
        // 恢复按钮状态
        elements.submitExecution.disabled = false;
        elements.laterExecution.disabled = false;
        elements.submitExecution.querySelector('.cyber-btn-text').textContent = '完成执行';
    }
}

// 显示执行任务通知
function showExecutionNotification(execution) {
    const commandName = execution.command_name || '未知命令';
    
    // 创建通知消息
    const message = {
        id: 'notification-' + Date.now(),
        message_from: 'system',
        message_type: 'system_notification',
        message_content: {
            type: 'system_notification',
            data: {
                response_text: `有新的执行任务需要处理: ${commandName}`
            }
        },
        created_at: new Date().toISOString()
    };
    
    // 添加到消息区域
    addMessage(message);
    scrollToBottom();
    
    // 显示Toast通知
    showToast(`新的执行任务: ${commandName}`, 'info');
}

// 将函数暴露到全局作用域
window.showMessageSourceModal = showMessageSourceModal;
window.copyMessageSource = copyMessageSource;
window.toggleExecutionContext = toggleExecutionContext;

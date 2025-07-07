// DeepSOC 首页脚本

// API基础URL
const API_BASE_URL = '/api';

// 在API请求头中添加认证信息的辅助函数
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

// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', () => {
    // 验证用户是否登录
    checkAuth();
    
    // 获取事件列表
    fetchEvents();
    
    // 刷新按钮点击事件
    document.getElementById('refresh-events').addEventListener('click', fetchEvents);
    
    // 表单提交事件
    document.getElementById('event-form').addEventListener('submit', (e) => {
        e.preventDefault();
        
        const token = localStorage.getItem('access_token') || getCookie('access_token');
        if (!token) {
            showToast('请先登录', 'error');
            setTimeout(() => {
                window.location.href = '/login';
            }, 1500);
            return;
        }
        
        const eventData = {
            event_name: document.getElementById('event-name').value,
            message: document.getElementById('event-message').value,
            context: document.getElementById('event-context').value,
            severity: document.getElementById('event-severity').value,
            source: document.getElementById('event-source').value
        };
        
        // 验证必填字段
        if (!eventData.message) {
            showToast('事件描述不能为空', 'error');
            return;
        }
        
        // 禁用提交按钮
        const submitButton = document.querySelector('#event-form button[type="submit"]');
        const originalButtonText = submitButton.textContent;
        submitButton.disabled = true;
        submitButton.textContent = '创建中...';
        
        // 发送创建事件请求
        fetch('/api/event/create', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(eventData),
            credentials: 'include'  // 包含凭证
        })
        .then(response => {
            if (response.status === 401) {
                // 未授权，跳转到登录页
                localStorage.removeItem('access_token');
                localStorage.removeItem('user_info');
                document.cookie = 'access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
                window.location.href = '/login';
                throw new Error('未登录或会话已过期');
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                showToast('事件创建成功', 'success');
                
                // 重置表单
                document.getElementById('event-form').reset();
                
                // 刷新事件列表
                fetchEvents();
                
                // 跳转到作战室页面
                setTimeout(() => {
                    window.location.href = `/warroom/${data.data.event_id}`;
                }, 1000);
            } else {
                showToast(data.message || '创建失败，请稍后重试', 'error');
                // 恢复提交按钮
                submitButton.disabled = false;
                submitButton.textContent = originalButtonText;
            }
        })
        .catch(error => {
            if (error.message !== '未登录或会话已过期') {
                console.error('创建事件错误:', error);
                showToast('网络错误，请稍后重试', 'error');
                // 恢复提交按钮
                submitButton.disabled = false;
                submitButton.textContent = originalButtonText;
            }
        });
    });
    
    // 登出按钮
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function() {
            logout();
        });
    }
    
    // 添加用户信息显示
    updateUserInfo();
});

// 获取事件列表
async function fetchEvents() {
    try {
        const eventsContainer = document.getElementById('events-container');
        
        if (!eventsContainer) return;
        
        // 显示加载中
        eventsContainer.innerHTML = `
            <div class="text-center py-5">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">加载中...</span>
                </div>
                <p class="mt-2">加载事件列表...</p>
            </div>
        `;
        
        const response = await fetch(`${API_BASE_URL}/event/list`, {
            headers: getAuthHeaders(),
            credentials: 'include'  // 包含凭证
        });
        
        if (response.status === 401) {
            // 未登录，显示提示信息
            eventsContainer.innerHTML = `
                <div class="text-center py-5">
                    <div class="alert alert-warning" role="alert">
                        请先<a href="/login" class="alert-link">登录</a>后查看事件列表
                    </div>
                </div>
            `;
            throw new Error('未登录或会话已过期');
        }
        
        const data = await response.json();
        
        if (data.status === 'success') {
            if (data.data.length === 0) {
                // 没有事件
                eventsContainer.innerHTML = `
                    <div class="text-center py-5">
                        <p class="text-muted">暂无安全事件</p>
                    </div>
                `;
                return;
            }
            
            // 渲染事件列表
            let html = '<div class="list-group">';
            
            data.data.forEach(event => {
                const createdAt = new Date(event.created_at).toLocaleString('zh-CN');
                const eventLink = `/warroom/${event.event_id}`;
                const statusBadge = getStatusBadge(event.event_status);
                const severityBadge = getSeverityBadge(event.severity);
                
                html += `
                    <a href="${eventLink}" class="list-group-item list-group-item-action">
                        <div class="d-flex w-100 justify-content-between">
                            <h5 class="mb-1">${event.event_name || '未命名事件'}</h5>
                            <small>${createdAt}</small>
                        </div>
                        <p class="mb-1">${event.message}</p>
                        <div class="d-flex justify-content-between">
                            <div>
                                <span class="badge rounded-pill ${severityBadge.class}">${severityBadge.text}</span>
                                <span class="badge rounded-pill ${statusBadge.class}">${statusBadge.text}</span>
                            </div>
                            <small>来源: ${event.source}</small>
                        </div>
                    </a>
                `;
            });
            
            html += '</div>';
            eventsContainer.innerHTML = html;
        } else {
            eventsContainer.innerHTML = `
                <div class="alert alert-danger" role="alert">
                    加载失败: ${data.message || '未知错误'}
                </div>
            `;
        }
    } catch (error) {
        console.error('获取事件列表错误:', error);
        if (error.message !== '未登录或会话已过期') {
            eventsContainer.innerHTML = `
                <div class="alert alert-danger" role="alert">
                    网络错误，请稍后重试
                </div>
            `;
        }
    }
}

// 检查用户是否已登录
function checkAuth() {
    const token = localStorage.getItem('access_token') || getCookie('access_token');
    
    // 根据登录状态更新UI
    updateAuthUI(!!token);
    
    if (token) {
        // 验证token有效性
        fetch('/api/auth/check-auth', {
            headers: {
                'Authorization': `Bearer ${token}`
            },
            credentials: 'include'  // 包含凭证
        })
        .then(response => response.json())
        .then(data => {
            if (!data.authenticated) {
                // token无效，清除本地存储，更新UI
                localStorage.removeItem('access_token');
                localStorage.removeItem('user_info');
                document.cookie = 'access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
                updateAuthUI(false);
            }
        })
        .catch(error => {
            console.error('验证认证状态错误:', error);
            localStorage.removeItem('access_token');
            localStorage.removeItem('user_info');
            document.cookie = 'access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
            updateAuthUI(false);
        });
    }
}

// 更新UI以反映认证状态
function updateAuthUI(isAuthenticated) {
    const cardList = document.querySelectorAll('.card');
    let createEventCard = null;
    cardList.forEach(card => {
        if (card.querySelector('#event-form')) {
            createEventCard = card;
        }
    });

    const loginPrompt = document.getElementById('login-prompt');
    if (createEventCard) {
        if (isAuthenticated) {
            createEventCard.classList.remove('d-none');
            if (loginPrompt) loginPrompt.classList.add('d-none');
        } else {
            createEventCard.classList.add('d-none');
            if (loginPrompt) loginPrompt.classList.remove('d-none');
        }
    }
    
    // 更新导航栏状态
    const loginNavItem = document.getElementById('login-nav-item');
    const userNavItem = document.getElementById('user-nav-item');
    const settingsNavItem = document.getElementById('settings-nav-item');
    const userMgmtNavItem = document.getElementById('user-management-nav-item');

    if (loginNavItem && userNavItem) {
        if (isAuthenticated) {
            loginNavItem.classList.add('d-none');
            userNavItem.classList.remove('d-none');
            if (settingsNavItem) settingsNavItem.classList.remove('d-none');
            if (userMgmtNavItem) {
                const info = JSON.parse(localStorage.getItem('user_info') || '{}');
                if (info.role === 'admin') userMgmtNavItem.classList.remove('d-none');
                else userMgmtNavItem.classList.add('d-none');
            }
        } else {
            loginNavItem.classList.remove('d-none');
            userNavItem.classList.add('d-none');
            if (settingsNavItem) settingsNavItem.classList.add('d-none');
            if (userMgmtNavItem) userMgmtNavItem.classList.add('d-none');
        }
    }
}

// 更新用户信息显示
function updateUserInfo() {
    const userInfoElement = document.getElementById('user-info');
    if (userInfoElement) {
        const userInfo = JSON.parse(localStorage.getItem('user_info') || '{}');
        if (userInfo.nickname || userInfo.username) {
            userInfoElement.textContent = userInfo.nickname || userInfo.username;
        }
    }
}

// 获取状态对应的徽章样式
function getStatusBadge(status) {
    const statusMap = {
        'pending': { class: 'bg-warning text-dark', text: '待处理' },
        'processing': { class: 'bg-info text-dark', text: '处理中' },
        'completed': { class: 'bg-success', text: '已完成' },
        'closed': { class: 'bg-secondary', text: '已关闭' },
        'error': { class: 'bg-danger', text: '错误' }
    };
    
    return statusMap[status] || { class: 'bg-secondary', text: status };
}

// 获取严重程度对应的徽章样式
function getSeverityBadge(severity) {
    const severityMap = {
        'low': { class: 'bg-success', text: '低' },
        'medium': { class: 'bg-warning text-dark', text: '中' },
        'high': { class: 'bg-danger', text: '高' }
    };
    
    return severityMap[severity] || { class: 'bg-secondary', text: severity };
}

// 显示提示信息
function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type === 'success' ? 'success' : type === 'error' ? 'danger' : 'primary'}`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    
    const bsToast = new bootstrap.Toast(toast, {
        autohide: true,
        delay: 3000
    });
    
    bsToast.show();
    
    // 自动清理DOM
    toast.addEventListener('hidden.bs.toast', function() {
        toast.remove();
    });
}

// 退出登录
function logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user_info');
    document.cookie = 'access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
    showToast('已成功退出登录', 'info');
    setTimeout(() => {
        window.location.href = '/login';
    }, 1500);
} 
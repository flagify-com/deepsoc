// 提示词管理页面脚本
const API_BASE_URL = '/api';

function getAuthHeaders() {
    const token = localStorage.getItem('access_token') || getCookie('access_token');
    return {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : ''
    };
}

function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
}

function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type === 'success' ? 'success' : type === 'error' ? 'danger' : 'primary'}`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>`;
    toastContainer.appendChild(toast);
    const bsToast = new bootstrap.Toast(toast, { autohide: true, delay: 3000 });
    bsToast.show();
    toast.addEventListener('hidden.bs.toast', () => toast.remove());
}

function updateAuthUI(isAuthenticated) {
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

function updateUserInfo() {
    const userInfoElement = document.getElementById('user-info');
    if (userInfoElement) {
        const userInfo = JSON.parse(localStorage.getItem('user_info') || '{}');
        if (userInfo.nickname || userInfo.username) {
            userInfoElement.textContent = userInfo.nickname || userInfo.username;
        }
    }
}

function checkAuth() {
    const token = localStorage.getItem('access_token') || getCookie('access_token');
    updateAuthUI(!!token);
    if (token) {
        fetch('/api/auth/check-auth', {
            headers: { 'Authorization': `Bearer ${token}` },
            credentials: 'include'
        })
        .then(r => r.json())
        .then(data => {
            if (!data.authenticated) {
                localStorage.removeItem('access_token');
                localStorage.removeItem('user_info');
                document.cookie = 'access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
                updateAuthUI(false);
            }
        })
        .catch(() => {
            localStorage.removeItem('access_token');
            localStorage.removeItem('user_info');
            document.cookie = 'access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
            updateAuthUI(false);
        });
    }
}

function loadPrompts() {
    fetch(`${API_BASE_URL}/prompt/list`, { headers: getAuthHeaders(), credentials: 'include' })
        .then(r => r.json())
        .then(data => {
            if (data.status === 'success') {
                const prompts = data.data;
                for (const role in prompts) {
                    const textarea = document.getElementById(`prompt-${role}`);
                    if (textarea) textarea.value = prompts[role];
                }
            } else {
                showToast(data.message || '加载失败', 'error');
            }
        })
        .catch(() => showToast('加载失败', 'error'));

}

function savePrompt(role) {
    const textarea = document.getElementById(`prompt-${role}`);
    if (!textarea) return;
    fetch(`${API_BASE_URL}/prompt/${role}`, {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify({ prompt: textarea.value }),
        credentials: 'include'
    })
        .then(r => r.json())
        .then(data => {
            if (data.status === 'success') {
                showToast('保存成功', 'success');
            } else {
                showToast(data.message || '保存失败', 'error');
            }
        })
        .catch(() => showToast('保存失败', 'error'));
}


document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    updateUserInfo();
    loadPrompts();
    document.querySelectorAll('.save-prompt-btn').forEach(btn => {
        btn.addEventListener('click', () => savePrompt(btn.dataset.role));
    });
    document.querySelectorAll('#prompt-nav a').forEach(a => {
        a.addEventListener('click', e => {
            e.preventDefault();
            const target = a.dataset.target;
            document.querySelectorAll('#prompt-nav a').forEach(link => link.classList.remove('active'));
            a.classList.add('active');
            document.querySelectorAll('.prompt-section').forEach(section => {
                if (section.dataset.role === target) section.classList.remove('d-none');
                else section.classList.add('d-none');
            });
        });
    });
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) logoutBtn.addEventListener('click', logout);
});

function logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user_info');
    document.cookie = 'access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
    showToast('已成功退出登录', 'info');
    setTimeout(() => { window.location.href = '/login'; }, 1500);
}

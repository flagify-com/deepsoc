// 用户管理页面脚本
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
    toast.innerHTML = `<div class="d-flex"><div class="toast-body">${message}</div><button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button></div>`;
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
            const info = JSON.parse(localStorage.getItem('user_info') || '{}');
            if (userMgmtNavItem) {
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

function loadUsers() {
    fetch(`${API_BASE_URL}/user/list`, { headers: getAuthHeaders(), credentials: 'include' })
        .then(r => r.json())
        .then(data => {
            if (data.status === 'success') {
                const tbody = document.querySelector('#user-table tbody');
                tbody.innerHTML = '';
                data.data.forEach(u => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `<td>${u.id}</td><td>${u.username}</td><td>${u.nickname || ''}</td><td>${u.email}</td><td>${u.phone || ''}</td><td>${u.role}</td><td>${u.is_active ? '启用' : '禁用'}</td><td><button class="btn btn-sm btn-secondary me-1" data-action="edit" data-id="${u.id}">编辑</button><button class="btn btn-sm btn-warning me-1" data-action="password" data-id="${u.id}">密码</button><button class="btn btn-sm btn-danger" data-action="delete" data-id="${u.id}">删除</button></td>`;
                    tbody.appendChild(tr);
                });
            } else {
                showToast(data.message || '加载失败', 'error');
            }
        })
        .catch(() => showToast('加载失败', 'error'));
}

function openUserModal(user) {
    const modal = new bootstrap.Modal(document.getElementById('user-modal'));
    document.getElementById('user-id').value = user ? user.id : '';
    document.getElementById('user-username').value = user ? user.username : '';
    document.getElementById('user-nickname').value = user ? (user.nickname || '') : '';
    document.getElementById('user-email').value = user ? user.email : '';
    document.getElementById('user-phone').value = user ? (user.phone || '') : '';
    document.getElementById('user-role').value = user ? user.role : 'user';
    if (user) document.getElementById('user-username').setAttribute('disabled', 'disabled');
    else document.getElementById('user-username').removeAttribute('disabled');
    modal.show();
}

function saveUser() {
    const id = document.getElementById('user-id').value;
    const payload = {
        username: document.getElementById('user-username').value.trim(),
        nickname: document.getElementById('user-nickname').value.trim(),
        email: document.getElementById('user-email').value.trim(),
        phone: document.getElementById('user-phone').value.trim(),
        role: document.getElementById('user-role').value
    };
    const password = document.getElementById('user-password').value;
    if (!id && !password) {
        showToast('密码不能为空', 'error');
        return;
    }
    if (password) payload.password = password;
    const method = id ? 'PUT' : 'POST';
    const url = id ? `${API_BASE_URL}/user/${id}` : `${API_BASE_URL}/user`;
    fetch(url, {
        method,
        headers: getAuthHeaders(),
        body: JSON.stringify(payload),
        credentials: 'include'
    })
        .then(r => r.json())
        .then(data => {
            if (data.status === 'success') {
                showToast('保存成功', 'success');
                bootstrap.Modal.getInstance(document.getElementById('user-modal')).hide();
                loadUsers();
            } else {
                showToast(data.message || '保存失败', 'error');
            }
        })
        .catch(() => showToast('保存失败', 'error'));
}

function updatePassword(userId) {
    const pwd = prompt('请输入新密码');
    if (!pwd) return;
    fetch(`${API_BASE_URL}/user/${userId}/password`, {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify({ password: pwd }),
        credentials: 'include'
    })
        .then(r => r.json())
        .then(data => {
            if (data.status === 'success') showToast('密码更新成功', 'success');
            else showToast(data.message || '更新失败', 'error');
        })
        .catch(() => showToast('更新失败', 'error'));
}

function deleteUser(userId) {
    if (!confirm('确定删除该用户吗?')) return;
    fetch(`${API_BASE_URL}/user/${userId}`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
        credentials: 'include'
    })
        .then(r => r.json())
        .then(data => {
            if (data.status === 'success') {
                showToast('已删除', 'success');
                loadUsers();
            } else {
                showToast(data.message || '删除失败', 'error');
            }
        })
        .catch(() => showToast('删除失败', 'error'));
}

function bindTableActions() {
    const tbody = document.querySelector('#user-table tbody');
    tbody.addEventListener('click', e => {
        const btn = e.target.closest('button');
        if (!btn) return;
        const id = btn.getAttribute('data-id');
        const action = btn.getAttribute('data-action');
        if (action === 'edit') {
            fetch(`${API_BASE_URL}/user/${id}`, { headers: getAuthHeaders(), credentials: 'include' })
                .then(r => r.json())
                .then(data => { if (data.status === 'success') openUserModal(data.data); });
        } else if (action === 'password') {
            updatePassword(id);
        } else if (action === 'delete') {
            deleteUser(id);
        }
    });
}

document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    updateUserInfo();
    loadUsers();
    bindTableActions();
    document.getElementById('create-user-btn').addEventListener('click', () => openUserModal(null));
    document.getElementById('save-user-btn').addEventListener('click', saveUser);
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

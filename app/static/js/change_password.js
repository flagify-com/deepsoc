// 修改密码页面脚本

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

document.addEventListener('DOMContentLoaded', () => {
    updateUserInfo();

    const form = document.getElementById('change-password-form');
    form.addEventListener('submit', e => {
        e.preventDefault();

        const oldPassword = document.getElementById('old-password').value;
        const newPassword = document.getElementById('new-password').value;

        fetch(`${API_BASE_URL}/auth/change-password`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
            credentials: 'include'
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showToast('密码修改成功，请重新登录', 'success');
                setTimeout(() => { logout(); }, 1500);
            } else {
                showToast(data.message || '修改失败', 'error');
            }
        })
        .catch(err => {
            console.error('修改密码错误:', err);
            showToast('网络错误，请稍后重试', 'error');
        });
    });

    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) logoutBtn.addEventListener('click', logout);
});

function updateUserInfo() {
    const userInfoElement = document.getElementById('user-info');
    if (userInfoElement) {
        const userInfo = JSON.parse(localStorage.getItem('user_info') || '{}');
        if (userInfo.nickname || userInfo.username) {
            userInfoElement.textContent = userInfo.nickname || userInfo.username;
        }
    }
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
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>`;

    toastContainer.appendChild(toast);

    const bsToast = new bootstrap.Toast(toast, { autohide: true, delay: 3000 });
    bsToast.show();

    toast.addEventListener('hidden.bs.toast', () => { toast.remove(); });
}

function logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user_info');
    document.cookie = 'access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
    showToast('已成功退出登录', 'info');
    setTimeout(() => { window.location.href = '/login'; }, 1500);
}

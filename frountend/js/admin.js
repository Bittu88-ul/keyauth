// ==================== ADMIN PANEL ====================
document.addEventListener('DOMContentLoaded', function() {
    redirectIfNotAuth();
    
    if (!isAdmin()) {
        window.location.href = '/dashboard.html';
        return;
    }
    
    loadAdminPanel();
});

async function loadAdminPanel() {
    try {
        // Load stats
        const stats = await apiRequest('/admin/stats');
        renderStats(stats);
        
        // Load users
        const users = await apiRequest('/admin/users');
        renderUsers(users);
        
        // Load apps
        const apps = await apiRequest('/admin/applications');
        renderApps(apps);
        
        // Load licenses
        const licenses = await apiRequest('/admin/licenses');
        renderLicenses(licenses);
        
    } catch (error) {
        showToast('Failed to load admin panel', 'error');
    }
}

function renderStats(stats) {
    document.getElementById('statUsers').textContent = stats.total_users || 0;
    document.getElementById('statApps').textContent = stats.total_applications || 0;
    document.getElementById('statLicenses').textContent = stats.total_licenses || 0;
    document.getElementById('statActivations').textContent = stats.total_activations || 0;
}

function renderUsers(data) {
    const tbody = document.getElementById('usersTableBody');
    tbody.innerHTML = data.users.map(user => `
        <tr>
            <td>${user.id}</td>
            <td><strong>${user.username}</strong></td>
            <td>${user.email}</td>
            <td>
                <span class="badge ${user.is_admin ? 'admin' : 'user'}">
                    ${user.is_admin ? 'Admin' : 'User'}
                </span>
                ${user.is_banned ? '<span class="badge banned">Banned</span>' : ''}
            </td>
            <td>${new Date(user.created_at).toLocaleDateString()}</td>
            <td>
                <button class="btn btn-warning btn-sm" onclick="toggleAdmin(${user.id}, ${!user.is_admin})">
                    ${user.is_admin ? 'Remove Admin' : 'Make Admin'}
                </button>
                <button class="btn btn-danger btn-sm" onclick="banUser(${user.id}, ${!user.is_banned})">
                    ${user.is_banned ? 'Unban' : 'Ban'}
                </button>
            </td>
        </tr>
    `).join('');
}

function renderApps(data) {
    const tbody = document.getElementById('appsTableBody');
    tbody.innerHTML = data.applications.map(app => `
        <tr>
            <td><strong>${app.name}</strong></td>
            <td><code>${app.owner_id}</code></td>
            <td>${app.user ? app.user.username : 'Unknown'}</td>
            <td>${app.license_count || 0}</td>
            <td>
                <span class="badge ${app.is_active ? 'active' : 'inactive'}">
                    ${app.is_active ? 'Active' : 'Inactive'}
                </span>
            </td>
            <td>${new Date(app.created_at).toLocaleDateString()}</td>
            <td>
                <button class="btn btn-danger btn-sm" onclick="adminDeleteApp(${app.id})">Delete</button>
            </td>
        </tr>
    `).join('');
}

function renderLicenses(data) {
    const tbody = document.getElementById('licensesTableBody');
    tbody.innerHTML = data.licenses.map(lic => `
        <tr>
            <td><code>${lic.license_key}</code></td>
            <td>${lic.app ? lic.app.app_name : 'Unknown'}</td>
            <td>
                <span class="badge ${lic.is_active && !isExpired(lic) ? 'active' : lic.is_active ? 'expired' : 'inactive'}">
                    ${lic.is_active ? (isExpired(lic) ? 'Expired' : 'Active') : 'Inactive'}
                </span>
            </td>
            <td>${lic.hwid ? '🔒 Locked' : 'Unlocked'}</td>
            <td>${lic.is_permanent ? 'Permanent' : new Date(lic.expires_at).toLocaleDateString()}</td>
            <td>${lic.current_activations || 0}/${lic.max_activations}</td>
            <td>
                <button class="btn btn-danger btn-sm" onclick="adminDeleteLicense('${lic.license_key}')">Delete</button>
            </td>
        </tr>
    `).join('');
}

function isExpired(license) {
    if (license.is_permanent) return false;
    if (!license.expires_at) return false;
    return new Date(license.expires_at) < new Date();
}

// ==================== ADMIN ACTIONS ====================

async function toggleAdmin(userId, makeAdmin) {
    try {
        await apiRequest('/admin/users/' + userId, {
            method: 'PUT',
            body: JSON.stringify({ is_admin: makeAdmin })
        });
        
        showToast('User updated', 'success');
        loadAdminPanel();
        
    } catch (error) {
        showToast(error.message, 'error');
    }
}

async function banUser(userId, ban) {
    try {
        await apiRequest('/admin/users/' + userId, {
            method: 'PUT',
            body: JSON.stringify({ is_banned: ban })
        });
        
        showToast(ban ? 'User banned' : 'User unbanned', 'success');
        loadAdminPanel();
        
    } catch (error) {
        showToast(error.message, 'error');
    }
}

async function adminDeleteApp(appId) {
    if (!confirm('Delete this application?')) return;
    
    try {
        await apiRequest('/admin/applications/' + appId, {
            method: 'DELETE'
        });
        
        showToast('App deleted', 'success');
        loadAdminPanel();
        
    } catch (error) {
        showToast(error.message, 'error');
    }
}

async function adminDeleteLicense(licenseKey) {
    if (!confirm('Delete this license?')) return;
    
    try {
        await apiRequest('/admin/licenses/' + licenseKey, {
            method: 'DELETE'
        });
        
        showToast('License deleted', 'success');
        loadAdminPanel();
        
    } catch (error) {
        showToast(error.message, 'error');
    }
}
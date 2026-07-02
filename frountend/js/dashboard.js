// ==================== DASHBOARD ====================
document.addEventListener('DOMContentLoaded', function() {
    redirectIfNotAuth();
    loadDashboard();
    
    // Create App Form
    const createForm = document.getElementById('createAppForm');
    if (createForm) {
        createForm.addEventListener('submit', handleCreateApp);
    }
});

async function loadDashboard() {
    try {
        // Load user info
        const userData = await apiRequest('/auth/me');
        document.getElementById('username').textContent = userData.user.username;
        
        // Load apps
        const appsData = await apiRequest('/licensing/apps');
        renderApps(appsData.applications);
        
        // Load stats
        updateStats(appsData.applications);
        
    } catch (error) {
        showToast('Failed to load dashboard', 'error');
    }
}

function updateStats(apps) {
    let totalLicenses = 0;
    let activeLicenses = 0;
    
    apps.forEach(app => {
        // We need to fetch licenses count separately or from the app object
        totalLicenses += app.license_count || 0;
    });
    
    document.getElementById('totalApps').textContent = apps.length;
    document.getElementById('totalLicenses').textContent = totalLicenses;
}

function renderApps(apps) {
    const container = document.getElementById('appList');
    container.innerHTML = '';
    
    if (apps.length === 0) {
        container.innerHTML = `
            <div class="card text-center" style="padding: 40px;">
                <p style="font-size: 18px; color: var(--gray);">No applications yet</p>
                <p style="color: var(--gray);">Create your first application below!</p>
            </div>
        `;
        return;
    }
    
    apps.forEach(app => {
        const card = document.createElement('div');
        card.className = 'app-card';
        card.innerHTML = `
            <div class="app-header">
                <div class="app-name">
                    ${app.name}
                    <span class="badge ${app.is_active ? '' : 'inactive'}">
                        ${app.is_active ? 'Active' : 'Inactive'}
                    </span>
                </div>
                <button class="btn btn-danger btn-sm" onclick="deleteApp(${app.id})">Delete</button>
            </div>
            <div class="app-details">
                <div><strong>Owner ID:</strong> <code>${app.owner_id}</code></div>
                <div><strong>Secret:</strong> <code>${app.secret}</code></div>
                <div><strong>Created:</strong> ${new Date(app.created_at).toLocaleDateString()}</div>
                <div><strong>Licenses:</strong> ${app.license_count || 0}</div>
            </div>
            <div class="app-actions">
                <button class="btn btn-success btn-sm" onclick="generateLicense(${app.id})">+ Generate License</button>
                <button class="btn btn-warning btn-sm" onclick="regenerateSecret(${app.id})">Regenerate Secret</button>
            </div>
            <div id="licenses-${app.id}" style="margin-top: 16px;">
                <!-- Licenses will be loaded here -->
            </div>
        `;
        container.appendChild(card);
        
        // Load licenses for this app
        loadLicenses(app.id);
    });
}

async function loadLicenses(appId) {
    try {
        const data = await apiRequest(`/licensing/apps/${appId}/licenses`);
        const container = document.getElementById(`licenses-${appId}`);
        
        if (data.licenses.length === 0) {
            container.innerHTML = `<p style="color: var(--gray); font-size: 13px;">No licenses yet</p>`;
            return;
        }
        
        container.innerHTML = data.licenses.map(lic => `
            <div class="license-item">
                <div>
                    <span class="key">${lic.license_key}</span>
                    <span class="status-badge ${
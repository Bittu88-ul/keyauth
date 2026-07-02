// ==================== CONFIGURATION ====================
const API_BASE_URL = 'https://my-flask-api-3-jhdp.onrender.com';

let JWT_TOKEN = localStorage.getItem('token');
let CURRENT_USER = JSON.parse(localStorage.getItem('user') || 'null');

// ==================== SERVER STATUS CHECK ====================
async function checkServerStatus() {
    const dot = document.getElementById('statusDot');
    const text = document.getElementById('statusText');
    
    if (!dot) return;
    
    dot.className = 'status-dot checking';
    text.textContent = 'Checking...';
    text.className = 'status-text checking';
    
    try {
        const response = await fetch(`${API_BASE_URL}/health`, {
            method: 'GET',
            signal: AbortSignal.timeout(5000)
        });
        
        if (response.ok) {
            dot.className = 'status-dot online';
            text.textContent = 'Server Online';
            text.className = 'status-text online';
        } else {
            throw new Error('Server error');
        }
    } catch (error) {
        dot.className = 'status-dot offline';
        text.textContent = 'Server Offline';
        text.className = 'status-text offline';
    }
}

// ==================== TOAST NOTIFICATIONS ====================
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer') || createToastContainer();
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toastContainer';
    container.className = 'toast-container';
    document.body.appendChild(container);
    return container;
}

// ==================== API HELPERS ====================
async function apiRequest(endpoint, options = {}) {
    const url = `${API_BASE_URL}/api${endpoint}`;
    console.log('📡 API Call:', url);
    
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };
    
    if (JWT_TOKEN) {
        headers['Authorization'] = `Bearer ${JWT_TOKEN}`;
    }
    
    const config = {
        ...options,
        headers,
        credentials: 'include'
    };
    
    try {
        const response = await fetch(url, config);
        const data = await response.json();
        
        if (!response.ok) {
            if (response.status === 401) {
                if (window.location.pathname !== '/login.html') {
                    localStorage.removeItem('token');
                    localStorage.removeItem('user');
                    window.location.href = '/login.html';
                }
            }
            throw new Error(data.error || 'Request failed');
        }
        
        return data;
    } catch (error) {
        console.error('❌ API Error:', error);
        if (!error.message.includes('Failed to fetch')) {
            showToast(error.message, 'error');
        } else {
            showToast('❌ Server not reachable! Check if backend is running.', 'error');
        }
        throw error;
    }
}

// ==================== AUTH HELPERS ====================
function isAuthenticated() {
    return !!JWT_TOKEN;
}

function isAdmin() {
    return CURRENT_USER && CURRENT_USER.is_admin;
}

function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    JWT_TOKEN = null;
    CURRENT_USER = null;
    window.location.href = '/login.html';
}

function redirectIfNotAuth() {
    if (!isAuthenticated()) {
        window.location.href = '/login.html';
    }
}

function redirectIfAuth() {
    if (isAuthenticated()) {
        if (isAdmin()) {
            window.location.href = '/admin.html';
        } else {
            window.location.href = '/dashboard.html';
        }
    }
}

// ==================== INIT ====================
document.addEventListener('DOMContentLoaded', function() {
    console.log('✅ Frontend Loaded!');
    checkServerStatus();
    setInterval(checkServerStatus, 30000);
});

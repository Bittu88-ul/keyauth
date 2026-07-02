// ==================== REGISTER ====================
document.addEventListener('DOMContentLoaded', function() {
    const registerForm = document.getElementById('registerForm');
    if (registerForm) {
        registerForm.addEventListener('submit', handleRegister);
    }
    
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }
});

async function handleRegister(e) {
    e.preventDefault();
    
    const username = document.getElementById('username').value.trim();
    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value;
    const confirm = document.getElementById('confirmPassword').value;
    const submitBtn = document.querySelector('#registerForm button[type="submit"]');
    const messageEl = document.getElementById('registerMessage');
    
    // Validation
    if (password !== confirm) {
        messageEl.textContent = 'Passwords do not match!';
        messageEl.style.color = '#FF5252';
        return;
    }
    
    if (password.length < 6) {
        messageEl.textContent = 'Password must be at least 6 characters!';
        messageEl.style.color = '#FF5252';
        return;
    }
    
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner"></span> Registering...';
    messageEl.textContent = '';
    
    try {
        const data = await apiRequest('/auth/register', {
            method: 'POST',
            body: JSON.stringify({ username, email, password })
        });
        
        messageEl.textContent = '✅ Registration successful! Redirecting to login...';
        messageEl.style.color = '#00E676';
        
        setTimeout(() => {
            window.location.href = '/login.html';
        }, 1500);
        
    } catch (error) {
        messageEl.textContent = error.message || 'Registration failed';
        messageEl.style.color = '#FF5252';
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Create Account';
    }
}

// ==================== LOGIN ====================
async function handleLogin(e) {
    e.preventDefault();
    
    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value;
    const submitBtn = document.querySelector('#loginForm button[type="submit"]');
    const messageEl = document.getElementById('loginMessage');
    
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner"></span> Logging in...';
    messageEl.textContent = '';
    
    try {
        const data = await apiRequest('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, password })
        });
        
        // Save token and user
        JWT_TOKEN = data.token;
        CURRENT_USER = data.user;
        localStorage.setItem('token', data.token);
        localStorage.setItem('user', JSON.stringify(data.user));
        
        messageEl.textContent = '✅ Login successful! Redirecting...';
        messageEl.style.color = '#00E676';
        
        setTimeout(() => {
            if (data.user.is_admin) {
                window.location.href = '/admin.html';
            } else {
                window.location.href = '/dashboard.html';
            }
        }, 1000);
        
    } catch (error) {
        messageEl.textContent = error.message || 'Login failed';
        messageEl.style.color = '#FF5252';
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Login';
    }
}
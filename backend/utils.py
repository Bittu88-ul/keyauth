import secrets
import hashlib
import re
import uuid
import platform
import datetime
import jwt
from flask import current_app, request, session, jsonify
from functools import wraps

def generate_owner_id():
    """Generate unique Owner ID for application"""
    return f"OWNER_{secrets.token_hex(10).upper()}"

def generate_secret():
    """Generate unique Secret key for application"""
    return f"SEC_{secrets.token_hex(16).upper()}"

def generate_license_key():
    """Generate unique License Key"""
    return f"LIC-{secrets.token_hex(8).upper()}-{secrets.token_hex(4).upper()}"

def generate_api_key():
    """Generate API Key for SDK"""
    return f"API_{secrets.token_hex(20).upper()}"

def hash_password(password):
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    """Verify password"""
    return hash_password(password) == hashed

def generate_hwid(device_info):
    """Generate Hardware ID from device information"""
    combined = ""
    combined += device_info.get('cpu', '')
    combined += device_info.get('motherboard', '')
    combined += device_info.get('disk_serial', '')
    combined += device_info.get('mac_address', '')
    combined += device_info.get('os', '')
    
    if not combined:
        combined = f"{platform.processor()}{platform.node()}{uuid.getnode()}"
    
    return hashlib.sha256(combined.encode()).hexdigest()

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_username(username):
    """Validate username - only alphanumeric and underscore"""
    pattern = r'^[a-zA-Z0-9_]{3,30}$'
    return re.match(pattern, username) is not None

def generate_jwt_token(user_id, username, is_admin=False):
    """Generate JWT token for API authentication"""
    payload = {
        'user_id': user_id,
        'username': username,
        'is_admin': is_admin,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
    }
    return jwt.encode(payload, current_app.config['JWT_SECRET_KEY'], algorithm='HS256')

def decode_jwt_token(token):
    """Decode JWT token"""
    try:
        return jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
    except:
        return None

def get_client_ip():
    """Get client IP address"""
    if 'X-Forwarded-For' in request.headers:
        return request.headers['X-Forwarded-For'].split(',')[0]
    return request.remote_addr or '127.0.0.1'

def get_current_timestamp():
    """Get current UTC timestamp"""
    return datetime.datetime.utcnow()

def format_datetime(dt):
    """Format datetime for JSON response"""
    if dt:
        return dt.isoformat()
    return None

# ==================== AUTH DECORATORS (IMPORTANT!) ====================

def login_required(f):
    """Decorator to check if user is logged in"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check session first (web)
        if 'user_id' in session:
            return f(*args, **kwargs)
        
        # Check Bearer token (API)
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            payload = decode_jwt_token(token)
            if payload:
                request.user_id = payload['user_id']
                request.username = payload['username']
                request.is_admin = payload.get('is_admin', False)
                return f(*args, **kwargs)
        
        return jsonify({'error': 'Authentication required'}), 401
    return decorated_function

def admin_required(f):
    """Decorator to check if user is admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' in session:
            from models import User
            user = User.query.get(session['user_id'])
            if user and user.is_admin:
                return f(*args, **kwargs)
        
        # Check JWT
        if hasattr(request, 'is_admin') and request.is_admin:
            return f(*args, **kwargs)
        
        return jsonify({'error': 'Admin access required'}), 403
    return decorated_function
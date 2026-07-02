from flask import Blueprint, request, jsonify, session, current_app
from flask_cors import cross_origin
from datetime import datetime
from functools import wraps
import jwt

from models import db, User, LoginHistory
from utils import (
    hash_password, verify_password, validate_email, 
    validate_username, generate_api_key, generate_jwt_token,
    decode_jwt_token, get_client_ip
)

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# ==================== DECORATORS ====================

def login_required(f):
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
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' in session:
            user = User.query.get(session['user_id'])
            if user and user.is_admin:
                return f(*args, **kwargs)
        
        # Check JWT
        if hasattr(request, 'is_admin') and request.is_admin:
            return f(*args, **kwargs)
        
        return jsonify({'error': 'Admin access required'}), 403
    return decorated_function

# ==================== AUTH ROUTES ====================

@auth_bp.route('/register', methods=['POST'])
@cross_origin()
def register():
    """User registration with email and password"""
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        # Validation
        if not email or not username or not password:
            return jsonify({'error': 'Email, username, and password are required'}), 400
        
        if not validate_email(email):
            return jsonify({'error': 'Invalid email format'}), 400
        
        if not validate_username(username):
            return jsonify({'error': 'Username must be 3-30 characters (alphanumeric and underscore only)'}), 400
        
        if len(password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters'}), 400
        
        # Check duplicate
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already registered'}), 409
        
        if User.query.filter_by(username=username).first():
            return jsonify({'error': 'Username already taken'}), 409
        
        # Create user
        user = User(
            email=email,
            username=username,
            password_hash=hash_password(password),
            api_key=generate_api_key()
        )
        
        # Make first user admin (optional)
        if User.query.count() == 0:
            user.is_admin = True
        
        db.session.add(user)
        db.session.commit()
        
        return jsonify({
            'message': 'Registration successful!',
            'user': user.to_dict(),
            'api_key': user.api_key
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/login', methods=['POST'])
@cross_origin()
def login():
    """User login with email and password"""
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400
        
        user = User.query.filter_by(email=email).first()
        
        # Log login attempt
        login_log = LoginHistory(
            user_id=user.id if user else None,
            ip_address=get_client_ip(),
            user_agent=request.headers.get('User-Agent', 'Unknown'),
            is_successful=False
        )
        
        if not user or not verify_password(password, user.password_hash):
            db.session.add(login_log)
            db.session.commit()
            return jsonify({'error': 'Invalid email or password'}), 401
        
        if user.is_banned:
            return jsonify({'error': 'Account is banned. Contact support.'}), 403
        
        # Update last login
        user.last_login = datetime.utcnow()
        login_log.is_successful = True
        db.session.commit()
        
        # Set session for web
        session['user_id'] = user.id
        session['username'] = user.username
        session['is_admin'] = user.is_admin
        
        # Generate JWT for API
        jwt_token = generate_jwt_token(user.id, user.username, user.is_admin)
        
        return jsonify({
            'message': 'Login successful',
            'user': user.to_dict(),
            'token': jwt_token,
            'api_key': user.api_key
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/logout', methods=['POST'])
@login_required
@cross_origin()
def logout():
    """Logout user"""
    session.clear()
    return jsonify({'message': 'Logged out successfully'}), 200

@auth_bp.route('/me', methods=['GET'])
@login_required
@cross_origin()
def get_current_user():
    """Get current user info"""
    try:
        if 'user_id' in session:
            user = User.query.get(session['user_id'])
        else:
            user = User.query.get(request.user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({'user': user.to_dict()}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/refresh-token', methods=['POST'])
@login_required
@cross_origin()
def refresh_token():
    """Refresh JWT token"""
    try:
        if 'user_id' in session:
            user = User.query.get(session['user_id'])
        else:
            user = User.query.get(request.user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        new_token = generate_jwt_token(user.id, user.username, user.is_admin)
        return jsonify({'token': new_token}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/change-password', methods=['POST'])
@login_required
@cross_origin()
def change_password():
    """Change user password"""
    try:
        data = request.get_json()
        old_password = data.get('old_password')
        new_password = data.get('new_password')
        
        if not old_password or not new_password:
            return jsonify({'error': 'Old and new password required'}), 400
        
        if len(new_password) < 6:
            return jsonify({'error': 'New password must be at least 6 characters'}), 400
        
        if 'user_id' in session:
            user = User.query.get(session['user_id'])
        else:
            user = User.query.get(request.user_id)
        
        if not verify_password(old_password, user.password_hash):
            return jsonify({'error': 'Old password is incorrect'}), 401
        
        user.password_hash = hash_password(new_password)
        db.session.commit()
        
        return jsonify({'message': 'Password changed successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/verify-email/<email>', methods=['GET'])
@cross_origin()
def check_email_exists(email):
    """Check if email exists"""
    user = User.query.filter_by(email=email.lower()).first()
    return jsonify({'exists': user is not None}), 200

@auth_bp.route('/verify-username/<username>', methods=['GET'])
@cross_origin()
def check_username_exists(username):
    """Check if username exists"""
    user = User.query.filter_by(username=username).first()
    return jsonify({'exists': user is not None}), 200
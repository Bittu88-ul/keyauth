from flask import Blueprint, request, jsonify, session
from flask_cors import cross_origin
from datetime import datetime

from models import db, User, Application, License, LoginHistory, APILog
from utils import login_required, admin_required, format_datetime

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

# ==================== USER MANAGEMENT ====================

@admin_bp.route('/users', methods=['GET'])
@login_required
@admin_required
@cross_origin()
def get_all_users():
    """Get all users (admin only)"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        
        pagination = User.query.paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'users': [user.to_dict() for user in pagination.items],
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/users/<int:user_id>', methods=['GET'])
@login_required
@admin_required
@cross_origin()
def get_user(user_id):
    """Get specific user details"""
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({'user': user.to_dict()}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@login_required
@admin_required
@cross_origin()
def update_user(user_id):
    """Update user (admin only)"""
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        
        if 'is_admin' in data:
            user.is_admin = data['is_admin']
        if 'is_verified' in data:
            user.is_verified = data['is_verified']
        if 'is_banned' in data:
            user.is_banned = data['is_banned']
        if 'username' in data:
            # Check if username taken
            existing = User.query.filter_by(username=data['username']).first()
            if existing and existing.id != user_id:
                return jsonify({'error': 'Username already taken'}), 409
            user.username = data['username']
        
        db.session.commit()
        
        return jsonify({
            'message': 'User updated',
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@login_required
@admin_required
@cross_origin()
def delete_user(user_id):
    """Delete user (admin only)"""
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        if user.is_admin:
            return jsonify({'error': 'Cannot delete admin user'}), 403
        
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({'message': 'User deleted'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ==================== APPLICATION MANAGEMENT (ADMIN) ====================

@admin_bp.route('/applications', methods=['GET'])
@login_required
@admin_required
@cross_origin()
def get_all_applications():
    """Get all applications (admin only)"""
    try:
        apps = Application.query.all()
        
        return jsonify({
            'applications': [app.to_dict() for app in apps]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/applications/<int:app_id>', methods=['DELETE'])
@login_required
@admin_required
@cross_origin()
def admin_delete_app(app_id):
    """Delete any application (admin only)"""
    try:
        app = Application.query.get(app_id)
        if not app:
            return jsonify({'error': 'Application not found'}), 404
        
        db.session.delete(app)
        db.session.commit()
        
        return jsonify({'message': 'Application deleted'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ==================== LICENSE MANAGEMENT (ADMIN) ====================

@admin_bp.route('/licenses', methods=['GET'])
@login_required
@admin_required
@cross_origin()
def get_all_licenses():
    """Get all licenses (admin only)"""
    try:
        licenses = License.query.all()
        
        return jsonify({
            'licenses': [lic.to_dict() for lic in licenses]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/licenses/<license_key>', methods=['DELETE'])
@login_required
@admin_required
@cross_origin()
def admin_delete_license(license_key):
    """Delete any license (admin only)"""
    try:
        license = License.query.filter_by(license_key=license_key).first()
        if not license:
            return jsonify({'error': 'License not found'}), 404
        
        db.session.delete(license)
        db.session.commit()
        
        return jsonify({'message': 'License deleted'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ==================== STATISTICS (ADMIN) ====================

@admin_bp.route('/stats', methods=['GET'])
@login_required
@admin_required
@cross_origin()
def get_system_stats():
    """Get system statistics (admin only)"""
    try:
        total_users = User.query.count()
        total_apps = Application.query.count()
        total_licenses = License.query.count()
        active_licenses = License.query.filter_by(is_active=True).count()
        total_activations = LicenseActivation.query.count()
        
        # Recent activity
        recent_logins = LoginHistory.query.order_by(
            LoginHistory.login_time.desc()
        ).limit(10).all()
        
        return jsonify({
            'total_users': total_users,
            'total_applications': total_apps,
            'total_licenses': total_licenses,
            'active_licenses': active_licenses,
            'total_activations': total_activations,
            'recent_activity': [log.to_dict() for log in recent_logins]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== LOGS (ADMIN) ====================

@admin_bp.route('/logs', methods=['GET'])
@login_required
@admin_required
@cross_origin()
def get_logs():
    """Get API logs (admin only)"""
    try:
        limit = request.args.get('limit', 100, type=int)
        logs = APILog.query.order_by(
            APILog.created_at.desc()
        ).limit(limit).all()
        
        return jsonify({
            'logs': [log.to_dict() for log in logs]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
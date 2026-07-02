from flask import Blueprint, request, jsonify, session
from flask_cors import cross_origin
from datetime import datetime, timedelta
from functools import wraps

from models import db, User, Application, License, LicenseActivation
from utils import (
    generate_owner_id, generate_secret, generate_license_key,
    generate_hwid, get_client_ip, login_required
)

licensing_bp = Blueprint('licensing', __name__, url_prefix='/api/licensing')

# ==================== DECORATORS ====================

def app_owner_required(f):
    @wraps(f)
    def decorated_function(app_id, *args, **kwargs):
        app = Application.query.get(app_id)
        if not app:
            return jsonify({'error': 'Application not found'}), 404
        
        user_id = session.get('user_id') or getattr(request, 'user_id', None)
        if app.user_id != user_id:
            return jsonify({'error': 'You do not own this application'}), 403
        
        return f(app, *args, **kwargs)
    return decorated_function

# ==================== APPLICATION MANAGEMENT ====================

@licensing_bp.route('/apps', methods=['GET'])
@login_required
@cross_origin()
def get_apps():
    """Get all applications for current user"""
    try:
        user_id = session.get('user_id') or getattr(request, 'user_id', None)
        apps = Application.query.filter_by(user_id=user_id).all()
        
        return jsonify({
            'applications': [app.to_dict() for app in apps]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@licensing_bp.route('/apps', methods=['POST'])
@login_required
@cross_origin()
def create_app():
    """Create a new application"""
    try:
        data = request.get_json()
        app_name = data.get('app_name', '').strip()
        app_description = data.get('app_description', '').strip()
        
        if not app_name:
            return jsonify({'error': 'Application name is required'}), 400
        
        user_id = session.get('user_id') or getattr(request, 'user_id', None)
        
        # Check duplicate app name for this user
        existing = Application.query.filter_by(user_id=user_id, app_name=app_name).first()
        if existing:
            return jsonify({'error': 'Application with this name already exists'}), 409
        
        app = Application(
            user_id=user_id,
            app_name=app_name,
            app_description=app_description,
            owner_id=generate_owner_id(),
            secret=generate_secret()
        )
        
        db.session.add(app)
        db.session.commit()
        
        return jsonify({
            'message': 'Application created successfully',
            'application': app.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@licensing_bp.route('/apps/<int:app_id>', methods=['GET'])
@login_required
@cross_origin()
@app_owner_required
def get_app(app):
    """Get single application details"""
    return jsonify({'application': app.to_dict()}), 200

@licensing_bp.route('/apps/<int:app_id>', methods=['PUT'])
@login_required
@cross_origin()
@app_owner_required
def update_app(app):
    """Update application details"""
    try:
        data = request.get_json()
        
        if 'app_name' in data:
            app.app_name = data['app_name'].strip()
        if 'app_description' in data:
            app.app_description = data['app_description'].strip()
        if 'is_active' in data:
            app.is_active = data['is_active']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Application updated',
            'application': app.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@licensing_bp.route('/apps/<int:app_id>', methods=['DELETE'])
@login_required
@cross_origin()
@app_owner_required
def delete_app(app):
    """Delete application and all its licenses"""
    try:
        app_name = app.app_name
        db.session.delete(app)
        db.session.commit()
        
        return jsonify({'message': f'Application "{app_name}" deleted'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@licensing_bp.route('/apps/<int:app_id>/regenerate-secret', methods=['POST'])
@login_required
@cross_origin()
@app_owner_required
def regenerate_secret(app):
    """Regenerate application secret"""
    try:
        app.secret = generate_secret()
        db.session.commit()
        
        return jsonify({
            'message': 'Secret regenerated',
            'secret': app.secret
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ==================== LICENSE MANAGEMENT ====================

@licensing_bp.route('/apps/<int:app_id>/licenses', methods=['GET'])
@login_required
@cross_origin()
@app_owner_required
def get_licenses(app):
    """Get all licenses for an application"""
    try:
        licenses = License.query.filter_by(app_id=app.id).all()
        
        return jsonify({
            'licenses': [lic.to_dict() for lic in licenses]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@licensing_bp.route('/apps/<int:app_id>/licenses', methods=['POST'])
@login_required
@cross_origin()
@app_owner_required
def create_license(app):
    """Create a new license for application"""
    try:
        data = request.get_json()
        expires_days = data.get('expires_days', 365)
        is_permanent = data.get('is_permanent', False)
        max_activations = data.get('max_activations', 1)
        
        license_key = generate_license_key()
        
        license = License(
            app_id=app.id,
            license_key=license_key,
            is_permanent=is_permanent,
            max_activations=max_activations,
            expires_at=None if is_permanent else datetime.utcnow() + timedelta(days=expires_days)
        )
        
        db.session.add(license)
        db.session.commit()
        
        return jsonify({
            'message': 'License created',
            'license': license.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@licensing_bp.route('/licenses/<license_key>', methods=['GET'])
@login_required
@cross_origin()
def get_license(license_key):
    """Get license details"""
    try:
        license = License.query.filter_by(license_key=license_key).first()
        if not license:
            return jsonify({'error': 'License not found'}), 404
        
        # Check if user owns the app
        user_id = session.get('user_id') or getattr(request, 'user_id', None)
        if license.app.user_id != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        return jsonify({'license': license.to_dict()}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@licensing_bp.route('/licenses/<license_key>', methods=['PUT'])
@login_required
@cross_origin()
def update_license(license_key):
    """Update license settings"""
    try:
        license = License.query.filter_by(license_key=license_key).first()
        if not license:
            return jsonify({'error': 'License not found'}), 404
        
        # Check ownership
        user_id = session.get('user_id') or getattr(request, 'user_id', None)
        if license.app.user_id != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        data = request.get_json()
        
        if 'is_active' in data:
            license.is_active = data['is_active']
        if 'expires_days' in data and not license.is_permanent:
            license.expires_at = datetime.utcnow() + timedelta(days=data['expires_days'])
        if 'max_activations' in data:
            license.max_activations = data['max_activations']
        
        db.session.commit()
        
        return jsonify({
            'message': 'License updated',
            'license': license.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@licensing_bp.route('/licenses/<license_key>', methods=['DELETE'])
@login_required
@cross_origin()
def delete_license(license_key):
    """Delete a license"""
    try:
        license = License.query.filter_by(license_key=license_key).first()
        if not license:
            return jsonify({'error': 'License not found'}), 404
        
        # Check ownership
        user_id = session.get('user_id') or getattr(request, 'user_id', None)
        if license.app.user_id != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        db.session.delete(license)
        db.session.commit()
        
        return jsonify({'message': 'License deleted'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@licensing_bp.route('/licenses/<license_key>/hwid', methods=['POST'])
@login_required
@cross_origin()
def set_license_hwid(license_key):
    """Manually set HWID for a license"""
    try:
        license = License.query.filter_by(license_key=license_key).first()
        if not license:
            return jsonify({'error': 'License not found'}), 404
        
        # Check ownership
        user_id = session.get('user_id') or getattr(request, 'user_id', None)
        if license.app.user_id != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        data = request.get_json()
        hwid = data.get('hwid')
        
        if not hwid:
            return jsonify({'error': 'HWID required'}), 400
        
        license.hwid = hwid
        db.session.commit()
        
        return jsonify({
            'message': 'HWID set successfully',
            'license': license.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@licensing_bp.route('/licenses/<license_key>/hwid', methods=['DELETE'])
@login_required
@cross_origin()
def remove_license_hwid(license_key):
    """Remove HWID lock from a license"""
    try:
        license = License.query.filter_by(license_key=license_key).first()
        if not license:
            return jsonify({'error': 'License not found'}), 404
        
        # Check ownership
        user_id = session.get('user_id') or getattr(request, 'user_id', None)
        if license.app.user_id != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        license.hwid = None
        db.session.commit()
        
        return jsonify({'message': 'HWID removed'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ==================== CLIENT VALIDATION API ====================

@licensing_bp.route('/validate', methods=['POST'])
@cross_origin()
def validate_license():
    """
    Client SDK validation endpoint
    Request: {
        'license_key': 'LIC-XXXX-YYYY',
        'hwid': 'device_hwid_hex',
        'owner_id': 'OWNER_XXXXX'
    }
    """
    try:
        data = request.get_json()
        license_key = data.get('license_key')
        hwid = data.get('hwid')
        owner_id = data.get('owner_id')
        
        if not all([license_key, hwid, owner_id]):
            return jsonify({
                'valid': False,
                'error': 'Missing required fields: license_key, hwid, owner_id'
            }), 400
        
        # Find app by owner_id
        app = Application.query.filter_by(owner_id=owner_id).first()
        if not app:
            return jsonify({
                'valid': False,
                'error': 'Invalid application'
            }), 404
        
        # Find license
        license = License.query.filter_by(license_key=license_key, app_id=app.id).first()
        if not license:
            return jsonify({
                'valid': False,
                'error': 'Invalid license key'
            }), 404
        
        # Check basic validations
        if not license.is_active:
            return jsonify({
                'valid': False,
                'error': 'License is deactivated'
            }), 403
        
        if license.is_expired():
            return jsonify({
                'valid': False,
                'error': 'License has expired'
            }), 403
        
        # Check activation limits
        activation_count = LicenseActivation.query.filter_by(license_id=license.id).count()
        if activation_count >= license.max_activations:
            # Check if this HWID is already activated
            existing_activation = LicenseActivation.query.filter_by(
                license_id=license.id,
                hwid=hwid
            ).first()
            
            if not existing_activation:
                return jsonify({
                    'valid': False,
                    'error': f'Maximum activations ({license.max_activations}) reached'
                }), 403
        
        # HWID management
        if license.hwid is None:
            # First activation - lock HWID
            license.hwid = hwid
        elif license.hwid != hwid:
            return jsonify({
                'valid': False,
                'error': 'HWID mismatch. License locked to another device'
            }), 403
        
        # Create or update activation record
        activation = LicenseActivation.query.filter_by(
            license_id=license.id,
            hwid=hwid
        ).first()
        
        if not activation:
            activation = LicenseActivation(
                license_id=license.id,
                hwid=hwid,
                ip_address=get_client_ip(),
                user_agent=request.headers.get('User-Agent', 'Unknown')
            )
            db.session.add(activation)
        else:
            activation.last_validated = datetime.utcnow()
        
        # Update license
        license.last_validation = datetime.utcnow()
        license.last_activated = datetime.utcnow()
        license.current_activations = LicenseActivation.query.filter_by(
            license_id=license.id
        ).count()
        
        db.session.commit()
        
        return jsonify({
            'valid': True,
            'license_key': license.license_key,
            'app_name': app.app_name,
            'username': app.user.username,
            'expires_at': license.expires_at.isoformat() if license.expires_at else None,
            'is_permanent': license.is_permanent,
            'max_activations': license.max_activations,
            'current_activations': license.current_activations,
            'hwid_locked': license.hwid is not None
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'valid': False,
            'error': f'Internal server error: {str(e)}'
        }), 500

@licensing_bp.route('/deactivate', methods=['POST'])
@cross_origin()
def deactivate_license():
    """
    Deactivate license from a device
    Request: {
        'license_key': 'LIC-XXXX-YYYY',
        'hwid': 'device_hwid_hex',
        'owner_id': 'OWNER_XXXXX'
    }
    """
    try:
        data = request.get_json()
        license_key = data.get('license_key')
        hwid = data.get('hwid')
        owner_id = data.get('owner_id')
        
        if not all([license_key, hwid, owner_id]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        app = Application.query.filter_by(owner_id=owner_id).first()
        if not app:
            return jsonify({'error': 'Invalid application'}), 404
        
        license = License.query.filter_by(license_key=license_key, app_id=app.id).first()
        if not license:
            return jsonify({'error': 'Invalid license key'}), 404
        
        # Check if HWID matches
        if license.hwid and license.hwid != hwid:
            return jsonify({'error': 'HWID mismatch'}), 403
        
        # Remove activation
        activation = LicenseActivation.query.filter_by(
            license_id=license.id,
            hwid=hwid
        ).first()
        
        if activation:
            db.session.delete(activation)
            
            # Update counts
            license.current_activations = LicenseActivation.query.filter_by(
                license_id=license.id
            ).count()
            
            # If no activations left, clear HWID lock
            if license.current_activations == 0:
                license.hwid = None
            
            db.session.commit()
            return jsonify({'message': 'Deactivated successfully'}), 200
        
        return jsonify({'error': 'Activation not found'}), 404
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ==================== STATISTICS ====================

@licensing_bp.route('/apps/<int:app_id>/stats', methods=['GET'])
@login_required
@cross_origin()
@app_owner_required
def get_app_stats(app):
    """Get statistics for an application"""
    try:
        total_licenses = License.query.filter_by(app_id=app.id).count()
        active_licenses = License.query.filter_by(app_id=app.id, is_active=True).count()
        total_activations = LicenseActivation.query.join(License).filter(
            License.app_id == app.id
        ).count()
        
        return jsonify({
            'app_name': app.app_name,
            'total_licenses': total_licenses,
            'active_licenses': active_licenses,
            'total_activations': total_activations,
            'created_at': app.created_at.isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
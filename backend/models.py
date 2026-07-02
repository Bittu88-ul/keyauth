from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_verified = db.Column(db.Boolean, default=False)
    is_banned = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    api_key = db.Column(db.String(100), unique=True)
    
    # Relationships
    applications = db.relationship('Application', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    login_history = db.relationship('LoginHistory', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'username': self.username,
            'is_admin': self.is_admin,
            'is_verified': self.is_verified,
            'is_banned': self.is_banned,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }

class Application(db.Model):
    __tablename__ = 'applications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    app_name = db.Column(db.String(100), nullable=False)
    app_description = db.Column(db.Text)
    owner_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    secret = db.Column(db.String(100), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    licenses = db.relationship('License', backref='app', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.app_name,
            'description': self.app_description,
            'owner_id': self.owner_id,
            'secret': self.secret,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'license_count': self.licenses.count()
        }

class License(db.Model):
    __tablename__ = 'licenses'
    
    id = db.Column(db.Integer, primary_key=True)
    app_id = db.Column(db.Integer, db.ForeignKey('applications.id'), nullable=False, index=True)
    license_key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    hwid = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True)
    is_permanent = db.Column(db.Boolean, default=False)
    expires_at = db.Column(db.DateTime)
    max_activations = db.Column(db.Integer, default=1)
    current_activations = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_activated = db.Column(db.DateTime)
    last_validation = db.Column(db.DateTime)
    
    # Relationships
    activations = db.relationship('LicenseActivation', backref='license', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'license_key': self.license_key,
            'hwid': self.hwid,
            'is_active': self.is_active,
            'is_permanent': self.is_permanent,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'max_activations': self.max_activations,
            'current_activations': self.current_activations,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_activation': self.last_activated.isoformat() if self.last_activated else None
        }
    
    def is_expired(self):
        if self.is_permanent:
            return False
        if not self.expires_at:
            return False
        return self.expires_at < datetime.utcnow()

class LicenseActivation(db.Model):
    __tablename__ = 'license_activations'
    
    id = db.Column(db.Integer, primary_key=True)
    license_id = db.Column(db.Integer, db.ForeignKey('licenses.id'), nullable=False, index=True)
    hwid = db.Column(db.String(200), nullable=False)
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(200))
    activated_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_validated = db.Column(db.DateTime)
    
    def to_dict(self):
        return {
            'id': self.id,
            'hwid': self.hwid,
            'ip_address': self.ip_address,
            'activated_at': self.activated_at.isoformat() if self.activated_at else None,
            'last_validated': self.last_validated.isoformat() if self.last_validated else None
        }

class LoginHistory(db.Model):
    __tablename__ = 'login_history'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(200))
    login_time = db.Column(db.DateTime, default=datetime.utcnow)
    is_successful = db.Column(db.Boolean, default=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'ip_address': self.ip_address,
            'login_time': self.login_time.isoformat() if self.login_time else None,
            'is_successful': self.is_successful
        }

class APILog(db.Model):
    __tablename__ = 'api_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    endpoint = db.Column(db.String(100))
    ip_address = db.Column(db.String(50))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    request_data = db.Column(db.Text)
    response_status = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'endpoint': self.endpoint,
            'ip_address': self.ip_address,
            'response_status': self.response_status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
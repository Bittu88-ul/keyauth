from flask import Flask, jsonify, render_template_string
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import Config
from models import db
from auth import auth_bp
from licensing import licensing_bp
from admin import admin_bp

# ==================== INIT APP ====================

app = Flask(__name__)
app.config.from_object(Config)

# ==================== INIT EXTENSIONS ====================

db.init_app(app)
CORS(app, origins=['http://localhost:3000', 'http://127.0.0.1:3000', 'http://10.47.206.158:3000', 'http://10.47.206.158:5000'], supports_credentials=True, allow_headers=['Content-Type', 'Authorization'])
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[app.config['RATELIMIT_DEFAULT']],
    storage_uri=app.config['RATELIMIT_STORAGE_URL']
)
limiter.init_app(app)

# ==================== REGISTER BLUEPRINTS ====================

app.register_blueprint(auth_bp)
app.register_blueprint(licensing_bp)
app.register_blueprint(admin_bp)

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Resource not found'}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({'error': 'Rate limit exceeded. Please try again later.'}), 429

# ==================== HEALTH CHECK ====================

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'version': '1.0.0'
    }), 200

# ==================== HOME (TEMPORARY) ====================

@app.route('/', methods=['GET'])
def home():
    """Temporary homepage showing API is running"""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>License Management API</title></head>
    <body>
        <h1>🚀 License Management System API</h1>
        <p>Server is running!</p>
        <hr>
        <h2>Available Endpoints:</h2>
        <ul>
            <li><b>Auth:</b> /api/auth/register, /api/auth/login</li>
            <li><b>Licensing:</b> /api/licensing/apps, /api/licensing/validate</li>
            <li><b>Admin:</b> /api/admin/users, /api/admin/stats</li>
        </ul>
        <p>Check <a href="/health">/health</a> for server status</p>
    </body>
    </html>
    """
    return render_template_string(html)

# ==================== CREATE DATABASE TABLES ====================

def init_db():
    """Initialize database with tables and default admin user"""
    with app.app_context():
        db.create_all()
        
        # Create admin user if not exists
        from models import User
        from utils import hash_password
        
        admin_email = app.config.get('ADMIN_EMAIL', 'admin@yourdomain.com')
        admin_password = app.config.get('ADMIN_PASSWORD', 'Admin@123')
        
        admin = User.query.filter_by(email=admin_email).first()
        if not admin:
            admin = User(
                email=admin_email,
                username='admin',
                password_hash=hash_password(admin_password),
                is_admin=True,
                is_verified=True
            )
            db.session.add(admin)
            db.session.commit()
            print(f"✅ Admin user created: {admin_email} / {admin_password}")
        
        print("✅ Database initialized successfully!")

# ==================== RUN APP ====================

if __name__ == '__main__':
    init_db()
    app.run(
        host='127.0.0.1',
        port=5000,
        debug=True
    )
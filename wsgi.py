# ==============================================================================
# wsgi.py - WSGI Entry Point for Production (Gunicorn)
# ------------------------------------------------------------------------------
# ROL: Punct de intrare MINIMAL pentru Gunicorn care exportă doar app.server
#      FĂRĂ să execute inițializarea database/callbacks la import!
#
# UTILIZARE (Gunicorn):
#   gunicorn --workers 4 --threads 2 wsgi:application
#
# RESPECTĂ: .cursorrules - Separation of Concerns, Defensive Programming
# ==============================================================================

import os
import sys

# Asigură-te că directorul curent e în Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import DOAR app instance (nu run_medical care face init!)
from app_instance import app

# Exportăm Flask application pentru Gunicorn
application = app.server

# === INIȚIALIZARE LA STARTUP (NU la primul request!) ===
# CRITICAL: DB trebuie inițializat ÎNAINTE de orice request, altfel Flask aruncă
# AssertionError: teardown_appcontext can no longer be called after first request

def initialize_application():
    """
    Inițializare aplicație la STARTUP (NU lazy init!).
    Se execută imediat după import, ÎNAINTE de orice request HTTP.
    """
    import os
    from dotenv import load_dotenv
    from urllib.parse import urlparse
    
    # Încărcăm environment variables
    load_dotenv()
    
    # === LOGGING ===
    from logger_setup import logger
    logger.warning("=" * 70)
    logger.warning("🏥 INIȚIALIZARE APLICAȚIE MEDICAL - STARTUP")
    logger.warning("=" * 70)
    
    # === DATABASE INIT ===
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        logger.error("❌ DATABASE_URL nu este setat!")
        raise RuntimeError("DATABASE_URL environment variable not set!")
    
    application.config['SQLALCHEMY_DATABASE_URI'] = database_url
    application.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    application.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Connection pooling
    application.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 10,
        'max_overflow': 20,
        'pool_timeout': 30,
        'pool_recycle': 1800,
        'pool_pre_ping': True,
        'connect_args': {
            'connect_timeout': 10,
            'options': '-c statement_timeout=60000'
        }
    }
    
    # Session config
    application.config['SESSION_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE', 'False') == 'True'
    application.config['SESSION_COOKIE_HTTPONLY'] = True
    application.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    application.config['PERMANENT_SESSION_LIFETIME'] = int(os.getenv('PERMANENT_SESSION_LIFETIME', '30')) * 24 * 3600
    
    logger.warning(f"📊 Database configured: {urlparse(database_url).hostname}")
    
    # === AUTH INIT (CRITICAL: trebuie făcut ÎNAINTE de orice request!) ===
    from auth.models import db, init_db, create_admin_user
    from auth.auth_manager import init_auth_manager
    from auth_routes import init_auth_routes
    
    # IMPORTANT: Pasăm 'app' (Dash instance), nu 'application' (Flask server)
    # init_db va extrage app.server intern
    init_db(app)
    init_auth_manager(app)
    init_auth_routes(app)
    
    logger.warning("✅ Database & Authentication initialized")
    
    # === DASH LIBRARIES REGISTRATION (CRITICAL!) ===
    # MUST import Dash component libraries BEFORE setting layout
    # Otherwise Dash won't register them and will return 500 for component assets
    import dash.dcc
    import dash.html
    from dash import dash_table  # Dash 2.x syntax (dash_table integrated in main package)
    logger.warning("✅ Dash component libraries imported (dcc, html, dash_table)")
    
    # === CALLBACKS & LAYOUT ===
    from app_layout_new import layout
    import callbacks
    import callbacks_medical
    import admin_callbacks
    
    app.layout = layout
    
    logger.warning(f"✅ Layout & Callbacks registered: {len(app.callback_map)} callbacks")
    
    # === ADMIN USER ===
    with application.app_context():
        try:
            admin_email = os.getenv('ADMIN_EMAIL', 'admin@pulsoximetrie.ro')
            admin_password = os.getenv('ADMIN_PASSWORD', 'Admin123!Change')
            admin_name = os.getenv('ADMIN_NAME', 'Administrator')
            
            from auth.models import Doctor
            existing_admin = Doctor.query.filter_by(email=admin_email).first()
            
            if not existing_admin:
                create_admin_user(admin_email, admin_password, admin_name)
                logger.warning(f"🔑 Admin user created: {admin_email}")
            else:
                logger.warning(f"✅ Admin user exists: {admin_email}")
        except Exception as e:
            logger.error(f"❌ Admin user creation failed: {e}", exc_info=True)
    
    # === RATE LIMITER CLEANUP ===
    from auth.rate_limiter import schedule_cleanup_task
    schedule_cleanup_task()
    
    logger.warning("=" * 70)
    logger.warning("✅ APPLICATION FULLY INITIALIZED - Ready for requests!")
    logger.warning("=" * 70)


# === EXECUTĂ INIȚIALIZAREA LA IMPORT (STARTUP) ===
try:
    initialize_application()
except Exception as e:
    # Log critical error and re-raise to prevent app from starting in broken state
    from logger_setup import logger
    logger.critical(f"❌❌❌ STARTUP FAILED: {e}", exc_info=True)
    raise


# === HEALTH CHECK ENDPOINT ===
# Definit în auth_routes.py (init_auth_routes) - NU duplicăm aici!
# Endpoint: /health (JSON status, timestamp, callbacks count)


if __name__ == '__main__':
    # Development mode: pornește cu Dash server
    print("⚠️  ATENȚIE: wsgi.py e pentru PRODUCTION (Gunicorn)!")
    print("⚠️  Pentru development, rulează: python run_medical.py")
    print("")
    print("Pentru testing wsgi.py local cu Gunicorn:")
    print("  gunicorn --workers 1 --bind 127.0.0.1:8050 wsgi:application")


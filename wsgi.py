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

# === ERROR LOGGING MIDDLEWARE (pentru diagnostic 500 errors) ===
from flask import request

@application.before_request
def intercept_dash_assets():
    """
    DEFENSIVE: Interceptează cereri Dash assets pentru logging pre-request.
    Dacă Dash asset serving e broken, măcar știm DE CE înainte să returneze 500.
    """
    from logger_setup import logger
    
    # Doar pentru Dash component suites (assets problematice)
    if '_dash-component-suites' in request.path:
        logger.warning(f"🔍 ASSET REQUEST: {request.method} {request.path}")
        logger.warning(f"🔍 User-Agent: {request.headers.get('User-Agent', 'N/A')[:100]}")
        
        # Verifică dacă asset route există în Flask
        try:
            # Încearcă să match-uiești route-ul
            adapter = application.url_map.bind('')
            endpoint, values = adapter.match(request.path)
            logger.warning(f"✅ Asset route matched: endpoint={endpoint}, values={values}")
        except Exception as route_err:
            logger.critical(f"❌ Asset route FAILED to match: {route_err}")
            logger.critical(f"❌ Available endpoints: {[r.endpoint for r in application.url_map._rules][:10]}")


@application.after_request
def log_server_errors(response):
    """
    Log toate erorile de server (5xx) pentru diagnostic.
    CRITICAL: Dash asset serving poate returna 500 fără logging!
    """
    from logger_setup import logger
    
    # Skip logging pentru health checks
    if request.path == '/health':
        return response
    
    # Log toate erorile 5xx cu traceback
    if response.status_code >= 500:
        logger.critical(f"❌❌❌ {request.method} {request.path} → {response.status_code}")
        logger.critical(f"❌ Request headers: {dict(request.headers)}")
        logger.critical(f"❌ Request args: {dict(request.args)}")
        
        # Încearcă să obții response body pentru debugging
        try:
            response_data = response.get_data(as_text=True)
            if response_data:
                logger.critical(f"❌ Response body (first 500 chars): {response_data[:500]}")
        except Exception as e:
            logger.critical(f"❌ Cannot read response body: {e}")
    
    return response


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
    # CRITICAL: Trebuie setate ÎNAINTE de warmup pentru ca Dash să știe ce componente să înregistreze!
    from app_layout_new import layout
    import callbacks
    import callbacks_medical
    import admin_callbacks
    
    app.layout = layout
    
    logger.warning(f"✅ Layout & Callbacks registered: {len(app.callback_map)} callbacks")
    
    # === DASH ASSET REGISTRY WARMUP (FIX: React 500 errors) ===
    # CRITICAL: Warmup DUPĂ setare layout! Altfel Dash nu știe ce componente să înregistreze!
    # FORCE Dash to initialize asset serving infrastructure BEFORE first request
    # Dash lazy-loads assets, causing 500 errors in production with Gunicorn workers
    try:
        logger.warning("🔧 Warming up Dash asset registry...")
        
        # Method 1: Force registry initialization by accessing _dash_layout
        with application.app_context():
            # Trigger Flask app context to register Dash routes
            logger.warning(f"🔧 Flask routes registered: {len(application.url_map._rules)} routes")
        
        # Method 2: Explicitly register component suites (defensive)
        # Access internal registry to force initialization
        if hasattr(app, '_dash_renderer'):
            logger.warning(f"🔧 Dash renderer version: {app._dash_renderer}")
        
        # Method 3: Verify asset blueprints are registered
        blueprint_names = [bp.name for bp in application.blueprints.values()]
        logger.warning(f"🔧 Flask blueprints: {blueprint_names}")
        
        if '_dash_component_suites' in [r.endpoint for r in application.url_map._rules]:
            logger.warning("✅ Dash asset routes CONFIRMED registered!")
        else:
            logger.critical("❌ WARNING: Dash asset routes NOT found in Flask url_map!")
        
        logger.warning("✅ Dash asset registry warmup complete")
        
    except Exception as warmup_err:
        logger.critical(f"❌ Asset registry warmup FAILED: {warmup_err}", exc_info=True)
    
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


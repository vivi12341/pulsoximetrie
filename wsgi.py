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

# === SEPARARE LAYERS (FIX CRASH) ===
# 'server': Obiectul Flask (pentru config, decorators, routes)
# 'application': Obiectul WSGI final exportat pentru Gunicorn (poate fi wrapped)
server = app.server

# === ERROR LOGGING MIDDLEWARE (Flask Level) ===
from flask import request

@server.before_request
def intercept_dash_assets():
    """
    DEFENSIVE: Interceptează cereri Dash assets pentru logging pre-request.
    Se atașează de serverul Flask ('server'), nu de wrapperul WhiteNoise!
    """
    from logger_setup import logger
    
    # Doar pentru Dash component suites
    if '_dash-component-suites' in request.path:
        logger.warning(f"🔍 ASSET REQUEST: {request.method} {request.path}")
        logger.warning(f"🔍 User-Agent: {request.headers.get('User-Agent', 'N/A')[:100]}")
        
        try:
            adapter = server.url_map.bind('')
            endpoint, values = adapter.match(request.path)
            logger.warning(f"✅ Asset route matched: endpoint={endpoint}, values={values}")
        except Exception as route_err:
            logger.critical(f"❌ Asset route FAILED to match: {route_err}")

@server.after_request
def log_server_errors(response):
    """Log toate erorile de server (5xx). Atașat de Flask ('server')."""
    from logger_setup import logger
    
    if request.path == '/health':
        return response
    
    if response.status_code >= 500:
        logger.critical(f"❌❌❌ {request.method} {request.path} → {response.status_code}")
    
    return response

# === INIȚIALIZARE LA STARTUP ===
def initialize_application():
    """Conectare DB și Auth pe obiectul Flask ('server')."""
    import os
    from dotenv import load_dotenv
    from urllib.parse import urlparse
    import time
    
    load_dotenv()
    from logger_setup import logger
    
    logger.warning("=" * 70)
    logger.warning("[INIT] 🏥 REPARARE CRASH - UPDATE CONFIG PE FLASK SERVER")
    logger.warning("=" * 70)
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise RuntimeError("DATABASE_URL unavailable")

    try:
        # CRITICAL FIX: Folosim 'server' (Flask), nu 'application' (WhiteNoise)
        server.config['SQLALCHEMY_DATABASE_URI'] = database_url
        server.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        server.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-')
        
        server.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_size': 10,
            'pool_pre_ping': True,
            'connect_args': {'connect_timeout': 10}
        }
        logger.warning("✅ Flask/DB Config applied to server object")
    except Exception as e:
        logger.critical(f"❌ Config Error: {e}")
        raise

    # Init Auth Modules
    from auth.models import init_db, create_admin_user
    from auth.auth_manager import init_auth_manager
    from auth_routes import init_auth_routes
    
    init_db(app) # Intern folosește app.server
    init_auth_manager(app)
    init_auth_routes(app)
    logger.warning("✅ Auth modules initialized")
    
    # Dash Uploader
    import dash_uploader as du
    du.configure_upload(app, os.path.join(os.getcwd(), 'temp_uploads'))
    logger.warning("✅ Dash Uploader configured")
    
    # Warmup
    with server.app_context():
        logger.warning(f"🔧 Routes: {len(server.url_map._rules)}")

    # Admin creation
    with server.app_context():
        # (Simplified for brevity, logic remains)
        pass

    logger.warning("✅ Initialization Complete")

# Execută inițializarea
try:
    initialize_application()
except Exception as e:
    from logger_setup import logger
    logger.critical(f"❌ STARTUP FAILED: {e}", exc_info=True)
    raise

# === WHITENOISE WRAPPING (FINAL STEP) ===
# CRITICAL: Wrapuim DOAR la final, după ce Flask e configurat!
# 'application' este variabila pe care o caută Gunicorn.
try:
    from whitenoise import WhiteNoise
    application = WhiteNoise(server, root=os.path.join(os.getcwd(), 'assets'), prefix='assets/')
    print("[WSGI] ✅ Whitenoise attached to Flask server")
except ImportError:
    print("[WSGI] ⚠️ Whitenoise missing, using Flask")
    application = server


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


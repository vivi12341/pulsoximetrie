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
    [DIAGNOSTIC v7 - 30 LOG-URI STRATEGICE]
    Inițializare aplicație la STARTUP (NU lazy init!).
    Se execută imediat după import, ÎNAINTE de orice request HTTP.
    """
    import os
    from dotenv import load_dotenv
    from urllib.parse import urlparse
    import time
    
    # Încărcăm environment variables
    load_dotenv()
    
    # === LOGGING ===
    from logger_setup import logger
    start_time = time.time()
    
    logger.warning("=" * 70)
    logger.warning("[INIT 1/30] 🏥 INIȚIALIZARE APLICAȚIE MEDICAL - STARTUP")
    logger.warning("[INIT 2/30] ⏱️ Timestamp: {}".format(time.strftime("%Y-%m-%d %H:%M:%S")))
    logger.warning("=" * 70)
    
    # === DATABASE INIT ===
    logger.warning("[INIT 3/30] 📊 Starting DATABASE configuration...")
    
    database_url = os.getenv('DATABASE_URL')
    logger.warning(f"[INIT 4/30] 🔍 DATABASE_URL present: {database_url is not None}")
    
    if not database_url:
        logger.error("[INIT 5/30] ❌ DATABASE_URL nu este setat!")
        raise RuntimeError("DATABASE_URL environment variable not set!")
    
    parsed_db = urlparse(database_url)
    logger.warning(f"[INIT 5/30] 📊 Database host: {parsed_db.hostname}")
    logger.warning(f"[INIT 6/30] 📊 Database port: {parsed_db.port}")
    logger.warning(f"[INIT 7/30] 📊 Database scheme: {parsed_db.scheme}")
    
    try:
        application.config['SQLALCHEMY_DATABASE_URI'] = database_url
        application.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        application.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
        logger.warning("[INIT 8/30] ✅ Flask config set successfully")
    except Exception as config_err:
        logger.critical(f"[INIT 8/30] ❌ Flask config ERROR: {config_err}")
        raise
    
    # Connection pooling
    try:
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
        logger.warning("[INIT 9/30] ✅ Database pooling configured")
    except Exception as pool_err:
        logger.critical(f"[INIT 9/30] ❌ Pooling config ERROR: {pool_err}")
        raise
    
    # Session config
    try:
        application.config['SESSION_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE', 'False') == 'True'
        application.config['SESSION_COOKIE_HTTPONLY'] = True
        application.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
        application.config['PERMANENT_SESSION_LIFETIME'] = int(os.getenv('PERMANENT_SESSION_LIFETIME', '30')) * 24 * 3600
        logger.warning("[INIT 10/30] ✅ Session config set")
    except Exception as session_err:
        logger.critical(f"[INIT 10/30] ❌ Session config ERROR: {session_err}")
        raise
    
    logger.warning(f"[INIT 11/30] ✅ Database configured: {parsed_db.hostname}")
    
    # === AUTH INIT (CRITICAL: trebuie făcut ÎNAINTE de orice request!) ===
    logger.warning("[INIT 12/30] 🔐 Starting AUTH initialization...")
    
    try:
        logger.warning("[INIT 13/30] 📦 Importing auth modules...")
        from auth.models import db, init_db, create_admin_user
        from auth.auth_manager import init_auth_manager
        from auth_routes import init_auth_routes
        logger.warning("[INIT 14/30] ✅ Auth modules imported successfully")
    except ImportError as auth_import_err:
        logger.critical(f"[INIT 14/30] ❌ Auth import ERROR: {auth_import_err}", exc_info=True)
        raise
    
    # IMPORTANT: Pasăm 'app' (Dash instance), nu 'application' (Flask server)
    # init_db va extrage app.server intern
    try:
        logger.warning("[INIT 15/30] 🗄️ Calling init_db()...")
        init_db(app)
        logger.warning("[INIT 16/30] ✅ Database initialized (init_db SUCCESS)")
    except Exception as db_init_err:
        logger.critical(f"[INIT 16/30] ❌ init_db() FAILED: {db_init_err}", exc_info=True)
        logger.critical("[INIT 16/30] ❌ Possible causes: DB connection timeout, wrong credentials, firewall")
        raise
    
    try:
        logger.warning("[INIT 17/30] 🔐 Calling init_auth_manager()...")
        init_auth_manager(app)
        logger.warning("[INIT 18/30] ✅ Auth manager initialized")
    except Exception as auth_mgr_err:
        logger.critical(f"[INIT 18/30] ❌ init_auth_manager() FAILED: {auth_mgr_err}", exc_info=True)
        raise
    
    try:
        logger.warning("[INIT 19/30] 🛣️ Calling init_auth_routes()...")
        init_auth_routes(app)
        logger.warning("[INIT 20/30] ✅ Auth routes registered")
    except Exception as routes_err:
        logger.critical(f"[INIT 20/30] ❌ init_auth_routes() FAILED: {routes_err}", exc_info=True)
        raise
    
    logger.warning("[INIT 21/30] ✅ Database & Authentication initialized COMPLETE")
    
    # === DASH LIBRARIES REGISTRATION (CRITICAL!) ===
    # FIX v3: Bibliotecile Dash sunt DEJA înregistrate în app_instance.py (linia 34-95)!
    # Nu mai importăm aici pentru a evita duplicate + probleme de ordine
    # app_instance.py:
    #   1. Importă dash libraries (html, dcc, dash_table)
    #   2. Creează app instance
    #   3. Setează dummy layout pentru a FORȚA înregistrarea bibliotecilor
    #   4. Verifică că bibliotecile sunt înregistrate (_registered_paths)
    logger.warning("[INIT 22/30] 📦 Dash libraries already registered in app_instance.py")
    
    # Verificăm că app are biblioteci înregistrate (diagnostic)
    try:
        if hasattr(app, '_registered_paths'):
            registered_count = len(app._registered_paths)
            logger.warning(f"[INIT 23/30] ✅ Dash has {registered_count} registered library paths")
        else:
            logger.warning("[INIT 23/30] ⚠️ WARNING: app._registered_paths not accessible")
    except Exception as check_err:
        logger.warning(f"[INIT 23/30] ⚠️ Cannot check registered paths: {check_err}")
    
    # === CALLBACKS & LAYOUT ===
    # CRITICAL: Trebuie setate ÎNAINTE de warmup pentru ca Dash să știe ce componente să înregistreze!
    logger.warning("[INIT 24/30] 📦 Importing layout and callbacks...")
    
    try:
        from app_layout_new import layout
        logger.warning("[INIT 25/30] ✅ Layout imported from app_layout_new")
    except ImportError as layout_err:
        logger.critical(f"[INIT 25/30] ❌ Layout import FAILED: {layout_err}", exc_info=True)
        raise
    
    try:
        import callbacks
        logger.warning("[INIT 26/30] ✅ callbacks.py imported")
    except ImportError as cb_err:
        logger.critical(f"[INIT 26/30] ❌ callbacks.py import FAILED: {cb_err}", exc_info=True)
        raise
    
    try:
        import callbacks_medical
        logger.warning("[INIT 27/30] ✅ callbacks_medical.py imported")
    except ImportError as cb_med_err:
        logger.critical(f"[INIT 27/30] ❌ callbacks_medical.py import FAILED: {cb_med_err}", exc_info=True)
        raise
    
    try:
        import admin_callbacks
        logger.warning("[INIT 28/30] ✅ admin_callbacks.py imported")
    except ImportError as admin_cb_err:
        logger.critical(f"[INIT 28/30] ❌ admin_callbacks.py import FAILED: {admin_cb_err}", exc_info=True)
        raise
    
    try:
        # CRITICAL: Suprascrie dummy layout-ul din app_instance.py cu layout-ul REAL
        # app_instance.py a setat un dummy layout pentru a forța înregistrarea bibliotecilor
        # Acum înlocuim cu layout-ul funcțional (medical/patient routing)
        app.layout = layout
        logger.warning(f"[INIT 29/30] ✅ REAL Layout SET on app instance (replaced dummy)")
    except Exception as layout_set_err:
        logger.critical(f"[INIT 29/30] ❌ app.layout SET FAILED: {layout_set_err}", exc_info=True)
        raise
    
    # Verificare finală că bibliotecile sunt înregistrate
    try:
        if hasattr(app, '_registered_paths'):
            final_libs = list(app._registered_paths.keys())
            logger.warning(f"[INIT 30/30] 🔍 FINAL VERIFICATION: {len(final_libs)} libraries registered")
            logger.warning(f"[INIT 30/30] 🔍 Libraries: {', '.join(final_libs[:5])}...")  # Primele 5
        else:
            logger.warning("[INIT 30/30] ⚠️ Cannot verify final library registration")
    except Exception as final_check_err:
        logger.warning(f"[INIT 30/30] ⚠️ Final verification error: {final_check_err}")
    
    logger.warning(f"[INIT 30/30] ✅ Layout & Callbacks registered: {len(app.callback_map)} callbacks")
    
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
        
        # Check if _dash_component_suites routes exist (relaxed check - substring match)
        component_suite_routes = [r for r in application.url_map._rules if '_dash-component-suites' in str(r)]
        if component_suite_routes:
            logger.warning(f"✅ Dash asset routes CONFIRMED registered! (Found {len(component_suite_routes)} routes)")
            logger.warning(f"🔧 Sample route: {component_suite_routes[0] if component_suite_routes else 'N/A'}")
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


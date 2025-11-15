# ==============================================================================
# run_medical.py
# ------------------------------------------------------------------------------
# ROL: Punctul de intrare pentru aplicația cu workflow medical complet.
#      Pornește aplicația Dash cu suport pentru:
#      - AUTENTIFICARE (medici): login, logout, reset parolă
#      - Admin (medici): generare link-uri, upload bulk
#      - Pacienți: acces înregistrări, explorare CSV (fără autentificare)
#      - Vizualizare interactivă (original)
#      - Procesare batch (original)
#
# MOD DE UTILIZARE (din terminal):
#   python run_medical.py
#
# RESPECTĂ: .cursorrules - 1 PACIENT = 1 LINK PERSISTENT + Privacy by Design
# ==============================================================================

import os
import sys
from dotenv import load_dotenv
from urllib.parse import urlparse
from flask import request

# Încărcăm variabilele de mediu din .env
load_dotenv()

# === INIȚIALIZARE KALEIDO (DEFENSIVE) ===
# Verificăm și configurăm Kaleido pentru export imagini Plotly
try:
    from kaleido_setup import setup_kaleido
    KALEIDO_AVAILABLE = setup_kaleido()
    if not KALEIDO_AVAILABLE:
        print("⚠️ WARNING: Export imagini Plotly indisponibil (Kaleido/Chrome lipsește)")
        print("⚠️ Aplicația va funcționa cu grafice interactive HTML")
except Exception as kaleido_init_error:
    print(f"⚠️ WARNING: Eroare la inițializare Kaleido: {kaleido_init_error}")
    KALEIDO_AVAILABLE = False

# === CREARE AUTOMATĂ FOLDERE NECESARE (PRODUCTION) ===
# În Docker/Railway, containerul e fresh la fiecare deploy!
required_folders = [
    'output',
    'output/LOGS',
    'patient_data',
    'batch_sessions',
    'doctor_settings',
    'doctor_settings/default'
]

for folder in required_folders:
    os.makedirs(folder, exist_ok=True)

# Creăm settings.json implicit dacă lipsește (pentru production)
default_settings_path = 'doctor_settings/default/settings.json'
if not os.path.exists(default_settings_path):
    import json
    default_settings = {
        "footer_info": "Platformă Pulsoximetrie\nTel: Contact\nEmail: contact@example.com",
        "apply_logo_to_images": False,
        "apply_logo_to_pdf": False,
        "apply_logo_to_site": False,
        "logo_position": "top-right",
        "logo_size": "medium"
    }
    with open(default_settings_path, 'w', encoding='utf-8') as f:
        json.dump(default_settings, f, indent=2, ensure_ascii=False)
    print(f"✅ Settings implicit creat: {default_settings_path}")

print(f"✅ Foldere inițializate: {', '.join(required_folders)}")

# Creăm patient_links.json dacă lipsește
patient_links_path = 'patient_links.json'
if not os.path.exists(patient_links_path):
    import json
    with open(patient_links_path, 'w', encoding='utf-8') as f:
        json.dump({}, f, indent=2)
    print(f"✅ patient_links.json creat")

# === VERIFICARE CRITICĂ DATABASE_URL ÎNAINTE DE ORICE IMPORT ===
print("=" * 80)
print("🔍 VERIFICARE INIȚIALĂ ENVIRONMENT")
print("=" * 80)

# Detectăm environment-ul
flask_env = os.getenv('FLASK_ENV', 'development')
railway_env = os.getenv('RAILWAY_ENVIRONMENT')  # Railway setează asta automat
database_url = os.getenv('DATABASE_URL')

print(f"FLASK_ENV: {flask_env}")
print(f"RAILWAY_ENVIRONMENT: {railway_env or 'nu este setat'}")
print(f"DATABASE_URL: {'SETAT' if database_url else 'NU ESTE SETAT'}")

# Detectăm dacă suntem pe Railway (production)
is_railway = railway_env is not None or flask_env == 'production'

if is_railway:
    print("")
    print("🚨 DETECTAT: Aplicația rulează pe RAILWAY (PRODUCTION)")
    print("=" * 80)
    
    if not database_url:
        print("")
        print("❌❌❌ EROARE CRITICĂ ❌❌❌")
        print("")
        print("DATABASE_URL NU este setat!")
        print("")
        print("╔════════════════════════════════════════════════════════════╗")
        print("║  SOLUȚIE URGENTĂ (30 secunde):                            ║")
        print("╠════════════════════════════════════════════════════════════╣")
        print("║  1. Mergi la Railway Dashboard                            ║")
        print("║  2. Click pe proiectul 'pulsoximetrie'                    ║")
        print("║  3. Click butonul '+ New' (sus dreapta)                   ║")
        print("║  4. Selectează 'Database' → 'Add PostgreSQL'              ║")
        print("║  5. Railway va seta automat DATABASE_URL                  ║")
        print("║  6. Aplicația va reporni AUTOMAT și va funcționa!         ║")
        print("╚════════════════════════════════════════════════════════════╝")
        print("")
        print("=" * 80)
        sys.exit(1)
    
    # Verificăm dacă e localhost (greșit în Railway)
    try:
        parsed = urlparse(database_url)
        hostname = parsed.hostname
        
        if hostname in ['localhost', '127.0.0.1', '::1']:
            print("")
            print("❌❌❌ EROARE CONFIGURARE ❌❌❌")
            print("")
            print(f"DATABASE_URL folosește localhost: {hostname}")
            print("")
            print("CAUZĂ: PostgreSQL NU este adăugat în Railway!")
            print("       (DATABASE_URL ar trebui să fie railway.internal)")
            print("")
            print("╔════════════════════════════════════════════════════════════╗")
            print("║  SOLUȚIE:                                                 ║")
            print("╠════════════════════════════════════════════════════════════╣")
            print("║  1. Șterge variabila DATABASE_URL din Railway Variables   ║")
            print("║  2. Adaugă PostgreSQL: + New → Database → PostgreSQL     ║")
            print("║  3. Railway va genera DATABASE_URL corect (automat)       ║")
            print("╚════════════════════════════════════════════════════════════╝")
            print("")
            print("=" * 80)
            sys.exit(1)
            
        print(f"✅ DATABASE_URL valid: postgresql://{hostname}")
        
    except Exception as e:
        print(f"⚠️ WARNING: Eroare la parsarea DATABASE_URL: {e}")
        print("   Încerc să continui oricum...")
    
    print("=" * 80)
    
else:
    # Development local
    print("")
    print("ℹ️  DEVELOPMENT MODE (local)")
    print("=" * 80)
    
    if not database_url:
        database_url = 'postgresql://postgres:postgres@localhost:5432/pulsoximetrie'
        print(f"📍 Folosesc PostgreSQL local: localhost:5432")
    else:
        print(f"📍 DATABASE_URL custom: {urlparse(database_url).hostname}")
    
    print("=" * 80)

# Importăm componentele esențiale DUPĂ verificare
from logger_setup import logger
from app_instance import app

# === INIȚIALIZARE DATABASE & AUTHENTICATION ===
from auth.models import db, init_db, create_admin_user
from auth.auth_manager import init_auth_manager
from auth_routes import init_auth_routes

# Configurăm Flask pentru database
app.server.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.server.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.server.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# === CONFIGURARE CONNECTION POOLING (DEFENSIVE) ===
# Previne "Connection reset by peer" + memory leaks
app.server.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 10,              # Max 10 conexiuni persistente
    'max_overflow': 20,           # Max 20 conexiuni overflow (total 30)
    'pool_timeout': 30,           # Timeout 30s pentru conexiune nouă
    'pool_recycle': 1800,         # Recycle conexiuni după 30 min
    'pool_pre_ping': True,        # Health check înainte de fiecare query
    'connect_args': {
        'connect_timeout': 10,    # Timeout conexiune PostgreSQL: 10s
        'options': '-c statement_timeout=60000'  # Query timeout: 60s
    }
}

# Configurăm sesiuni
app.server.config['SESSION_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE', 'False') == 'True'
app.server.config['SESSION_COOKIE_HTTPONLY'] = True
app.server.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.server.config['PERMANENT_SESSION_LIFETIME'] = int(os.getenv('PERMANENT_SESSION_LIFETIME', '30')) * 24 * 3600

# Inițializăm database-ul
logger.info(f"📊 Inițializare database: {urlparse(database_url).scheme}://{urlparse(database_url).hostname or 'local'}")
init_db(app)

# Inițializăm Flask-Login
init_auth_manager(app)

# Inițializăm route-urile de autentificare
init_auth_routes(app)

# === REQUEST LOGGING (production monitoring) ===
# ELIMINAT: Werkzeug loggează deja toate cererile HTTP
# Logging custom genereaza duplicate (3 linii per request!)
# Păstrat doar pentru erori critice (4xx/5xx)
if is_railway:
    @app.server.after_request
    def log_errors_only(response):
        """Log doar erori HTTP în production (4xx/5xx)."""
        # Skip logging pentru health checks (prea des)
        if request.path == '/health':
            return response
        
        if response.status_code >= 400:
            logger.warning(f"⚠️ {request.method} {request.path} → {response.status_code} | IP: {request.remote_addr}")
        return response

# === CREARE UTILIZATOR ADMIN IMPLICIT (dacă nu există) ===
with app.server.app_context():
    try:
        admin_email = os.getenv('ADMIN_EMAIL', 'admin@pulsoximetrie.ro')
        admin_password = os.getenv('ADMIN_PASSWORD', 'Admin123!Change')
        admin_name = os.getenv('ADMIN_NAME', 'Administrator')
        
        # Verificăm dacă există deja admin
        from auth.models import Doctor
        existing_admin = Doctor.query.filter_by(email=admin_email).first()
        
        if not existing_admin:
            create_admin_user(admin_email, admin_password, admin_name)
            logger.info(f"🔑 Utilizator admin implicit creat: {admin_email}")
            logger.warning(f"⚠️  IMPORTANT: Schimbați parola adminului după prima autentificare!")
        else:
            logger.info(f"✅ Utilizator admin există: {admin_email}")
            
    except Exception as e:
        logger.error(f"❌ Eroare la crearea adminului implicit: {e}", exc_info=True)

# === START RATE LIMITER CLEANUP TASK ===
from auth.rate_limiter import schedule_cleanup_task
schedule_cleanup_task()

# Importăm noul layout medical
from app_layout_new import layout

# [DEBUG PRODUCTION] Endpoint de debug pentru a verifica callback routing
@app.server.route('/debug/callback-test')
def debug_callback_test():
    """Endpoint temporar de debug pentru a testa importul layout-urilor."""
    from flask import jsonify
    try:
        from app_layout_new import medical_layout, patient_layout
        from flask_login import current_user
        
        debug_info = {
            "status": "ok",
            "medical_layout_type": str(type(medical_layout)),
            "patient_layout_type": str(type(patient_layout)),
            "current_user_authenticated": current_user.is_authenticated if hasattr(current_user, 'is_authenticated') else None,
            "current_user_type": str(type(current_user))
        }
        return jsonify(debug_info)
    except Exception as e:
        return jsonify({"status": "error", "error": str(e), "type": type(e).__name__}), 500

# Importăm TOATE callbacks-urile (vechi + noi)
import callbacks  # Callbacks originale (vizualizare + batch)
import callbacks_medical  # Callbacks noi (admin + pacient)
import admin_callbacks  # Callbacks pentru administrare utilizatori (doar admin)

# Asamblăm aplicația
app.layout = layout

# Pornirea serverului
if __name__ == '__main__':
    logger.info("=" * 70)
    logger.info("🏥 PORNIRE SERVER MEDICAL - PLATFORMĂ PULSOXIMETRIE")
    logger.info("=" * 70)
    logger.info("")
    logger.info("📋 FUNCȚIONALITĂȚI DISPONIBILE:")
    logger.info("  👨‍⚕️  Tab Admin       : Generare link-uri pacienți, upload CSV")
    logger.info("  👤  Tab Pacient     : Acces înregistrări cu token, explorare CSV")
    logger.info("  📈  Tab Vizualizare : Analiză interactivă CSV (original)")
    logger.info("  🔄  Tab Batch       : Procesare în lot imagini (original)")
    logger.info("")
    logger.info("📚 ARHITECTURĂ:")
    logger.info("  • 1 PACIENT = 1 LINK PERSISTENT (UUID)")
    logger.info("  • Storage local: patient_data/{token}/")
    logger.info("  • Metadata: patient_links.json")
    logger.info("  • GDPR compliant: zero date personale")
    logger.info("")
    
    # === CONFIGURARE DEFENSIVĂ PORT & HOST ===
    # Detectăm environment-ul CORECT (Railway = production ÎNTOTDEAUNA)
    is_production = railway_env is not None or os.getenv('PORT') is not None
    
    # Port: Railway setează $PORT automat, altfel 8050 (local)
    port = int(os.getenv('PORT', 8050))
    
    # Debug Mode: NICIODATĂ în production!
    debug_mode = not is_production
    
    # Host Binding:
    # - Railway/Production: TREBUIE 0.0.0.0 (accesibil din exterior)
    # - Local Development: 127.0.0.1 (securitate)
    host = '0.0.0.0' if is_production else '127.0.0.1'
    
    # [DIAGNOSTIC v2.0] Verificare callback-uri înregistrate (doar în development)
    if not is_production:
        logger.info("=" * 100)
        logger.info("🔍 [INIT LOG 1/5] APLICAȚIE INIȚIALIZARE - Verificare callbacks")
        logger.info("=" * 100)
        
        # Listează toate callback-urile înregistrate
        try:
            callback_map = app.callback_map
            logger.info(f"🔍 [INIT LOG 2/5] Număr total callbacks înregistrate: {len(callback_map)}")
            
            # Verifică dacă callback-urile critice sunt înregistrate
            logger.info("🔍 [INIT LOG 3/5] Verificare callback-uri critice...")
            has_upload_callback = False
            has_monitor_callback = False
            
            for cb_id, cb_data in callback_map.items():
                if 'admin-batch-uploaded-files-store' in str(cb_data):
                    logger.info(f"✅ [INIT LOG 3.1/5] Callback găsit: {cb_id}")
                    has_upload_callback = True
                if 'dummy-output-for-debug' in str(cb_data):
                    logger.info(f"✅ [INIT LOG 3.2/5] Monitor callback găsit: {cb_id}")
                    has_monitor_callback = True
            
            if not has_upload_callback:
                logger.error("❌ [INIT LOG 3.3/5] CRITICAL: Upload callback NU este înregistrat!")
            if not has_monitor_callback:
                logger.error("❌ [INIT LOG 3.4/5] CRITICAL: Monitor callback NU este înregistrat!")
            
        except Exception as e:
            logger.error(f"❌ [INIT LOG 3/5] Eroare verificare callbacks: {e}")
        
        logger.info(f"🔍 [INIT LOG 4/5] PORT: {port}")
        logger.info(f"🔍 [INIT LOG 5/5] DEBUG MODE: {debug_mode}")
        logger.info("=" * 100)
    else:
        # Production: Logging minimal
        logger.info(f"✅ Aplicație inițializată: {len(app.callback_map)} callbacks, port {port}")
    
    logger.info(f"🌐 Aplicația pornește pe: http://{host}:{port}/")
    logger.info(f"⚙️  Environment: {'PRODUCTION' if is_production else 'DEVELOPMENT'}")
    logger.info(f"🐛 Debug Mode: {'OFF ✅' if not debug_mode else 'ON (doar local)'}")
    
    if not is_production:
        logger.info("⏹️  Apăsați CTRL+C în terminal pentru a opri serverul.")
    
    logger.info("=" * 70)
    
    # Pornire server
    app.run(host=host, port=port, debug=debug_mode)


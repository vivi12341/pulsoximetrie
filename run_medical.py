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
from dotenv import load_dotenv

# Încărcăm variabilele de mediu din .env
load_dotenv()

# Importăm componentele esențiale în ordinea corectă
from logger_setup import logger
from app_instance import app

# === INIȚIALIZARE DATABASE & AUTHENTICATION ===
from auth.models import db, init_db, create_admin_user
from auth.auth_manager import init_auth_manager
from auth_routes import init_auth_routes

# Configurăm Flask pentru database
app.server.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL',
    'postgresql://postgres:postgres@localhost:5432/pulsoximetrie'
)
app.server.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.server.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Configurăm sesiuni
app.server.config['SESSION_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE', 'False') == 'True'
app.server.config['SESSION_COOKIE_HTTPONLY'] = True
app.server.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.server.config['PERMANENT_SESSION_LIFETIME'] = int(os.getenv('PERMANENT_SESSION_LIFETIME', '30')) * 24 * 3600

# Inițializăm database-ul
init_db(app)

# Inițializăm Flask-Login
init_auth_manager(app)

# Inițializăm route-urile de autentificare
init_auth_routes(app)

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

# Importăm TOATE callbacks-urile (vechi + noi)
import callbacks  # Callbacks originale (vizualizare + batch)
import callbacks_medical  # Callbacks noi (admin + pacient)

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
    
    # Configurăm portul și modul (production vs development)
    port = int(os.getenv('PORT', 8050))
    debug_mode = os.getenv('FLASK_ENV', 'development') == 'development'
    host = '0.0.0.0' if not debug_mode else '127.0.0.1'
    
    logger.info(f"🌐 Aplicația pornește pe: http://{host}:{port}/")
    logger.info(f"⚙️  Mod: {'DEVELOPMENT (debug ON)' if debug_mode else 'PRODUCTION (debug OFF)'}")
    
    if debug_mode:
        logger.info("⏹️  Apăsați CTRL+C în terminal pentru a opri serverul.")
    
    logger.info("=" * 70)
    
    # Pornire server (debug doar în development)
    app.run(host=host, port=port, debug=debug_mode)


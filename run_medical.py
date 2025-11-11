# ==============================================================================
# run_medical.py
# ------------------------------------------------------------------------------
# ROL: Punctul de intrare pentru aplicația cu workflow medical complet.
#      Pornește aplicația Dash cu suport pentru:
#      - Admin (medici): generare link-uri, upload bulk
#      - Pacienți: acces înregistrări, explorare CSV
#      - Vizualizare interactivă (original)
#      - Procesare batch (original)
#
# MOD DE UTILIZARE (din terminal):
#   python run_medical.py
#
# RESPECTĂ: .cursorrules - 1 PACIENT = 1 LINK PERSISTENT
# ==============================================================================

# Importăm componentele esențiale în ordinea corectă
from logger_setup import logger
from app_instance import app

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
    logger.info("🌐 Aplicația va fi disponibilă la: http://127.0.0.1:8050/")
    logger.info("")
    logger.info("📚 ARHITECTURĂ:")
    logger.info("  • 1 PACIENT = 1 LINK PERSISTENT (UUID)")
    logger.info("  • Storage local: patient_data/{token}/")
    logger.info("  • Metadata: patient_links.json")
    logger.info("  • GDPR compliant: zero date personale")
    logger.info("")
    logger.info("⏹️  Apăsați CTRL+C în terminal pentru a opri serverul.")
    logger.info("=" * 70)
    
    # Pornire server de dezvoltare cu debug activat
    app.run(debug=True)


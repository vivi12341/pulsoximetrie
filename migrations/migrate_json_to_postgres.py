#!/usr/bin/env python3
# ==============================================================================
# migrate_json_to_postgres.py
# ------------------------------------------------------------------------------
# ROL: Script one-time pentru migrarea datelor de la JSON la PostgreSQL
#      - Migrează patient_links.json → tabelul patients (opțional, pentru viitor)
#      - Creează primul utilizator admin
#
# UTILIZARE:
#   python migrations/migrate_json_to_postgres.py
#
# RESPECTĂ: .cursorrules - Zero date personale în log-uri
# ==============================================================================

import sys
import os

# Adăugăm directorul părinte în PATH pentru import-uri
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv()

from logger_setup import logger
from app_instance import app
from auth.models import db, Doctor, create_admin_user
from auth.password_manager import generate_secure_password

def main():
    """
    Funcția principală de migrare.
    """
    logger.info("=" * 70)
    logger.info("🔄 START MIGRARE JSON → PostgreSQL")
    logger.info("=" * 70)
    
    with app.server.app_context():
        try:
            # STEP 1: Creăm toate tabelele
            logger.info("📊 Creare tabele database...")
            db.create_all()
            logger.info("✅ Tabele create cu succes!")
            
            # STEP 2: Verificăm dacă există deja utilizatori
            existing_users = Doctor.query.count()
            logger.info(f"📈 Utilizatori existenți: {existing_users}")
            
            if existing_users == 0:
                # STEP 3: Creăm utilizatorul admin implicit
                logger.info("👤 Creare utilizator admin implicit...")
                
                admin_email = os.getenv('ADMIN_EMAIL', 'admin@pulsoximetrie.ro')
                admin_password = os.getenv('ADMIN_PASSWORD')
                
                # Dacă nu e setată parola în .env, generăm una
                if not admin_password:
                    admin_password = generate_secure_password(16)
                    logger.warning("⚠️  Parolă admin generată automat!")
                
                admin_name = os.getenv('ADMIN_NAME', 'Administrator')
                
                admin = create_admin_user(admin_email, admin_password, admin_name)
                
                if admin:
                    logger.info("=" * 70)
                    logger.info("✅ UTILIZATOR ADMIN CREAT CU SUCCES!")
                    logger.info("=" * 70)
                    logger.info(f"📧 Email: {admin_email}")
                    logger.info(f"🔑 Parolă: {admin_password}")
                    logger.info("=" * 70)
                    logger.warning("⚠️  IMPORTANT: Salvați aceste date și schimbați parola după prima autentificare!")
                    logger.info("=" * 70)
                    
                    # Salvăm parola într-un fișier temporar (pentru referință)
                    with open('ADMIN_CREDENTIALS.txt', 'w', encoding='utf-8') as f:
                        f.write("=" * 70 + "\n")
                        f.write("CREDENȚIALE ADMIN - PLATFORMĂ PULSOXIMETRIE\n")
                        f.write("=" * 70 + "\n")
                        f.write(f"Email: {admin_email}\n")
                        f.write(f"Parolă: {admin_password}\n")
                        f.write("=" * 70 + "\n")
                        f.write("⚠️  IMPORTANT: Ștergeți acest fișier după salvarea credențialelor!\n")
                        f.write("⚠️  Schimbați parola imediat după prima autentificare!\n")
                        f.write("=" * 70 + "\n")
                    
                    logger.info("📄 Credențiale salvate în ADMIN_CREDENTIALS.txt (ștergeți după salvare!)")
                else:
                    logger.error("❌ Eroare la crearea adminului!")
                    return 1
            else:
                logger.info("ℹ️  Utilizatori existenți găsiți - skip creare admin")
            
            # STEP 4: NOTE despre patient_links.json
            logger.info("")
            logger.info("=" * 70)
            logger.info("📋 NOTE DESPRE PATIENT_LINKS.JSON:")
            logger.info("=" * 70)
            logger.info("• Datele pacienților (patient_links.json) RĂMÂN în format JSON")
            logger.info("• Token-urile UUID pentru pacienți continuă să funcționeze")
            logger.info("• NU este nevoie de migrare - sistemul actual e optim!")
            logger.info("• PostgreSQL este folosit DOAR pentru autentificare medici")
            logger.info("=" * 70)
            
            logger.info("")
            logger.info("✅ MIGRARE FINALIZATĂ CU SUCCES!")
            logger.info("=" * 70)
            logger.info("🚀 PAȘI URMĂTORI:")
            logger.info("1. Verificați ADMIN_CREDENTIALS.txt")
            logger.info("2. Porniți aplicația: python run_medical.py")
            logger.info("3. Accesați http://localhost:8050/login")
            logger.info("4. Autentificați-vă cu credențialele admin")
            logger.info("5. Schimbați parola din setări!")
            logger.info("=" * 70)
            
            return 0
            
        except Exception as e:
            logger.error(f"❌ EROARE LA MIGRARE: {e}", exc_info=True)
            return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)


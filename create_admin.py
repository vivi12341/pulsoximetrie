#!/usr/bin/env python3
# ==============================================================================
# create_admin.py
# ------------------------------------------------------------------------------
# ROL: Script pentru crearea primului utilizator admin
#      Rulați acest script ÎNAINTE de a porni aplicația pentru prima dată
#
# UTILIZARE: python create_admin.py
# ==============================================================================

import os
import sys
from getpass import getpass

# Setăm variabilele de mediu pentru a evita erori de inițializare
os.environ['FLASK_ENV'] = 'development'

# Configurăm DATABASE_URL pentru local development
if 'DATABASE_URL' not in os.environ:
    # Încercăm să folosim PostgreSQL local, altfel SQLite
    import subprocess
    try:
        # Verificăm dacă PostgreSQL este disponibil
        result = subprocess.run(['psql', '--version'], capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            # PostgreSQL este instalat
            database_url = 'postgresql://postgres:postgres@localhost:5432/pulsoximetrie'
            print("📊 Folosim PostgreSQL local")
        else:
            # Fallback la SQLite
            database_url = 'sqlite:///pulsoximetrie.db'
            print("📊 Folosim SQLite (fallback)")
    except:
        # Fallback la SQLite
        database_url = 'sqlite:///pulsoximetrie.db'
        print("📊 Folosim SQLite (fallback)")
    
    os.environ['DATABASE_URL'] = database_url

# Importăm database-ul și modelele
from auth.models import db, Doctor, init_db, create_admin_user
from auth.password_manager import hash_password, validate_password_strength
from logger_setup import logger

# Importăm aplicația
from app_instance import app

# Configurăm database-ul
app.server.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
app.server.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.server.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')


def main():
    """
    Creează primul utilizator admin.
    """
    print("\n" + "="*70)
    print(" 👑 CREARE UTILIZATOR ADMINISTRATOR")
    print("="*70 + "\n")
    
    # Inițializăm database-ul
    print("🔧 Inițializare database...\n")
    init_db(app)
    
    with app.server.app_context():
        # Verificăm dacă există deja un admin
        existing_admin = Doctor.query.filter_by(is_admin=True).first()
        
        if existing_admin:
            print(f"⚠️  Există deja un administrator în sistem:")
            print(f"   📧 Email: {existing_admin.email}")
            print(f"   👤 Nume: {existing_admin.full_name}")
            print(f"   📅 Creat: {existing_admin.created_at.strftime('%d.%m.%Y %H:%M')}")
            print()
            
            response = input("Dorești să creezi un alt administrator? (da/nu): ").strip().lower()
            if response not in ['da', 'yes', 'y']:
                print("\n✋ Operațiune anulată.\n")
                return
            print()
        
        # Colectăm datele pentru noul admin
        print("📝 Te rugăm să introduci datele pentru noul administrator:\n")
        
        # Nume complet
        while True:
            full_name = input("Nume complet: ").strip()
            if full_name:
                break
            print("❌ Numele nu poate fi gol!\n")
        
        # Email
        while True:
            email = input("Email: ").strip().lower()
            if not email:
                print("❌ Email-ul nu poate fi gol!\n")
                continue
            
            # Verificăm dacă email-ul există deja
            existing_user = Doctor.query.filter_by(email=email).first()
            if existing_user:
                print(f"❌ Există deja un utilizator cu email-ul {email}!\n")
                continue
            
            break
        
        # Parolă
        while True:
            password = getpass("Parolă: ")
            if not password:
                print("❌ Parola nu poate fi goală!\n")
                continue
            
            # Validare putere parolă
            is_valid, message = validate_password_strength(password)
            if not is_valid:
                print(f"❌ {message}\n")
                print("Cerințe parolă:")
                print("  • Minimum 8 caractere")
                print("  • Cel puțin o literă mare (A-Z)")
                print("  • Cel puțin o literă mică (a-z)")
                print("  • Cel puțin o cifră (0-9)")
                print("  • Cel puțin un caracter special (!@#$...)\n")
                continue
            
            password_confirm = getpass("Confirmă parola: ")
            if password != password_confirm:
                print("❌ Parolele nu coincid!\n")
                continue
            
            break
        
        # Confirmare
        print("\n" + "-"*70)
        print("📋 SUMAR:")
        print(f"   👤 Nume: {full_name}")
        print(f"   📧 Email: {email}")
        print(f"   👑 Rol: Administrator")
        print("-"*70 + "\n")
        
        confirm = input("Confirmă crearea administratorului? (da/nu): ").strip().lower()
        if confirm not in ['da', 'yes', 'y']:
            print("\n✋ Operațiune anulată.\n")
            return
        
        # Creăm administratorul
        try:
            new_admin = Doctor(
                email=email,
                password_hash=hash_password(password),
                full_name=full_name,
                is_admin=True,
                is_active=True
            )
            
            db.session.add(new_admin)
            db.session.commit()
            
            print("\n" + "="*70)
            print("✅ SUCCES!")
            print("="*70)
            print(f"\n👑 Administratorul {full_name} ({email}) a fost creat cu succes!")
            print("\n🔐 Poți să te autentifici acum la: http://localhost:8050/login")
            print("\n💡 Pentru a porni aplicația, rulează: python run_medical.py\n")
            
        except Exception as e:
            logger.error(f"❌ Eroare la crearea administratorului: {e}")
            db.session.rollback()
            print(f"\n❌ EROARE: Nu s-a putut crea administratorul: {str(e)}\n")
            sys.exit(1)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✋ Operațiune întreruptă de utilizator.\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ EROARE: {str(e)}\n")
        sys.exit(1)


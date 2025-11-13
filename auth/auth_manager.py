# ==============================================================================
# auth/auth_manager.py
# ------------------------------------------------------------------------------
# ROL: Gestionează autentificarea cu Flask-Login:
#      - Login/logout
#      - Session management
#      - User loader pentru Flask-Login
#
# RESPECTĂ: .cursorrules - Logging comprehensiv fără date sensibile
# ==============================================================================

from flask_login import LoginManager, login_user, logout_user, current_user
from flask import request
from datetime import datetime
from typing import Optional
from logger_setup import logger

from auth.models import db, Doctor, LoginSession
from auth.password_manager import verify_password, needs_rehash, hash_password
from auth.rate_limiter import check_rate_limit, record_failed_attempt, reset_rate_limit

# === INIȚIALIZARE FLASK-LOGIN ===
login_manager = LoginManager()
login_manager.login_view = '/login'  # Redirect aici dacă nu e autentificat
login_manager.login_message = 'Trebuie să te autentifici pentru a accesa această pagină.'
login_manager.login_message_category = 'warning'


# ==============================================================================
# USER LOADER (necesar pentru Flask-Login)
# ==============================================================================

@login_manager.user_loader
def load_user(user_id: str) -> Optional[Doctor]:
    """
    Încarcă un utilizator din database pe baza ID-ului.
    Apelat automat de Flask-Login la fiecare request.
    
    Args:
        user_id: ID-ul utilizatorului (string)
        
    Returns:
        Doctor sau None dacă nu există
    """
    try:
        doctor = Doctor.query.get(int(user_id))
        
        if doctor and doctor.is_active:
            return doctor
        else:
            return None
            
    except Exception as e:
        logger.error(f"Eroare la încărcarea utilizatorului ID {user_id}: {e}")
        return None


# ==============================================================================
# FUNCȚII AUTENTIFICARE
# ==============================================================================

def authenticate_doctor(email: str, password: str, remember_me: bool = False) -> tuple[bool, Optional[Doctor], str]:
    """
    Autentifică un doctor pe baza email-ului și parolei.
    
    WORKFLOW:
    1. Verifică rate limiting (max 5 încercări/15min)
    2. Găsește doctorul după email
    3. Verifică dacă contul e activ
    4. Verifică dacă contul e blocat (brute-force)
    5. Verifică parola
    6. Actualizează sesiunea
    7. Re-hash-uiește parola dacă folosește parametri vechi
    
    Args:
        email: Email-ul doctorului
        password: Parola în clar
        remember_me: Dacă True, sesiunea durează 30 zile (altfel 1 zi)
        
    Returns:
        tuple: (success: bool, doctor: Doctor|None, message: str)
    """
    # STEP 1: Verificăm rate limiting
    ip_address = request.remote_addr if request else 'unknown'
    
    if not check_rate_limit(email, ip_address):
        logger.warning(f"🚨 Rate limit depășit pentru {email[:3]}***@{email.split('@')[1]} din IP {ip_address}")
        return False, None, "Prea multe încercări eșuate. Contul este blocat temporar (15 minute)."
    
    # STEP 2: Găsim doctorul
    doctor = Doctor.query.filter_by(email=email).first()
    
    if not doctor:
        # NU dezvăluim că email-ul nu există (protecție enumerare)
        record_failed_attempt(email, ip_address)
        logger.debug(f"Încercare login cu email inexistent: {email[:3]}***")
        return False, None, "Email sau parolă incorectă."
    
    # STEP 3: Verificăm dacă contul e activ
    if not doctor.is_active:
        logger.warning(f"⚠️ Tentativă login pe cont dezactivat: {email}")
        return False, None, "Contul tău este dezactivat. Contactează administratorul."
    
    # STEP 4: Verificăm dacă contul e blocat (brute-force)
    if doctor.is_locked():
        logger.warning(f"🔒 Tentativă login pe cont blocat: {email}")
        minutes_left = int((doctor.locked_until - datetime.utcnow()).total_seconds() / 60)
        return False, None, f"Contul este blocat temporar ({minutes_left} minute rămase)."
    
    # STEP 5: Verificăm parola
    if not verify_password(password, doctor.password_hash):
        # Parolă incorectă
        record_failed_attempt(email, ip_address)
        doctor.failed_login_attempts += 1
        
        # Blocăm contul după 5 încercări eșuate
        if doctor.failed_login_attempts >= 5:
            doctor.lock_account(minutes=15)
            logger.warning(f"🔒 Cont blocat după 5 încercări eșuate: {email}")
            db.session.commit()
            return False, None, "Prea multe încercări eșuate. Contul este blocat 15 minute."
        
        db.session.commit()
        logger.debug(f"❌ Parolă incorectă pentru {email[:3]}*** (încercarea {doctor.failed_login_attempts}/5)")
        return False, None, "Email sau parolă incorectă."
    
    # STEP 6: Autentificare reușită! 🎉
    # Resetăm rate limiting
    reset_rate_limit(email, ip_address)
    
    # Înregistrăm login-ul reușit
    doctor.record_successful_login(ip_address)
    
    # Creăm sesiunea în Flask-Login
    login_user(doctor, remember=remember_me, duration=None)
    
    # Creăm înregistrare în LoginSession pentru tracking
    from auth.password_manager import generate_secure_token
    session_token = generate_secure_token(32)
    
    new_session = LoginSession(
        doctor_id=doctor.id,
        session_token=session_token,
        ip_address=ip_address,
        user_agent=request.headers.get('User-Agent', 'Unknown') if request else 'Unknown'
    )
    db.session.add(new_session)
    db.session.commit()
    
    logger.info(f"✅ Login reușit: {email} din IP {ip_address}")
    
    # STEP 7: Re-hash parolă dacă folosește parametri vechi
    if needs_rehash(doctor.password_hash):
        doctor.password_hash = hash_password(password)
        db.session.commit()
        logger.info(f"🔄 Parolă re-hash-uită cu parametri noi pentru {email}")
    
    return True, doctor, "Autentificare reușită!"


def logout_doctor(deactivate_all_sessions: bool = False) -> bool:
    """
    Deconectează doctorul curent.
    
    Args:
        deactivate_all_sessions: Dacă True, deconectează de pe TOATE dispozitivele
        
    Returns:
        bool: True dacă logout-ul a reușit
    """
    if not current_user.is_authenticated:
        return False
    
    doctor_id = current_user.id
    doctor_email = current_user.email
    
    if deactivate_all_sessions:
        # Deactivăm TOATE sesiunile
        count = LoginSession.deactivate_all_for_doctor(doctor_id)
        logger.info(f"🔴 Logout global pentru {doctor_email}: {count} sesiuni dezactivate")
    else:
        # Deactivăm doar sesiunea curentă
        # (Flask-Login gestionează sesiunea curentă automat)
        pass
    
    # Logout Flask-Login
    logout_user()
    
    logger.info(f"👋 Logout reușit: {doctor_email}")
    return True


def get_current_doctor() -> Optional[Doctor]:
    """
    Returnează doctorul curent autentificat.
    
    Returns:
        Doctor sau None dacă nu e autentificat
    """
    if current_user.is_authenticated:
        return current_user
    return None


def is_authenticated() -> bool:
    """
    Verifică dacă utilizatorul curent este autentificat.
    
    Returns:
        bool: True dacă e autentificat
    """
    return current_user.is_authenticated


def require_admin() -> bool:
    """
    Verifică dacă utilizatorul curent este admin.
    
    Returns:
        bool: True dacă e admin și autentificat
    """
    if not current_user.is_authenticated:
        return False
    return current_user.is_admin


# ==============================================================================
# FUNCȚII SESIUNI
# ==============================================================================

def get_active_sessions(doctor_id: int, limit: int = 10) -> list:
    """
    Preia sesiunile active pentru un doctor.
    
    Args:
        doctor_id: ID-ul doctorului
        limit: Număr maxim de sesiuni (default: 10)
        
    Returns:
        list: Listă de LoginSession
    """
    sessions = LoginSession.get_active_sessions_for_doctor(doctor_id, limit)
    return sessions


def deactivate_all_sessions(doctor_id: int) -> int:
    """
    Deactivează toate sesiunile pentru un doctor.
    
    Args:
        doctor_id: ID-ul doctorului
        
    Returns:
        int: Numărul de sesiuni dezactivate
    """
    count = LoginSession.deactivate_all_for_doctor(doctor_id)
    logger.info(f"🔴 Toate sesiunile dezactivate pentru doctor ID {doctor_id}: {count} sesiuni")
    return count


# ==============================================================================
# FUNCȚII UTILITĂȚI
# ==============================================================================

def get_login_statistics(doctor_id: int) -> dict:
    """
    Preia statistici de login pentru un doctor.
    
    Args:
        doctor_id: ID-ul doctorului
        
    Returns:
        dict: Statistici (total logins, ultimul login, etc.)
    """
    doctor = Doctor.query.get(doctor_id)
    
    if not doctor:
        return {}
    
    total_sessions = LoginSession.query.filter_by(doctor_id=doctor_id).count()
    active_sessions = LoginSession.query.filter_by(
        doctor_id=doctor_id, 
        is_active=True
    ).count()
    
    return {
        'total_logins': total_sessions,
        'active_sessions': active_sessions,
        'last_login_at': doctor.last_login_at.isoformat() if doctor.last_login_at else None,
        'last_login_ip': doctor.last_login_ip,
        'failed_attempts': doctor.failed_login_attempts,
        'is_locked': doctor.is_locked()
    }


def init_auth_manager(app):
    """
    Inițializează Flask-Login cu aplicația.
    
    Args:
        app: Instanța Flask/Dash
    """
    login_manager.init_app(app.server)
    logger.info("✅ Flask-Login inițializat cu succes.")


logger.info("✅ Modulul auth_manager.py inițializat cu succes.")


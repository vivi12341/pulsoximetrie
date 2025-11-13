# ==============================================================================
# auth/rate_limiter.py
# ------------------------------------------------------------------------------
# ROL: Protecție împotriva atacurilor brute-force:
#      - Limitare încercări login (5/15min per email + IP)
#      - Limitare cereri reset parolă (3/1h per email)
#      - Cleanup automat date vechi
#
# RESPECTĂ: .cursorrules - Logging fără date personale
# ==============================================================================

from datetime import datetime, timedelta
from typing import Dict, Optional
from collections import defaultdict
from logger_setup import logger

# === STORAGE IN-MEMORY (pentru Railway - memorie volatilă) ===
# În producție cu multiple instanțe, folosiți Redis sau database
_login_attempts: Dict[str, list] = defaultdict(list)
_reset_attempts: Dict[str, list] = defaultdict(list)

# === CONFIGURARE LIMITE ===
MAX_LOGIN_ATTEMPTS = 5
LOGIN_WINDOW_MINUTES = 15

MAX_RESET_ATTEMPTS = 3
RESET_WINDOW_HOURS = 1


# ==============================================================================
# FUNCȚII RATE LIMITING - LOGIN
# ==============================================================================

def check_rate_limit(email: str, ip_address: str) -> bool:
    """
    Verifică dacă un email sau IP poate încerca să se autentifice.
    
    LIMITĂ: 5 încercări eșuate în 15 minute per email SAU IP.
    
    Args:
        email: Email-ul utilizatorului
        ip_address: IP-ul de unde se face cererea
        
    Returns:
        bool: True dacă poate încerca, False dacă e blocat
    """
    now = datetime.utcnow()
    cutoff = now - timedelta(minutes=LOGIN_WINDOW_MINUTES)
    
    # Curățăm încercările vechi (cleanup automat)
    _cleanup_old_attempts(_login_attempts, cutoff)
    
    # Verificăm pentru email
    email_key = f"email:{email}"
    email_attempts = [t for t in _login_attempts.get(email_key, []) if t > cutoff]
    
    if len(email_attempts) >= MAX_LOGIN_ATTEMPTS:
        logger.debug(f"🚨 Rate limit email: {email[:3]}*** ({len(email_attempts)}/{MAX_LOGIN_ATTEMPTS})")
        return False
    
    # Verificăm pentru IP
    ip_key = f"ip:{ip_address}"
    ip_attempts = [t for t in _login_attempts.get(ip_key, []) if t > cutoff]
    
    if len(ip_attempts) >= MAX_LOGIN_ATTEMPTS:
        logger.debug(f"🚨 Rate limit IP: {ip_address} ({len(ip_attempts)}/{MAX_LOGIN_ATTEMPTS})")
        return False
    
    return True


def record_failed_attempt(email: str, ip_address: str):
    """
    Înregistrează o încercare de login eșuată.
    
    Args:
        email: Email-ul utilizatorului
        ip_address: IP-ul de unde s-a făcut cererea
    """
    now = datetime.utcnow()
    
    email_key = f"email:{email}"
    ip_key = f"ip:{ip_address}"
    
    _login_attempts[email_key].append(now)
    _login_attempts[ip_key].append(now)
    
    logger.debug(f"📝 Încercare eșuată înregistrată: {email[:3]}*** din {ip_address}")


def reset_rate_limit(email: str, ip_address: str):
    """
    Resetează rate limiting după un login reușit.
    
    Args:
        email: Email-ul utilizatorului
        ip_address: IP-ul de unde s-a făcut cererea
    """
    email_key = f"email:{email}"
    ip_key = f"ip:{ip_address}"
    
    if email_key in _login_attempts:
        del _login_attempts[email_key]
    
    if ip_key in _login_attempts:
        del _login_attempts[ip_key]
    
    logger.debug(f"🔄 Rate limit resetat: {email[:3]}*** din {ip_address}")


def get_remaining_attempts(email: str, ip_address: str) -> int:
    """
    Returnează numărul de încercări rămase înainte de blocare.
    
    Args:
        email: Email-ul utilizatorului
        ip_address: IP-ul
        
    Returns:
        int: Număr de încercări rămase (0 = blocat)
    """
    now = datetime.utcnow()
    cutoff = now - timedelta(minutes=LOGIN_WINDOW_MINUTES)
    
    email_key = f"email:{email}"
    email_attempts = [t for t in _login_attempts.get(email_key, []) if t > cutoff]
    
    ip_key = f"ip:{ip_address}"
    ip_attempts = [t for t in _login_attempts.get(ip_key, []) if t > cutoff]
    
    # Returnăm minimul (cea mai restrictivă limită)
    email_remaining = MAX_LOGIN_ATTEMPTS - len(email_attempts)
    ip_remaining = MAX_LOGIN_ATTEMPTS - len(ip_attempts)
    
    return min(email_remaining, ip_remaining, MAX_LOGIN_ATTEMPTS)


# ==============================================================================
# FUNCȚII RATE LIMITING - RESET PAROLĂ
# ==============================================================================

def check_reset_rate_limit(email: str) -> bool:
    """
    Verifică dacă un email poate cere resetare parolă.
    
    LIMITĂ: 3 cereri în 1 oră per email.
    
    Args:
        email: Email-ul utilizatorului
        
    Returns:
        bool: True dacă poate cere reset, False dacă e blocat
    """
    now = datetime.utcnow()
    cutoff = now - timedelta(hours=RESET_WINDOW_HOURS)
    
    # Curățăm încercările vechi
    _cleanup_old_attempts(_reset_attempts, cutoff)
    
    # Verificăm pentru email
    reset_requests = [t for t in _reset_attempts.get(email, []) if t > cutoff]
    
    if len(reset_requests) >= MAX_RESET_ATTEMPTS:
        logger.debug(f"🚨 Rate limit reset parolă: {email[:3]}*** ({len(reset_requests)}/{MAX_RESET_ATTEMPTS})")
        return False
    
    return True


def record_reset_attempt(email: str):
    """
    Înregistrează o cerere de reset parolă.
    
    Args:
        email: Email-ul utilizatorului
    """
    now = datetime.utcnow()
    _reset_attempts[email].append(now)
    
    logger.debug(f"📝 Cerere reset parolă înregistrată: {email[:3]}***")


def get_remaining_reset_attempts(email: str) -> int:
    """
    Returnează numărul de cereri reset rămase.
    
    Args:
        email: Email-ul utilizatorului
        
    Returns:
        int: Număr de cereri rămase (0 = blocat)
    """
    now = datetime.utcnow()
    cutoff = now - timedelta(hours=RESET_WINDOW_HOURS)
    
    reset_requests = [t for t in _reset_attempts.get(email, []) if t > cutoff]
    
    return MAX_RESET_ATTEMPTS - len(reset_requests)


def get_reset_cooldown_minutes(email: str) -> int:
    """
    Returnează câte minute trebuie să aștepte până poate cere din nou reset.
    
    Args:
        email: Email-ul utilizatorului
        
    Returns:
        int: Minute de așteptare (0 = poate cere acum)
    """
    now = datetime.utcnow()
    cutoff = now - timedelta(hours=RESET_WINDOW_HOURS)
    
    reset_requests = [t for t in _reset_attempts.get(email, []) if t > cutoff]
    
    if len(reset_requests) < MAX_RESET_ATTEMPTS:
        return 0
    
    # Calculăm când expiră cea mai veche cerere
    oldest_request = min(reset_requests)
    unlock_time = oldest_request + timedelta(hours=RESET_WINDOW_HOURS)
    remaining = unlock_time - now
    
    return max(0, int(remaining.total_seconds() / 60))


# ==============================================================================
# FUNCȚII UTILITARE
# ==============================================================================

def _cleanup_old_attempts(attempts_dict: Dict, cutoff: datetime):
    """
    Curăță încercările mai vechi decât cutoff (garbage collection).
    
    Args:
        attempts_dict: Dicționarul cu încercări
        cutoff: Data limită (ștergem tot ce e mai vechi)
    """
    keys_to_delete = []
    
    for key, timestamps in attempts_dict.items():
        # Păstrăm doar timestamp-urile mai noi decât cutoff
        attempts_dict[key] = [t for t in timestamps if t > cutoff]
        
        # Marcăm pentru ștergere cheile goale
        if not attempts_dict[key]:
            keys_to_delete.append(key)
    
    # Ștergem cheile goale
    for key in keys_to_delete:
        del attempts_dict[key]


def cleanup_all_expired() -> tuple[int, int]:
    """
    Curăță toate încercările expirate (rulat periodic).
    
    Returns:
        tuple: (login_attempts_cleaned, reset_attempts_cleaned)
    """
    now = datetime.utcnow()
    
    # Cleanup login attempts
    login_cutoff = now - timedelta(minutes=LOGIN_WINDOW_MINUTES)
    login_before = len(_login_attempts)
    _cleanup_old_attempts(_login_attempts, login_cutoff)
    login_after = len(_login_attempts)
    login_cleaned = login_before - login_after
    
    # Cleanup reset attempts
    reset_cutoff = now - timedelta(hours=RESET_WINDOW_HOURS)
    reset_before = len(_reset_attempts)
    _cleanup_old_attempts(_reset_attempts, reset_cutoff)
    reset_after = len(_reset_attempts)
    reset_cleaned = reset_before - reset_after
    
    if login_cleaned > 0 or reset_cleaned > 0:
        logger.debug(f"🧹 Cleanup rate limiter: {login_cleaned} login + {reset_cleaned} reset")
    
    return login_cleaned, reset_cleaned


def get_rate_limit_stats() -> dict:
    """
    Returnează statistici despre rate limiting (pentru monitoring).
    
    Returns:
        dict: Statistici
    """
    return {
        'active_login_limits': len(_login_attempts),
        'active_reset_limits': len(_reset_attempts),
        'max_login_attempts': MAX_LOGIN_ATTEMPTS,
        'login_window_minutes': LOGIN_WINDOW_MINUTES,
        'max_reset_attempts': MAX_RESET_ATTEMPTS,
        'reset_window_hours': RESET_WINDOW_HOURS
    }


def reset_all_limits():
    """
    Resetează TOATE limitele (doar pentru testing/debugging).
    
    ⚠️ NU folosiți în producție!
    """
    _login_attempts.clear()
    _reset_attempts.clear()
    logger.warning("⚠️ TOATE limitele rate limiter au fost resetate!")


# ==============================================================================
# TASK PERIODIC - CLEANUP (rulat la fiecare 30 minute)
# ==============================================================================

def schedule_cleanup_task():
    """
    Programează task-ul periodic de cleanup.
    Apelat din run_medical.py la pornirea aplicației.
    """
    from threading import Timer
    
    def run_cleanup():
        cleanup_all_expired()
        # Re-programăm pentru următoarele 30 minute
        schedule_cleanup_task()
    
    # Rulăm după 30 minute (1800 secunde)
    timer = Timer(1800, run_cleanup)
    timer.daemon = True  # Thread daemon (se închide cu aplicația)
    timer.start()
    
    logger.debug("⏰ Task cleanup rate limiter programat (30 minute)")


logger.info("✅ Modulul rate_limiter.py inițializat cu succes.")


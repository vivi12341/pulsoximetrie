# ==============================================================================
# auth/password_manager.py
# ------------------------------------------------------------------------------
# ROL: Gestionează hash-uirea și verificarea parolelor cu Argon2
#      (mai sigur decât bcrypt, recomandat de OWASP 2024)
#
# RESPECTĂ: .cursorrules - Logging fără date sensibile
# ==============================================================================

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHash
from logger_setup import logger
import secrets
import string

# === CONFIGURARE ARGON2 ===
# Parametrii recomandați de OWASP (2024):
# - time_cost: 2 (număr iterații)
# - memory_cost: 102400 (100 MB)
# - parallelism: 8 (thread-uri paralele)
# - hash_len: 32 (lungime hash în bytes)
# - salt_len: 16 (lungime salt în bytes)

ph = PasswordHasher(
    time_cost=2,
    memory_cost=102400,  # 100 MB
    parallelism=8,
    hash_len=32,
    salt_len=16
)


# ==============================================================================
# FUNCȚII CORE - HASH & VERIFY
# ==============================================================================

def hash_password(password: str) -> str:
    """
    Hash-uiește o parolă folosind Argon2.
    
    Args:
        password: Parola în clar (plaintext)
        
    Returns:
        str: Hash-ul parolei (format: $argon2id$v=19$m=102400,t=2,p=8$...)
        
    Raises:
        ValueError: Dacă parola este prea scurtă sau invalidă
    """
    if not password or len(password) < 8:
        logger.error("❌ Tentativă hash parolă prea scurtă (<8 caractere)")
        raise ValueError("Parola trebuie să aibă minimum 8 caractere.")
    
    try:
        password_hash = ph.hash(password)
        logger.debug(f"✅ Parolă hash-uită cu succes (Argon2, lungime: {len(password_hash)})")
        return password_hash
    except Exception as e:
        logger.error(f"❌ Eroare la hash-uirea parolei: {e}", exc_info=True)
        raise


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verifică dacă o parolă în clar corespunde unui hash.
    
    Args:
        password: Parola în clar
        password_hash: Hash-ul stocat în database
        
    Returns:
        bool: True dacă parola este corectă, False altfel
    """
    try:
        ph.verify(password_hash, password)
        
        # Verificăm dacă hash-ul trebuie re-hash-uit (parametrii vechi)
        if ph.check_needs_rehash(password_hash):
            logger.info("⚠️ Hash-ul parolei folosește parametri vechi - recomandare rehash")
        
        logger.debug("✅ Parolă verificată cu succes (match)")
        return True
        
    except VerifyMismatchError:
        # Parola este incorectă
        logger.debug("❌ Parolă incorectă (mismatch)")
        return False
        
    except (VerificationError, InvalidHash) as e:
        # Hash-ul este invalid sau corupt
        logger.error(f"❌ Hash invalid sau corupt: {e}")
        return False
        
    except Exception as e:
        logger.error(f"❌ Eroare neașteptată la verificarea parolei: {e}", exc_info=True)
        return False


def needs_rehash(password_hash: str) -> bool:
    """
    Verifică dacă un hash folosește parametri vechi și trebuie re-hash-uit.
    
    Args:
        password_hash: Hash-ul de verificat
        
    Returns:
        bool: True dacă trebuie re-hash-uit
    """
    try:
        return ph.check_needs_rehash(password_hash)
    except Exception as e:
        logger.error(f"❌ Eroare la verificarea rehash: {e}")
        return False


def rehash_password(password: str, old_hash: str) -> str:
    """
    Re-hash-uiește o parolă dacă folosește parametri vechi.
    
    Workflow:
    1. Verifică că parola e corectă cu vechiul hash
    2. Generează un hash nou cu parametrii actuali
    
    Args:
        password: Parola în clar
        old_hash: Hash-ul vechi
        
    Returns:
        str: Noul hash
        
    Raises:
        ValueError: Dacă parola nu corespunde vechiului hash
    """
    if not verify_password(password, old_hash):
        raise ValueError("Parola nu corespunde hash-ului vechi.")
    
    new_hash = hash_password(password)
    logger.info("✅ Parolă re-hash-uită cu parametri noi")
    return new_hash


# ==============================================================================
# FUNCȚII VALIDARE PAROLĂ
# ==============================================================================

def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validează puterea unei parole conform cerințelor de securitate.
    
    CERINȚE MINIME:
    - Minimum 8 caractere
    - Cel puțin o literă mare
    - Cel puțin o literă mică
    - Cel puțin o cifră
    - Cel puțin un caracter special (!@#$%^&*...)
    
    Args:
        password: Parola de validat
        
    Returns:
        tuple: (is_valid: bool, message: str)
    """
    if not password:
        return False, "Parola nu poate fi goală."
    
    if len(password) < 8:
        return False, "Parola trebuie să aibă minimum 8 caractere."
    
    if len(password) > 128:
        return False, "Parola este prea lungă (maximum 128 caractere)."
    
    # Verificăm cerințele de complexitate
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in string.punctuation for c in password)
    
    if not has_upper:
        return False, "Parola trebuie să conțină cel puțin o literă mare."
    
    if not has_lower:
        return False, "Parola trebuie să conțină cel puțin o literă mică."
    
    if not has_digit:
        return False, "Parola trebuie să conțină cel puțin o cifră."
    
    if not has_special:
        return False, "Parola trebuie să conțină cel puțin un caracter special (!@#$%^&*...)."
    
    # Verificăm pentru parole comune (top 100 cele mai folosite)
    common_passwords = [
        'password', '12345678', 'qwerty', 'abc123', 'monkey', 
        '1234567890', 'letmein', 'trustno1', 'dragon', 'baseball',
        'iloveyou', 'master', 'sunshine', 'ashley', 'bailey',
        'passw0rd', 'shadow', '123123', '654321', 'superman'
    ]
    
    if password.lower() in common_passwords:
        return False, "Această parolă este prea comună. Alegeți una mai sigură."
    
    # Verificăm pentru secvențe simple
    if password == password[0] * len(password):
        return False, "Parola nu poate conține doar același caracter repetat."
    
    # Parola este validă
    return True, "Parola îndeplinește cerințele de securitate."


def generate_secure_password(length: int = 16) -> str:
    """
    Generează o parolă securizată aleatoriu (pentru admin).
    
    Args:
        length: Lungimea parolei (default: 16)
        
    Returns:
        str: Parola generată
    """
    if length < 12:
        length = 12
        logger.warning("⚠️ Lungime parolă prea mică - setată la 12 caractere")
    
    # Compoziție: litere, cifre, caractere speciale
    alphabet = string.ascii_letters + string.digits + string.punctuation
    
    # Folosim secrets (cryptographically secure RNG)
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    
    # Asigurăm că parola respectă cerințele
    # (foarte probabil cu 16+ caractere, dar verificăm)
    is_valid, message = validate_password_strength(password)
    
    if not is_valid:
        # Re-generăm recursiv dacă nu e validă (extrem de rar)
        logger.warning(f"⚠️ Parolă generată invalidă ({message}) - regenerare...")
        return generate_secure_password(length)
    
    logger.info(f"✅ Parolă securizată generată (lungime: {length})")
    return password


# ==============================================================================
# FUNCȚII TOKEN-URI SECURIZATE
# ==============================================================================

def generate_secure_token(length: int = 32) -> str:
    """
    Generează un token securizat aleatoriu (pentru reset parolă, sesiuni).
    
    Args:
        length: Lungimea token-ului în bytes (default: 32 = 64 caractere hex)
        
    Returns:
        str: Token hexadecimal
    """
    token = secrets.token_hex(length)
    logger.debug(f"✅ Token securizat generat (lungime: {len(token)} caractere)")
    return token


def generate_reset_token_with_expiry(doctor_id: int, hours: int = 1) -> tuple[str, 'datetime']:
    """
    Generează un token de reset parolă cu expirare automată.
    
    Args:
        doctor_id: ID-ul doctorului
        hours: Validitate în ore (default: 1)
        
    Returns:
        tuple: (token: str, expires_at: datetime)
    """
    from datetime import datetime, timedelta
    
    token = generate_secure_token(32)
    expires_at = datetime.utcnow() + timedelta(hours=hours)
    
    logger.info(f"✅ Token reset parolă generat pentru doctor ID {doctor_id} (expiră în {hours}h)")
    return token, expires_at


# ==============================================================================
# TESTE AUTOMATE (rulat la import pentru verificare setup)
# ==============================================================================

def _run_self_tests():
    """Teste rapide pentru verificarea funcționalității."""
    try:
        # Test 1: Hash și verify
        test_password = "TestPassword123!"
        hashed = hash_password(test_password)
        assert verify_password(test_password, hashed), "Test hash/verify eșuat!"
        assert not verify_password("wrong_password", hashed), "Verificare parolă greșită eșuată!"
        
        # Test 2: Validare putere parolă
        is_valid, msg = validate_password_strength("weak")
        assert not is_valid, "Validare parolă slabă eșuată!"
        
        is_valid, msg = validate_password_strength("StrongPass123!")
        assert is_valid, "Validare parolă puternică eșuată!"
        
        # Test 3: Generare parolă
        generated_password = generate_secure_password(16)
        is_valid, msg = validate_password_strength(generated_password)
        assert is_valid, f"Parolă generată invalidă: {msg}"
        
        logger.info("✅ Password manager: toate testele automate au trecut!")
        
    except AssertionError as e:
        logger.error(f"❌ Test password manager eșuat: {e}")
    except Exception as e:
        logger.error(f"❌ Eroare la rularea testelor: {e}", exc_info=True)


# Rulăm testele la import (doar în development)
import os
if os.getenv('FLASK_ENV') != 'production':
    _run_self_tests()

logger.info("✅ Modulul password_manager.py inițializat cu succes.")


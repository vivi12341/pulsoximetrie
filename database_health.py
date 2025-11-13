# ==============================================================================
# database_health.py
# ------------------------------------------------------------------------------
# ROL: Verificări de health pentru conexiunea la database
#      - Validare DATABASE_URL
#      - Test conexiune
#      - Fallback strategies
# ==============================================================================

import os
import sys
from logger_setup import logger
from urllib.parse import urlparse

def validate_database_url(database_url: str) -> tuple[bool, str]:
    """
    Validează DATABASE_URL și returnează (is_valid, message).
    
    Args:
        database_url: URL-ul bazei de date
        
    Returns:
        tuple: (is_valid: bool, message: str)
    """
    if not database_url:
        return False, "DATABASE_URL nu este setat!"
    
    try:
        parsed = urlparse(database_url)
        
        # Verificăm schema (postgresql/sqlite)
        if parsed.scheme not in ['postgresql', 'postgresql+psycopg2', 'sqlite']:
            return False, f"Schema nesuportată: {parsed.scheme}"
        
        # Pentru PostgreSQL, verificăm componentele
        if parsed.scheme.startswith('postgresql'):
            if not parsed.hostname:
                return False, "PostgreSQL: hostname lipsă!"
            if not parsed.username:
                return False, "PostgreSQL: username lipsă!"
            if parsed.hostname == 'localhost' and os.getenv('FLASK_ENV') == 'production':
                return False, "⚠️ PRODUCTION folosește localhost - PostgreSQL nu este configurat corect!"
        
        return True, f"✅ DATABASE_URL valid: {parsed.scheme}://{parsed.hostname or 'local'}"
        
    except Exception as e:
        return False, f"Eroare la parsarea DATABASE_URL: {e}"


def test_database_connection(app) -> tuple[bool, str]:
    """
    Testează conexiunea la database.
    
    Args:
        app: Instanța Flask
        
    Returns:
        tuple: (is_connected: bool, message: str)
    """
    try:
        from sqlalchemy import text
        from auth.models import db
        
        with app.app_context():
            # Test simplu de conexiune
            db.session.execute(text('SELECT 1'))
            db.session.commit()
            
        return True, "✅ Conexiune database reușită!"
        
    except Exception as e:
        return False, f"❌ Conexiune database eșuată: {str(e)[:200]}"


def get_database_url_with_fallback(strict_mode: bool = False) -> str:
    """
    Preia DATABASE_URL cu fallback inteligent.
    
    Args:
        strict_mode: Dacă True, eșuează în production fără DATABASE_URL valid
        
    Returns:
        str: DATABASE_URL sau fallback
    """
    database_url = os.getenv('DATABASE_URL')
    flask_env = os.getenv('FLASK_ENV', 'development')
    is_production = flask_env == 'production'
    
    # Validăm DATABASE_URL
    is_valid, message = validate_database_url(database_url)
    
    if is_valid:
        logger.info(f"✅ {message}")
        return database_url
    
    # DATABASE_URL invalid sau lipsă
    logger.warning(f"⚠️ {message}")
    
    if is_production and strict_mode:
        # În PRODUCTION STRICT, nu permitem fallback
        logger.error("🚨 PRODUCTION MODE: DATABASE_URL obligatoriu!")
        logger.error("=" * 70)
        logger.error("INSTRUCȚIUNI RAILWAY:")
        logger.error("1. Mergi la Railway Dashboard")
        logger.error("2. Click pe proiectul 'pulsoximetrie'")
        logger.error("3. Click '+ New' → 'Database' → 'Add PostgreSQL'")
        logger.error("4. Railway va seta automat DATABASE_URL")
        logger.error("5. Aplicația va reporni automat")
        logger.error("=" * 70)
        sys.exit(1)
    
    # Development sau non-strict: folosim fallback
    if is_production:
        logger.warning("⚠️ PRODUCTION fără PostgreSQL - folosesc SQLite temporar (NU pentru producție reală!)")
        fallback = "sqlite:///./tmp_pulsoximetrie.db"
    else:
        logger.info("ℹ️ Development mode - folosesc PostgreSQL local")
        fallback = "postgresql://postgres:postgres@localhost:5432/pulsoximetrie"
    
    logger.info(f"📍 Fallback: {fallback}")
    return fallback


def log_database_info(database_url: str):
    """
    Loghează informații despre configurația database.
    
    Args:
        database_url: URL-ul bazei de date
    """
    try:
        parsed = urlparse(database_url)
        
        logger.info("=" * 70)
        logger.info("📊 CONFIGURARE DATABASE")
        logger.info("=" * 70)
        logger.info(f"  Schema: {parsed.scheme}")
        logger.info(f"  Host: {parsed.hostname or 'local (SQLite)'}")
        logger.info(f"  Port: {parsed.port or 'default'}")
        logger.info(f"  Database: {parsed.path.lstrip('/') if parsed.path else 'N/A'}")
        logger.info(f"  User: {parsed.username or 'N/A'}")
        logger.info("=" * 70)
        
    except Exception as e:
        logger.warning(f"Nu pot afișa info database: {e}")


logger.info("✅ Modulul database_health.py inițializat cu succes.")


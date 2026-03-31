# ==============================================================================
# shared/logger_setup.py (VERSIUNEA 2.2 - FIX ENCODING UTF-8)
# ------------------------------------------------------------------------------
# ROL: Configurează sistemul de logging centralizat pentru întreaga aplicație.
# ==============================================================================

import logging
from logging.handlers import RotatingFileHandler
import os
import sys

from shared import config


def setup_logger():
    """
    Creează și configurează instanța de logger principală a aplicației.
    """
    is_production = (
        os.getenv('RAILWAY_ENVIRONMENT') is not None or
        os.getenv('PORT') is not None
    )
    try:
        os.makedirs(config.LOGS_DIR, exist_ok=True)
    except OSError as e:
        print(f"EROARE CRITICĂ: Nu s-a putut crea directorul de log la '{config.LOGS_DIR}'. Motiv: {e}")
        sys.exit(1)

    log_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - [%(module)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    log_file_path = os.path.join(config.LOGS_DIR, 'app_activity.log')

    file_handler = RotatingFileHandler(
        log_file_path,
        maxBytes=5*1024*1024,
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging.WARNING if is_production else logging.INFO)

    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except AttributeError:
            pass

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)
    console_handler.setLevel(logging.WARNING if is_production else logging.INFO)

    app_logger = logging.getLogger("PulsoximetrieApp")
    app_logger.setLevel(logging.INFO)

    if not app_logger.handlers:
        app_logger.addHandler(file_handler)
        app_logger.addHandler(console_handler)

        try:
            from ui.debug_system import memory_handler
            app_logger.addHandler(memory_handler)
        except ImportError:
            pass

    return app_logger


logger = setup_logger()

is_prod = os.getenv('RAILWAY_ENVIRONMENT') is not None or os.getenv('PORT') is not None
if is_prod:
    logger.warning("⚙️  PRODUCTION MODE: Logging level = WARNING (reduce noise)")
else:
    logger.info("="*50)
    logger.info("Sistemul de logging a fost inițializat cu succes.")
    logger.info(f"Log-urile vor fi salvate în fișierul: {os.path.abspath(os.path.join(config.LOGS_DIR, 'app_activity.log'))}")
    logger.info("⚙️  DEVELOPMENT MODE: Logging level = INFO (verbose)")
    logger.info("="*50)

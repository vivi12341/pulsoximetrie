# ==============================================================================
# logger_setup.py (VERSIUNEA 2.2 - FIX ENCODING UTF-8)
# ------------------------------------------------------------------------------
# ROL: Configurează sistemul de logging centralizat pentru întreaga aplicație.
#      Definește unde și cum sunt scrise mesajele de log (consolă și fișier).
#
# MODIFICĂRI CHEIE (v2.2):
#  - [FIX] Forțare encoding UTF-8 pentru StreamHandler (consolă)
#  - [WHY] Windows folosește implicit cp1252 → UnicodeEncodeError pe caractere românești
#
# MOD DE UTILIZARE:
#   from logger_setup import logger
#   logger.info("Acesta este un mesaj informativ.")
#   logger.error("A apărut o eroare critică.")
# ==============================================================================

import logging
from logging.handlers import RotatingFileHandler
import os
import sys

# Importăm configurațiile definite centralizat
import config

# --- Funcția de Configurare a Logger-ului ---

def setup_logger():
    """
    Creează și configurează instanța de logger principală a aplicației.

    Logger-ul va avea două destinații (handlers):
    1. StreamHandler: Trimite log-urile către consolă (stdout), util pentru
       dezvoltare și monitorizare în timp real.
       - PRODUCTION: WARNING level (reduce volumul)
       - DEVELOPMENT: INFO level (verbose)
    2. RotatingFileHandler: Scrie log-urile într-un fișier. Când fișierul
       atinge o anumită dimensiune, este arhivat și se creează unul nou.
       Acest lucru previne crearea unor fișiere de log excesiv de mari.

    Returns:
        logging.Logger: Instanța de logger configurată.
    """
    # Detectăm environment-ul (production vs development)
    is_production = (
        os.getenv('RAILWAY_ENVIRONMENT') is not None or 
        os.getenv('PORT') is not None
    )
    # Ne asigurăm că directoarele de output și de log există.
    # Le creăm dacă lipsesc, pentru a evita erori la pornire.
    try:
        os.makedirs(config.LOGS_DIR, exist_ok=True)
    except OSError as e:
        # Dacă nu putem crea folderul de log, este o eroare critică.
        # Afișăm eroarea și ieșim din program.
        print(f"EROARE CRITICĂ: Nu s-a putut crea directorul de log la '{config.LOGS_DIR}'. Motiv: {e}")
        sys.exit(1)

    # Definirea formatului pentru mesajele de log.
    # Include data, ora, nivelul de severitate, numele modulului și mesajul.
    log_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - [%(module)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # --- Configurare Handler pentru Fișier (File Handler) ---
    log_file_path = os.path.join(config.LOGS_DIR, 'app_activity.log')
    
    # Folosim RotatingFileHandler pentru a controla dimensiunea fișierului.
    # maxBytes=5*1024*1024 -> 5 MB
    # backupCount=5 -> Păstrează ultimele 5 fișiere de log arhivate.
    file_handler = RotatingFileHandler(
        log_file_path,
        maxBytes=5*1024*1024,
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(log_formatter)
    # File handler: INFO în development, WARNING în production (reduce I/O)
    file_handler.setLevel(logging.WARNING if is_production else logging.INFO)

    # --- Configurare Handler pentru Consolă (Stream Handler) ---
    # [FIX v2.2] Forțăm encoding UTF-8 pentru consolă pe Windows
    # [WHY] Windows folosește implicit cp1252, care nu suportă caractere românești (ț, ș, ă)
    # Reconfigurăm stdout cu UTF-8 înainte de a crea handler-ul
    if sys.stdout.encoding != 'utf-8':
        try:
            # Python 3.7+ permite reconfigurare encoding pentru stdout
            sys.stdout.reconfigure(encoding='utf-8')
        except AttributeError:
            # Python < 3.7 - fallback: continuăm fără fix (va genera warning-uri)
            pass
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)
    # Console handler: WARNING în production (reduce noise), INFO în development
    console_handler.setLevel(logging.WARNING if is_production else logging.INFO)

    # --- Creare și Asamblare Logger Principal ---
    # Obținem logger-ul rădăcină al aplicației.
    app_logger = logging.getLogger("PulsoximetrieApp")
    # Logger level: INFO întotdeauna (handlers filtrează per environment)
    app_logger.setLevel(logging.INFO)

    # Prevenim adăugarea multiplă de handlers dacă funcția e apelată din greșeală de mai multe ori.
    if not app_logger.handlers:
        app_logger.addHandler(file_handler)
        app_logger.addHandler(console_handler)

    return app_logger

# --- Instanțierea Logger-ului ---
# Apelăm funcția o singură dată la importarea modulului pentru a crea instanța
# globală de logger, care va fi apoi importată de celelalte module.
logger = setup_logger()

# Mesaj de confirmare că logger-ul a fost inițializat cu succes.
is_prod = os.getenv('RAILWAY_ENVIRONMENT') is not None or os.getenv('PORT') is not None
logger.info("="*50)
logger.info("Sistemul de logging a fost inițializat cu succes.")
logger.info(f"Log-urile vor fi salvate în fișierul: {os.path.abspath(os.path.join(config.LOGS_DIR, 'app_activity.log'))}")
if is_prod:
    logger.warning("⚙️  PRODUCTION MODE: Logging level = WARNING (reduce noise)")
else:
    logger.info("⚙️  DEVELOPMENT MODE: Logging level = INFO (verbose)")
logger.info("="*50)
# ==============================================================================
# app_instance.py
# ------------------------------------------------------------------------------
# ROL: Definește și exportă instanța centrală a aplicației Dash.
#      Acest fișier există pentru a preveni importurile circulare. Modulele
#      care au nevoie de obiectul 'app' (cum ar fi callbacks.py sau run.py)
#      îl vor importa direct de aici.
#
# MOD DE UTILIZARE:
#   from app_instance import app
# ==============================================================================

import dash

# Importăm instanța de logger pentru a înregistra pornirea aplicației
from logger_setup import logger

# --- Inițializarea Aplicației Dash ---

# Creăm instanța principală a aplicației.
# `__name__` este o variabilă standard Python care ajută Dash să localizeze
# fișierele statice din folderul 'assets'.
# Putem adăuga aici și foi de stil externe (CSS) dacă este cazul.
app = dash.Dash(
    __name__,
    suppress_callback_exceptions=True # Necesar pentru layout-uri dinamice cu tab-uri
)

# Setăm un titlu pentru fereastra browser-ului
app.title = "Analizator Pulsoximetrie"

# Înregistrăm un mesaj informativ pentru a confirma că instanța a fost creată.
logger.info("Instanța aplicației Dash a fost creată cu succes.")
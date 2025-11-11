# ==============================================================================
# run.py
# ------------------------------------------------------------------------------
# ROL: Punctul de intrare principal pentru pornirea aplicației.
#      Acest script asamblează componentele cheie (instanța app și layout-ul)
#      și pornește serverul de dezvoltare Dash.
#
# MOD DE UTILIZARE (din terminal):
#   python run.py
# ==============================================================================

# Importăm componentele esențiale pe care le-am definit în module separate.
# Acestea trebuie importate în această ordine specifică pentru a asigura
# că totul este inițializat corect înainte de a fi utilizat.

# 1. Importăm instanța de logger prima dată pentru a fi disponibilă peste tot.
from logger_setup import logger

# 2. Importăm instanța aplicației Dash.
from app_instance import app

# 3. Importăm layout-ul vizual al aplicației.
from app_layout import layout

# 4. Importăm modulul de callbacks pentru a le înregistra în aplicație.
#    Chiar dacă nu folosim explicit o variabilă din 'callbacks', importul
#    acestui fișier este esențial pentru ca decoratoarele @app.callback
#    să fie executate și ca logica interactivă să funcționeze.
import callbacks

# --- Asamblarea finală a aplicației ---
# Atribuim structura vizuală (layout) proprietății corespunzătoare
# a instanței noastre de aplicație Dash.
app.layout = layout

# --- Pornirea serverului ---
# Blocul `if __name__ == '__main__':` este o practică standard în Python.
# Asigură că serverul este pornit doar atunci când scriptul `run.py` este
# executat direct, și nu atunci când este importat de un alt script.
if __name__ == '__main__':
    logger.info("=" * 50)
    logger.info("PORNIRE SERVER DE DEZVOLTARE DASH...")
    logger.info("Aplicația va fi disponibilă la adresa: http://127.0.0.1:8050/")
    logger.info("Apăsați CTRL+C în terminal pentru a opri serverul.")
    logger.info("=" * 50)
    
    # Pornim serverul de dezvoltare.
    # debug=True activează funcționalități utile pentru dezvoltare,
    # cum ar fi reîncărcarea automată la modificarea codului și un
    # panou de depanare interactiv în browser.
    # Nu folosiți debug=True într-un mediu de producție!
    
    # [OPȚIONAL] Dezactivează Dev Tools UI (păstrând hot-reload):
    # app.run(debug=True, dev_tools_ui=False)
    
    app.run(debug=True)  # Dev Tools active - util pentru debugging
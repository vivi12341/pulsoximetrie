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
import os
import io
import zipfile
from flask import send_from_directory, send_file
from datetime import datetime

# Importăm instanța de logger pentru a înregistra pornirea aplicației
from logger_setup import logger

# === CRITICAL FIX: DASH 3.X LIBRARY REGISTRATION ===
# PROBLEMA: Dash 3.x lazy-load biblioteci → "dash" is not a registered library → 500 error
# CAUZA: În producție (Railway), Gunicorn workers nu au biblioteci înregistrate la import
# SOLUȚIE: Forțăm înregistrarea EXPLICITĂ a bibliotecilor ÎNAINTE de orice layout/callback!

logger.warning("=" * 80)
logger.warning("[APP_INSTANCE 1/10] 📦 Initializing Dash 3.x libraries...")
logger.warning("=" * 80)

# Import ALL Dash component libraries (CRITICAL: trebuie făcut ÎNAINTE de app creation!)
try:
    from dash import html, dcc, dash_table, Input, Output, State, callback
    logger.warning("[APP_INSTANCE 2/10] ✅ Dash 3.x libraries imported: html, dcc, dash_table")
except ImportError as dash_lib_err:
    logger.critical(f"[APP_INSTANCE 2/10] ❌ CRITICAL: Dash libraries import FAILED: {dash_lib_err}")
    raise

# --- Inițializarea Aplicației Dash ---

# Creăm instanța principală a aplicației.
# `__name__` este o variabilă standard Python care ajută Dash să localizeze
# fișierele statice din folderul 'assets'.
# Putem adăuga aici și foi de stil externe (CSS) dacă este cazul.
logger.warning("[APP_INSTANCE 3/10] 🚀 Creating Dash app instance...")

app = dash.Dash(
    __name__,
    suppress_callback_exceptions=True # Necesar pentru layout-uri dinamice cu tab-uri
)

logger.warning("[APP_INSTANCE 4/10] ✅ Dash app instance created")

# Setăm un titlu pentru fereastra browser-ului
# Setăm un titlu pentru fereastra browser-ului
app.title = "Analizator Pulsoximetrie"

# === CRITICAL: CDN SERVING (Dash 3.x Compatibility) ===
# PROBLEMA LOCAL SERVING: Dash 3.x path incompatibility
# - Local serving folosește paths diferite pentru componente
# - dash_html_components.min.js NU este în registered paths când serve_locally=True
# - DependencyException: "html/dash_html_components.min.js" not found
#
# SOLUȚIE TEMPORARĂ: Revenim la CDN (problemă originală poate fi alta)
# TODO: Investigare Plotly 500 errors fără a schimba serving strategy
app.scripts.config.serve_locally = False  # CDN serving (stable pentru Dash 3.x)
app.css.config.serve_locally = False
logger.warning("[APP_INSTANCE 4.1/10] 🌐 CDN Serving RE-ENABLED (Dash 3.x paths compatibility)")

# === FORCE DASH LIBRARY REGISTRATION (DEFENSIVE) ===
# CRITICAL: Dash 3.x înregistrează biblioteci DOAR când găsește componente în layout!
# În producție, dacă layout-ul e setat DUPĂ ce worker-ul e forked, înregistrarea eșuează!
# SOLUȚIE: Forțăm înregistrarea prin crearea unui layout DUMMY care conține TOATE componentele

logger.warning("[APP_INSTANCE 5/10] 🔧 Forcing Dash library registration...")

try:
    # [FIX v2] CRITICAL: Forțăm înregistrarea ÎNAINTE de setare layout
    # Dash 3.x înregistrează biblioteci când găsește componente în layout
    # Dar trebuie să FORȚĂM înregistrarea explicit pentru Gunicorn workers
    
    # Pasul 1: Creăm componente pentru a triggera înregistrarea
    logger.warning("[APP_INSTANCE 5.1/10] Creating dummy components...")
    dummy_html = html.Div("Force registration")
    dummy_dcc = dcc.Store(id='dummy-registration-store')
    
    # CRITICAL FIX: Add dcc.Graph to force Plotly registration!
    # WITHOUT this, plotly.min.js is NOT registered → 500 error
    import plotly.graph_objects as go
    dummy_graph = dcc.Graph(
        id='dummy-graph-force-plotly',
        figure=go.Figure()  # Empty figure to trigger registration
    )
    logger.warning("[APP_INSTANCE 5.2/10] ✅ Created dcc.Graph to force Plotly registration")
    
    # Pasul 2: Setăm layout DUMMY cu componentele esențiale
    dummy_layout = html.Div([
        dummy_html,
        dummy_dcc,
        dummy_graph  # FORCE PLOTLY REGISTRATION
    ])
    
    # CRITICAL: Setăm layout IMEDIAT pentru a triggera înregistrarea
    app.layout = dummy_layout
    logger.warning("[APP_INSTANCE 6/10] ✅ Dummy layout set (including Graph for Plotly)")
    
    # Pasul 3: FORȚĂM warmup-ul registrului Dash
    # Accesăm app._registered_paths pentru a declanșa lazy initialization
    if hasattr(app, 'registered_paths'):
        _ = app.registered_paths  # Trigger property getter
        logger.warning("[APP_INSTANCE 6.1/10] ✅ Triggered registered_paths property")
    
    # Pasul 4: Verificăm că Flask routes-urile sunt înregistrate
    try:
        with app.server.app_context():
            route_count = len(list(app.server.url_map.iter_rules()))
            logger.warning(f"[APP_INSTANCE 6.2/10] ✅ Flask routes registered: {route_count}")
    except Exception as route_err:
        logger.warning(f"[APP_INSTANCE 6.2/10] ⚠️ Cannot count routes: {route_err}")
    
    # Verificăm că bibliotecile sunt înregistrate
    # Dash 3.x stochează bibliotecile înregistrate în app._registered_paths
    if hasattr(app, '_registered_paths'):
        registered_libs = list(app._registered_paths.keys())
        logger.warning(f"[APP_INSTANCE 7/10] 🔍 Registered libraries: {registered_libs}")
        
        # Verificăm că dash_table este înregistrat
        if 'dash_table' in registered_libs or 'dash' in registered_libs:
            logger.warning("[APP_INSTANCE 8/10] ✅ dash_table library CONFIRMED registered!")
        else:
            logger.error(f"[APP_INSTANCE 8/10] ⚠️ WARNING: dash_table NOT found in registered libs: {registered_libs}")
    else:
        logger.warning("[APP_INSTANCE 7/10] ⚠️ WARNING: app._registered_paths not found (Dash version?)")
    
    logger.warning("[APP_INSTANCE 9/10] ✅ Dash library registration COMPLETE")
    
except Exception as reg_err:
    logger.critical(f"[APP_INSTANCE 9/10] ❌ CRITICAL: Library registration FAILED: {reg_err}", exc_info=True)
    # Nu aruncăm eroare - aplicația poate continua, dar logging-ul ajută la debugging

logger.warning("[APP_INSTANCE 10/10] ✅ app_instance.py initialization COMPLETE")
logger.warning("=" * 80)

# === CONFIGURARE SERVIRE IMAGINI ȘI PDF-URI PACIENȚI ===
# Route personalizat pentru servirea resurselor din patient_data
@app.server.route('/patient_assets/<token>/<resource_type>/<filename>')
def serve_patient_resource(token, resource_type, filename):
    """
    Servește resurse (imagini, PDF-uri) din folderul pacientului.
    
    Args:
        token: UUID-ul pacientului
        resource_type: 'images' sau 'pdfs'
        filename: Numele fișierului
    """
    patient_folder = os.path.join('patient_data', token, resource_type)
    return send_from_directory(patient_folder, filename)


@app.server.route('/download_all/<token>')
def download_all_resources(token):
    """
    Creează și servește un ZIP cu toate resursele pacientului (CSV, imagini, PDF-uri).
    
    Args:
        token: UUID-ul pacientului
        
    Returns:
        ZIP file cu toate resursele
    """
    try:
        patient_folder = os.path.join('patient_data', token)
        
        # Creăm ZIP în memorie
        memory_file = io.BytesIO()
        
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Adăugăm CSV-uri
            csv_folder = os.path.join(patient_folder, 'csvs')
            if os.path.exists(csv_folder):
                for filename in os.listdir(csv_folder):
                    if filename.endswith('.csv'):
                        file_path = os.path.join(csv_folder, filename)
                        zf.write(file_path, f'csvs/{filename}')
            
            # Adăugăm imagini
            images_folder = os.path.join(patient_folder, 'images')
            if os.path.exists(images_folder):
                for filename in os.listdir(images_folder):
                    if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                        file_path = os.path.join(images_folder, filename)
                        zf.write(file_path, f'images/{filename}')
            
            # Adăugăm PDF-uri
            pdfs_folder = os.path.join(patient_folder, 'pdfs')
            if os.path.exists(pdfs_folder):
                for filename in os.listdir(pdfs_folder):
                    if filename.endswith('.pdf'):
                        file_path = os.path.join(pdfs_folder, filename)
                        zf.write(file_path, f'pdfs/{filename}')
        
        memory_file.seek(0)
        
        # Generăm numele fișierului ZIP
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        zip_filename = f'Date_Pulsoximetrie_{token[:8]}_{timestamp}.zip'
        
        logger.info(f"📦 ZIP generat pentru {token[:8]}... - {zip_filename}")
        
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=zip_filename
        )
        
    except Exception as e:
        logger.error(f"Eroare la generarea ZIP pentru {token}: {e}", exc_info=True)
        return f"Eroare la generarea arhivei: {str(e)}", 500


# Înregistrăm un mesaj informativ pentru a confirma că instanța a fost creată.
logger.info("Instanța aplicației Dash a fost creată cu succes.")
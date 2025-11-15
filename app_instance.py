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
# CRITICAL: Import librăriile Dash ÎNAINTE de a crea instanța!
# Acest lucru forțează Dash să înregistreze html, dcc, dash_table
# ÎNAINTE de inițializarea app, rezolvând erori 500 pentru asset serving
from dash import html, dcc, dash_table
import os
import io
import zipfile
from flask import send_from_directory, send_file
from datetime import datetime

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
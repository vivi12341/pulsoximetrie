# ==============================================================================
# callbacks.py (VERSIUNEA 2.1 - DIAGNOSTIC ÎMBUNĂTĂȚIT)
# ------------------------------------------------------------------------------
# ROL: Conține toată logica interactivă a aplicației Dash.
#
# MODIFICĂRI CHEIE (v2.1):
#  - DIAGNOSTIC: S-a adăugat un log de nivel DEBUG care afișează primele
#    rânduri ale DataFrame-ului parsat (`df.head()`). Acest lucru permite
#    o inspecție rapidă a datelor imediat după parsare, direct din log-uri.
#  - PĂSTRAT: Toate îmbunătățirile anterioare de logging de performanță și
#    management al erorilor au fost păstrate.
# ==============================================================================

import base64
import os
import threading
import time
import logging # Adăugat pentru a verifica nivelul de logging
import pandas as pd

from dash.dependencies import Input, Output, State
from dash import html, no_update

# Importăm componentele esențiale din arhitectura noastră
from app_instance import app
from logger_setup import logger
import config
from data_parser import parse_csv_data
from plot_generator import create_plot
from batch_processor import run_batch_job

# --- Callback pentru încărcarea și afișarea fișierului CSV ---
@app.callback(
    [Output('interactive-graph', 'figure'),
     Output('output-filename-container', 'children'),
     Output('loaded-data-store', 'data'),
     Output('global-notification-container', 'children')],
    [Input('upload-data-component', 'contents')],
    [State('upload-data-component', 'filename')]
)
def update_graph_on_upload(file_contents, file_name):
    """
    Se declanșează când un utilizator încarcă un fișier.
    Parsează fișierul, generează graficul și stochează datele.
    """
    if file_contents is None:
        return no_update, no_update, no_update, no_update

    # [WHY] Logăm evenimentul de încărcare chiar la începutul execuției.
    logger.info(f"Început procesare pentru fișierul încărcat: {file_name}")
    
    # [WHY] Adăugăm un log de DEBUG pentru a putea inspecta conținutul brut dacă e necesar.
    logger.debug(f"Tip conținut: {file_contents.split(',', 1)[0]}")

    try:
        content_type, content_string = file_contents.split(',')
        decoded_content = base64.b64decode(content_string)

        # [WHY] Logăm momentul exact înainte de a apela parser-ul.
        logger.info("Se apelează `parse_csv_data` pentru validare și curățare date.")
        df = parse_csv_data(decoded_content, file_name)

        # --- LOG NOU PENTRU DIAGNOSTIC DE DATE ---
        # Verificăm dacă logger-ul este setat pe DEBUG pentru a evita procesare inutilă
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Primele 5 rânduri ale DataFrame-ului parsat și curățat:\n{df.head().to_string()}")

        # [WHY] Logăm un sumar al datelor curate înainte de a genera graficul.
        logger.info(f"Date parsate cu succes. {len(df)} rânduri valide. Se apelează `create_plot`.")
        
        # --- LOGGING DE PERFORMANȚĂ (START) ---
        logger.info("Începere generare grafic...")
        start_time = time.time()

        # [WHY] La încărcarea inițială, graficul arată TOT setul de date (zoom out maxim),
        # deci aplicăm scalarea minimă (30%) pentru linii subțiri
        initial_scale = config.ZOOM_SCALE_CONFIG['min_scale']
        logger.info(f"Încărcare inițială: se aplică scalare {initial_scale*100:.0f}% (zoom out maxim).")
        fig = create_plot(df, file_name, line_width_scale=initial_scale, marker_size_scale=initial_scale)
        
        # --- LOGGING DE PERFORMANȚĂ (STOP) ---
        end_time = time.time()
        duration = end_time - start_time
        logger.info(f"Generare grafic finalizată în {duration:.2f} secunde.")

        success_message = html.Div(f"Fișier încărcat cu succes: {file_name}", style={'padding': '10px', 'color': 'green'})
        
        json_data = df.to_json(date_format='iso', orient='split')

        logger.info(f"Procesare completă pentru '{file_name}'. Se returnează figura și datele către UI.")
        
        return fig, success_message, json_data, None

    except Exception as e: # Prindem Exception, este mai robust decât doar ValueError
        # [WHY] Logăm eroarea cu `exc_info=True` pentru a obține un traceback complet în log-uri.
        logger.error(
            f"EROARE CRITICĂ în timpul procesării fișierului '{file_name}': {e}",
            exc_info=True
        )
        
        error_notification = html.Div(
            f"EROARE: Nu s-a putut procesa fișierul '{file_name}'. Verificați log-urile pentru detalii. Mesaj: {e}",
            style={
                'padding': '10px', 'backgroundColor': '#ffdddd', 'border': '1px solid red',
                'borderRadius': '5px', 'color': 'red', 'fontWeight': 'bold', 'margin': '10px 0'
            }
        )
        return {}, None, None, error_notification


# --- Callback pentru pornirea procesului de batch (Neschimbat) ---
@app.callback(
    Output('batch-status-container', 'children'),
    Input('start-batch-button', 'n_clicks'),
    [State('input-folder-path', 'value'),
     State('output-folder-path', 'value'),
     State('window-minutes-input', 'value')]
)
def start_batch_processing(n_clicks, input_folder, output_folder, window_minutes):
    """
    Se declanșează la apăsarea butonului 'Pornește Procesarea în Lot'.
    Pornește funcția de batch într-un thread separat pentru a nu bloca interfața.
    
    [FIX v2.1] Validare defensivă: tratăm None și string gol ca valori invalide
    [WHY] Input-urile controlled pot trimite '' (string gol) în loc de None
    """
    if n_clicks == 0:
        return "Așteptare comenzi pentru procesarea în lot..."

    logger.info("Butonul de pornire batch a fost apăsat.")

    # [FIX v2.1] Validare defensivă pentru input-uri controlled
    # Tratăm atât None cât și string gol ca valori invalide
    if not input_folder or input_folder.strip() == '':
        error_msg = "EROARE: Calea către folderul de intrare este obligatorie."
        logger.error(error_msg)
        return html.Pre(error_msg, style={'color': 'red'})

    if not window_minutes or int(window_minutes) <= 0:
        error_msg = "EROARE: Durata ferestrei trebuie să fie un număr pozitiv."
        logger.error(error_msg)
        return html.Pre(error_msg, style={'color': 'red'})

    # [FIX v2.1] Validare defensivă pentru output_folder (poate fi None sau '')
    if not output_folder or output_folder.strip() == '':
        output_folder = config.OUTPUT_DIR
        logger.info(f"Calea de ieșire nu a fost specificată. Se va folosi calea implicită: '{output_folder}'")

    try:
        os.makedirs(output_folder, exist_ok=True)
    except OSError as e:
        error_msg = f"EROARE: Nu s-a putut crea folderul de ieșire '{output_folder}'. Motiv: {e}"
        logger.error(error_msg)
        return html.Pre(error_msg, style={'color': 'red'})

    batch_thread = threading.Thread(
        target=run_batch_job,
        args=(input_folder, output_folder, window_minutes)
    )
    batch_thread.start()

    status_message = (
        f"Procesarea în lot a început la {os.path.abspath(input_folder)}.\n"
        f"Rezultatele vor fi salvate în {os.path.abspath(output_folder)}.\n\n"
        f"Puteți monitoriza progresul detaliat în consolă sau în fișierul de log:\n"
        f"{os.path.abspath(os.path.join(config.LOGS_DIR, 'app_activity.log'))}\n\n"
        "Aplicația va rămâne funcțională în timpul procesării."
    )
    logger.info("Thread-ul pentru procesarea în lot a fost pornit.")
    return html.Pre(status_message)


# --- Callback pentru Zoom Dinamic (Ajustare Grosime Linie) ---
@app.callback(
    Output('interactive-graph', 'figure', allow_duplicate=True),
    [Input('interactive-graph', 'relayoutData')],
    [State('loaded-data-store', 'data'),
     State('output-filename-container', 'children')],
    prevent_initial_call=True
)
def update_line_width_on_zoom(relayout_data, stored_data, filename_container):
    """
    Callback declanșat când utilizatorul face zoom/pan pe grafic.
    Ajustează dinamic grosimea liniei și dimensiunea markerilor în funcție de nivelul de zoom:
    - Zoom IN (detaliu maxim) → linie GROASĂ (100%)
    - Zoom OUT (vedere completă) → linie SUBȚIRE (30%)
    
    Arhitectură defensivă:
    - Verifică existența datelor și a range-ului valid
    - Calculează nivelul de zoom ca raport între range vizibil și range total
    - Scalează liniară între min_scale (30%) și max_scale (100%)
    """
    # [WHY] Guard clause - verificăm dacă avem toate datele necesare
    if not relayout_data or not stored_data or not filename_container:
        logger.debug("Callback zoom: Date insuficiente, se returnează no_update.")
        return no_update
    
    # [WHY] Extragem numele fișierului din container pentru logging consistent
    try:
        if isinstance(filename_container, dict) and 'props' in filename_container:
            file_name = filename_container['props'].get('children', 'Unknown')
        else:
            file_name = str(filename_container) if filename_container else 'Unknown'
    except:
        file_name = 'Unknown'
    
    logger.debug(f"Callback zoom declanșat pentru '{file_name}'. relayout_data keys: {list(relayout_data.keys())}")
    
    # [WHY] Verificăm dacă avem un eveniment de zoom pe axa X (timpul)
    # Plotly trimite 'xaxis.range[0]' și 'xaxis.range[1]' sau 'xaxis.range' la zoom
    x_range = None
    
    if 'xaxis.range[0]' in relayout_data and 'xaxis.range[1]' in relayout_data:
        x_range = [relayout_data['xaxis.range[0]'], relayout_data['xaxis.range[1]']]
    elif 'xaxis.range' in relayout_data:
        x_range = relayout_data['xaxis.range']
    elif 'autosize' in relayout_data or 'xaxis.autorange' in relayout_data:
        # [WHY] La reset (double-click), revin la scalarea maximă (100%)
        logger.info(f"Reset/autoscale detectat pentru '{file_name}'. Se aplică scalare 100%.")
        x_range = None  # Va fi tratat mai jos
    
    # [WHY] Dacă nu este un eveniment de zoom relevant, ignorăm
    if x_range is None and 'autosize' not in relayout_data and 'xaxis.autorange' not in relayout_data:
        logger.debug("Eveniment relayout fără modificare zoom X. Se ignoră.")
        return no_update
    
    # [WHY] Deserializăm datele stocate
    try:
        df = pd.read_json(stored_data, orient='split')
        df.index = pd.to_datetime(df.index)
    except Exception as e:
        logger.error(f"Eroare la deserializare date din store: {e}", exc_info=True)
        return no_update
    
    if df.empty or len(df) < 2:
        logger.warning("DataFrame gol sau insuficient în store. Se returnează no_update.")
        return no_update
    
    # [WHY] Calculăm range-ul total al datelor (în milisecunde pentru calcul precis)
    total_start = df.index.min()
    total_end = df.index.max()
    total_duration_ms = (total_end - total_start).total_seconds() * 1000
    
    if total_duration_ms <= 0:
        logger.warning("Durată totală invalidă în date. Se returnează no_update.")
        return no_update
    
    # [WHY] Calculăm nivelul de zoom
    if x_range is None:
        # Reset/autorange - presupunem că vedem tot
        zoom_ratio = 1.0
        logger.debug("Range X absent (autorange). Presupunem zoom_ratio=1.0 (vedere completă).")
    else:
        # [WHY] Convertim range-ul vizibil în timestamps
        try:
            visible_start = pd.to_datetime(x_range[0])
            visible_end = pd.to_datetime(x_range[1])
            visible_duration_ms = (visible_end - visible_start).total_seconds() * 1000
            
            # [WHY] Calculăm raportul: ce procent din date e vizibil
            # zoom_ratio = 1.0 (100%) = tot vizibil (zoom out maxim)
            # zoom_ratio = 0.1 (10%) = doar 10% vizibil (zoom in 10x)
            zoom_ratio = visible_duration_ms / total_duration_ms
            zoom_ratio = max(0.01, min(1.0, zoom_ratio))  # Clamp între 1% și 100%
            
            logger.debug(f"Calcul zoom: visible_duration={visible_duration_ms:.0f}ms, total={total_duration_ms:.0f}ms, ratio={zoom_ratio:.3f}")
        except Exception as e:
            logger.error(f"Eroare la calculul zoom ratio: {e}", exc_info=True)
            return no_update
    
    # [WHY] Calculăm factorul de scalare inversă
    # zoom_ratio mare (aproape 1.0) → vedem mult → linie SUBȚIRE (30%)
    # zoom_ratio mic (aproape 0) → vedem puțin → linie GROASĂ (100%)
    zoom_config = config.ZOOM_SCALE_CONFIG
    min_scale = zoom_config['min_scale']
    max_scale = zoom_config['max_scale']
    
    # Scalare liniară inversă:
    # zoom_ratio=1.0 (tot vizibil) → scale=min_scale (30%)
    # zoom_ratio=0.0 (aproape nimic vizibil) → scale=max_scale (100%)
    scale_factor = max_scale - (zoom_ratio * (max_scale - min_scale))
    scale_factor = max(min_scale, min(max_scale, scale_factor))  # Siguranță
    
    logger.info(f"Zoom dinamic: ratio={zoom_ratio:.3f}, scale_factor={scale_factor:.3f} ({scale_factor*100:.1f}%)")
    
    # [WHY] Regenerăm figura cu noii parametri de scalare
    try:
        logger.debug("Regenerare figură cu noul scale_factor...")
        fig = create_plot(df, file_name, line_width_scale=scale_factor, marker_size_scale=scale_factor)
        
        # [WHY] CRITIC: Trebuie să aplicăm ACELAȘI range de zoom pe noua figură
        # Altfel, graficul se va reseta la vedere completă
        # Aplicăm pe ambele axe X (row=1,col=2 și row=2,col=2) deși sunt shared
        if x_range is not None:
            fig.update_xaxes(range=x_range, row=1, col=2)
            fig.update_xaxes(range=x_range, row=2, col=2)
        
        logger.info(f"Figură regenerată cu succes cu scale_factor={scale_factor:.3f}")
        return fig
    except Exception as e:
        logger.error(f"Eroare la regenerarea figurii în callback zoom: {e}", exc_info=True)
        return no_update
# ==============================================================================
# callbacks.py
# ------------------------------------------------------------------------------
# ROL: Conține toată logica interactivă a aplicației Dash. Leagă acțiunile
#      utilizatorului (input-uri) de rezultatele afișate (output-uri).
#      Acest modul este 'creierul' care face aplicația să funcționeze.
# ==============================================================================

import base64
import os
import threading # Folosim threading pentru a rula procesul de batch în fundal

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
    Parsează fișierul, generează graficul inițial și stochează datele.
    """
    # Dacă nu s-a încărcat niciun fișier, nu actualizăm nimic
    if file_contents is None:
        return no_update, no_update, no_update, no_update

    logger.info(f"Detectat fișier încărcat: {file_name}")

    # Decodăm conținutul fișierului din Base64
    content_type, content_string = file_contents.split(',')
    decoded_content = base64.b64decode(content_string)

    try:
        # Folosim modulul de parsare pentru a obține un DataFrame curat
        df = parse_csv_data(decoded_content, file_name)

        # Generăm graficul inițial cu toate datele
        fig = create_plot(df, file_name)

        # Creăm un mesaj de succes și afișăm numele fișierului
        success_message = html.Div(f"Fișier încărcat cu succes: {file_name}", style={'padding': '10px', 'color': 'green'})
        
        # Convertim DataFrame-ul în format JSON pentru a-l stoca în dcc.Store
        # Acest lucru permite altor callback-uri să acceseze datele fără a re-parsa fișierul.
        json_data = df.to_json(date_format='iso', orient='split')

        logger.info(f"Fișierul '{file_name}' a fost procesat și afișat cu succes.")
        
        return fig, success_message, json_data, None # None la notificări, deoarece avem mesaj de succes local

    except ValueError as e:
        # Dacă parsarea eșuează, afișăm o notificare de eroare
        logger.error(f"Eroare la procesarea fișierului '{file_name}': {e}")
        error_notification = html.Div(
            f"EROARE: Nu s-a putut procesa fișierul '{file_name}'. Motiv: {e}",
            style={
                'padding': '10px', 'backgroundColor': '#ffdddd', 'border': '1px solid red',
                'borderRadius': '5px', 'color': 'red', 'fontWeight': 'bold'
            }
        )
        # Resetăm graficul, numele fișierului și datele stocate
        return {}, None, None, error_notification


# --- Callback pentru pornirea procesului de batch ---
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
    """
    # Se declanșează doar dacă butonul a fost apăsat
    if n_clicks == 0:
        return "Așteptare comenzi pentru procesarea în lot..."

    logger.info("Butonul de pornire batch a fost apăsat.")

    # --- Validare input-uri ---
    if not input_folder:
        error_msg = "EROARE: Calea către folderul de intrare este obligatorie."
        logger.error(error_msg)
        return html.Pre(error_msg, style={'color': 'red'})

    if not window_minutes or int(window_minutes) <= 0:
        error_msg = "EROARE: Durata ferestrei trebuie să fie un număr pozitiv."
        logger.error(error_msg)
        return html.Pre(error_msg, style={'color': 'red'})

    # Folosim calea de output default din config dacă nu este specificată una
    if not output_folder:
        output_folder = config.OUTPUT_DIR
        logger.info(f"Calea de ieșire nu a fost specificată. Se va folosi calea implicită: '{output_folder}'")

    # Ne asigurăm că folderul de output există
    try:
        os.makedirs(output_folder, exist_ok=True)
    except OSError as e:
        error_msg = f"EROARE: Nu s-a putut crea folderul de ieșire '{output_folder}'. Motiv: {e}"
        logger.error(error_msg)
        return html.Pre(error_msg, style={'color': 'red'})

    # --- Pornirea procesului în fundal ---
    # Creăm un thread care va rula funcția grea `run_batch_job`.
    # Acest lucru este ESENȚIAL pentru ca interfața web să nu înghețe.
    batch_thread = threading.Thread(
        target=run_batch_job,
        args=(input_folder, output_folder, window_minutes)
    )
    batch_thread.start()

    # Returnăm un mesaj de confirmare imediat către utilizator
    status_message = (
        f"Procesarea în lot a început la {os.path.abspath(input_folder)}.\n"
        f"Rezultatele vor fi salvate în {os.path.abspath(output_folder)}.\n\n"
        f"Puteți monitoriza progresul detaliat în consolă sau în fișierul de log:\n"
        f"{os.path.abspath(os.path.join(config.LOGS_DIR, 'app_activity.log'))}\n\n"
        "Aplicația va rămâne funcțională în timpul procesării."
    )
    logger.info("Thread-ul pentru procesarea în lot a fost pornit.")
    return html.Pre(status_message)
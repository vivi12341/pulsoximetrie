# ==============================================================================
# callbacks_medical.py (WORKFLOW MEDICAL)
# ------------------------------------------------------------------------------
# ROL: Callbacks pentru funcționalitatea medical workflow:
#      - Admin: Creare link-uri, upload CSV pentru pacienți
#      - Pacient: Acces înregistrări, explorare CSV temporară
#
# RESPECTĂ: .cursorrules - Privacy by Design, Logging comprehensiv
# ==============================================================================

import base64
import pandas as pd
import os
import plotly.graph_objects as go
from dash.dependencies import Input, Output, State, ALL
from dash import html, no_update, dcc
from datetime import datetime

from app_instance import app
from logger_setup import logger
import patient_links
from data_parser import parse_csv_data
from plot_generator import create_plot
from batch_processor import run_batch_job
import config


# ==============================================================================
# CALLBACK ROUTING - DETECTARE TOKEN ȘI AFIȘARE LAYOUT
# ==============================================================================

@app.callback(
    [Output('dynamic-layout-container', 'children'),
     Output('url-token-detected', 'data')],
    [Input('url', 'search')]
)
def route_layout_based_on_url(search):
    """
    Detectează dacă URL conține token și afișează layout-ul corespunzător:
    - Cu token (?token=xxx) → Layout simplificat pentru PACIENȚI
    - Fără token → Layout complet pentru MEDICI (cu tab-uri)
    """
    from app_layout_new import medical_layout, patient_layout
    
    # Verificăm dacă există token în URL
    if search and 'token=' in search:
        # Extragem token-ul din URL
        try:
            token = search.split('token=')[1].split('&')[0]
            logger.info(f"🔵 Acces pacient detectat cu token: {token[:8]}...")
            
            # Validăm token-ul
            if patient_links.validate_token(token):
                logger.info(f"✅ Token valid: {token[:8]}... → Afișare layout pacient")
                return patient_layout, token
            else:
                logger.warning(f"⚠️ Token invalid: {token[:8]}...")
                return html.Div([
                    html.H2("❌ Acces Interzis", style={'color': 'red', 'textAlign': 'center', 'marginTop': '50px'}),
                    html.P("Token-ul este invalid sau a expirat. Contactați medicul dumneavoastră.", 
                           style={'textAlign': 'center', 'color': '#666'})
                ], style={'padding': '50px'}), None
                
        except Exception as e:
            logger.error(f"Eroare la extragerea token-ului din URL: {e}", exc_info=True)
            return medical_layout, None
    
    # Fără token → Layout pentru medici
    logger.debug("🏥 Acces medic detectat (fără token) → Afișare layout complet")
    return medical_layout, None


def format_recording_date_ro(recording_date, start_time, end_time):
    """
    Formatează data înregistrării în format citibil românesc:
    "Marți 14 octombrie 2025 de la ora 20:32 până în Miercuri 15 octombrie 2025 la ora 04:45"
    """
    from datetime import datetime
    
    # Zile săptămână în română
    days_ro = {
        0: 'Luni', 1: 'Marți', 2: 'Miercuri', 3: 'Joi',
        4: 'Vineri', 5: 'Sâmbătă', 6: 'Duminică'
    }
    
    # Luni în română
    months_ro = {
        1: 'ianuarie', 2: 'februarie', 3: 'martie', 4: 'aprilie',
        5: 'mai', 6: 'iunie', 7: 'iulie', 8: 'august',
        9: 'septembrie', 10: 'octombrie', 11: 'noiembrie', 12: 'decembrie'
    }
    
    try:
        # Parsăm data și ora de început
        start_datetime = datetime.strptime(f"{recording_date} {start_time}", "%Y-%m-%d %H:%M")
        
        # Pentru ora de sfârșit, trebuie să determinăm data corectă
        # Dacă ora de sfârșit < ora de început, înseamnă că a trecut la ziua următoare
        end_hour = int(end_time.split(':')[0])
        start_hour = int(start_time.split(':')[0])
        
        if end_hour < start_hour:
            # A trecut la ziua următoare
            from datetime import timedelta
            end_date = start_datetime.date() + timedelta(days=1)
            end_datetime = datetime.strptime(f"{end_date} {end_time}", "%Y-%m-%d %H:%M")
        else:
            # Aceeași zi
            end_datetime = datetime.strptime(f"{recording_date} {end_time}", "%Y-%m-%d %H:%M")
        
        # Formatăm data de început
        start_day_name = days_ro[start_datetime.weekday()]
        start_day = start_datetime.day
        start_month = months_ro[start_datetime.month]
        start_year = start_datetime.year
        start_hour_minute = start_datetime.strftime("%H:%M")
        
        # Formatăm data de sfârșit
        end_day_name = days_ro[end_datetime.weekday()]
        end_day = end_datetime.day
        end_month = months_ro[end_datetime.month]
        end_year = end_datetime.year
        end_hour_minute = end_datetime.strftime("%H:%M")
        
        # Construim textul final
        if start_datetime.date() == end_datetime.date():
            # Aceeași zi
            formatted = f"{start_day_name} {start_day} {start_month} {start_year} de la ora {start_hour_minute} până la ora {end_hour_minute}"
        else:
            # Zile diferite
            formatted = f"{start_day_name} {start_day} {start_month} {start_year} de la ora {start_hour_minute} până în {end_day_name} {end_day} {end_month} {end_year} la ora {end_hour_minute}"
        
        return formatted
        
    except Exception as e:
        logger.error(f"Eroare la formatarea datei: {e}", exc_info=True)
        return f"{recording_date} | {start_time} - {end_time}"


@app.callback(
    [Output('patient-data-view', 'children'),
     Output('patient-main-graph', 'figure')],
    [Input('url-token-detected', 'data')]
)
def load_patient_data_from_token(token):
    """
    Încarcă automat datele pacientului când token-ul este detectat în URL.
    """
    if not token:
        return no_update, no_update
    
    logger.info(f"📊 Încărcare date pentru pacient: {token[:8]}...")
    
    try:
        # Tracking vizualizare
        patient_links.track_link_view(token)
        
        # Preluăm metadata pacientului
        patient_data = patient_links.get_patient_link(token, track_view=False)  # Track deja făcut
        
        if not patient_data:
            error_msg = html.Div([
                html.H3("⚠️ Date Indisponibile", style={'color': 'orange'}),
                html.P("Nu s-au găsit date pentru acest token.")
            ], style={'padding': '20px', 'textAlign': 'center'})
            return error_msg, go.Figure()
        
        # Formatăm data în română
        formatted_date = format_recording_date_ro(
            patient_data.get('recording_date', ''),
            patient_data.get('start_time', ''),
            patient_data.get('end_time', '')
        )
        
        # Construim info card (FĂRĂ vizualizări - doar pentru medici!)
        info_card = html.Div([
            # Data înregistrării (MAI ÎNTÂI)
            html.Div([
                html.Strong("📅 ", style={'fontSize': '18px'}),
                html.Span(formatted_date, style={'fontSize': '16px', 'color': '#2c3e50'})
            ], style={'marginBottom': '15px'}),
            
            # Numărul aparatului (AL DOILEA)
            html.Div([
                html.Strong("🔧 Aparat: ", style={'color': '#555'}),
                html.Span(patient_data.get('device_name', 'Aparat Necunoscut'))
            ], style={'marginBottom': '10px'}),
            
            # Notițe medicale (dacă există)
            html.Div([
                html.Hr(style={'margin': '20px 0'}),
                html.H4("📝 Notițe Medicale", style={'color': '#2980b9'}),
                html.P(
                    patient_data.get('medical_notes') or 'Nu există notițe medicale.',
                    style={
                        'padding': '15px',
                        'backgroundColor': '#fff3cd' if patient_data.get('medical_notes') else '#f8f9fa',
                        'borderRadius': '5px',
                        'border': '1px solid #ffc107' if patient_data.get('medical_notes') else '1px solid #dee2e6',
                        'whiteSpace': 'pre-wrap'
                    }
                )
            ]) if patient_data.get('medical_notes') else None
            
        ], style={
            'padding': '25px',
            'backgroundColor': '#fff',
            'borderRadius': '10px',
            'boxShadow': '0 2px 8px rgba(0,0,0,0.1)',
            'marginBottom': '20px'
        })
        
        # TODO: Încărcăm CSV-ul și generăm graficul
        # Deocamdată returnăm un grafic gol - va fi implementat când adăugăm stocarea CSV
        empty_fig = go.Figure()
        empty_fig.update_layout(
            title="Graficul va fi disponibil în curând",
            xaxis_title="Timp",
            yaxis_title="SpO2 (%)",
            height=500
        )
        
        logger.info(f"✅ Date încărcate cu succes pentru pacient {token[:8]}...")
        return info_card, empty_fig
        
    except Exception as e:
        logger.error(f"Eroare la încărcarea datelor pacientului: {e}", exc_info=True)
        error_msg = html.Div([
            html.H3("❌ Eroare", style={'color': 'red'}),
            html.P(f"A apărut o eroare: {str(e)}")
        ], style={'padding': '20px', 'textAlign': 'center'})
        return error_msg, go.Figure()


# ==============================================================================
# CALLBACKS ADMIN - DASHBOARD MEDICAL PROFESIONAL
# ==============================================================================

@app.callback(
    [Output('admin-batch-result', 'children'),
     Output('admin-refresh-trigger', 'data')],
    [Input('admin-start-batch-button', 'n_clicks')],
    [State('admin-batch-input-folder', 'value'),
     State('admin-batch-output-folder', 'value'),
     State('admin-batch-window-minutes', 'value')]
)
def admin_run_batch_processing(n_clicks, input_folder, output_folder, window_minutes):
    """
    Callback pentru procesare batch + generare automată link-uri.
    """
    if n_clicks == 0:
        return no_update, no_update
    
    if not input_folder or input_folder.strip() == '':
        return html.Div(
            "⚠️ Specificați folderul de intrare!",
            style={'padding': '15px', 'backgroundColor': '#fff3cd', 'border': '1px solid #ffc107', 'borderRadius': '5px'}
        ), no_update
    
    # Folosim folder default pentru output dacă nu e specificat
    if not output_folder or output_folder.strip() == '':
        output_folder = config.OUTPUT_DIR
    
    logger.info(f"🚀 Admin pornește procesare batch: {input_folder} → {output_folder}")
    
    try:
        # Validăm existența folderului
        if not os.path.exists(input_folder):
            return html.Div(
                f"❌ Folderul de intrare nu există: {input_folder}",
                style={'padding': '15px', 'backgroundColor': '#ffdddd', 'border': '1px solid red', 'borderRadius': '5px', 'color': 'red'}
            ), no_update
        
        # Rulăm procesarea batch (returnează lista de link-uri generate)
        generated_links = run_batch_job(input_folder, output_folder, window_minutes)
        
        if not generated_links:
            return html.Div([
                html.H4("⚠️ Procesare Finalizată, Dar Fără Link-uri Generate", style={'color': 'orange'}),
                html.P("Verificați dacă există fișiere CSV valide în folder și log-urile pentru detalii.")
            ], style={'padding': '20px', 'backgroundColor': '#fff3cd', 'border': '1px solid #ffc107', 'borderRadius': '10px'}), n_clicks
        
        # Construim mesajul de succes cu lista de link-uri
        link_rows = []
        for link in generated_links:
            link_url = f"http://127.0.0.1:8050/?token={link['token']}"
            link_rows.append(
                html.Div([
                    html.Strong(f"📅 {link['recording_date']} | {link['start_time']} - {link['end_time']}", style={'display': 'block', 'marginBottom': '5px'}),
                    html.Small(f"🔧 {link['device_name']} | 🖼️ {link['images_count']} imagini", style={'color': '#666', 'display': 'block', 'marginBottom': '5px'}),
                    html.Div([
                        html.Code(
                            link_url,
                            style={'backgroundColor': '#f0f0f0', 'padding': '5px', 'fontSize': '11px', 'display': 'block', 'wordBreak': 'break-all'}
                        )
                    ], style={'marginBottom': '5px'}),
                    html.Small(f"Token: {link['token'][:16]}...", style={'color': '#95a5a6', 'fontSize': '10px'})
                ], style={
                    'padding': '15px',
                    'marginBottom': '10px',
                    'backgroundColor': '#e8f5e9',
                    'borderRadius': '5px',
                    'border': '1px solid #27ae60'
                })
            )
        
        return html.Div([
            html.H4(f"✅ Procesare Batch Finalizată Cu Succes!", style={'color': 'green'}),
            html.P(f"🔗 {len(generated_links)} link-uri generate automat:"),
            html.Hr(),
            html.Div(link_rows, style={'maxHeight': '400px', 'overflowY': 'auto'})
        ], style={'padding': '20px', 'backgroundColor': '#d4edda', 'border': '1px solid #28a745', 'borderRadius': '10px'}), n_clicks
        
    except Exception as e:
        logger.error(f"Eroare la procesare batch: {e}", exc_info=True)
        return html.Div(
            f"❌ EROARE: {str(e)}",
            style={'padding': '15px', 'backgroundColor': '#ffdddd', 'border': '1px solid red', 'borderRadius': '5px', 'color': 'red'}
        ), no_update


@app.callback(
    [Output('data-view-container', 'children'),
     Output('expanded-row-id', 'data')],
    [Input('admin-refresh-data-view', 'n_clicks'),
     Input('admin-refresh-trigger', 'data'),
     Input({'type': 'expand-row-btn', 'index': ALL}, 'n_clicks')],
    [State('expanded-row-id', 'data'),
     State({'type': 'expand-row-btn', 'index': ALL}, 'id')]
)
def load_data_view_with_accordion(n_clicks_refresh, trigger, expand_clicks, expanded_id, expand_btn_ids):
    """
    Încarcă vizualizarea datelor cu funcționalitate accordion (expandare/colapsare).
    """
    from dash import ctx
    import base64
    
    logger.debug("Callback data-view apelat.")
    
    # Determinăm care rând trebuie expandat
    current_expanded = expanded_id
    
    # Verificăm dacă s-a dat click pe un buton de expandare
    if ctx.triggered_id and isinstance(ctx.triggered_id, dict) and ctx.triggered_id.get('type') == 'expand-row-btn':
        clicked_token = ctx.triggered_id['index']
        # Toggle: dacă e deja expandat, îl închidem; altfel îl deschidem
        if current_expanded == clicked_token:
            current_expanded = None
        else:
            current_expanded = clicked_token
    
    try:
        all_links = patient_links.get_all_links_for_admin()
        
        if not all_links:
            return html.Div(
                "📭 Nu există înregistrări încă. Procesați fișiere CSV din tab-ul 'Procesare Batch'.",
                style={'padding': '50px', 'textAlign': 'center', 'color': '#666', 'fontStyle': 'italic', 'backgroundColor': '#f8f9fa', 'borderRadius': '10px'}
            )
        
        # Construim lista de rânduri cu funcționalitate accordion
        rows = []
        for link_data in all_links:
            token = link_data['token']
            is_expanded = (current_expanded == token)
            
            # Formatare dată
            date_display = "Data nespecificată"
            if link_data.get('recording_date'):
                date_display = format_recording_date_ro(
                    link_data.get('recording_date', ''),
                    link_data.get('start_time', ''),
                    link_data.get('end_time', '')
                )
            
            # Status vizualizări
            view_count = link_data.get('view_count', 0)
            view_display = f"👁️ {view_count}"
            
            # Iconița pentru expand/collapse
            expand_icon = "▼" if is_expanded else "▶"
            
            # === RÂND COMPACT (întotdeauna vizibil) - CLICKABIL PE ÎNTREAGA LINIE ===
            compact_row = html.Button(
                children=[
                    # Iconița expand/collapse
                    html.Span(
                        expand_icon,
                        style={
                            'display': 'inline-block',
                            'marginRight': '15px',
                            'padding': '5px 15px',
                            'backgroundColor': '#3498db' if is_expanded else '#95a5a6',
                            'color': 'white',
                            'borderRadius': '5px',
                            'fontSize': '14px',
                            'fontWeight': 'bold',
                            'minWidth': '40px',
                            'textAlign': 'center'
                        }
                    ),
                    
                    # Info condensată
                    html.Div([
                        html.Strong(f"📅 {date_display}", style={'fontSize': '15px', 'color': '#2c3e50', 'display': 'block'}),
                        html.Small(f"🔧 {link_data['device_name']} | {view_display}", style={'color': '#7f8c8d', 'display': 'block', 'marginTop': '3px'})
                    ], style={'flex': '1', 'textAlign': 'left'})
                ],
                id={'type': 'expand-row-btn', 'index': token},
                n_clicks=0,
                style={
                    'width': '100%',
                    'display': 'flex',
                    'alignItems': 'center',
                    'padding': '15px',
                    'backgroundColor': '#ecf0f1' if not is_expanded else '#d5dbdb',
                    'border': 'none',
                    'borderRadius': '8px',
                    'cursor': 'pointer',
                    'transition': 'all 0.2s ease',
                    'boxShadow': '0 1px 3px rgba(0,0,0,0.05)',
                    # Hover effect
                    ':hover': {
                        'backgroundColor': '#dfe4ea',
                        'boxShadow': '0 2px 6px rgba(0,0,0,0.1)'
                    }
                }
            )
            
            # === DETALII EXPANDATE (vizibil doar când is_expanded=True) ===
            expanded_content = None
            if is_expanded:
                # Încărcăm imaginile pentru rândul expandat
                images_content = [html.P("Nu există imagini disponibile.", style={'color': '#666', 'fontStyle': 'italic'})]
                
                # Încercăm să găsim folderul cu imagini pentru această înregistrare
                try:
                    # Verificăm dacă avem calea stocată în metadata
                    output_folder_path = link_data.get('output_folder_path')
                    
                    if output_folder_path and os.path.exists(output_folder_path):
                        # Găsim imaginile din folder
                        image_files = [f for f in os.listdir(output_folder_path) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
                        
                        if image_files:
                            # Sortăm imaginile alfabetic
                            image_files.sort()
                            
                            # Creăm galerie de imagini
                            images_content = []
                            images_count = len(image_files)
                            
                            # Adăugăm header cu număr imagini
                            images_content.append(
                                html.P(
                                    f"📊 {images_count} imagini generate",
                                    style={'fontSize': '14px', 'color': '#2c3e50', 'fontWeight': 'bold', 'marginBottom': '15px'}
                                )
                            )
                            
                            # Creăm vizualizarea desfășurată (LIST VIEW - default)
                            for img_file in image_files:
                                img_path = os.path.join(output_folder_path, img_file)
                                try:
                                    with open(img_path, 'rb') as img_f:
                                        img_data = base64.b64encode(img_f.read()).decode()
                                        images_content.append(
                                            html.Div([
                                                html.Img(
                                                    src=f'data:image/jpeg;base64,{img_data}',
                                                    style={
                                                        'width': '100%',
                                                        'maxWidth': '900px',
                                                        'borderRadius': '8px',
                                                        'boxShadow': '0 2px 8px rgba(0,0,0,0.15)',
                                                        'marginBottom': '10px',
                                                        'border': '1px solid #ddd',
                                                        'display': 'block',
                                                        'marginLeft': 'auto',
                                                        'marginRight': 'auto'
                                                    }
                                                ),
                                                html.P(
                                                    img_file,
                                                    style={
                                                        'fontSize': '13px',
                                                        'color': '#7f8c8d',
                                                        'textAlign': 'center',
                                                        'marginBottom': '25px',
                                                        'fontFamily': 'monospace'
                                                    }
                                                )
                                            ], className='image-item', **{'data-img-src': f'data:image/jpeg;base64,{img_data}', 'data-img-name': img_file})
                                        )
                                except Exception as img_err:
                                    logger.error(f"Eroare la încărcarea imaginii {img_file}: {img_err}")
                        else:
                            images_content = [html.P(
                                f"Nu s-au găsit imagini în folderul: {output_folder_path}",
                                style={'color': '#e74c3c', 'fontStyle': 'italic'}
                            )]
                    else:
                        # Fallback: încercăm să găsim folderul după numărul aparatului
                        output_base = config.OUTPUT_DIR
                        if os.path.exists(output_base):
                            device_num = link_data['device_name'].split('#')[-1] if '#' in link_data['device_name'] else ''
                            
                            for folder_name in os.listdir(output_base):
                                folder_path = os.path.join(output_base, folder_name)
                                if os.path.isdir(folder_path) and device_num in folder_name:
                                    image_files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
                                    if image_files:
                                        image_files.sort()
                                        images_content = []
                                        
                                        images_content.append(
                                            html.P(
                                                f"📊 {len(image_files)} imagini găsite (căutare automată)",
                                                style={'fontSize': '14px', 'color': '#f39c12', 'fontWeight': 'bold', 'marginBottom': '15px'}
                                            )
                                        )
                                        
                                        for img_file in image_files:
                                            img_path = os.path.join(folder_path, img_file)
                                            try:
                                                with open(img_path, 'rb') as img_f:
                                                    img_data = base64.b64encode(img_f.read()).decode()
                                                    images_content.append(
                                                        html.Div([
                                                            html.Img(
                                                                src=f'data:image/jpeg;base64,{img_data}',
                                                                style={
                                                                    'width': '100%',
                                                                    'maxWidth': '900px',
                                                                    'borderRadius': '8px',
                                                                    'boxShadow': '0 2px 8px rgba(0,0,0,0.15)',
                                                                    'marginBottom': '10px',
                                                                    'border': '1px solid #ddd'
                                                                }
                                                            ),
                                                            html.P(
                                                                img_file,
                                                                style={
                                                                    'fontSize': '13px',
                                                                    'color': '#7f8c8d',
                                                                    'textAlign': 'center',
                                                                    'marginBottom': '25px',
                                                                    'fontFamily': 'monospace'
                                                                }
                                                            )
                                                        ])
                                                    )
                                            except Exception as img_err:
                                                logger.error(f"Eroare la încărcarea imaginii {img_file}: {img_err}")
                                        break
                        
                except Exception as e:
                    logger.error(f"Eroare la căutarea imaginilor pentru {token[:8]}...: {e}", exc_info=True)
                    images_content = [html.P(
                        f"⚠️ Eroare la încărcarea imaginilor: {str(e)}",
                        style={'color': '#e74c3c', 'fontStyle': 'italic'}
                    )]
                
                expanded_content = html.Div([
                    html.Hr(style={'margin': '15px 0', 'border': 'none', 'borderTop': '2px solid #bdc3c7'}),
                    
                    # Secțiune grafic interactiv (TODO: va fi implementat cu CSV stocat)
                    html.Div([
                        html.H4("📈 Grafic Interactiv", style={'color': '#2980b9', 'marginBottom': '10px'}),
                        html.P(
                            "Graficul interactiv va fi disponibil după implementarea stocării CSV-urilor.",
                            style={'color': '#666', 'fontStyle': 'italic', 'fontSize': '14px'}
                        )
                    ], style={'marginBottom': '25px', 'padding': '20px', 'backgroundColor': '#f8f9fa', 'borderRadius': '8px'}),
                    
                    # Secțiune imagini generate cu toggle view
                    html.Div([
                        # Header cu butoane toggle
                        html.Div([
                            html.H4("🖼️ Imagini Generate", style={'color': '#2980b9', 'marginBottom': '0', 'display': 'inline-block', 'marginRight': '20px'}),
                            html.Div([
                                html.Button(
                                    '📊 Ansamblu',
                                    id={'type': 'view-grid-btn', 'index': token},
                                    n_clicks=0,
                                    style={
                                        'padding': '8px 20px',
                                        'marginRight': '10px',
                                        'backgroundColor': '#95a5a6',
                                        'color': 'white',
                                        'border': 'none',
                                        'borderRadius': '5px',
                                        'cursor': 'pointer',
                                        'fontSize': '13px',
                                        'fontWeight': 'bold',
                                        'transition': 'all 0.2s'
                                    }
                                ),
                                html.Button(
                                    '📄 Desfășurat',
                                    id={'type': 'view-list-btn', 'index': token},
                                    n_clicks=0,
                                    style={
                                        'padding': '8px 20px',
                                        'backgroundColor': '#27ae60',
                                        'color': 'white',
                                        'border': 'none',
                                        'borderRadius': '5px',
                                        'cursor': 'pointer',
                                        'fontSize': '13px',
                                        'fontWeight': 'bold',
                                        'transition': 'all 0.2s',
                                        'boxShadow': '0 2px 4px rgba(0,0,0,0.2)'
                                    }
                                )
                            ], style={'display': 'inline-block', 'verticalAlign': 'middle'})
                        ], style={'marginBottom': '15px', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between'}),
                        
                        # Container pentru imagini (va fi populat dinamic)
                        html.Div(
                            id={'type': 'images-display-container', 'index': token},
                            children=images_content
                        )
                    ], style={'marginBottom': '25px'}),
                    
                    # Secțiune raport PDF
                    html.Div([
                        html.H4("📄 Raport PDF", style={'color': '#2980b9', 'marginBottom': '10px'}),
                        html.Div(
                            children=[
                                html.P(
                                    "📎 Funcționalitate PDF în dezvoltare - Veți putea încărca și vizualiza rapoarte PDF aici.",
                                    style={'color': '#666', 'fontStyle': 'italic', 'marginBottom': '15px'}
                                ),
                                html.Div([
                                    dcc.Upload(
                                        id={'type': 'pdf-upload', 'index': token},
                                        children=html.Div([
                                            '📁 Click pentru a încărca PDF (viitor)'
                                        ]),
                                        style={
                                            'width': '100%',
                                            'height': '60px',
                                            'lineHeight': '60px',
                                            'borderWidth': '2px',
                                            'borderStyle': 'dashed',
                                            'borderRadius': '8px',
                                            'textAlign': 'center',
                                            'backgroundColor': '#f8f9fa',
                                            'color': '#95a5a6',
                                            'cursor': 'not-allowed',
                                            'opacity': '0.6'
                                        },
                                        disabled=True  # Disabled până la implementare completă
                                    )
                                ])
                            ]
                        )
                    ], style={'marginBottom': '25px', 'padding': '20px', 'backgroundColor': '#f8f9fa', 'borderRadius': '8px'}),
                    
                    # Secțiune interpretare medicală
                    html.Div([
                        html.H4("📝 Interpretare Medicală", style={'color': '#2980b9', 'marginBottom': '10px'}),
                        dcc.Textarea(
                            id={'type': 'medical-interpretation', 'index': token},
                            value=link_data.get('medical_notes', ''),
                            placeholder='Scrieți interpretarea medicală aici (ex: Episoade de desaturare nocturnă, apnee obstructivă severă, recomand CPAP)...',
                            style={
                                'width': '100%',
                                'minHeight': '120px',
                                'padding': '15px',
                                'border': '2px solid #3498db',
                                'borderRadius': '8px',
                                'fontSize': '14px',
                                'fontFamily': 'Arial, sans-serif'
                            }
                        ),
                        html.Button(
                            '💾 Salvează Interpretare',
                            id={'type': 'save-interpretation-btn', 'index': token},
                            n_clicks=0,
                            style={
                                'marginTop': '10px',
                                'padding': '10px 25px',
                                'backgroundColor': '#27ae60',
                                'color': 'white',
                                'border': 'none',
                                'borderRadius': '5px',
                                'cursor': 'pointer',
                                'fontWeight': 'bold'
                            }
                        ),
                        html.Span(
                            id={'type': 'save-interpretation-feedback', 'index': token},
                            style={'marginLeft': '15px', 'color': 'green', 'fontWeight': 'bold'}
                        )
                    ], style={'marginBottom': '25px'}),
                    
                    # Link către pacient
                    html.Div([
                        html.Hr(style={'margin': '20px 0'}),
                        html.Strong("🔗 Link Pacient: ", style={'marginRight': '10px'}),
                        dcc.Input(
                            value=f"http://127.0.0.1:8050/?token={token}",
                            readOnly=True,
                            style={
                                'width': '70%',
                                'padding': '8px',
                                'backgroundColor': '#ecf0f1',
                                'border': '1px solid #bdc3c7',
                                'borderRadius': '5px',
                                'fontSize': '12px',
                                'fontFamily': 'monospace'
                            }
                        )
                    ])
                    
                ], style={
                    'padding': '25px',
                    'backgroundColor': '#ffffff',
                    'borderRadius': '8px',
                    'marginTop': '10px',
                    'boxShadow': 'inset 0 2px 8px rgba(0,0,0,0.05)'
                })
            
            # Combinăm rândul compact + detaliile expandate
            row_container = html.Div([
                compact_row,
                expanded_content if expanded_content else None
            ], style={
                'marginBottom': '15px',
                'backgroundColor': '#fff',
                'borderRadius': '10px',
                'boxShadow': '0 2px 6px rgba(0,0,0,0.1)',
                'overflow': 'hidden'
            })
            
            rows.append(row_container)
        
        return html.Div(rows), current_expanded
        
    except Exception as e:
        logger.error(f"Eroare la încărcarea data-view: {e}", exc_info=True)
        return html.Div(
            f"❌ EROARE la încărcarea datelor: {str(e)}",
            style={'padding': '20px', 'backgroundColor': '#ffdddd', 'border': '1px solid red', 'borderRadius': '5px', 'color': 'red'}
        ), current_expanded


@app.callback(
    Output('admin-dashboard-table', 'children'),
    [Input('admin-refresh-dashboard', 'n_clicks'),
     Input('admin-refresh-trigger', 'data')]
)
def admin_load_dashboard_table(n_clicks, trigger):
    """
    Încarcă tabelul dashboard cu toate link-urile și metadata.
    """
    logger.debug("Refresh dashboard admin solicitat.")
    
    try:
        all_links = patient_links.get_all_links_for_admin()
        
        if not all_links:
            return html.Div(
                "📭 Nu există link-uri generate încă. Rulați o procesare batch pentru a crea link-uri.",
                style={'padding': '30px', 'textAlign': 'center', 'color': '#666', 'fontStyle': 'italic', 'backgroundColor': '#f8f9fa', 'borderRadius': '5px'}
            )
        
        # Construim carduri pentru fiecare link
        link_cards = []
        for link_data in all_links:
            token = link_data['token']
            link_url = f"http://127.0.0.1:8050/?token={token}"
            
            # Formatare dată citibilă în română
            date_display = "Data nespecificată"
            if link_data.get('recording_date'):
                date_display = format_recording_date_ro(
                    link_data.get('recording_date', ''),
                    link_data.get('start_time', ''),
                    link_data.get('end_time', '')
                )
            
            # Status trimis
            sent_status_display = "✅ Trimis" if link_data.get('sent_status') else "📤 Netrimis"
            sent_color = '#27ae60' if link_data.get('sent_status') else '#e74c3c'
            
            # Vizualizări (DOAR în dashboard medical!)
            view_count = link_data.get('view_count', 0)
            first_viewed = link_data.get('first_viewed_at')
            view_display = f"👁️ {view_count} vizualizări"
            if view_count > 0 and first_viewed:
                view_display += f" (prima: {first_viewed[:10]})"
            
            link_cards.append(
                html.Div([
                    # Header card - DATA MAI ÎNTÂI!
                    html.Div([
                        html.Div([
                            html.Strong(f"📅 {date_display}", style={'fontSize': '16px', 'color': '#2c3e50', 'display': 'block'}),
                            html.Small(f"🔧 {link_data['device_name']}", style={'color': '#7f8c8d', 'display': 'block', 'marginTop': '5px'})
                        ], style={'flex': '1'}),
                        html.Div([
                            html.Span(sent_status_display, style={
                                'padding': '5px 12px',
                                'backgroundColor': sent_color,
                                'color': 'white',
                                'borderRadius': '15px',
                                'fontSize': '12px',
                                'fontWeight': 'bold',
                                'marginRight': '10px'
                            }),
                            html.Span(view_display, style={
                                'padding': '5px 12px',
                                'backgroundColor': '#3498db',
                                'color': 'white',
                                'borderRadius': '15px',
                                'fontSize': '12px',
                                'fontWeight': 'bold'
                            })
                        ])
                    ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '15px'}),
                    
                    # Link-ul (copiabil)
                    html.Div([
                        html.Label("🔗 Link Pacient:", style={'fontWeight': 'bold', 'display': 'block', 'marginBottom': '5px', 'fontSize': '14px'}),
                        dcc.Input(
                            value=link_url,
                            readOnly=True,
                            style={'width': '100%', 'padding': '8px', 'backgroundColor': '#ecf0f1', 'border': '1px solid #bdc3c7', 'borderRadius': '5px', 'fontSize': '12px', 'fontFamily': 'monospace'}
                        )
                    ], style={'marginBottom': '15px'}),
                    
                    # Notițe medicale (editabile)
                    html.Div([
                        html.Label("📝 Notițe Medicale:", style={'fontWeight': 'bold', 'display': 'block', 'marginBottom': '5px', 'fontSize': '14px'}),
                        dcc.Textarea(
                            id={'type': 'medical-notes-textarea', 'index': token},
                            value=link_data.get('medical_notes', ''),
                            placeholder='Scrieți notițe medicale aici (ex: Apnee severă, follow-up în 2 săptămâni)...',
                            style={'width': '100%', 'minHeight': '80px', 'padding': '10px', 'border': '1px solid #bdc3c7', 'borderRadius': '5px', 'fontSize': '14px'}
                        )
                    ], style={'marginBottom': '15px'}),
                    
                    # Acțiuni (checkbox + buton salvare)
                    html.Div([
                        dcc.Checklist(
                            id={'type': 'sent-status-checkbox', 'index': token},
                            options=[{'label': ' Marcat ca trimis către pacient', 'value': 'sent'}],
                            value=['sent'] if link_data.get('sent_status') else [],
                            style={'display': 'inline-block', 'marginRight': '20px'}
                        ),
                        html.Button(
                            '💾 Salvează Modificări',
                            id={'type': 'save-link-metadata-btn', 'index': token},
                            n_clicks=0,
                            style={
                                'padding': '10px 20px',
                                'backgroundColor': '#3498db',
                                'color': 'white',
                                'border': 'none',
                                'borderRadius': '5px',
                                'cursor': 'pointer',
                                'fontWeight': 'bold'
                            }
                        ),
                        html.Span(
                            id={'type': 'save-feedback', 'index': token},
                            style={'marginLeft': '15px', 'color': 'green', 'fontWeight': 'bold'}
                        )
                    ], style={'display': 'flex', 'alignItems': 'center'}),
                    
                    # Footer cu info token
                    html.Hr(style={'margin': '15px 0'}),
                    html.Small(f"Token: {token}", style={'color': '#95a5a6', 'fontSize': '10px'})
                    
                ], style={
                    'padding': '20px',
                    'marginBottom': '20px',
                    'backgroundColor': '#fff',
                    'borderRadius': '10px',
                    'border': '2px solid #e0e0e0',
                    'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'
                })
            )
        
        return html.Div(link_cards)
        
    except Exception as e:
        logger.error(f"Eroare la încărcarea dashboard-ului: {e}", exc_info=True)
        return html.Div(
            f"❌ EROARE la încărcarea dashboard-ului: {str(e)}",
            style={'padding': '15px', 'backgroundColor': '#ffdddd', 'border': '1px solid red', 'borderRadius': '5px', 'color': 'red'}
        )


@app.callback(
    [Output({'type': 'images-display-container', 'index': ALL}, 'children'),
     Output({'type': 'view-grid-btn', 'index': ALL}, 'style'),
     Output({'type': 'view-list-btn', 'index': ALL}, 'style')],
    [Input({'type': 'view-grid-btn', 'index': ALL}, 'n_clicks'),
     Input({'type': 'view-list-btn', 'index': ALL}, 'n_clicks')],
    [State({'type': 'view-grid-btn', 'index': ALL}, 'id')],
    prevent_initial_call=True
)
def toggle_images_view(grid_clicks, list_clicks, btn_ids):
    """
    Comută între vizualizarea Grid (ansamblu) și List (desfășurat) pentru imagini.
    """
    from dash import ctx
    import base64
    
    # Verificări de siguranță
    if not btn_ids:
        logger.warning("toggle_images_view: btn_ids este gol")
        return [], [], []
    
    if not ctx.triggered_id:
        logger.debug("toggle_images_view: Niciun trigger detectat")
        return [no_update] * len(btn_ids), [no_update] * len(btn_ids), [no_update] * len(btn_ids)
    
    triggered_token = ctx.triggered_id['index']
    triggered_type = ctx.triggered_id['type']
    
    logger.info(f"🔄 Toggle view: {triggered_type} pentru token {triggered_token[:8]}...")
    
    results_images = []
    results_grid_style = []
    results_list_style = []
    
    for i, btn_id in enumerate(btn_ids):
        token = btn_id['index']
        
        if token == triggered_token:
            # Găsim informațiile despre acest link pentru a reîncărca imaginile
            link_data = patient_links.get_patient_link(token, track_view=False)
            output_folder_path = link_data.get('output_folder_path') if link_data else None
            
            # FALLBACK INTELIGENT: Dacă nu avem output_folder_path, căutăm după dată și aparat
            if not output_folder_path or not os.path.exists(output_folder_path):
                logger.warning(f"output_folder_path lipsă sau invalid pentru {token[:8]}... Caut automat...")
                
                # Extragem device number și data
                device_num = link_data['device_name'].split('#')[-1].strip() if link_data else ''
                recording_date = link_data.get('recording_date', '') if link_data else ''
                
                if device_num and recording_date:
                    # Convertim data din YYYY-MM-DD în format folder
                    try:
                        from datetime import datetime
                        date_obj = datetime.strptime(recording_date, '%Y-%m-%d')
                        day = date_obj.day
                        month_name = ['ian', 'feb', 'mar', 'apr', 'mai', 'iun', 
                                     'iul', 'aug', 'sep', 'oct', 'nov', 'dec'][date_obj.month - 1]
                        year = date_obj.year
                        
                        # Căutăm folder care conține această dată și aparat
                        output_base = config.OUTPUT_DIR
                        if os.path.exists(output_base):
                            for folder_name in os.listdir(output_base):
                                folder_path = os.path.join(output_base, folder_name)
                                if os.path.isdir(folder_path):
                                    # Verificăm dacă folderul conține device_num și data aproximativă
                                    if device_num in folder_name and f"{day:02d}{month_name}{year}" in folder_name:
                                        output_folder_path = folder_path
                                        logger.info(f"✅ Găsit automat folder: {folder_name}")
                                        break
                    except Exception as e:
                        logger.error(f"Eroare la căutarea automată folder: {e}")
            
            if not output_folder_path or not os.path.exists(output_folder_path):
                logger.error(f"❌ Nu s-a găsit folder pentru {token[:8]}...")
            
            if triggered_type == 'view-grid-btn':
                # Trecem la vizualizare GRID (ansamblu cu thumbnail-uri)
                logger.info(f"📊 Comutare la GRID view pentru {token[:8]}...")
                
                if output_folder_path and os.path.exists(output_folder_path):
                    image_files = [f for f in os.listdir(output_folder_path) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
                    image_files.sort()
                    
                    logger.info(f"Găsite {len(image_files)} imagini în {output_folder_path}")
                    
                    grid_items = []
                    grid_items.append(
                        html.P(
                            f"📊 Vizualizare ansamblu: {len(image_files)} imagini",
                            style={'fontSize': '14px', 'color': '#2c3e50', 'fontWeight': 'bold', 'marginBottom': '20px', 'textAlign': 'left'}
                        )
                    )
                    
                    # Creăm grid cu thumbnail-uri
                    for img_file in image_files:
                        img_path = os.path.join(output_folder_path, img_file)
                        try:
                            with open(img_path, 'rb') as img_f:
                                img_data = base64.b64encode(img_f.read()).decode()
                                grid_items.append(
                                    html.Div([
                                        html.Img(
                                            src=f'data:image/jpeg;base64,{img_data}',
                                            style={
                                                'width': '100%',
                                                'borderRadius': '8px 8px 0 0',
                                                'display': 'block'
                                            }
                                        ),
                                        html.P(
                                            img_file,
                                            style={
                                                'fontSize': '11px',
                                                'color': '#7f8c8d',
                                                'textAlign': 'center',
                                                'margin': '8px 5px',
                                                'fontFamily': 'monospace',
                                                'overflow': 'hidden',
                                                'textOverflow': 'ellipsis',
                                                'whiteSpace': 'nowrap'
                                            }
                                        )
                                    ], style={
                                        'display': 'inline-block',
                                        'width': '30%',
                                        'margin': '1.5%',
                                        'verticalAlign': 'top',
                                        'backgroundColor': '#fff',
                                        'borderRadius': '8px',
                                        'boxShadow': '0 2px 6px rgba(0,0,0,0.1)',
                                        'overflow': 'hidden',
                                        'transition': 'transform 0.2s, box-shadow 0.2s'
                                    })
                                )
                        except Exception as e:
                            logger.error(f"Eroare la încărcarea imaginii {img_file} în grid: {e}")
                    
                    results_images.append(html.Div(grid_items, style={'textAlign': 'center'}))
                    logger.info(f"✅ Grid generat cu {len(grid_items)-1} imagini")
                else:
                    logger.warning(f"⚠️ Nu există folder la: {output_folder_path}")
                    results_images.append([html.P("Nu există imagini disponibile.", style={'color': '#666', 'fontStyle': 'italic'})])
                
                # Stiluri butoane: Grid activ, List inactiv
                results_grid_style.append({
                    'padding': '8px 20px',
                    'marginRight': '10px',
                    'backgroundColor': '#27ae60',
                    'color': 'white',
                    'border': 'none',
                    'borderRadius': '5px',
                    'cursor': 'pointer',
                    'fontSize': '13px',
                    'fontWeight': 'bold',
                    'transition': 'all 0.2s',
                    'boxShadow': '0 2px 4px rgba(0,0,0,0.2)'
                })
                results_list_style.append({
                    'padding': '8px 20px',
                    'backgroundColor': '#95a5a6',
                    'color': 'white',
                    'border': 'none',
                    'borderRadius': '5px',
                    'cursor': 'pointer',
                    'fontSize': '13px',
                    'fontWeight': 'bold',
                    'transition': 'all 0.2s'
                })
                
            else:  # view-list-btn
                # Trecem la vizualizare LIST (desfășurat - imagini mari)
                logger.info(f"📄 Comutare la LIST view pentru {token[:8]}...")
                
                if output_folder_path and os.path.exists(output_folder_path):
                    image_files = [f for f in os.listdir(output_folder_path) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
                    image_files.sort()
                    
                    list_items = []
                    list_items.append(
                        html.P(
                            f"📊 {len(image_files)} imagini generate",
                            style={'fontSize': '14px', 'color': '#2c3e50', 'fontWeight': 'bold', 'marginBottom': '15px'}
                        )
                    )
                    
                    # Creăm listă cu imagini mari
                    for img_file in image_files:
                        img_path = os.path.join(output_folder_path, img_file)
                        try:
                            with open(img_path, 'rb') as img_f:
                                img_data = base64.b64encode(img_f.read()).decode()
                                list_items.append(
                                    html.Div([
                                        html.Img(
                                            src=f'data:image/jpeg;base64,{img_data}',
                                            style={
                                                'width': '100%',
                                                'maxWidth': '900px',
                                                'borderRadius': '8px',
                                                'boxShadow': '0 2px 8px rgba(0,0,0,0.15)',
                                                'marginBottom': '10px',
                                                'border': '1px solid #ddd',
                                                'display': 'block',
                                                'marginLeft': 'auto',
                                                'marginRight': 'auto'
                                            }
                                        ),
                                        html.P(
                                            img_file,
                                            style={
                                                'fontSize': '13px',
                                                'color': '#7f8c8d',
                                                'textAlign': 'center',
                                                'marginBottom': '25px',
                                                'fontFamily': 'monospace'
                                            }
                                        )
                                    ])
                                )
                        except Exception as e:
                            logger.error(f"Eroare la încărcarea imaginii {img_file} în list: {e}")
                    
                    results_images.append(list_items)
                else:
                    results_images.append([html.P("Nu există imagini disponibile.", style={'color': '#666', 'fontStyle': 'italic'})])
                
                # Stiluri butoane: Grid inactiv, List activ
                results_grid_style.append({
                    'padding': '8px 20px',
                    'marginRight': '10px',
                    'backgroundColor': '#95a5a6',
                    'color': 'white',
                    'border': 'none',
                    'borderRadius': '5px',
                    'cursor': 'pointer',
                    'fontSize': '13px',
                    'fontWeight': 'bold',
                    'transition': 'all 0.2s'
                })
                results_list_style.append({
                    'padding': '8px 20px',
                    'backgroundColor': '#27ae60',
                    'color': 'white',
                    'border': 'none',
                    'borderRadius': '5px',
                    'cursor': 'pointer',
                    'fontSize': '13px',
                    'fontWeight': 'bold',
                    'transition': 'all 0.2s',
                    'boxShadow': '0 2px 4px rgba(0,0,0,0.2)'
                })
        else:
            # Acest token nu a fost triggerat - păstrăm starea curentă
            results_images.append(no_update)
            results_grid_style.append(no_update)
            results_list_style.append(no_update)
    
    return results_images, results_grid_style, results_list_style


@app.callback(
    Output({'type': 'save-interpretation-feedback', 'index': ALL}, 'children'),
    [Input({'type': 'save-interpretation-btn', 'index': ALL}, 'n_clicks')],
    [State({'type': 'medical-interpretation', 'index': ALL}, 'value'),
     State({'type': 'save-interpretation-btn', 'index': ALL}, 'id')],
    prevent_initial_call=True
)
def save_medical_interpretation(n_clicks_list, interpretation_list, ids_list):
    """
    Salvează interpretarea medicală pentru o înregistrare.
    """
    if not any(n_clicks_list):
        return [no_update] * len(n_clicks_list)
    
    results = []
    for i, n_clicks in enumerate(n_clicks_list):
        if n_clicks and n_clicks > 0:
            token = ids_list[i]['index']
            interpretation = interpretation_list[i] if i < len(interpretation_list) else ""
            
            logger.info(f"Salvare interpretare medicală pentru {token[:8]}...: {len(interpretation)} caractere")
            
            try:
                success = patient_links.update_link_medical_notes(token, interpretation)
                if success:
                    results.append("✅ Salvat!")
                else:
                    results.append("⚠️ Eroare")
            except Exception as e:
                logger.error(f"Eroare la salvare interpretare: {e}", exc_info=True)
                results.append("❌ Eroare")
        else:
            results.append(no_update)
    
    return results


@app.callback(
    Output({'type': 'save-feedback', 'index': ALL}, 'children'),
    [Input({'type': 'save-link-metadata-btn', 'index': ALL}, 'n_clicks')],
    [State({'type': 'medical-notes-textarea', 'index': ALL}, 'value'),
     State({'type': 'sent-status-checkbox', 'index': ALL}, 'value'),
     State({'type': 'save-link-metadata-btn', 'index': ALL}, 'id')],
    prevent_initial_call=True
)
def admin_save_link_metadata(n_clicks_list, notes_list, sent_list, ids_list):
    """
    Salvează notițele medicale și status-ul de trimitere pentru un link.
    """
    if not any(n_clicks_list):
        return [no_update] * len(n_clicks_list)
    
    results = []
    for i, n_clicks in enumerate(n_clicks_list):
        if n_clicks and n_clicks > 0:
            token = ids_list[i]['index']
            medical_notes = notes_list[i] if i < len(notes_list) else ""
            sent_status = 'sent' in sent_list[i] if i < len(sent_list) and sent_list[i] else False
            
            logger.info(f"Admin salvează metadata pentru {token[:8]}...: Notes={len(medical_notes)} chars, Sent={sent_status}")
            
            try:
                # Salvăm notițele
                notes_ok = patient_links.update_link_medical_notes(token, medical_notes)
                
                # Salvăm status-ul de trimitere
                sent_ok = patient_links.mark_link_as_sent(token, sent_status)
                
                if notes_ok and sent_ok:
                    results.append("✅ Salvat!")
                else:
                    results.append("⚠️ Eroare")
            except Exception as e:
                logger.error(f"Eroare la salvare metadata: {e}", exc_info=True)
                results.append("❌ Eroare")
        else:
            results.append(no_update)
    
    return results


# ==============================================================================
# CALLBACKS PACIENT
# ==============================================================================

@app.callback(
    [Output('patient-content-container', 'style'),
     Output('patient-access-result', 'children'),
     Output('current-patient-token', 'data')],
    [Input('patient-access-button', 'n_clicks')],
    [State('patient-token-input', 'value')]
)
def patient_access_with_token(n_clicks, token):
    """
    Callback pentru acces pacient cu token.
    """
    if n_clicks == 0:
        return no_update, no_update, no_update
    
    if not token or token.strip() == '':
        return no_update, html.Div(
            "⚠️ Introduceți token-ul primit de la medic!",
            style={'padding': '15px', 'backgroundColor': '#fff3cd', 'border': '1px solid #ffc107', 'borderRadius': '5px'}
        ), no_update
    
    logger.info(f"Tentativă acces pacient cu token: {token[:8]}...")
    
    # Validăm token-ul
    if patient_links.validate_token(token):
        patient_data = patient_links.get_patient_link(token)
        
        return (
            {'display': 'block'},  # Afișăm conținutul pacient
            html.Div([
                html.H4("✅ Acces Autorizat!", style={'color': 'green'}),
                html.P(f"Bine ați venit! Aparat: {patient_data['device_name']}")
            ], style={'padding': '15px', 'backgroundColor': '#d4edda', 'border': '1px solid #28a745', 'borderRadius': '5px'}),
            token  # Salvăm token-ul în store
        )
    else:
        return (
            no_update,
            html.Div(
                "❌ Token invalid sau inactiv! Verificați codul primit de la medic.",
                style={'padding': '15px', 'backgroundColor': '#ffdddd', 'border': '1px solid red', 'borderRadius': '5px', 'color': 'red'}
            ),
            no_update
        )


@app.callback(
    Output('patient-recordings-list', 'children'),
    [Input('current-patient-token', 'data')]
)
def display_patient_recordings(token):
    """
    Afișează lista de înregistrări pentru pacient.
    """
    if not token:
        return html.Div(
            "🔒 Accesați cu token-ul pentru a vedea înregistrările.",
            style={'padding': '20px', 'textAlign': 'center', 'color': '#666', 'fontStyle': 'italic'}
        )
    
    recordings = patient_links.get_patient_recordings(token)
    
    if not recordings:
        return html.Div(
            "📭 Nu aveți încă înregistrări. Contactați medicul pentru a adăuga date.",
            style={'padding': '20px', 'textAlign': 'center', 'color': '#666', 'fontStyle': 'italic'}
        )
    
    # Creăm carduri pentru fiecare înregistrare
    recording_cards = []
    for rec in recordings:
        recording_cards.append(
            html.Div([
                html.H4(f"📅 {rec['recording_date']}", style={'color': '#2c3e50'}),
                html.P(f"⏱️ Interval: {rec['start_time']} - {rec['end_time']}"),
                html.P(f"📊 SaO2: avg={rec['stats']['avg_spo2']:.1f}%, min={rec['stats']['min_spo2']}%, max={rec['stats']['max_spo2']}%"),
                html.P(f"📁 Fișier: {rec['original_filename']}", style={'fontSize': '12px', 'color': '#7f8c8d'}),
                html.Button(
                    '📈 Vezi Grafic',
                    id={'type': 'view-recording-btn', 'index': rec['id']},
                    style={
                        'padding': '10px 20px',
                        'backgroundColor': '#3498db',
                        'color': 'white',
                        'border': 'none',
                        'borderRadius': '5px',
                        'cursor': 'pointer',
                        'marginRight': '10px'
                    }
                ),
                html.Button(
                    '📥 Descarcă CSV',
                    id={'type': 'download-csv-btn', 'index': rec['id']},
                    style={
                        'padding': '10px 20px',
                        'backgroundColor': '#27ae60',
                        'color': 'white',
                        'border': 'none',
                        'borderRadius': '5px',
                        'cursor': 'pointer'
                    }
                )
            ], style={
                'padding': '20px',
                'marginBottom': '15px',
                'backgroundColor': '#ecf0f1',
                'borderRadius': '10px',
                'border': '1px solid #bdc3c7'
            })
        )
    
    return html.Div(recording_cards)


@app.callback(
    [Output('patient-explore-graph', 'figure'),
     Output('global-notification-container', 'children', allow_duplicate=True)],
    [Input('patient-explore-upload', 'contents')],
    [State('patient-explore-upload', 'filename')],
    prevent_initial_call=True
)
def patient_explore_csv(file_contents, file_name):
    """
    Callback pentru explorare CSV temporară de către pacient.
    ⚠️ IMPORTANT: Nu salvează în DB, doar plotare temporară!
    """
    if file_contents is None:
        return no_update, no_update
    
    logger.info(f"Pacient explorează CSV temporar: '{file_name}'")
    
    try:
        # Decodăm și parsăm
        content_type, content_string = file_contents.split(',')
        decoded_content = base64.b64decode(content_string)
        df = parse_csv_data(decoded_content, file_name)
        
        # Generăm graficul
        initial_scale = config.ZOOM_SCALE_CONFIG['min_scale']
        fig = create_plot(df, file_name, line_width_scale=initial_scale, marker_size_scale=initial_scale)
        
        notification = html.Div(
            f"✅ CSV explorat: {file_name} ({len(df)} puncte). ⚠️ Graficul este temporar.",
            style={'padding': '15px', 'backgroundColor': '#fff3cd', 'border': '1px solid #ffc107', 'borderRadius': '5px', 'marginBottom': '20px'}
        )
        
        logger.info(f"Explorare CSV temporară reușită pentru '{file_name}'")
        return fig, notification
        
    except Exception as e:
        logger.error(f"Eroare la explorare CSV: {e}", exc_info=True)
        error_notification = html.Div(
            f"❌ EROARE: {str(e)}",
            style={'padding': '15px', 'backgroundColor': '#ffdddd', 'border': '1px solid red', 'borderRadius': '5px', 'color': 'red', 'marginBottom': '20px'}
        )
        return go.Figure(), error_notification


logger.info("✅ Modulul callbacks_medical.py încărcat cu succes.")


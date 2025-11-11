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
from dash.dependencies import Input, Output, State
from dash import html, no_update
from datetime import datetime

from app_instance import app
from logger_setup import logger
import patient_links
from data_parser import parse_csv_data
from plot_generator import create_plot
import config


# ==============================================================================
# CALLBACKS ADMIN
# ==============================================================================

@app.callback(
    Output('admin-link-creation-result', 'children'),
    [Input('admin-create-link-button', 'n_clicks')],
    [State('admin-device-name-input', 'value'),
     State('admin-notes-input', 'value')]
)
def create_patient_link(n_clicks, device_name, notes):
    """
    Callback pentru crearea unui link nou de pacient de către medic.
    """
    if n_clicks == 0:
        return no_update
    
    if not device_name or device_name.strip() == '':
        return html.Div(
            "⚠️ ERROR: Numele aparatului este obligatoriu!",
            style={'padding': '15px', 'backgroundColor': '#ffdddd', 'border': '1px solid red', 'borderRadius': '5px', 'color': 'red'}
        )
    
    logger.info(f"Admin solicită crearea link nou pentru aparat: '{device_name}'")
    
    token = patient_links.generate_patient_link(device_name, notes or "")
    
    if token:
        link_url = f"http://127.0.0.1:8050/?token={token}"
        
        return html.Div([
            html.H4("✅ Link Creat Cu Succes!", style={'color': 'green'}),
            html.P("Link-ul persistent pentru pacient a fost generat:"),
            html.Div([
                html.Strong("Link: "),
                html.Code(link_url, style={'backgroundColor': '#f0f0f0', 'padding': '5px', 'fontSize': '14px'})
            ], style={'marginBottom': '10px'}),
            html.Div([
                html.Strong("Token: "),
                html.Code(token, style={'backgroundColor': '#f0f0f0', 'padding': '5px', 'fontSize': '12px'})
            ], style={'marginBottom': '10px'}),
            html.P("📋 Copiați link-ul sau token-ul și trimiteți-l pacientului (email/SMS).", style={'fontStyle': 'italic'}),
            html.P(f"📊 Aparat: {device_name}", style={'color': '#666'}),
            html.P(f"📝 Notițe: {notes or '(fără notițe)'}", style={'color': '#666'})
        ], style={'padding': '20px', 'backgroundColor': '#d4edda', 'border': '1px solid #28a745', 'borderRadius': '10px'})
    else:
        return html.Div(
            "❌ EROARE: Nu s-a putut crea link-ul. Verificați log-urile.",
            style={'padding': '15px', 'backgroundColor': '#ffdddd', 'border': '1px solid red', 'borderRadius': '5px', 'color': 'red'}
        )


@app.callback(
    [Output('admin-patient-selector', 'options'),
     Output('admin-patients-list', 'children')],
    [Input('admin-refresh-button', 'n_clicks'),
     Input('admin-create-link-button', 'n_clicks')]
)
def refresh_patient_list(n_clicks_refresh, n_clicks_create):
    """
    Reîmprospătează lista de pacienți din dropdown și din tabel.
    """
    logger.debug("Refresh listă pacienți solicitat.")
    
    patients = patient_links.get_all_patient_links()
    
    # Opțiuni pentru dropdown
    dropdown_options = [
        {'label': f"{p['device_name']} - {p['recordings_count']} înreg. (Token: ...{p['token'][-8:]})", 'value': p['token']}
        for p in patients
    ]
    
    # Tabel pentru vizualizare
    if not patients:
        table = html.Div(
            "📭 Nu există pacienți înregistrați încă.",
            style={'padding': '20px', 'textAlign': 'center', 'color': '#666', 'fontStyle': 'italic'}
        )
    else:
        table_rows = []
        for p in patients:
            table_rows.append(
                html.Div([
                    html.Div([
                        html.Strong(f"🔗 {p['device_name']}", style={'fontSize': '16px', 'color': '#2c3e50'}),
                        html.Br(),
                        html.Small(f"Token: ...{p['token'][-12:]}", style={'color': '#7f8c8d'}),
                        html.Br(),
                        html.Small(f"Creat: {p['created_at'][:10]}", style={'color': '#7f8c8d'}),
                        html.Br(),
                        html.Small(f"📊 {p['recordings_count']} înregistrări", style={'color': '#27ae60', 'fontWeight': 'bold'}),
                        html.Br(),
                        html.Small(f"📝 {p['notes'] or '(fără notițe)'}", style={'color': '#95a5a6', 'fontStyle': 'italic'})
                    ], style={'flex': '1'}),
                    html.Div([
                        html.Button(
                            '🗑️ Șterge',
                            id={'type': 'delete-patient-btn', 'index': p['token']},
                            style={
                                'padding': '5px 15px',
                                'backgroundColor': '#e74c3c',
                                'color': 'white',
                                'border': 'none',
                                'borderRadius': '5px',
                                'cursor': 'pointer'
                            }
                        )
                    ])
                ], style={
                    'display': 'flex',
                    'justifyContent': 'space-between',
                    'alignItems': 'center',
                    'padding': '15px',
                    'marginBottom': '10px',
                    'backgroundColor': '#ecf0f1',
                    'borderRadius': '10px',
                    'border': '1px solid #bdc3c7'
                })
            )
        
        table = html.Div(table_rows)
    
    logger.info(f"Listă pacienți actualizată: {len(patients)} pacienți activi.")
    return dropdown_options, table


@app.callback(
    Output('admin-upload-result', 'children'),
    [Input('admin-upload-csv', 'contents')],
    [State('admin-upload-csv', 'filename'),
     State('admin-patient-selector', 'value')]
)
def admin_upload_csv_for_patient(file_contents, file_name, patient_token):
    """
    Callback pentru upload CSV de către admin pentru un pacient existent.
    """
    if file_contents is None:
        return no_update
    
    if not patient_token:
        return html.Div(
            "⚠️ Selectați mai întâi un pacient din listă!",
            style={'padding': '15px', 'backgroundColor': '#fff3cd', 'border': '1px solid #ffc107', 'borderRadius': '5px'}
        )
    
    logger.info(f"Admin uploadează CSV '{file_name}' pentru pacient {patient_token[:8]}...")
    
    try:
        # Decodăm fișierul
        content_type, content_string = file_contents.split(',')
        decoded_content = base64.b64decode(content_string)
        
        # Parsăm CSV-ul
        df = parse_csv_data(decoded_content, file_name)
        
        # Extragem metadata
        recording_date = df.index.min().strftime('%Y-%m-%d')
        start_time = df.index.min().strftime('%H:%M:%S')
        end_time = df.index.max().strftime('%H:%M:%S')
        avg_spo2 = df['SpO2'].mean()
        min_spo2 = df['SpO2'].min()
        max_spo2 = df['SpO2'].max()
        
        # Adăugăm înregistrarea
        success = patient_links.add_recording(
            token=patient_token,
            csv_filename=file_name,
            csv_content=decoded_content,
            recording_date=recording_date,
            start_time=start_time,
            end_time=end_time,
            avg_spo2=float(avg_spo2),
            min_spo2=int(min_spo2),
            max_spo2=int(max_spo2)
        )
        
        if success:
            return html.Div([
                html.H4("✅ Înregistrare Adăugată Cu Succes!", style={'color': 'green'}),
                html.P(f"Fișier: {file_name}"),
                html.P(f"Data: {recording_date}"),
                html.P(f"Interval: {start_time} - {end_time}"),
                html.P(f"SaO2: avg={avg_spo2:.1f}%, min={min_spo2}%, max={max_spo2}%")
            ], style={'padding': '20px', 'backgroundColor': '#d4edda', 'border': '1px solid #28a745', 'borderRadius': '10px'})
        else:
            return html.Div(
                "❌ Eroare la salvarea înregistrării. Verificați log-urile.",
                style={'padding': '15px', 'backgroundColor': '#ffdddd', 'border': '1px solid red', 'borderRadius': '5px', 'color': 'red'}
            )
        
    except Exception as e:
        logger.error(f"Eroare la upload CSV admin: {e}", exc_info=True)
        return html.Div(
            f"❌ EROARE: {str(e)}",
            style={'padding': '15px', 'backgroundColor': '#ffdddd', 'border': '1px solid red', 'borderRadius': '5px', 'color': 'red'}
        )


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


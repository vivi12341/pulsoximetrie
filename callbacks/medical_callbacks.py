# ==============================================================================
# callbacks/medical_callbacks.py (WORKFLOW MEDICAL — admin + batch principal)
# ------------------------------------------------------------------------------
# ROL: Callbacks pentru funcționalitatea medical workflow:
#      - Admin: Creare link-uri, upload CSV pentru pacienți
#      - Modul pacient / PDF / branding: patient_view_callbacks, medical_branding_callbacks
#
# RESPECTĂ: .cursorrules - Privacy by Design, Logging comprehensiv
# ==============================================================================

import base64
import json
import pandas as pd
import os
import pathlib
import re
import time
import dash_uploader as du
import plotly.graph_objects as go
from dash.dependencies import Input, Output, State, ALL
from dash import html, no_update, dcc, callback_context
from datetime import datetime
from typing import List, Dict

from app_instance import app
from logger_setup import logger
import patient_links
from data_parser import parse_csv_data
from plot_generator import create_plot
from services.batch_service import run_batch_job
import batch_session_manager
import config
from auth_ui_components import create_auth_header
import data_service  # [NEW] Serviciu centralizat de date
from shared.runtime_mode import is_cloud_runtime


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def _parse_trigger_component_id(prop_id: str) -> dict:
    """Extrage id-ul componentei din prop_id Dash (înainte de .property)."""
    left = prop_id.rsplit(".", 1)[0]
    try:
        return json.loads(left)
    except json.JSONDecodeError:
        import ast
        return ast.literal_eval(left)


def _safe_under_batch_root(path_str: str) -> str | None:
    """Returnează calea rezolvată dacă este sub BATCH_BROWSE_ROOT, altfel None."""
    if not path_str or not str(path_str).strip():
        return None
    try:
        root = pathlib.Path(config.get_batch_browse_root()).resolve()
        p = pathlib.Path(path_str).expanduser().resolve()
        p.relative_to(root)
        return str(p)
    except (ValueError, OSError, RuntimeError):
        return None


def _parent_clamped(current: pathlib.Path, root: pathlib.Path) -> pathlib.Path:
    """Folder părinte, fără a ieși din root."""
    try:
        current = current.resolve()
        root = root.resolve()
        current.relative_to(root)
    except (ValueError, OSError):
        return root
    parent = current.parent
    try:
        parent.relative_to(root)
        return parent
    except ValueError:
        return root


def _list_subdir_names(abs_dir: str) -> list[str]:
    """Numele subdirectoarelor (fără ascunse .), sortate."""
    names: list[str] = []
    try:
        with os.scandir(abs_dir) as it:
            for e in it:
                if e.is_dir() and not e.name.startswith("."):
                    names.append(e.name)
    except OSError:
        return []
    return sorted(names, key=lambda s: s.lower())


# ==============================================================================
# Explorator foldere — mod batch local (căi pe server)
# ==============================================================================


@app.callback(
    [
        Output("admin-batch-browse-input-list", "children"),
        Output("admin-batch-browse-input-entries", "data"),
        Output("admin-batch-browse-input-path-display", "children"),
    ],
    Input("admin-batch-browse-input-current", "data"),
    prevent_initial_call=False,
)
def render_batch_browse_input_list(current_path):
    if is_cloud_runtime():
        return [], [], html.Span("")
    root = pathlib.Path(config.get_batch_browse_root()).resolve()
    cur = _safe_under_batch_root(str(current_path)) if current_path else None
    if not cur:
        cur = str(root)
    names = _list_subdir_names(cur)
    buttons = [
        html.Button(
            f"📁 {n}",
            id={"type": "admin-batch-browse-input-dir", "i": i},
            n_clicks=0,
            className="btn-secondary",
            style={"textAlign": "left", "padding": "8px 12px"},
        )
        for i, n in enumerate(names)
    ]
    if not buttons:
        buttons = [html.P("Niciun subfolder.", style={"color": "#7f8c8d", "fontSize": "13px"})]
    return buttons, names, html.Code(cur)


@app.callback(
    [
        Output("admin-batch-browse-output-list", "children"),
        Output("admin-batch-browse-output-entries", "data"),
        Output("admin-batch-browse-output-path-display", "children"),
    ],
    Input("admin-batch-browse-output-current", "data"),
    prevent_initial_call=False,
)
def render_batch_browse_output_list(current_path):
    if is_cloud_runtime():
        return [], [], html.Span("")
    root = pathlib.Path(config.get_batch_browse_root()).resolve()
    cur = _safe_under_batch_root(str(current_path)) if current_path else None
    if not cur:
        cur = str(root)
    names = _list_subdir_names(cur)
    buttons = [
        html.Button(
            f"📁 {n}",
            id={"type": "admin-batch-browse-output-dir", "i": i},
            n_clicks=0,
            className="btn-secondary",
            style={"textAlign": "left", "padding": "8px 12px"},
        )
        for i, n in enumerate(names)
    ]
    if not buttons:
        buttons = [html.P("Niciun subfolder.", style={"color": "#7f8c8d", "fontSize": "13px"})]
    return buttons, names, html.Code(cur)


@app.callback(
    Output("admin-batch-browse-input-current", "data"),
    [
        Input("admin-batch-mode-selector", "value"),
        Input("admin-batch-browse-input-up", "n_clicks"),
        Input({"type": "admin-batch-browse-input-dir", "i": ALL}, "n_clicks"),
    ],
    [
        State("admin-batch-browse-input-current", "data"),
        State("admin-batch-browse-input-entries", "data"),
    ],
    prevent_initial_call=False,
)
def sync_batch_browse_input_current(mode, n_up, n_dir_clicks, cur, entries):
    if is_cloud_runtime():
        return no_update
    root = pathlib.Path(config.get_batch_browse_root()).resolve()
    cur_safe = _safe_under_batch_root(str(cur)) if cur else None
    if not cur_safe:
        cur_safe = str(root)

    if not callback_context.triggered:
        return cur_safe

    trig = callback_context.triggered[0]
    prop_id = trig["prop_id"]
    val = trig.get("value")

    if prop_id.startswith("admin-batch-mode-selector"):
        if mode == "local":
            return str(root)
        return no_update

    if prop_id.startswith("admin-batch-browse-input-up"):
        if not n_up:
            return no_update
        return str(_parent_clamped(pathlib.Path(cur_safe), root))

    if "admin-batch-browse-input-dir" in prop_id:
        if not val:
            return no_update
        btn = _parse_prop_id_component(prop_id)
        idx = btn.get("i")
        if entries is None or idx is None or idx >= len(entries):
            return no_update
        sub = entries[idx]
        new_p = pathlib.Path(cur_safe) / sub
        ok = _safe_under_batch_root(str(new_p))
        return ok if ok else cur_safe

    return no_update


@app.callback(
    Output("admin-batch-browse-output-current", "data"),
    [
        Input("admin-batch-browse-output-up", "n_clicks"),
        Input({"type": "admin-batch-browse-output-dir", "i": ALL}, "n_clicks"),
    ],
    [
        State("admin-batch-browse-output-current", "data"),
        State("admin-batch-browse-output-entries", "data"),
    ],
    prevent_initial_call=False,
)
def sync_batch_browse_output_current(n_up, n_dir_clicks, cur, entries):
    if is_cloud_runtime():
        return no_update
    root = pathlib.Path(config.get_batch_browse_root()).resolve()
    cur_safe = _safe_under_batch_root(str(cur)) if cur else None
    if not cur_safe:
        cur_safe = str(root)

    if not callback_context.triggered:
        return cur_safe

    trig = callback_context.triggered[0]
    prop_id = trig["prop_id"]
    val = trig.get("value")

    if prop_id.startswith("admin-batch-browse-output-up"):
        if not n_up:
            return no_update
        return str(_parent_clamped(pathlib.Path(cur_safe), root))

    if "admin-batch-browse-output-dir" in prop_id:
        if not val:
            return no_update
        btn = _parse_prop_id_component(prop_id)
        idx = btn.get("i")
        if entries is None or idx is None or idx >= len(entries):
            return no_update
        sub = entries[idx]
        new_p = pathlib.Path(cur_safe) / sub
        ok = _safe_under_batch_root(str(new_p))
        return ok if ok else cur_safe

    return no_update


@app.callback(
    Output("admin-batch-input-folder", "value"),
    Input("admin-batch-browse-input-use", "n_clicks"),
    State("admin-batch-browse-input-current", "data"),
    prevent_initial_call=True,
)
def apply_batch_browse_input_folder(n_clicks, current_path):
    if is_cloud_runtime() or not n_clicks:
        return no_update
    ok = _safe_under_batch_root(str(current_path)) if current_path else None
    if not ok:
        return no_update
    return ok


@app.callback(
    Output("admin-batch-output-folder", "value"),
    Input("admin-batch-browse-output-use", "n_clicks"),
    State("admin-batch-browse-output-current", "data"),
    prevent_initial_call=True,
)
def apply_batch_browse_output_folder(n_clicks, current_path):
    if is_cloud_runtime() or not n_clicks:
        return no_update
    ok = _safe_under_batch_root(str(current_path)) if current_path else None
    if not ok:
        return no_update
    return ok


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def create_login_prompt():
    """
    Creează o pagină de login prompt frumoasă pentru utilizatori neautentificați.
    
    Returns:
        html.Div: Component Dash cu prompt de autentificare
    """
    from dash import dcc
    return html.Div([
        # URL tracking pentru callback-uri
        dcc.Location(id='url', refresh=False),
        
        html.Div([
            # Icon mare
            html.Div("🔐", style={
                'fontSize': '80px',
                'textAlign': 'center',
                'marginBottom': '30px'
            }),
            
            # Titlu
            html.H1(
                "Bine ați venit!",
                style={
                    'textAlign': 'center',
                    'color': '#2c3e50',
                    'marginBottom': '15px',
                    'fontSize': '36px'
                }
            ),
            
            # Subtitlu
            html.P(
                "Platformă Pulsoximetrie - Sistem Medical Securizat",
                style={
                    'textAlign': 'center',
                    'color': '#7f8c8d',
                    'fontSize': '18px',
                    'marginBottom': '40px'
                }
            ),
            
            # Mesaj informativ
            html.Div([
                html.P(
                    "Pentru a accesa platforma medicală, trebuie să vă autentificați.",
                    style={
                        'textAlign': 'center',
                        'color': '#555',
                        'fontSize': '16px',
                        'lineHeight': '1.6',
                        'marginBottom': '10px'
                    }
                ),
                html.P(
                    "Dacă sunteți pacient și aveți un link de acces personalizat, folosiți link-ul primit de la medicul dumneavoastră.",
                    style={
                        'textAlign': 'center',
                        'color': '#777',
                        'fontSize': '14px',
                        'lineHeight': '1.6',
                        'marginBottom': '40px'
                    }
                )
            ], style={
                'maxWidth': '600px',
                'margin': '0 auto',
                'padding': '20px',
                'backgroundColor': '#f8f9fa',
                'borderRadius': '10px',
                'marginBottom': '40px'
            }),
            
            # Butoane de acțiune
            html.Div([
                html.A(
                    "🔐 Autentificare Medici",
                    href='/login',
                    style={
                        'display': 'inline-block',
                        'padding': '18px 40px',
                        'background': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                        'color': 'white',
                        'textDecoration': 'none',
                        'borderRadius': '50px',
                        'fontSize': '18px',
                        'fontWeight': '600',
                        'boxShadow': '0 4px 20px rgba(102, 126, 234, 0.4)',
                        'transition': 'all 0.3s ease',
                        'marginRight': '15px',
                        'marginBottom': '15px'
                    }
                ),
            ], style={'textAlign': 'center', 'marginBottom': '30px'}),
            
            # Informații suplimentare
            html.Div([
                html.Hr(style={'margin': '30px 0', 'border': 'none', 'borderTop': '1px solid #e0e0e0'}),
                html.P([
                    "💡 ",
                    html.Strong("Pentru pacienți: "),
                    "Dacă ați primit un link personalizat de la medicul dumneavoastră (ex: ",
                    html.Code("https://app.com/?token=abc123", style={'backgroundColor': '#e8f4f8', 'padding': '2px 8px', 'borderRadius': '3px'}),
                    "), folosiți acel link direct. Nu este necesară autentificarea."
                ], style={
                    'textAlign': 'center',
                    'color': '#666',
                    'fontSize': '13px',
                    'lineHeight': '1.8'
                }),
                html.P([
                    "🔒 ",
                    html.Strong("Securitate: "),
                    "Toate datele sunt criptate și protejate conform GDPR. Platforma este 100% securizată."
                ], style={
                    'textAlign': 'center',
                    'color': '#666',
                    'fontSize': '13px',
                    'lineHeight': '1.8',
                    'marginTop': '15px'
                })
            ], style={
                'maxWidth': '700px',
                'margin': '0 auto',
                'padding': '20px'
            })
            
        ], style={
            'maxWidth': '900px',
            'margin': '0 auto',
            'padding': '60px 30px',
            'backgroundColor': 'white',
            'borderRadius': '20px',
            'boxShadow': '0 10px 50px rgba(0,0,0,0.1)'
        })
    ], style={
        'minHeight': '100vh',
        'background': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        'display': 'flex',
        'alignItems': 'center',
        'justifyContent': 'center',
        'padding': '20px'
    })


# ==============================================================================
# CALLBACK ROUTING - DETECTARE TOKEN ȘI AFIȘARE LAYOUT
# ==============================================================================

# ==============================================================================
# [SOLUȚIA A IMPLEMENTATĂ] Callback routing ȘTERS
# ------------------------------------------------------------------------------
# MOTIVAȚIE: Conflict cu get_layout() din app_layout_new.py care face routing
# DIRECT la nivel de funcție (Dash 3.x best practice).
# 
# Callback-ul route_layout_based_on_url() cauza:
# - Pagină "Loading..." infinită (dynamic-layout-container lipsea din layout)
# - Conflict între 2 sisteme de routing (funcție vs callback)
# 
# SOLUȚIE: get_layout() face routing DIRECT:
# - Token în URL → patient_layout
# - Autentificat → medical_layout  
# - Neautentificat → create_login_prompt()
# 
# Callback-urile care depindeau de url-token-detected au fost modificate să
# citească token-ul DIRECT din Flask request.args.get('token')
# ==============================================================================


# ==============================================================================
# CALLBACK HEADER AUTENTIFICARE
# ==============================================================================

@app.callback(
    Output('auth-header-container', 'children'),
    [Input('url', 'pathname')]
)
def update_auth_header(pathname):
    """
    Actualizează header-ul de autentificare pe toate paginile medicului.
    
    Afișează:
    - Buton "Autentifică-te" pentru utilizatori neautentificați
    - Informații doctor + buton "Deconectare" pentru utilizatori autentificați
    """
    try:
        return create_auth_header()
    except Exception as e:
        logger.error(f"Eroare la crearea header-ului de autentificare: {e}", exc_info=True)
        return html.Div()


# ==============================================================================
# CALLBACK COPY TO CLIPBOARD (Clientside - JavaScript)
# ==============================================================================

app.clientside_callback(
    """
    function(n_clicks, link_value) {
        if (n_clicks > 0 && link_value) {
            navigator.clipboard.writeText(link_value).then(function() {
                console.log('✅ Link copiat în clipboard:', link_value);
            }).catch(function(err) {
                console.error('❌ Eroare la copiere:', err);
            });
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output({'type': 'copy-link-batch', 'index': ALL}, 'n_clicks', allow_duplicate=True),
    Input({'type': 'copy-link-batch', 'index': ALL}, 'n_clicks'),
    State({'type': 'link-input-batch', 'index': ALL}, 'value'),
    prevent_initial_call=True
)

app.clientside_callback(
    """
    function(n_clicks, link_value) {
        if (n_clicks > 0 && link_value) {
            navigator.clipboard.writeText(link_value).then(function() {
                console.log('✅ Link copiat în clipboard:', link_value);
            }).catch(function(err) {
                console.error('❌ Eroare la copiere:', err);
            });
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output({'type': 'copy-link-view', 'index': ALL}, 'n_clicks', allow_duplicate=True),
    Input({'type': 'copy-link-view', 'index': ALL}, 'n_clicks'),
    State({'type': 'link-input-view', 'index': ALL}, 'value'),
    prevent_initial_call=True
)

app.clientside_callback(
    """
    function(n_clicks, link_value) {
        if (n_clicks > 0 && link_value) {
            navigator.clipboard.writeText(link_value).then(function() {
                console.log('✅ Link copiat în clipboard:', link_value);
            }).catch(function(err) {
                console.error('❌ Eroare la copiere:', err);
            });
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output({'type': 'copy-link-dashboard', 'index': ALL}, 'n_clicks', allow_duplicate=True),
    Input({'type': 'copy-link-dashboard', 'index': ALL}, 'n_clicks'),
    State({'type': 'link-input-dashboard', 'index': ALL}, 'value'),
    prevent_initial_call=True
)


def format_recording_date_ro(recording_date, start_time, end_time):
    """
    Formatează data înregistrării în format citibil românesc:
    "Marți 14/10/2025 de la ora 20:32 până în Miercuri 15/10/2025 la ora 04:45"
    Format dată: DD/MM/YYYY
    
    [UPDATED v2.0] Suportă AMBELE formate de timp:
    - HH:MM:SS (nou, din batch_processor.py fix)
    - HH:MM (vechi, date istorice)
    """
    from datetime import datetime
    
    # Zile săptămână în română
    days_ro = {
        0: 'Luni', 1: 'Marți', 2: 'Miercuri', 3: 'Joi',
        4: 'Vineri', 5: 'Sâmbătă', 6: 'Duminică'
    }
    
    try:
        # [FIX v2.0] Încercăm ÎNTÂI formatul nou HH:MM:SS, apoi fallback la HH:MM
        try:
            start_datetime = datetime.strptime(f"{recording_date} {start_time}", "%Y-%m-%d %H:%M:%S")
        except ValueError:
            # Fallback la formatul vechi HH:MM
            start_datetime = datetime.strptime(f"{recording_date} {start_time}", "%Y-%m-%d %H:%M")
        
        # Pentru ora de sfârșit, trebuie să determinăm data corectă
        # Dacă ora de sfârșit < ora de început, înseamnă că a trecut la ziua următoare
        end_hour = int(end_time.split(':')[0])
        start_hour = int(start_time.split(':')[0])
        
        if end_hour < start_hour:
            # A trecut la ziua următoare
            from datetime import timedelta
            end_date = start_datetime.date() + timedelta(days=1)
            # [FIX v2.0] Try both formats for end_time too
            try:
                end_datetime = datetime.strptime(f"{end_date} {end_time}", "%Y-%m-%d %H:%M:%S")
            except ValueError:
                end_datetime = datetime.strptime(f"{end_date} {end_time}", "%Y-%m-%d %H:%M")
        else:
            # Aceeași zi
            # [FIX v2.0] Try both formats
            try:
                end_datetime = datetime.strptime(f"{recording_date} {end_time}", "%Y-%m-%d %H:%M:%S")
            except ValueError:
                end_datetime = datetime.strptime(f"{recording_date} {end_time}", "%Y-%m-%d %H:%M")
        
        # Formatăm datele în DD/MM/YYYY
        start_day_name = days_ro[start_datetime.weekday()]
        start_date_formatted = start_datetime.strftime("%d/%m/%Y")
        start_hour_minute = start_datetime.strftime("%H:%M")
        
        end_day_name = days_ro[end_datetime.weekday()]
        end_date_formatted = end_datetime.strftime("%d/%m/%Y")
        end_hour_minute = end_datetime.strftime("%H:%M")
        
        # Construim textul final
        if start_datetime.date() == end_datetime.date():
            # Aceeași zi
            formatted = f"{start_day_name} {start_date_formatted} de la ora {start_hour_minute} până la ora {end_hour_minute}"
        else:
            # Zile diferite
            formatted = f"{start_day_name} {start_date_formatted} de la ora {start_hour_minute} până în {end_day_name} {end_date_formatted} la ora {end_hour_minute}"
        
        return formatted
        
    except Exception as e:
        logger.error(f"Eroare la formatarea datei: {e}", exc_info=True)
        return f"{recording_date} | {start_time} - {end_time}"



def render_pdf_section(pdf_data, token):
    """
    Generează o secțiune HTML completă pentru afișarea datelor din PDF.
    Stil: Card Medical cu secțiuni distincte pentru sumar, statistici detaliate, evenimente și interpretare.
    Include ABSOLUT TOATE datele disponibile, inclusiv text brut pentru fallback.
    """
    if not pdf_data or 'data' not in pdf_data:
        return html.Div("Date PDF incomplete.", style={'color': 'red'})

    data = pdf_data['data']
    pdf_path = pdf_data.get('pdf_path', '')
    parsed_at = pdf_data.get('parsed_at', 'Necunoscut')
    
    # 1. HEADER SECȚIUNE
    header = html.Div([
        html.H3("📄 Raport Medical Automat", style={'color': '#2c3e50', 'marginBottom': '5px'}),
        html.Small(f"Generat automat din PDF la data: {parsed_at}", style={'color': '#7f8c8d'})
    ], style={'borderBottom': '1px solid #eee', 'paddingBottom': '15px', 'marginBottom': '20px'})

    # 2. SUMAR PRINCIPAL (Box-uri colorate)
    stats = data.get('statistics', {})
    events = data.get('events', {})
    
    summary_cards = html.Div([
        # SpO2 Mediu
        html.Div([
            html.H4("SpO2 Mediu", style={'margin': '0', 'fontSize': '14px', 'color': '#7f8c8d'}),
            html.Div(f"{stats.get('avg_spo2', '-')}%", style={'fontSize': '28px', 'fontWeight': 'bold', 'color': '#2980b9'})
        ], style={'flex': '1', 'textAlign': 'center', 'padding': '15px', 'backgroundColor': '#e8f4f8', 'borderRadius': '8px', 'marginRight': '10px'}),
        
        # Puls Mediu
        html.Div([
            html.H4("Puls Mediu", style={'margin': '0', 'fontSize': '14px', 'color': '#7f8c8d'}),
            html.Div(f"{stats.get('avg_pulse', '-')} bpm", style={'fontSize': '28px', 'fontWeight': 'bold', 'color': '#27ae60'})
        ], style={'flex': '1', 'textAlign': 'center', 'padding': '15px', 'backgroundColor': '#eafaf1', 'borderRadius': '8px', 'marginRight': '10px'}),
        
        # Desaturări
        html.Div([
            html.H4("Desaturări", style={'margin': '0', 'fontSize': '14px', 'color': '#7f8c8d'}),
            html.Div(f"{events.get('desaturations_count', 0)}", style={'fontSize': '28px', 'fontWeight': 'bold', 'color': '#e74c3c'})
        ], style={'flex': '1', 'textAlign': 'center', 'padding': '15px', 'backgroundColor': '#fadbd8', 'borderRadius': '8px'})
    ], style={'display': 'flex', 'justifyContent': 'space-between', 'marginBottom': '25px'})

    # 3. DETALII COMPLETE (Tabel 2 coloane)
    details_content = html.Div([
        # Coloana Stânga: Info & Statistici
        html.Div([
            html.H5("📊 Statistici Detaliate", style={'color': '#2c3e50', 'borderBottom': '2px solid #3498db', 'paddingBottom': '5px'}),
            html.Table([
                html.Tr([html.Td("Aparat:"), html.Td(html.Strong(data.get('device_info', {}).get('device_number', '-') + ' (' + data.get('device_info', {}).get('device_name', '-') + ')'))]),
                html.Tr([html.Td("Data înreg.:"), html.Td(html.Strong(data.get('recording_info', {}).get('date', '-')))]),
                html.Tr([html.Td("Ora Start:"), html.Td(html.Strong(data.get('recording_info', {}).get('start_time', '-')))]),
                html.Tr([html.Td("Durată:"), html.Td(html.Strong(data.get('recording_info', {}).get('duration', '-')))]),
                html.Tr([html.Td("SpO2 Minim:"), html.Td(html.Strong(f"{stats.get('min_spo2', '-')}%"))]),
                html.Tr([html.Td("SpO2 Maxim:"), html.Td(html.Strong(f"{stats.get('max_spo2', '-')}%"))]),
                html.Tr([html.Td("SpO2 Mediu:"), html.Td(html.Strong(f"{stats.get('avg_spo2', '-')}%"))]),
                html.Tr([html.Td("Puls Minim:"), html.Td(html.Strong(f"{stats.get('min_pulse', '-')} bpm"))]),
                html.Tr([html.Td("Puls Maxim:"), html.Td(html.Strong(f"{stats.get('max_pulse', '-')} bpm"))]),
                html.Tr([html.Td("Puls Mediu:"), html.Td(html.Strong(f"{stats.get('avg_pulse', '-')} bpm"))]),
            ], style={'width': '100%', 'fontSize': '14px', 'lineHeight': '1.8'})
        ], style={'flex': '1', 'marginRight': '20px', 'minWidth': '300px'}),
        
        # Coloana Dreapta: Evenimente
        html.Div([
            html.H5("⚠️ Evenimente", style={'color': '#2c3e50', 'borderBottom': '2px solid #e74c3c', 'paddingBottom': '5px'}),
             html.Table([
                html.Tr([html.Td("Nr. Desaturări (<90%):"), html.Td(html.Strong(str(events.get('desaturations_count', 0))))]),
                html.Tr([html.Td("Durată totală desaturări:"), html.Td(html.Strong(str(events.get('total_desaturation_duration', '-'))))]),
                html.Tr([html.Td("Cea mai lungă desaturare:"), html.Td(html.Strong(str(events.get('longest_desaturation', '-'))))]),
            ], style={'width': '100%', 'fontSize': '14px', 'lineHeight': '1.8'})
        ], style={'flex': '1', 'minWidth': '300px'})
    ], style={'display': 'flex', 'marginBottom': '25px', 'flexWrap': 'wrap'})

    # 4. INTERPRETARE (Text complet)
    interpretation = data.get('interpretation', '')
    interp_section = None
    if interpretation:
        interp_section = html.Div([
            html.H5("📝 Interpretare Automată", style={'color': '#2c3e50', 'borderBottom': '2px solid #f39c12', 'paddingBottom': '5px'}),
            html.P(interpretation, style={'whiteSpace': 'pre-wrap', 'backgroundColor': '#fff3cd', 'padding': '15px', 'borderRadius': '5px', 'border': '1px solid #ffeeba'})
        ], style={'marginBottom': '20px'})
        
    # 5. HEADER SECȚIUNE RAW TEXT (Fallback pentru absolut toate datele)
    raw_text = data.get('raw_text', '')
    raw_section = None
    if raw_text:
        raw_section = html.Details([
            html.Summary("Vizualizare Text Complet (Raw Data)", style={'cursor': 'pointer', 'color': '#7f8c8d', 'marginBottom': '10px'}),
            html.Pre(raw_text, style={'whiteSpace': 'pre-wrap', 'fontSize': '11px', 'backgroundColor': '#f8f9fa', 'padding': '10px', 'maxHeight': '300px', 'overflowY': 'auto', 'border': '1px solid #eee'})
        ], style={'marginBottom': '20px'})

    # 6. DOWNLOAD BUTTON
    download_btn = html.A(
        html.Button('📥 Descarcă PDF Original', style={
            'padding': '10px 20px', 'backgroundColor': '#2c3e50', 'color': 'white', 
            'border': 'none', 'borderRadius': '5px', 'cursor': 'pointer', 'width': '100%'
        }),
        # Folosim ruta de download PDF
        href=f"/download_pdf/{token}/{os.path.basename(pdf_path)}" if pdf_path else "#",
        target="_blank",
        style={'textDecoration': 'none', 'display': 'block', 'marginTop': '10px'}
    )

    # ASAMBLARE CARD FINAL
    return html.Div([
        header,
        summary_cards,
        details_content,
        interp_section,
        raw_section,
        download_btn
    ], className="medical-card", style={'padding': '25px', 'backgroundColor': 'white', 'borderRadius': '10px', 'boxShadow': '0 4px 15px rgba(0,0,0,0.05)', 'marginTop': '30px', 'borderLeft': '5px solid #3498db'})


@app.callback(
    [Output('patient-data-view', 'children'),
     Output('patient-main-graph', 'figure')],
    [Input('force-routing-trigger', 'n_intervals'),
     Input('global-token-store', 'data')]  # CRITICAL FIX: Read token from dcc.Store, not request.args
)
def load_patient_data_from_token(n_intervals, token_from_store):
    """
    [SOLUȚIA CORECTATĂ] Încarcă automat datele pacientului când token-ul este detectat în URL.
    
    CRITICAL FIX: Token-ul se citește din global-token-store (populat client-side),
    NU din Flask re

quest.args (care e gol în contextul callback-urilor Dash triggerate de Interval).
    
    Trigger: dcc.Interval(id='force-routing-trigger') - se declanșează o singură dată la încărcarea paginii
    Input: global-token-store.data - token-ul extras client-side din window.location
    """
    from datetime import datetime
    
    # [ENHANCED DIAGNOSTIC v3] Full request context + token store logging
    logger.critical("="*100)
    logger.critical(f"🔍 [PATIENT_LOAD] *** CALLBACK START (v3 - Token from Store) ***")
    logger.critical(f"🔍 [PATIENT_LOAD] Timestamp: {datetime.now().isoformat()}")
    logger.critical(f"🔍 [PATIENT_LOAD] N_intervals: {n_intervals}")
    logger.critical(f"🔍 [PATIENT_LOAD] Token from Store: {token_from_store[:8] if token_from_store else 'NONE'}...")
    logger.critical("="*100)
    
    token = token_from_store
    
    if not token:
        logger.warning("⚠️ [UI_TRACE_LOAD] MISSING TOKEN in URL. Returning no_update.")
        return no_update, no_update
    
    logger.info(f"📊 [TRACE-DATA] [LOG 19] Încărcare date pentru pacient: {token[:8]}...")
    
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
        
        # === ÎNCĂRCĂM CSV-UL ȘI DATELE COMPLETE ===
        # === ÎNCĂRCĂM DATELE PRIN DATA SERVICE (Refactorizat v2) ===
        # [TRACE-DATA] [LOG 23] Apel DataService din Patient View
        logger.info(f"🏥 [TRACE-DATA] [LOG 23] Apel data_service.get_patient_dataframe pentru token {token[:8]}...")
        
        # Folosim logica centralizată din data_service.py
        df, csv_filename, status_msg = data_service.get_patient_dataframe(token)
        
        # [ENHANCED ERROR HANDLING v2] Detailed data service result checking
        if df is not None:
            logger.critical(f"✅ [PATIENT_LOAD] DataService SUCCESS")  
            logger.critical(f"✅ [PATIENT_LOAD] DataFrame shape: {df.shape}")
            logger.critical(f"✅ [PATIENT_LOAD] DataFrame columns: {list(df.columns)}")
            logger.critical(f"✅ [PATIENT_LOAD] First timestamp: {df.index[0] if len(df) > 0 else 'N/A'}")
            logger.critical(f"✅ [PATIENT_LOAD] Last timestamp: {df.index[-1] if len(df) > 0 else 'N/A'}")
        else:
            logger.critical(f"❌ [PATIENT_LOAD] DataService FAILED")
            logger.critical(f"❌ [PATIENT_LOAD] Status message: {status_msg}")
            logger.critical(f"❌ [PATIENT_LOAD] Returning user-friendly error UI")
            
            # Return empathetic error message with actionable guidance
            error_content = html.Div([
                html.Div([
                    html.H2("📭 Date Indisponibile", style={
                        'color': '#e67e22', 
                        'textAlign': 'center',
                        'marginBottom': '20px',
                        'fontSize': '32px'
                    }),
                    html.P([
                        "Nu s-au putut încărca datele pentru acest link. ",
                        html.Br(),
                        html.Br(),
                        "Acest lucru poate însemna că fișierele nu au fost încă procesate complet ",
                        "sau că există o problemă temporară cu sistemul de stocare."
                    ], style={
                        'textAlign': 'center', 
                        'color': '#7f8c8d', 
                        'marginBottom': '30px',
                        'fontSize': '16px',
                        'lineHeight': '1.8'
                    }),
                    html.Div([
                        html.Strong("📋 Detalii tehnice: ", style={'color': '#95a5a6'}),
                        html.Br(),
                        html.Code(status_msg, style={
                            'backgroundColor': '#ecf0f1', 
                            'padding': '10px',
                            'borderRadius': '5px',
                            'display': 'inline-block',
                            'marginTop': '10px',
                            'fontSize': '13px',
                            'color': '#555'
                        })
                    ], style={
                        'textAlign': 'center', 
                        'fontSize': '14px', 
                        'color': '#95a5a6',
                        'marginBottom': '30px'
                    }),
                    html.P([
                        "🩺 Vă rugăm să contactați medicul dumneavoastră pentru un link actualizat ",
                        "sau pentru mai multe informații."
                    ], style={
                        'textAlign': 'center', 
                        'marginTop': '40px', 
                        'fontStyle': 'italic',
                        'color': '#3498db',
                        'fontSize': '15px'
                    })
                ], style={
                    'maxWidth': '700px',
                    'margin': '80px auto',
                    'padding': '50px',
                    'backgroundColor': 'white',
                    'borderRadius': '15px',
                    'boxShadow': '0 4px 20px rgba(0,0,0,0.1)',
                    'border': '3px solid #e67e22'
                })
            ], style={'backgroundColor': '#f5f7fa', 'minHeight': '80vh', 'padding': '20px'})
            
            # Return empty figure with annotation
            empty_fig = go.Figure()
            empty_fig.add_annotation(
                text="Graficul nu este disponibil",
                xref="paper", yref="paper",
                x=0.5, y=0.5, 
                showarrow=False,
                font=dict(size=18, color="#95a5a6")
            )
            empty_fig.update_layout(
                xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
                yaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
                plot_bgcolor='white',
                height=400
            )
            
            return error_content, empty_fig
        
        # Generăm figura cu error boundaries defensive
        if df is not None and not df.empty:
            try:
                logger.critical(f"📈 [PATIENT_LOAD] START plot generation")
                logger.critical(f"📈 [PATIENT_LOAD] DataFrame ready: rows={len(df)}, empty={df.empty}")
                logger.critical(f"📈 [PATIENT_LOAD] Calling create_plot() with filename: {csv_filename}")
                
                fig = create_plot(df, file_name=csv_filename)
                
                # [DEFENSIVE VALIDATION] Check figure integrity
                if fig is None:
                    logger.critical("❌ [PATIENT_LOAD] create_plot returned None!")
                    fig = go.Figure()
                    fig.add_annotation(
                        text="⚠️ Graficul nu a putut fi generat",
                        xref="paper", yref="paper",
                        x=0.5, y=0.5, 
                        showarrow=False,
                        font=dict(size=20, color="red")
                    )
                    fig.update_layout(
                        xaxis=dict(showgrid=False, showticklabels=False),
                        yaxis=dict(showgrid=False, showticklabels=False),
                        height=500
                    )
                elif not hasattr(fig, 'data') or len(fig.data) == 0:
                    logger.critical("⚠️ [PATIENT_LOAD] Figure exists but has NO data traces!")
                    fig.add_annotation(
                        text="⚠️ Graficul nu conține date",
                        xref="paper", yref="paper",
                        x=0.5, y=0.5, 
                        showarrow=False,
                        font=dict(size=16, color="orange")
                    )
                else:
                    logger.critical(f"✅ [PATIENT_LOAD] Plot generated successfully!")
                    logger.critical(f"✅ [PATIENT_LOAD] Figure traces count: {len(fig.data)}")
                    # Removed buggy line: fig.layout.keys() causes AttributeError
                
                # Apply logo (non-critical, failures logged but ignored)
                try:
                    from plot_generator import apply_logo_to_figure
                    fig = apply_logo_to_figure(fig)
                    logger.debug("✅ [PATIENT_LOAD] Logo applied to figure")
                except Exception as logo_err:
                    logger.warning(f"⚠️ [PATIENT_LOAD] Logo application failed (non-critical): {logo_err}")

            except Exception as plot_err:
                logger.critical(f"💥 [PATIENT_LOAD] CRITICAL plot generation exception: {plot_err}", exc_info=True)
                
                # Create annotated error figure
                fig = go.Figure()
                error_text = str(plot_err)[:100] + "..." if len(str(plot_err)) > 100 else str(plot_err)
                fig.add_annotation(
                    text=f"❌ Eroare: {error_text}",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, 
                    showarrow=False,
                    font=dict(size=14, color="red"),
                    align="center"
                )
                fig.update_layout(
                    xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
                    yaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
                    plot_bgcolor='#fff5f5',
                    height=500,
                    margin=dict(l=40, r=40, t=40, b=40)
                )
        
        else:
            # [DIAGNOSTIC LOG 29] Fallback UI pentru lipsă date
            logger.warning(f"⚠️ [PATIENT_VIEW] Nu avem date (df is None/Empty). Afișăm mesaj eroare.")
            fig = go.Figure()
            fig.update_layout(
                title="⚠️ Graficul nu este disponibil încă",
                xaxis_title="Timp",
                yaxis_title="SpO2 (%)",
                height=500
            )
            
            # Mesaj detaliat pentru debugging
            # The 'recordings' variable is not defined in this scope, so this part is removed to avoid NameError.
            # The status_msg from data_service.get_patient_dataframe already provides context.
            # if not recordings or len(recordings) == 0:
            #     logger.warning(f"❌ Nicio înregistrare găsită pentru token {token[:8]}...")
            # else:
            #     logger.warning(f"❌ CSV lipsă pentru token {token[:8]}... (recordings: {len(recordings)})")
        
        # === CONSTRUIM AFIȘAREA COMPLETĂ ===
        content_sections = []
        
        # 1. INFO CARD
        info_card = html.Div([
            html.Div([
                html.Strong("📅 ", style={'fontSize': '18px'}),
                html.Span(formatted_date, style={'fontSize': '16px', 'color': '#2c3e50'})
            ], style={'marginBottom': '15px'}),
            
            html.Div([
                html.Strong("🔧 Aparat: ", style={'color': '#555'}),
                html.Span(patient_data.get('device_name', 'Aparat Necunoscut'))
            ], style={'marginBottom': '10px'}),
            
            # Notițe (dacă există)
            html.Div([
                html.Hr(style={'margin': '20px 0'}),
                html.H4("📝 Notițe", style={'color': '#2980b9'}),
                html.P(
                    patient_data.get('medical_notes') or 'Nu există notițe.',
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
        content_sections.append(info_card)
        
        # [CRITICAL FIX] Define patient_folder PRZED użytem
        patient_folder = os.path.join(patient_links.PATIENT_DATA_DIR, token)
        logger.warning(f"📁 [PATIENT_VIEW_FIX] patient_folder: {patient_folder}")
        logger.warning(f"📁 [PATIENT_VIEW_FIX] patient_folder exists: {os.path.exists(patient_folder)}")
        
        # [DIAGNOSTIC] Log DF status
        logger.warning(f"📊 [PATIENT_VIEW_FIX] df is None: {df is None}")
        if df is not None:
            logger.warning(f"📊 [PATIENT_VIEW_FIX] df.shape: {df.shape}")
            logger.warning(f"📊 [PATIENT_VIEW_FIX] df.empty: {df.empty}")
        else:
            logger.error(f"❌ [PATIENT_VIEW_FIX] DataFrame is NONE! Data not available!")
        
        # 2. IMAGINI GENERATE (dacă există)
        images_folder = os.path.join(patient_folder, "images")
        logger.info(f"🖼️ Verificare folder imagini: {images_folder} → Există: {os.path.exists(images_folder)}")
        
        if os.path.exists(images_folder):
            image_files = sorted([f for f in os.listdir(images_folder) if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
            logger.info(f"🖼️ Imagini găsite: {len(image_files)} fișiere")
            if image_files:
                images_section = html.Div([
                    # Header cu opțiuni
                    html.Div([
                        html.H3("🖼️ Imagini Generate", style={'color': '#2980b9', 'marginBottom': '0px', 'display': 'inline-block', 'marginRight': '20px'}),
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
                                    'marginRight': '15px',
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
                            ),
                            html.A(
                                '📥 Descarcă Tot (ZIP)',
                                id={'type': 'download-all-btn', 'index': token},
                                href=f'/download_all/{token}',
                                style={
                                    'padding': '8px 20px',
                                    'backgroundColor': '#3498db',
                                    'color': 'white',
                                    'textDecoration': 'none',
                                    'borderRadius': '5px',
                                    'fontSize': '13px',
                                    'fontWeight': 'bold',
                                    'display': 'inline-block'
                                }
                            )
                        ], style={'display': 'inline-block', 'verticalAlign': 'middle'})
                    ], style={'marginBottom': '15px', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between'}),
                    
                    # Container imagini (default: list view - desfășurat)
                    html.Div([
                        html.Div([
                            html.Img(
                                src=f'/patient_assets/{token}/images/{img}',
                                style={
                                    'width': '100%',
                                    'maxWidth': '800px',
                                    'border': '2px solid #ddd',
                                    'borderRadius': '8px',
                                    'marginBottom': '15px'
                                }
                            ),
                            html.Div([
                                html.Strong(img, style={'fontSize': '14px', 'color': '#555'}),
                                html.A(
                                    '📥 Descarcă',
                                    href=f'/patient_assets/{token}/images/{img}',
                                    download=img,
                                    style={
                                        'marginLeft': '15px',
                                        'padding': '5px 15px',
                                        'backgroundColor': '#3498db',
                                        'color': 'white',
                                        'textDecoration': 'none',
                                        'borderRadius': '5px',
                                        'fontSize': '12px'
                                    }
                                )
                            ], style={'marginBottom': '25px'})
                        ]) for img in image_files
                    ], id={'type': 'images-display-container', 'index': token})
                ], style={
                    'padding': '25px',
                    'backgroundColor': '#fff',
                    'borderRadius': '10px',
                    'boxShadow': '0 2px 8px rgba(0,0,0,0.1)',
                    'marginBottom': '20px'
                })
                content_sections.append(images_section)
        
        # 3. PDF-URI (dacă există)
        all_pdfs = patient_links.get_all_pdfs_for_link(token)
        logger.info(f"📄 PDF-uri găsite: {len(all_pdfs) if all_pdfs else 0}")
        
        if all_pdfs:
             # Iterăm prin fiecare PDF și generăm secțiunea detaliată
            for pdf_item in all_pdfs:
                try:
                    pdf_section = render_pdf_section(pdf_item, token)
                    content_sections.append(pdf_section)
                except Exception as pdf_error:
                    logger.error(f"Eroare la randarea secțiunii PDF: {pdf_error}", exc_info=True)
                    content_sections.append(html.Div(f"Eroare afișare PDF: {pdf_error}", style={'color': 'red'}))
        
        # Combinăm toate secțiunile
        full_content = html.Div(content_sections)
        
        logger.info(f"✅ Date complete încărcate pentru pacient {token[:8]}...")
        return full_content, fig
        
    except Exception as e:
        logger.error(f"Eroare la încărcarea datelor pacientului: {e}", exc_info=True)
        
        # [ENHANCED UX] Mesaj empatic pentru pacienți (UX Designer recommendation)
        error_msg = html.Div([
            html.Div([
                html.H2("😕 Oops! Ceva nu a mers bine", style={'color': '#e74c3c', 'textAlign': 'center', 'marginBottom': '20px'}),
                html.P([
                    "Ne pare rău, dar datele nu au putut fi încărcate momentan. ",
                    html.Br(),
                    "Vă rugăm să contactați medicul dumneavoastră dacă problema persistă."
                ], style={'textAlign': 'center', 'color': '#7f8c8d', 'fontSize': '16px', 'lineHeight': '1.6'}),
                html.Details([
                    html.Summary("Detalii tehnice (pentru suport)", 
                                style={'cursor': 'pointer', 'marginTop': '30px', 'color': '#95a5a6', 'textAlign': 'center'}),
                    html.Pre(f"Error: {str(e)}", 
                            style={'backgroundColor': '#ecf0f1', 'padding': '15px', 'borderRadius': '5px', 
                                   'fontSize': '12px', 'marginTop': '10px', 'textAlign': 'left'})
                ])
            ], style={
                'maxWidth': '600px',
                'margin': '100px auto',
                'padding': '40px',
                'backgroundColor': 'white',
                'borderRadius': '15px',
                'boxShadow': '0 4px 20px rgba(0,0,0,0.1)'
            })
        ])
        return error_msg, go.Figure()


# ==============================================================================
# CALLBACKS ADMIN - DASHBOARD MEDICAL PROFESIONAL
# ==============================================================================

@app.callback(
    [Output('admin-batch-local-mode', 'style'),
     Output('admin-batch-upload-mode', 'style')],
    [Input('admin-batch-mode-selector', 'value')],
    prevent_initial_call=False 
)
def toggle_batch_mode_display(selected_mode):
    """
    [FIX v2] Comută între modul local (folder) și modul upload (fișiere).
    """
    tag = "toggle_batch_mode_display"
    logger.info(f"[{tag}] START - selected_mode: {selected_mode}")
    
    if selected_mode == 'local':
        local_style = {'display': 'block', 'marginBottom': '20px'}
        upload_style = {'display': 'none'}
        logger.info(f"[{tag}] Mode: LOCAL → local visible, upload hidden")
        return local_style, upload_style
    else:
        local_style = {'display': 'none'}
        upload_style = {'display': 'block', 'marginBottom': '20px'}
        logger.info(f"[{tag}] Mode: UPLOAD → upload visible, local hidden")
        return local_style, upload_style


# ==============================================================================
# [T2 Solution] DASH UPLOADER CALLBACKS
# ==============================================================================

@du.callback(
    output=[
        Output('admin-batch-uploaded-files-store', 'data'),
        Output('admin-batch-session-id', 'data')
    ],
    id='admin-batch-file-upload',
)
def on_upload_complete(status):
    """
    [T2 Solution + v7 Defensive Error Handling] Streaming Upload Finalizat.
    """
    
    # [FIX] Wrap everything in try-except to prevent 500 Internal Server Error
    try:
        logger.info("="*100)
        logger.info("🚀 [UPLOAD CALLBACK] START - on_upload_complete trigerat")
        logger.info("="*100)
        
        # [LOG 1] Tip status primit
        logger.info(f"📦 [LOG 1] Status type: {type(status)}")
        logger.info(f"📦 [LOG 2] Status repr: {repr(status)[:500]}...")  # Prima 500 caractere
        
        # [FIX v3] Robust handling for dash-uploader status
        upload_id = "unknown_batch_session"
        new_files = []
        
        try:
            # Case A: List
            if isinstance(status, list):
                logger.info(f"✅ [LOG 3] Status este listă cu {len(status)} elemente")
                
                if not status:
                    logger.warning("⚠️ [LOG 4] Listă goală, returnez no_update")
                    return no_update, no_update
                
                first_item = status[0]
                logger.info(f"📦 [LOG 5] Primul element: type={type(first_item)}, repr={repr(first_item)[:200]}")
                
                if isinstance(first_item, str):
                    logger.info(f"✅ [LOG 6] Status este list[str]. Detectate {len(status)} fișiere path-uri.")
                    new_files = status
                    
                    # Log fiecare fișier detectat
                    for idx, file_path in enumerate(new_files):
                        logger.info(f"   📄 [LOG 7.{idx}] File #{idx+1}: {file_path}")
                    
                    # Extrage upload_id din path
                    try:
                        path_obj = pathlib.Path(first_item)
                        upload_id = path_obj.parent.name
                        logger.info(f"🆔 [LOG 8] Upload ID extras din path: {upload_id}")
                    except Exception as id_error:
                        logger.warning(f"⚠️ [LOG 9] Nu s-a putut extrage upload_id din path: {id_error}")
                        
                elif hasattr(first_item, 'uploaded_files'):
                    logger.info("✅ [LOG 10] Status este list[UploadStatus].")
                    for s_idx, s in enumerate(status):
                        logger.info(f"   📦 [LOG 11.{s_idx}] UploadStatus #{s_idx+1}: {len(s.uploaded_files)} files")
                        new_files.extend(s.uploaded_files)
                    if hasattr(first_item, 'upload_id'):
                        upload_id = first_item.upload_id
                        logger.info(f"🆔 [LOG 12] Upload ID din UploadStatus: {upload_id}")
                else:
                     logger.error(f"❌ [LOG 13] Tip necunoscut în listă: {type(first_item)}")
            
            # Case B: Object (UploadStatus)
            elif hasattr(status, 'uploaded_files'):
                logger.info("✅ [LOG 14] Status este UploadStatus object (single).")
                new_files = status.uploaded_files
                logger.info(f"📦 [LOG 15] uploaded_files count: {len(new_files)}")
                
                for idx, f in enumerate(new_files):
                    logger.info(f"   📄 [LOG 16.{idx}] File #{idx+1}: {f}")
                
                if hasattr(status, 'upload_id'):
                    upload_id = status.upload_id
                    logger.info(f"🆔 [LOG 17] Upload ID din status object: {upload_id}")
            else:
                logger.error(f"❌ [LOG 18] Status are tip complet neașteptat: {type(status)}")
                logger.error(f"❌ [LOG 19] Dir(status): {dir(status)}")
                return no_update, no_update
    
        except Exception as e:
             logger.error(f"❌ [LOG 20] EXCEPȚIE la parsarea status: {e}", exc_info=True)
             return no_update, no_update
    
        logger.info(f"🆔 [LOG 21] Upload ID FINAL: {upload_id}")
        logger.info(f"📊 [LOG 22] New files count: {len(new_files)}")
        
        if not new_files:
            logger.warning("⚠️ [LOG 23] new_files este goală, returnez no_update")
            return no_update, no_update
            
        first_file = pathlib.Path(new_files[0])
        session_folder = first_file.parent
        logger.info(f"📂 [LOG 24] Session Folder: {session_folder}")
        logger.info(f"📂 [LOG 25] Session Folder EXISTS: {os.path.exists(session_folder)}")
        
        # [FIX v5] Retry-based folder scanning cu delay pentru async writes
        all_files_metadata = []
        
        max_retries = 10
        retry_delay = 0.1
        max_delay = 1.0
        
        logger.info(f"🔄 [LOG 26] Start retry loop: max_retries={max_retries}")
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    current_delay = min(retry_delay * (1.5 ** attempt), max_delay)
                    logger.info(f"⏳ [LOG 27.{attempt}] Aștept {current_delay:.3f}s înainte de retry...")
                    time.sleep(current_delay)
                
                temp_metadata = []
                
                # Scanare folder
                logger.info(f"🔍 [LOG 28.{attempt}] === SCAN ATTEMPT #{attempt + 1}/{max_retries} ===")
                
                try:
                    # [Double-Check] Session existence check inside loop
                    if not os.path.exists(session_folder):
                        logger.warning(f"⚠️ [LOG 29.{attempt}] Folder încă inexistent: {session_folder}")
                        continue

                    entries = list(os.scandir(session_folder))
                    logger.info(f"📁 [LOG 29.{attempt}] os.scandir găsit: {len(entries)} intrări totale")
                except Exception as scandir_error:
                    logger.error(f"❌ [LOG 30.{attempt}] EROARE os.scandir: {scandir_error}")
                    continue
                
                # Listare detaliată fișiere
                for e_idx, entry in enumerate(entries):
                    logger.info(f"   🔎 [LOG 31.{attempt}.{e_idx}] Entry: '{entry.name}' | is_dir={entry.is_dir()} | is_file={entry.is_file()}")
                    
                    if entry.is_dir():
                        logger.info(f"      ⏭️ [LOG 32.{attempt}.{e_idx}] SKIP (director)")
                        continue
                        
                    if entry.name.startswith('.'):
                        logger.info(f"      ⏭️ [LOG 33.{attempt}.{e_idx}] SKIP (ascuns)")
                        continue
                    
                    # Verificare extensie
                    fname = entry.name
                    fname_lower = fname.lower()
                    
                    logger.info(f"      📝 [LOG 34.{attempt}.{e_idx}] Filename: '{fname}' | lowercase: '{fname_lower}'")
                    
                    f_type = 'OTHER'
                    if fname_lower.endswith('.pdf'):
                        f_type = 'PDF'
                        logger.info(f"      ✅ [LOG 35.{attempt}.{e_idx}] DETECTAT PDF!")
                    elif fname_lower.endswith('.csv'):
                        f_type = 'CSV'
                        logger.info(f"      ✅ [LOG 36.{attempt}.{e_idx}] DETECTAT CSV!")
                    else:
                        logger.info(f"      ⏭️ [LOG 37.{attempt}.{e_idx}] SKIP (tip: {f_type})")
                        continue
                    
                    # Obține dimensiune fișier
                    try:
                        file_size = entry.stat().st_size
                        logger.info(f"      📏 [LOG 38.{attempt}.{e_idx}] Size: {file_size} bytes")
                    except Exception as stat_error:
                        logger.error(f"      ❌ [LOG 39.{attempt}.{e_idx}] EROARE stat: {stat_error}")
                        file_size = 0
                    
                    # Adaugă la metadata
                    file_meta = {
                        'filename': fname,
                        'temp_path': entry.path,
                        'type': f_type,
                        'size': file_size
                    }
                    temp_metadata.append(file_meta)
                    logger.info(f"      ✅ [LOG 40.{attempt}.{e_idx}] ADĂUGAT la metadata: {f_type} - {fname}")
                
                # Sumarizare scan
                csv_count = sum(1 for f in temp_metadata if f['type'] == 'CSV')
                pdf_count = sum(1 for f in temp_metadata if f['type'] == 'PDF')
                logger.info(f"📊 [LOG 41.{attempt}] Scan result: Total={len(temp_metadata)}, CSV={csv_count}, PDF={pdf_count}")
                
                # Logică stabilizare
                if len(temp_metadata) > len(all_files_metadata):
                    logger.info(f"📈 [LOG 42.{attempt}] GĂSITE FIȘIERE NOI! Diferență: {len(temp_metadata) - len(all_files_metadata)}")
                    all_files_metadata = temp_metadata
                    logger.info(f"🔄 [LOG 43.{attempt}] Continuăm să scanăm (posibil mai multe fișiere în curs)...\r")
                    continue
                elif len(temp_metadata) == len(all_files_metadata) and len(all_files_metadata) > 0:
                    logger.info(f"✅ [LOG 44.{attempt}] STABILIZAT! Număr constant: {len(all_files_metadata)}")
                    all_files_metadata = temp_metadata
                    logger.info(f"🏁 [LOG 45.{attempt}] BREAK din loop (stabilizat)")
                    break
                else:
                    logger.info(f"🔄 [LOG 46.{attempt}] Actualizare metadata (edge case)")
                    all_files_metadata = temp_metadata
                    
            except Exception as scan_error:
                logger.error(f"❌ [LOG 47.{attempt}] EXCEPȚIE în scan: {scan_error}", exc_info=True)
                continue
        
        # Rezultat final
        logger.info("="*100)
        logger.info(f"🏁 [LOG 48] SCAN COMPLET după {attempt + 1} încercări")
        logger.info(f"📊 [LOG 49] REZULTAT FINAL: {len(all_files_metadata)} fișiere detectate")
        
        if all_files_metadata:
            csv_final = sum(1 for f in all_files_metadata if f['type'] == 'CSV')
            pdf_final = sum(1 for f in all_files_metadata if f['type'] == 'PDF')
            logger.info(f"📊 [LOG 50] BREAKDOWN: CSV={csv_final}, PDF={pdf_final}")
            
            for idx, f_meta in enumerate(all_files_metadata):
                logger.info(f"   [{idx+1}] {f_meta['type']}: {f_meta['filename']} ({f_meta['size']} bytes)")
        else:
            logger.warning("⚠️ [LOG 51] NICIUN FIȘIER DETECTAT! all_files_metadata este goală!")
        
        logger.info(f"🎯 [LOG 52] Returnez: metadata({len(all_files_metadata)} items), upload_id='{upload_id}'")
        logger.info("="*100)
            
        return all_files_metadata, str(upload_id)
    
    except Exception as e:
        logger.error("="*100)
        logger.error("💥💥💥 CALLBACK CRASH - EROARE CRITICĂ! 💥💥💥")
        logger.error(f"💥 Exception type: {type(e).__name__}")
        logger.error(f"💥 Exception message: {str(e)}")
        logger.error("💥 Full traceback:")
        logger.error("="*100, exc_info=True)
        # Prevent 500 error by returning empty update
        return no_update, no_update


@app.callback(
    Output('admin-batch-uploaded-files-list', 'children'),
    [Input('admin-batch-uploaded-files-store', 'data')]
)
def update_upload_ui_list(files_data):
    """
    Randează lista vizuală a fișierelor bazată pe datele din Store.
    """
    tag = "update_upload_ui_list"
    if not files_data:
        logger.info(f"[{tag}] 📭 Nu există date în store (files_data e gol/None).")
        return html.P("📭 Nu există fișiere încărcate încă.", style={
            'textAlign': 'center', 'color': '#95a5a6', 'padding': '20px',
            'backgroundColor': '#f8f9fa', 'borderRadius': '5px', 'border': '1px dashed #bdc3c7'
        })
    
    logger.info(f"[{tag}] 📊 Actualizare UI cu {len(files_data)} fișiere.")
        
    csv_count = sum(1 for f in files_data if f.get('type') == 'CSV')
    pdf_count = sum(1 for f in files_data if f.get('type') == 'PDF')
    
    return html.Div([
        html.Div([
            html.Strong(f"📊 Total: {len(files_data)} fișiere", style={'marginRight': '20px'}),
            html.Span(f"📄 CSV: {csv_count}", style={'marginRight': '15px', 'color': '#27ae60'}),
            html.Span(f"📕 PDF: {pdf_count}", style={'color': '#e74c3c'}),
            html.Button(
                '🗑️ Șterge toate', id='admin-batch-clear-files-btn', n_clicks=0,
                style={'padding': '5px 15px', 'fontSize': '12px', 'backgroundColor': '#e74c3c', 'color': 'white', 'border': 'none', 'borderRadius': '3px', 'cursor': 'pointer', 'float': 'right'}
            )
        ], style={'padding': '12px', 'backgroundColor': '#ecf0f1', 'borderRadius': '5px 5px 0 0', 'borderBottom': '2px solid #bdc3c7', 'marginBottom': '10px'}),
        
        html.Div([
            html.Div([
                html.Div([
                    html.Span('📄' if f.get('type') == 'CSV' else '📕', style={'fontSize': '20px', 'marginRight': '10px'}),
                    html.Strong(f.get('filename'), style={'fontSize': '13px'}),
                    html.Small(f" ({_format_file_size(f.get('size', 0))})", style={'color': '#7f8c8d', 'marginLeft': '8px'}),
                ], style={'display': 'flex', 'alignItems': 'center'}),
                html.Button(
                    '❌', id={'type': 'delete-uploaded-file', 'index': i}, n_clicks=0,
                    style={'padding': '4px 10px', 'fontSize': '14px', 'backgroundColor': '#e74c3c', 'color': 'white', 'border': 'none', 'borderRadius': '3px', 'cursor': 'pointer'}
                )
            ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'padding': '10px', 'marginBottom': '8px',
                        'backgroundColor': '#e8f5e9' if f.get('type') == 'CSV' else '#ffebee', 'borderRadius': '4px', 'border': f"1px solid {'#27ae60' if f.get('type') == 'CSV' else '#e74c3c'}"})
            for i, f in enumerate(files_data)
        ])
    ], style={'padding': '15px', 'backgroundColor': '#fff', 'borderRadius': '0 0 5px 5px', 'border': '1px solid #bdc3c7', 'maxHeight': '300px', 'overflowY': 'auto'})


def _format_file_size(size_bytes):
    """Helper pentru formatare dimensiune fișier."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


@app.callback(
    Output('admin-batch-uploaded-files-store', 'data', allow_duplicate=True),
    [Input('admin-batch-clear-files-btn', 'n_clicks'),
     Input({'type': 'delete-uploaded-file', 'index': ALL}, 'n_clicks')],
    [State('admin-batch-uploaded-files-store', 'data')],
    prevent_initial_call=True
)
def handle_file_deletion(clear_all_clicks, delete_clicks, current_files):
    """
    Șterge fișiere uploadate (individual sau toate).
    """
    from dash import ctx
    
    # [DEFENSIVE DEBUG] Logging pentru troubleshooting
    logger.info("=" * 80)
    logger.info("🗑️ HANDLE FILE DELETION - Callback trigerat")
    logger.info(f"📦 ctx.triggered_id: {ctx.triggered_id}")
    logger.info(f"📦 current_files (BEFORE): {[f['filename'] for f in current_files] if current_files else None}")
    logger.info(f"📦 current_files length: {len(current_files) if current_files else 0}")
    logger.info("=" * 80)
    
    if not ctx.triggered_id:
        logger.warning("⚠️ ctx.triggered_id este None - returnez no_update")
        return no_update
    
    # Ștergere toate fișierele
    if ctx.triggered_id == 'admin-batch-clear-files-btn':
        logger.info("🗑️ ȘTERGERE TOATE FIȘIERELE (clear all clicked)")
        logger.info("🎯 RETURN: [] (listă goală) → STORE")
        return []
    
    # Ștergere fișier individual
    if isinstance(ctx.triggered_id, dict) and ctx.triggered_id['type'] == 'delete-uploaded-file':
        index_to_delete = ctx.triggered_id['index']
        if current_files and 0 <= index_to_delete < len(current_files):
            deleted_file = current_files[index_to_delete]
            remaining = [f for i, f in enumerate(current_files) if i != index_to_delete]
            logger.info(f"🗑️ ȘTERGERE FIȘIER INDIVIDUAL: {deleted_file['filename']} (index {index_to_delete})")
            logger.info(f"📊 Rămân {len(remaining)} fișiere: {[f['filename'] for f in remaining]}")
            logger.info(f"🎯 RETURN: {len(remaining)} fișiere → STORE")
            return remaining
        else:
            logger.error(f"❌ Index invalid pentru ștergere: {index_to_delete} (current_files length: {len(current_files) if current_files else 0})")
    
    logger.warning("⚠️ Nicio condiție satisfăcută - returnez no_update")
    return no_update


@app.callback(
    [Output('admin-batch-result', 'children'),
     Output('admin-refresh-trigger', 'data'),
     Output('admin-batch-session-id', 'data', allow_duplicate=True),
     Output('admin-batch-progress-container', 'style'),
     Output('admin-batch-progress-interval', 'disabled'),
     Output('admin-batch-uploaded-files-store', 'data', allow_duplicate=True),
     Output('active-date-filter', 'data', allow_duplicate=True)],  # [FIX] Resetăm filtrul dată după batch
    [Input('admin-start-batch-button', 'n_clicks')],
    [State('admin-batch-mode-selector', 'value'),
     State('admin-batch-input-folder', 'value'),
     State('admin-batch-session-id', 'data'),
     State('admin-batch-output-folder', 'value'),
     State('admin-batch-window-minutes', 'value')],
    prevent_initial_call=True
)
def admin_run_batch_processing(n_clicks, batch_mode, input_folder, session_id, output_folder, window_minutes):
    """
    Callback pentru procesare batch + generare automată link-uri + tracking progres.
    Suportă AMBELE moduri: local (folder) și upload (fișiere).
    """
    # [FIX] Top-level try-except pentru a prinde ORICE eroare și a preveni 500 Generic
    try:
        if n_clicks == 0:
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update
        
        logger.warning(f"🔍 [BATCH] START PROCESSING - Mode: {batch_mode}, Session: {session_id}")
        
        processing_folder = None
        
        # === DETERMINARE FOLDER PROCESARE ===
        if batch_mode == 'local':
            # Mod local: verificăm folder
            if not input_folder or input_folder.strip() == '':
                return html.Div(
                    "⚠️ Specificați folderul de intrare!",
                    style={'padding': '15px', 'backgroundColor': '#fff3cd', 'border': '1px solid #ffc107', 'borderRadius': '5px'}
                ), no_update, no_update, no_update, no_update, no_update, no_update
            
            processing_folder = input_folder
            logger.warning(f"✅ Procesare LOCALĂ din folder: {input_folder}")
            
        else:  # batch_mode == 'upload'
            # Verificăm session_id (care este upload_id din dash-uploader)
            if not session_id or not isinstance(session_id, str):
                logger.error(f"❌ [BATCH] Session ID invalid: {session_id}")
                return html.Div(
                    "⚠️ Niciun fișier încărcat! Vă rugăm să încărcați fișierele întâi.",
                    style={'padding': '15px', 'backgroundColor': '#fff3cd', 'border': '1px solid #ffc107', 'borderRadius': '5px'}
                ), no_update, no_update, no_update, no_update, no_update, no_update
            
            # Construim calea către folderul de upload dash-uploader
            # Acesta se află în ./temp_uploads/{session_id}
            base_upload_dir = os.path.join(os.getcwd(), 'temp_uploads')
            processing_folder = os.path.join(base_upload_dir, session_id)
            
            if not os.path.exists(processing_folder):
                 # [DEBUG] Listare conținut folder părinte pentru a vedea ce există
                 try:
                     available_folders = os.listdir(base_upload_dir) if os.path.exists(base_upload_dir) else ["DIR_MISSING"]
                 except:
                     available_folders = ["ERROR_SCANNING"]
                     
                 logger.error(f"❌ Folder lipsă: {processing_folder}")
                 logger.error(f"📂 Foldere disponibile în {base_upload_dir}: {available_folders}")
                 
                 return html.Div(
                    f"⚠️ Sesiunea de upload nu a fost găsită. Căutat în: {processing_folder}. Disponibil: {available_folders}",
                    style={'padding': '15px', 'backgroundColor': '#ffdddd', 'border': '1px solid red', 'borderRadius': '5px'}
                ), no_update, no_update, no_update, no_update, no_update, no_update

            logger.warning(f"🚀 [BATCH] Procesare UPLOAD din folder: {processing_folder}")
        
        # Folosim folder default pentru output dacă nu e specificat
        if not output_folder or output_folder.strip() == '':
            output_folder = config.OUTPUT_DIR
        
        logger.info(f"📊 Admin pornește procesare batch: {processing_folder} → {output_folder}")
        
        # Găsim toate fișierele CSV și PDF din folder
        csv_files = [f for f in os.listdir(processing_folder) if f.lower().endswith('.csv')]
        pdf_files = [f for f in os.listdir(processing_folder) if f.lower().endswith('.pdf')]
        
        if not csv_files:
            return html.Div(
                f"⚠️ Nu există fișiere CSV în folder! (Găsite: {len(pdf_files)} PDF-uri)",
                style={'padding': '15px', 'backgroundColor': '#fff3cd', 'border': '1px solid #ffc107', 'borderRadius': '5px'}
            ), no_update, no_update, no_update, no_update, no_update, no_update
        
        # Creăm sesiune batch cu tracking
        batch_id = batch_session_manager.create_batch_session(
            total_files=len(csv_files),  # PDF-urile sunt procesate asociat, numărăm CSV-urile ca "task-uri"
            file_list=csv_files
        )
        
        logger.info(f"📊 Sesiune batch creată: {batch_id} cu {len(csv_files)} fișiere")
        
        # ACTIVĂM bara de progres și interval-ul de refresh
        progress_style = {'display': 'block', 'marginBottom': '20px'}
        interval_disabled = False
        
        # Rulăm procesarea batch
        # Nota: Deși avem dash-uploader, logica de procesare rămâne aceeași
        # run_batch_job citește din folderul specificat
        generated_links = run_batch_job(
            processing_folder,  
            output_folder, 
            window_minutes,
            session_id=batch_id  
        )
        
        # Marcăm sesiunea ca finalizată
        batch_session_manager.mark_session_completed(batch_id)
        
        # Ștergem folderul temporar dacă e în mod upload
        if batch_mode == 'upload':
            import shutil
            try:
                shutil.rmtree(processing_folder)
                logger.info(f"🗑️ Folder temporar șters: {processing_folder}")
            except Exception as cleanup_error:
                logger.warning(f"Nu s-a putut șterge folderul temporar: {cleanup_error}")
        
        # [FIX v3] NU MAI GOLIM AUTOMAT STORE-UL după procesare
        # [WHY] Utilizatorul poate dori să proceseze din nou sau să verifice lista
        # [SOLUTION] Butonul "🗑️ Șterge toate" permite golire manuală
        files_to_clear = no_update  # Nu golim automat
        logger.warning(f"🗑️ Store files_to_clear: {files_to_clear} (batch_mode={batch_mode})")
        logger.warning("✅ Store-ul rămâne INTACT după procesare (golire manuală disponibilă)")
        
        if not generated_links:
            return html.Div([
                html.H4("⚠️ Procesare Finalizată, Dar Fără Link-uri Generate", style={'color': 'orange'}),
                html.P("Verificați dacă există fișiere CSV valide și log-urile pentru detalii.")
            ], style={'padding': '20px', 'backgroundColor': '#fff3cd', 'border': '1px solid #ffc107', 'borderRadius': '10px'}), n_clicks, None, {'display': 'none'}, True, files_to_clear, no_update
        
        # Construim mesajul de succes cu lista de link-uri
        # Obținem APP_URL din environment (Railway sau localhost)
        app_url = os.getenv('APP_URL', 'http://127.0.0.1:8050')
        
        link_rows = []
        for link in generated_links:
            link_url = f"{app_url}/?token={link['token']}"
            link_rows.append(
                html.Div([
                    html.Strong(f"📅 {link['recording_date']} | {link['start_time']} - {link['end_time']}", style={'display': 'block', 'marginBottom': '8px'}),
                    html.Small(f"🔧 {link['device_name']} | 🖼️ {link['images_count']} imagini", style={'color': '#666', 'display': 'block', 'marginBottom': '8px'}),
                    html.Div([
                        dcc.Input(
                            id={'type': 'link-input-batch', 'index': link['token']},
                            value=link_url,
                            readOnly=True,
                            style={
                                'width': '100%',
                                'padding': '8px',
                                'fontSize': '11px',
                                'fontFamily': 'monospace',
                                'backgroundColor': '#f0f0f0',
                                'border': '1px solid #bdc3c7',
                                'borderRadius': '3px',
                                'marginBottom': '8px'
                            }
                        ),
                        html.Div([
                            html.Button(
                                '📋 ',
                                id={'type': 'copy-link-batch', 'index': link['token']},
                                n_clicks=0,
                                style={
                                    'padding': '6px 15px',
                                    'marginRight': '8px',
                                    'backgroundColor': '#3498db',
                                    'color': 'white',
                                    'border': 'none',
                                    'borderRadius': '3px',
                                    'cursor': 'pointer',
                                    'fontWeight': 'bold'
                                }
                            ),
                            html.A(
                                '🌐 Testează în browser',
                                href=link_url,
                                target='_blank',
                                style={
                                    'padding': '6px 15px',
                                    'backgroundColor': '#27ae60',
                                    'color': 'white',
                                    'textDecoration': 'none',
                                    'borderRadius': '3px',
                                    'fontSize': '12px',
                                    'fontWeight': 'bold',
                                    'display': 'inline-block'
                                }
                            )
                        ], style={'display': 'flex', 'gap': '8px'})
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
            html.Small(f"ℹ️ {len(pdf_files)} PDF-uri detectate în folder pentru asociere.", style={'color': '#666', 'display': 'block', 'marginBottom': '10px'}),
            html.Hr(),
            html.Div(link_rows, style={'maxHeight': '400px', 'overflowY': 'auto'})
        ], style={'padding': '20px', 'backgroundColor': '#d4edda', 'border': '1px solid #28a745', 'borderRadius': '10px'}), n_clicks, session_id, progress_style, interval_disabled, files_to_clear, None  # [FIX] Return None pentru resetare filtru dată
        
    except Exception as e:
        logger.error("="*100)
        logger.error("💥 [BATCH PROCESSING] CRITICAL ERROR CAUGHT!")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Exception message: {str(e)}")
        logger.error("="*100, exc_info=True)
        
        return (
            html.Div(
                [
                    html.H4("❌ EROARE CRITICĂ", style={'color': 'red'}),
                    html.P(f"Batch processing a eșuat: {str(e)}"),
                    html.P("Verificați Railway logs pentru detalii complete.")
                ],
                style={'padding': '15px', 'backgroundColor': '#ffdddd', 'border': '1px solid red', 'borderRadius': '5px', 'color': 'red'}
            ), 
            no_update,  # admin-refresh-trigger
            None,  # admin-batch-session-id
            {'display': 'none'},  # admin-batch-progress-container
            True,  # admin-batch-progress-interval disabled
            no_update,  # admin-batch-uploaded-files-store
            no_update  # active-date-filter
        )


@app.callback(
    [Output('data-view-container', 'children'),
     Output('expanded-row-id', 'data'),
     Output('collapsed-groups-store', 'data')],
    [Input('admin-refresh-data-view', 'n_clicks'),
     Input('admin-refresh-trigger', 'data'),
     Input({'type': 'expand-row-btn', 'index': ALL}, 'n_clicks'),
     Input({'type': 'toggle-group-btn', 'index': ALL}, 'n_clicks'),
     Input('active-date-filter', 'data'),
     Input('date-filter-mode', 'value'),  # [NEW] Filter mode: 'upload' or 'recording'
     Input('date-grouping', 'value')],
    [State('expanded-row-id', 'data'),
     State({'type': 'expand-row-btn', 'index': ALL}, 'id'),
     State({'type': 'toggle-group-btn', 'index': ALL}, 'id'),
     State('collapsed-groups-store', 'data')]
)
def load_data_view_with_accordion(n_clicks_refresh, trigger, expand_clicks, toggle_group_clicks, date_filter, filter_mode, grouping, expanded_id, expand_btn_ids, toggle_group_ids, collapsed_groups):
    """
    Încarcă vizualizarea datelor cu funcționalitate accordion (expandare/colapsare).
    """
    from dash import ctx
    import base64
    
    logger.debug("Callback data-view apelat.")
    
    # [DIAGNOSTIC LOG GLOBAL]
    trigger_id = ctx.triggered_id
    logger.info("="*80)
    logger.info(f"⚡ [ADMIN_CALLBACK] TRIGGERED! ID: {trigger_id}")
    
    # LOG: Afișăm ce a trigger-uit callback-ul
    if trigger_id:
        logger.info(f"   - Type: {type(trigger_id)}")
        if isinstance(trigger_id, dict):
             logger.info(f"   - Dict Keys: {trigger_id.keys()}")
             logger.info(f"   - Index: {trigger_id.get('index')}")
    else:
        logger.info("   - Initial Call / No Trigger")
    
    logger.info("="*80)

    # Inițializăm collapsed_groups dacă e None
    if collapsed_groups is None:
        collapsed_groups = []
    
    # Determinăm care rând trebuie expandat
    current_expanded = expanded_id
    
    # Verificăm dacă s-a dat click pe un buton de toggle grup
    if ctx.triggered_id and isinstance(ctx.triggered_id, dict) and ctx.triggered_id.get('type') == 'toggle-group-btn':
        clicked_group = ctx.triggered_id['index']
        logger.info(f"🔵 CLICK TOGGLE GRUP DETECTAT: '{clicked_group}'")
        logger.info(f"📋 Grupuri collapsed înainte: {collapsed_groups}")
        # Toggle: dacă grupul e collapsed, îl expandăm; altfel îl colapsăm
        if clicked_group in collapsed_groups:
            collapsed_groups.remove(clicked_group)
            logger.info(f"✅ EXPANDARE grup: '{clicked_group}' → Grupuri collapsed: {collapsed_groups}")
        else:
            collapsed_groups.append(clicked_group)
            logger.info(f"⬇️ COLAPSARE grup: '{clicked_group}' → Grupuri collapsed: {collapsed_groups}")
    
    # Verificăm dacă s-a dat click pe un buton de expandare rând
    if ctx.triggered_id and isinstance(ctx.triggered_id, dict) and ctx.triggered_id.get('type') == 'expand-row-btn':
        clicked_token = ctx.triggered_id['index']
        # Toggle: dacă e deja expandat, îl închidem; altfel îl deschidem
        if current_expanded == clicked_token:
            current_expanded = None
        else:
            current_expanded = clicked_token
    
    try:
        from datetime import datetime
        
        logger.info("="*100)
        logger.info("📊 [DATA VIEW] load_data_view_with_accordion CALLBACK START")
        logger.info("="*100)
        
        # [LOG 1-5] Parametri callback
        logger.info(f"📋 [LOG 1] date_filter param: {date_filter}")
        logger.info(f"📋 [LOG 1.5] filter_mode param: {filter_mode}")  # [NEW] Log filter mode
        logger.info(f"📋 [LOG 2] grouping param: {grouping}")
        logger.info(f"📋 [LOG 3] n_clicks_refresh: {n_clicks_refresh}")
        logger.info(f"📋 [LOG 4] trigger data: {trigger}")
        logger.info(f"📋 [LOG 5] expanded_id: {expanded_id}")
        
        # [LOG 6-10] Încărcare date
        logger.info(f"🔄 [LOG 6] Calling patient_links.get_all_links_for_admin()...")
        all_links = patient_links.get_all_links_for_admin()
        logger.info(f"📊 [LOG 7] TOTAL LINKS RECEIVED: {len(all_links)}")
        
        if not all_links:
            logger.warning("⚠️ [LOG 8] NO LINKS FOUND - returning empty state")
            return html.Div(
                "📭 Nu există înregistrări încă. Procesați fișiere CSV din tab-ul 'Procesare Batch'.",
                style={'padding': '50px', 'textAlign': 'center', 'color': '#666', 'fontStyle': 'italic', 'backgroundColor': '#f8f9fa', 'borderRadius': '10px'}
            ), current_expanded, collapsed_groups
        
        # [LOG 11-15] Analiza date range
        logger.info(f"📅 [LOG 11] Analyzing date range of all links...")
        dates_found = []
        for link in all_links:
            if link.get('recording_date'):
                dates_found.append(link['recording_date'])
            elif link.get('created_at'):
                try:
                    created = datetime.fromisoformat(link['created_at']).date().isoformat()
                    dates_found.append(created)
                except:
                    pass
        
        if dates_found:
            logger.info(f"📅 [LOG 12] Oldest date in dataset: {min(dates_found)}")
            logger.info(f"📅 [LOG 13] Newest date in dataset: {max(dates_found)}")
            logger.info(f"📅 [LOG 14] Sample dates (first 5): {dates_found[:5]}")
        else:
            logger.warning("⚠️ [LOG 15] NO DATES FOUND in any link!")
        
        # [LOG 16-20] Detalii link-uri înainte de filtrare
        logger.info(f"📋 [LOG 16] First 3 links details:")
        for idx, link in enumerate(all_links[:3]):
            logger.info(f"   [LOG 17.{idx}] Token: {link['token'][:8]}... | created_at: {link.get('created_at')} | recording_date: {link.get('recording_date')} | device: {link.get('device_name')[:30]}...")
        
        # === FILTRARE TEMPORALĂ ===
        logger.info(f"🔍 [LOG 18] Checking date filter...")
        if date_filter and date_filter.get('start') and date_filter.get('end'):
            start_date = datetime.fromisoformat(date_filter['start']).date()
            end_date = datetime.fromisoformat(date_filter['end']).date()
            filter_label = date_filter.get('label', 'Interval Personalizat')
            
            logger.info(f"🔍 [LOG 19] DATE FILTER ACTIVE!")
            logger.info(f"🔍 [LOG 20] Filter label: '{filter_label}'")
            logger.info(f"🔍 [LOG 21] Filter start_date: {start_date}")
            logger.info(f"🔍 [LOG 22] Filter end_date: {end_date}")
            logger.info(f"🔍 [LOG 23] Links BEFORE filtering: {len(all_links)}")
            
            # [DUAL FILTER MODE] Filtrăm după modul selectat: upload sau medical date
            logger.warning(f"🔧 [FILTER_MODE] Active mode: {filter_mode}")
            logger.warning(f"🔧 [FILTER_MODE] Filtering by: {'Last Processing Date (last_processed_at)' if filter_mode == 'upload' else 'Medical Test Date (recording_date)'}")
            
            filtered_links = []
            for idx, link in enumerate(all_links):
                if filter_mode == 'upload':
                    # MODE A: Filter by LAST PROCESSING date (last_processed_at with fallback to created_at)
                    # [FIX v5.0] Use last_processed_at to show reprocessed files
                    processing_date_str = link.get('last_processed_at') or link.get('created_at')
                    if processing_date_str:
                        try:
                            processing_date = datetime.fromisoformat(processing_date_str).date()
                            is_in_range = start_date <= processing_date <= end_date
                            field_used = 'last_processed_at' if link.get('last_processed_at') else 'created_at (fallback)'
                            logger.info(f"   [LOG 24.{idx}] Token {link['token'][:8]}... | {field_used}: {processing_date} | in_range: {is_in_range}")
                            if is_in_range:
                                filtered_links.append(link)
                        except Exception as parse_err:
                            logger.warning(f"   ⚠️ [LOG 25.{idx}] Token {link['token'][:8]}... | Processing date parse FAILED: {parse_err}")
                    else:
                        logger.warning(f"   ⚠️ [LOG 26.{idx}] Token {link['token'][:8]}... | NO last_processed_at OR created_at field!")
                else:
                    # MODE B: Filter by medical recording date (recording_date)
                    if link.get('recording_date'):
                        try:
                            rec_date = datetime.strptime(link['recording_date'], '%Y-%m-%d').date()
                            is_in_range = start_date <= rec_date <= end_date
                            logger.info(f"   [LOG 24.{idx}] Token {link['token'][:8]}... | recording_date: {rec_date} | in_range: {is_in_range}")
                            if is_in_range:
                                filtered_links.append(link)
                        except Exception as parse_err:
                            logger.warning(f"   ⚠️ [LOG 25.{idx}] Token {link['token'][:8]}... | Recording date parse FAILED: {parse_err}")
                    else:
                        logger.warning(f"   ⚠️ [LOG 26.{idx}] Token {link['token'][:8]}... | NO recording_date field!")
            
            logger.info(f"✅ [LOG 27] Links AFTER filtering: {len(filtered_links)} (removed {len(all_links) - len(filtered_links)})")
            all_links = filtered_links
        else:
            logger.info(f"ℹ️ [LOG 28] NO DATE FILTER active - showing ALL {len(all_links)} links")
        
        # === GRUPARE PE ZILE/SĂPTĂMÂNI/LUNI ===
        grouped_links = {}
        if grouping == 'day':
            # Grupare pe zile (cu format DD/MM/YYYY pentru display)
            for link in all_links:
                date_raw = link.get('recording_date', 'Dată necunoscută')
                if date_raw != 'Dată necunoscută':
                    try:
                        # Convertim din YYYY-MM-DD în DD/MM/YYYY pentru afișare
                        rec_date = datetime.strptime(date_raw, '%Y-%m-%d').date()
                        date_key = rec_date.strftime('%d/%m/%Y')
                    except:
                        date_key = 'Dată necunoscută'
                else:
                    date_key = 'Dată necunoscută'
                
                if date_key not in grouped_links:
                    grouped_links[date_key] = []
                grouped_links[date_key].append(link)
        elif grouping == 'week':
            # Grupare pe săptămâni
            for link in all_links:
                if link.get('recording_date'):
                    try:
                        rec_date = datetime.strptime(link['recording_date'], '%Y-%m-%d').date()
                        # Calculăm numărul săptămânii
                        week_num = rec_date.isocalendar()[1]
                        year = rec_date.year
                        week_key = f"Săptămâna {week_num}, {year}"
                        if week_key not in grouped_links:
                            grouped_links[week_key] = []
                        grouped_links[week_key].append(link)
                    except:
                        if 'Dată necunoscută' not in grouped_links:
                            grouped_links['Dată necunoscută'] = []
                        grouped_links['Dată necunoscută'].append(link)
                else:
                    if 'Dată necunoscută' not in grouped_links:
                        grouped_links['Dată necunoscută'] = []
                    grouped_links['Dată necunoscută'].append(link)
        elif grouping == 'month':
            # Grupare pe luni (cu format DD/MM/YYYY pentru display)
            for link in all_links:
                if link.get('recording_date'):
                    try:
                        rec_date = datetime.strptime(link['recording_date'], '%Y-%m-%d').date()
                        # Formatăm luna în format românesc  
                        month_names = ['Ianuarie', 'Februarie', 'Martie', 'Aprilie', 'Mai', 'Iunie', 
                                     'Iulie', 'August', 'Septembrie', 'Octombrie', 'Noiembrie', 'Decembrie']
                        month_key = f"{month_names[rec_date.month - 1]} {rec_date.year}"
                        if month_key not in grouped_links:
                            grouped_links[month_key] = []
                        grouped_links[month_key].append(link)
                    except:
                        if 'Dată necunoscută' not in grouped_links:
                            grouped_links['Dată necunoscută'] = []
                        grouped_links['Dată necunoscută'].append(link)
                else:
                    if 'Dată necunoscută' not in grouped_links:
                        grouped_links['Dată necunoscută'] = []
                    grouped_links['Dată necunoscută'].append(link)
        else:
            # Fără grupare - afișare liniară
            grouped_links['Toate înregistrările'] = all_links
        
        if not all_links:
            filter_msg = f" pentru perioada selectată ({date_filter.get('label', '')})" if date_filter else ""
            return html.Div(
                f"📭 Nu există înregistrări{filter_msg}. Încercați să modificați filtrul sau să procesați mai multe fișiere CSV.",
                style={'padding': '50px', 'textAlign': 'center', 'color': '#666', 'fontStyle': 'italic', 'backgroundColor': '#f8f9fa', 'borderRadius': '10px'}
            ), current_expanded, collapsed_groups
        
        # Construim lista de rânduri cu funcționalitate accordion
        rows = []

        def _group_chrono_key(gname: str):
            """Cheie sortare: cele mai recente primele; 'Dată necunoscută' la final."""
            if grouping == 'day':
                if gname == 'Dată necunoscută':
                    return datetime.min.date()
                try:
                    return datetime.strptime(gname, '%d/%m/%Y').date()
                except Exception:
                    return datetime.min.date()
            if grouping == 'week':
                if gname == 'Dată necunoscută':
                    return (0, 0)
                m = re.match(r'Săptămâna\s+(\d+),\s*(\d+)', gname)
                if m:
                    return (int(m.group(2)), int(m.group(1)))
                return (0, 0)
            if grouping == 'month':
                if gname == 'Dată necunoscută':
                    return (0, 0)
                month_names_ro = [
                    'Ianuarie', 'Februarie', 'Martie', 'Aprilie', 'Mai', 'Iunie',
                    'Iulie', 'August', 'Septembrie', 'Octombrie', 'Noiembrie', 'Decembrie',
                ]
                parts = gname.rsplit(' ', 1)
                if len(parts) == 2:
                    month_name, year_s = parts[0], parts[1]
                    try:
                        y = int(year_s)
                        if month_name in month_names_ro:
                            return (y, month_names_ro.index(month_name) + 1)
                    except ValueError:
                        pass
                return (0, 0)
            return gname

        def _link_rec_sort_key(link: dict):
            rd = link.get('recording_date') or ''
            st = link.get('start_time') or ''
            try:
                d = datetime.strptime(rd, '%Y-%m-%d').date() if rd else datetime.min.date()
            except Exception:
                d = datetime.min.date()
            return (d, st)

        sorted_groups = sorted(
            grouped_links.items(), key=lambda it: _group_chrono_key(it[0]), reverse=True
        )

        # Parcurgem fiecare grupă
        for group_name, group_links in sorted_groups:
            group_links = sorted(group_links, key=_link_rec_sort_key, reverse=True)
            is_group_collapsed = group_name in collapsed_groups
            
            # Header pentru grupă (CLICABIL cu toggle)
            if grouping in ['week', 'month', 'day']:
                # Iconița pentru collapse/expand
                toggle_icon = "▼" if not is_group_collapsed else "▶"
                
                rows.append(html.Button(
                    children=[
                        html.Div([
                            html.Span(
                                toggle_icon, 
                                style={
                                    'fontSize': '18px', 
                                    'marginRight': '10px', 
                                    'color': 'white' if not is_group_collapsed else '#3498db',
                                    'transition': 'transform 0.3s ease'
                                }
                            ),
                            html.Span(
                                f"📅 {group_name}", 
                                style={
                                    'fontSize': '18px', 
                                    'fontWeight': 'bold', 
                                    'color': 'white' if not is_group_collapsed else '#2c3e50'
                                }
                            ),
                            html.Span(
                                f" — {len(group_links)} {'înregistrare' if len(group_links) == 1 else 'înregistrări'}",
                                style={
                                    'fontSize': '14px', 
                                    'color': 'rgba(255,255,255,0.9)' if not is_group_collapsed else '#7f8c8d', 
                                    'marginLeft': '10px'
                                }
                            )
                        ], style={'display': 'flex', 'alignItems': 'center'})
                    ],
                    id={'type': 'toggle-group-btn', 'index': group_name},
                    n_clicks=0,
                    style={
                        'width': '100%',
                        'padding': '15px 20px',
                        'marginTop': '25px',
                        'marginBottom': '10px',
                        'backgroundColor': '#3498db' if not is_group_collapsed else '#ecf0f1',
                        'color': 'white' if not is_group_collapsed else '#2c3e50',
                        'border': f"2px solid {'#3498db' if not is_group_collapsed else '#bdc3c7'}",
                        'borderRadius': '8px',
                        'cursor': 'pointer',
                        'textAlign': 'left',
                        'fontSize': '16px',
                        'fontWeight': 'bold',
                        'transition': 'all 0.3s ease',
                        'boxShadow': '0 3px 6px rgba(0,0,0,0.15)' if not is_group_collapsed else '0 2px 4px rgba(0,0,0,0.08)'
                    },
                    className='group-toggle-button'
                ))
            
            # Container pentru înregistrările din acest grup
            group_rows = []
            
            logger.info(f"🔍 Grup '{group_name}': are {len(group_links)} link-uri în group_links")
            
            # Rânduri pentru fiecare link din grupă (ascunse dacă grupul e collapsed)
            for idx, link_data in enumerate(group_links):
                logger.info(f"  ↳ INTRAT în loop pentru link #{idx+1} din grup '{group_name}' - token: {link_data['token'][:8]}...")
                token = link_data['token']
                is_expanded = (current_expanded == token)
                logger.info(f"  ↳ Token {token[:8]}... - is_expanded: {is_expanded}")
                
                # Formatare dată
                date_display = "Data nespecificată"
                logger.info(f"  ↳ Începere formatare dată pentru {token[:8]}...")
                try:
                    if link_data.get('recording_date'):
                        date_display = format_recording_date_ro(
                            link_data.get('recording_date', ''),
                            link_data.get('start_time', ''),
                            link_data.get('end_time', '')
                        )
                    logger.info(f"  ↳ Formatare dată completă: {date_display[:50]}...")
                except Exception as format_err:
                    logger.error(f"  ❌ EROARE la formatare dată pentru {token[:8]}: {format_err}", exc_info=True)
                    date_display = f"{link_data.get('recording_date', 'N/A')} {link_data.get('start_time', '')} - {link_data.get('end_time', '')}"
                
                # Status vizualizări
                view_count = link_data.get('view_count', 0)
                view_display = f"👁️ {view_count}"
                
                # Status PDF-uri
                pdf_count = len(link_data.get('pdf_paths', []))
                pdf_display = f" | 📕 {pdf_count}" if pdf_count > 0 else ""

                logger.info(f"  ↳ Creare compact_row pentru {token[:8]}...")
                
                # === RÂND COMPACT (întotdeauna vizibil) - CLICKABIL PE ÎNTREAGA LINIE ===
                compact_row = html.Button(
                    children=[
                        # Info condensată (FĂRĂ iconița play)
                        html.Div([
                            html.Strong(f"📅 {date_display}", style={'fontSize': '16px', 'color': '#2c3e50', 'display': 'block', 'marginBottom': '5px'}),
                            html.Small(f"🔧 {link_data['device_name']} | {view_display}{pdf_display}", style={'color': '#7f8c8d', 'display': 'block', 'fontSize': '13px'})
                        ], style={'flex': '1', 'textAlign': 'left'})
                    ],
                    id={'type': 'expand-row-btn', 'index': token},
                    n_clicks=0,
                    style={
                        'width': '100%',
                        'display': 'flex',
                        'alignItems': 'center',
                        'padding': '18px 20px',
                        'backgroundColor': '#fff' if not is_expanded else '#e8f4f8',
                        'border': '2px solid #ddd' if not is_expanded else '2px solid #3498db',
                        'borderLeft': '5px solid #3498db' if is_expanded else '5px solid #95a5a6',
                        'borderRadius': '8px',
                        'cursor': 'pointer',
                        'transition': 'all 0.3s ease',
                        'boxShadow': '0 2px 4px rgba(0,0,0,0.08)' if not is_expanded else '0 4px 12px rgba(52, 152, 219, 0.2)',
                        'marginBottom': '10px'
                    }
                )
                
                logger.info(f"  ↳ Compact_row creat pentru {token[:8]}, acum expanded_content...")
                
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
                    
                    # Secțiune grafic interactiv - IMPLEMENTAT v2.0
                    graph_content = []
                    try:
                        # [DIAGNOSTIC LOG A1] Start Admin Graph
                        logger.info(f"📊 [ADMIN_VIEW] Start generare grafic pentru token: {token[:8]}...")
                        
                        # 1. Recuperăm datele folosind serviciul centralizat
                        # [DIAGNOSTIC LOG A2] Apel DataService
                        graph_df, graph_filename, graph_status = data_service.get_patient_dataframe(token)
                        
                        if graph_df is not None and not graph_df.empty:
                            # [DIAGNOSTIC LOG A3] Data Found
                            logger.info(f"✅ [ADMIN_VIEW] Date găsite: {len(graph_df)} rânduri. Generare figură...")
                            
                            # 2. Generăm graficul
                            admin_fig = create_plot(graph_df, file_name=graph_filename)
                            
                            # [DIAGNOSTIC LOG A4] Plot Created
                            if admin_fig:
                                 logger.info(f"✅ [ADMIN_VIEW] Figura creată. Traces: {len(admin_fig.data) if hasattr(admin_fig, 'data') else 'N/A'}")
                            else:
                                 logger.error("❌ [ADMIN_VIEW] create_plot a returnat None!")

                            # Adăugăm logo dacă e configurat (opțional)
                            try:
                                from plot_generator import apply_logo_to_figure
                                admin_fig = apply_logo_to_figure(admin_fig)
                            except Exception as logo_e:
                                logger.warning(f"⚠️ [ADMIN_VIEW] Eroare logo: {logo_e}")
                            
                            # 3. Randăm componenta Graph
                            # [DIAGNOSTIC LOG A5] Rendering Graph
                            graph_content = html.Div([
                                html.H4("📈 Grafic Interactiv Detaliat", style={'color': '#2980b9', 'marginBottom': '10px'}),
                                dcc.Graph(
                                    figure=admin_fig,
                                    config={'displayModeBar': True, 'scrollZoom': True},
                                    style={'height': '500px'},
                                    id={"type": "admin-graph", "index": token} # ID unic pentru debug
                                )
                            ], style={'marginBottom': '25px', 'padding': '15px', 'backgroundColor': 'white', 'borderRadius': '8px', 'border': '1px solid #ddd'})
                            logger.info(f"🚀 [ADMIN_VIEW] Componenta Graph adăugată în layout pentru {token[:8]}")
                        else:
                             # Fallback: Mesaj că nu există date
                             # [DIAGNOSTIC LOG A6] No Data
                             logger.warning(f"⚠️ [ADMIN_VIEW] Nu există date (df is None). Status: {graph_status}")
                             graph_content = html.Div([
                                html.H4("📉 Date Grafic Indisponibile", style={'color': '#7f8c8d', 'marginBottom': '10px'}),
                                html.P(f"Motiv: {graph_status}", style={'fontStyle': 'italic', 'color': '#e74c3c'})
                            ], style={'marginBottom': '25px', 'padding': '20px', 'backgroundColor': '#f8f9fa', 'borderRadius': '8px'})
                    except Exception as graph_err:
                        # [DIAGNOSTIC LOG A7] Exception
                        logger.error(f"❌ [ADMIN_VIEW] Eroare critică generare grafic: {graph_err}", exc_info=True)
                        graph_content = html.Div(f"Eroare generare grafic: {str(graph_err)}", style={'color': 'red'})


                    expanded_content = html.Div([
                        html.Hr(style={'margin': '15px 0', 'border': 'none', 'borderTop': '2px solid #bdc3c7'}),
                        
                        # AICI INSERĂM GRAFICUL GENERAT
                        html.Div(graph_content),
                        
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
                            
                            # Upload nou PDF
                            html.Div([
                                dcc.Upload(
                                    id={'type': 'pdf-upload', 'index': token},
                                    children=html.Div([
                                        '📁 Click pentru a încărca raport PDF (Checkme O2)'
                                    ]),
                                    style={
                                        'width': '100%',
                                        'height': '60px',
                                        'lineHeight': '60px',
                                        'borderWidth': '2px',
                                        'borderStyle': 'dashed',
                                        'borderRadius': '8px',
                                        'textAlign': 'center',
                                        'backgroundColor': '#e8f5e9',
                                        'color': '#27ae60',
                                        'cursor': 'pointer',
                                        'fontWeight': 'bold'
                                    },
                                    multiple=False
                                ),
                                html.Div(
                                    id={'type': 'pdf-upload-feedback', 'index': token},
                                    style={'marginTop': '10px'}
                                )
                            ], style={'marginBottom': '20px'}),
                            
                            # Afișare PDF-uri existente (încărcat dinamic la expandare)
                            html.Div(
                                id={'type': 'pdf-display-container', 'index': token},
                                children=render_pdfs_display(token, patient_links.get_all_pdfs_for_link(token))
                            )
                        ], style={'marginBottom': '25px', 'padding': '20px', 'backgroundColor': '#f8f9fa', 'borderRadius': '8px'}),
                        
                        # Secțiune interpretare
                        html.Div([
                            html.H4("📝 Interpretare", style={'color': '#2980b9', 'marginBottom': '10px'}),
                            dcc.Textarea(
                                id={'type': 'medical-interpretation', 'index': token},
                                value=link_data.get('medical_notes', ''),
                                placeholder='Scrieți interpretarea aici (ex: Episoade de desaturare nocturnă, apnee obstructivă severă, recomand CPAP)...',
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
                            html.Strong("🔗 Link Pacient: ", style={'marginRight': '10px', 'display': 'block', 'marginBottom': '10px'}),
                            dcc.Input(
                                id={'type': 'link-input-view', 'index': token},
                                value=f"{os.getenv('APP_URL', 'http://127.0.0.1:8050')}/?token={token}",
                                readOnly=True,
                                style={
                                    'width': '100%',
                                    'padding': '10px',
                                    'backgroundColor': '#ecf0f1',
                                    'border': '2px solid #bdc3c7',
                                    'borderRadius': '5px',
                                    'fontSize': '12px',
                                    'fontFamily': 'monospace',
                                    'marginBottom': '10px'
                                }
                            ),
                            html.Div([
                                html.Button(
                                    '📋 Copy Link',
                                    id={'type': 'copy-link-view', 'index': token},
                                    n_clicks=0,
                                    style={
                                        'padding': '8px 20px',
                                        'marginRight': '10px',
                                        'backgroundColor': '#3498db',
                                        'color': 'white',
                                        'border': 'none',
                                        'borderRadius': '5px',
                                        'cursor': 'pointer',
                                        'fontSize': '13px',
                                        'fontWeight': 'bold'
                                    }
                                ),
                                html.A(
                                    '🌐 Testează în browser',
                                    href=f"{os.getenv('APP_URL', 'http://127.0.0.1:8050')}/?token={token}",
                                    target='_blank',
                                    style={
                                        'padding': '8px 20px',
                                        'backgroundColor': '#27ae60',
                                        'color': 'white',
                                        'textDecoration': 'none',
                                        'borderRadius': '5px',
                                        'fontSize': '13px',
                                        'fontWeight': 'bold',
                                        'display': 'inline-block'
                                    }
                                )
                            ], style={'display': 'flex', 'gap': '10px'})
                        ], style={'marginTop': '20px'}),
                        
                        # Secțiune ștergere înregistrare
                        html.Div([
                            html.Hr(style={'margin': '20px 0', 'borderTop': '2px solid #e74c3c'}),
                            html.Div([
                                html.Strong("⚠️ Zonă Periculoasă", style={'color': '#e74c3c', 'fontSize': '16px', 'marginBottom': '10px', 'display': 'block'}),
                                html.P(
                                    "Ștergerea acestei înregistrări va șterge permanent toate datele asociate (CSV, imagini, PDF-uri). Această acțiune este IREVERSIBILĂ!",
                                    style={'fontSize': '13px', 'color': '#555', 'marginBottom': '15px', 'lineHeight': '1.6'}
                                ),
                                html.Button(
                                    '🗑️ Șterge această înregistrare',
                                    id={'type': 'delete-link-btn', 'index': token},
                                    n_clicks=0,
                                    style={
                                        'padding': '10px 30px',
                                        'backgroundColor': '#e74c3c',
                                        'color': 'white',
                                        'border': 'none',
                                        'borderRadius': '5px',
                                        'cursor': 'pointer',
                                        'fontSize': '14px',
                                        'fontWeight': 'bold'
                                    }
                                )
                            ], style={
                                'padding': '20px',
                                'backgroundColor': '#fff3cd',
                                'border': '2px solid #e74c3c',
                                'borderRadius': '8px'
                            })
                        ], style={'marginTop': '30px'})
                        
                    ], style={
                        'padding': '25px',
                        'backgroundColor': '#ffffff',
                        'borderRadius': '8px',
                        'marginTop': '10px',
                        'boxShadow': 'inset 0 2px 8px rgba(0,0,0,0.05)'
                    })
                
                logger.info(f"  ↳ Creare row_container pentru {token[:8]}...")
                
                # Combinăm rândul compact + detaliile expandate (ÎN AFARA blocului if is_expanded)
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
                
                logger.info(f"  ↳ APPEND row_container pentru token {token[:8]}... în group_rows")
                group_rows.append(row_container)
            
            # Wrappăm toate înregistrările din grup într-un container
            # DACĂ grupul NU este collapsed, adăugăm container-ul
            logger.info(f"🔍 Înainte de verificare: len(group_rows)={len(group_rows)}, is_group_collapsed={is_group_collapsed}")
            if group_rows and not is_group_collapsed:
                group_container = html.Div(
                    group_rows,
                    style={
                        'paddingLeft': '10px',
                        'paddingRight': '10px',
                        'marginBottom': '10px'
                    }
                )
                rows.append(group_container)
                logger.info(f"✅ Adăugat container pentru grup '{group_name}' cu {len(group_rows)} înregistrări")
            elif is_group_collapsed:
                logger.info(f"⬇️ Grup '{group_name}' este COLLAPSED - {len(group_rows)} înregistrări ASCUNSE")
        
        logger.info(f"📊 RETURNARE: Total {len(rows)} elemente în rows (grupuri + headere)")
        logger.info(f"📋 Grupuri collapsed finale: {collapsed_groups}")
        return html.Div(rows), current_expanded, collapsed_groups
        
    except Exception as e:
        logger.error(f"Eroare la încărcarea data-view: {e}", exc_info=True)
        return html.Div(
            f"❌ EROARE la încărcarea datelor: {str(e)}",
            style={'padding': '20px', 'backgroundColor': '#ffdddd', 'border': '1px solid red', 'borderRadius': '5px', 'color': 'red'}
        ), current_expanded, []




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
        
        # Obținem APP_URL din environment
        app_url = os.getenv('APP_URL', 'http://127.0.0.1:8050')
        
        # Construim carduri pentru fiecare link
        link_cards = []
        for link_data in all_links:
            token = link_data['token']
            link_url = f"{app_url}/?token={token}"
            
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
                    
                    # Link-ul (copiabil) + Butoane
                    html.Div([
                        html.Label("🔗 Link Pacient:", style={'fontWeight': 'bold', 'display': 'block', 'marginBottom': '5px', 'fontSize': '14px'}),
                        dcc.Input(
                            id={'type': 'link-input-dashboard', 'index': token},
                            value=link_url,
                            readOnly=True,
                            style={'width': '100%', 'padding': '8px', 'backgroundColor': '#ecf0f1', 'border': '1px solid #bdc3c7', 'borderRadius': '5px', 'fontSize': '12px', 'fontFamily': 'monospace', 'marginBottom': '8px'}
                        ),
                        html.Div([
                            html.Button(
                                '📋 Copy',
                                id={'type': 'copy-link-dashboard', 'index': token},
                                n_clicks=0,
                                style={
                                    'padding': '6px 15px',
                                    'marginRight': '8px',
                                    'backgroundColor': '#3498db',
                                    'color': 'white',
                                    'border': 'none',
                                    'borderRadius': '4px',
                                    'cursor': 'pointer',
                                    'fontSize': '12px',
                                    'fontWeight': 'bold'
                                }
                            ),
                            html.A(
                                '🌐 Testează',
                                href=link_url,
                                target='_blank',
                                style={
                                    'padding': '6px 15px',
                                    'backgroundColor': '#27ae60',
                                    'color': 'white',
                                    'textDecoration': 'none',
                                    'borderRadius': '4px',
                                    'fontSize': '12px',
                                    'fontWeight': 'bold',
                                    'display': 'inline-block'
                                }
                            )
                        ], style={'display': 'flex', 'gap': '8px'})
                    ], style={'marginBottom': '15px'}),
                    
                    # Notițe (editabile)
                    html.Div([
                        html.Label("📝 Notițe:", style={'fontWeight': 'bold', 'display': 'block', 'marginBottom': '5px', 'fontSize': '14px'}),
                        dcc.Textarea(
                            id={'type': 'medical-notes-textarea', 'index': token},
                            value=link_data.get('medical_notes', ''),
                            placeholder='Scrieți notițe aici (ex: Apnee severă, follow-up în 2 săptămâni)...',
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


# CALLBACK DEZACTIVAT TEMPORAR - cauza console error "A callback is missing Inputs"
# Pattern-matching cu ALL necesita componente dummy in layout initial
# TODO: Re-implementare cu MATCH sau adaugare componente dummy CORECTE
# @app.callback(
#     [Output({'type': 'images-display-container', 'index': ALL}, 'children'),
#      Output({'type': 'view-grid-btn', 'index': ALL}, 'style'),
#      Output({'type': 'view-list-btn', 'index': ALL}, 'style')],
#     [Input({'type': 'view-grid-btn', 'index': ALL}, 'n_clicks'),
#      Input({'type': 'view-list-btn', 'index': ALL}, 'n_clicks')],
#     [State({'type': 'view-grid-btn', 'index': ALL}, 'id')],
#     prevent_initial_call=True
# )
def toggle_images_view_DISABLED(grid_clicks, list_clicks, btn_ids):
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
            
            logger.info(f"Salvare interpretare pentru {token[:8]}...: {len(interpretation)} caractere")
            
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

# --- Callback modules (split for maintainability) ---
import callbacks.patient_view_callbacks  # noqa: F401, E402
import callbacks.medical_branding_callbacks  # noqa: F401, E402

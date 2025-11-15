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
from typing import List, Dict

from app_instance import app
from logger_setup import logger
import patient_links
from data_parser import parse_csv_data
from plot_generator import create_plot
from batch_processor import run_batch_job
import batch_session_manager
import config
from auth_ui_components import create_auth_header
import os


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def create_login_prompt():
    """
    Creează o pagină de login prompt frumoasă pentru utilizatori neautentificați.
    
    Returns:
        html.Div: Component Dash cu prompt de autentificare
    """
    return html.Div([
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

@app.callback(
    [Output('dynamic-layout-container', 'children'),
     Output('url-token-detected', 'data')],
    [Input('url', 'pathname'),
     Input('url', 'search')],
    prevent_initial_call=False  # EXPLICIT: callback trebuie să se execute la prima încărcare!
)
def route_layout_based_on_url(pathname, search):
    """
    [DIAGNOSTIC v5 - 40 LOG-URI]
    Detectează dacă URL conține token și afișează layout-ul corespunzător.
    """
    # === LOG 1-5: ENTRY POINT ===
    logger.warning(f"[LOG 1/40] 🔵🔵🔵 CALLBACK START - pathname={pathname}")
    logger.warning(f"[LOG 2/40] 🔵 Search param: {search}")
    logger.warning(f"[LOG 3/40] 🔵 Callback trigger source: URL change detected")
    logger.warning(f"[LOG 4/40] 🔵 Python version check: {import sys; sys.version}")
    logger.warning(f"[LOG 5/40] 🔵 Callback function ID: route_layout_based_on_url")
    
    # === LOG 6-10: IMPORT PHASE ===
    logger.warning(f"[LOG 6/40] 📦 Starting imports...")
    
    try:
        logger.warning(f"[LOG 7/40] 📦 Attempting to import app_layout_new...")
        from app_layout_new import medical_layout, patient_layout
        logger.warning(f"[LOG 8/40] ✅ app_layout_new imported successfully")
        
        logger.warning(f"[LOG 9/40] 📦 Attempting to import flask_login...")
        from flask_login import current_user
        logger.warning(f"[LOG 10/40] ✅ flask_login imported successfully")
        
        # Verificare tipuri importate
        logger.warning(f"[LOG 11/40] 🔍 medical_layout type: {type(medical_layout)}")
        logger.warning(f"[LOG 12/40] 🔍 patient_layout type: {type(patient_layout)}")
        logger.warning(f"[LOG 13/40] 🔍 current_user type: {type(current_user)}")
        
    except ImportError as import_err:
        logger.critical(f"[LOG 14/40] ❌ ImportError: {import_err}")
        logger.critical(f"[LOG 15/40] ❌ Import traceback: {import traceback; traceback.format_exc()}")
        return html.Div([
            html.H1("⚠️ Import Error", style={'color': 'red', 'textAlign': 'center', 'marginTop': '100px'}),
            html.P(f"Cannot import: {str(import_err)}", style={'textAlign': 'center'})
        ]), None
    except Exception as import_err:
        logger.critical(f"[LOG 16/40] ❌ Unexpected import error: {import_err}")
        logger.critical(f"[LOG 17/40] ❌ Error type: {type(import_err).__name__}")
        return html.Div([
            html.H1("⚠️ Eroare Import", style={'color': 'red', 'textAlign': 'center', 'marginTop': '100px'}),
            html.P(f"Nu pot încărca interfața: {str(import_err)}", style={'textAlign': 'center'})
        ]), None
    
    # === LOG 18-25: AUTHENTICATION CHECK ===
    logger.warning(f"[LOG 18/40] 🔐 Checking authentication status...")
    
    try:
        logger.warning(f"[LOG 19/40] 🔐 Accessing current_user.is_authenticated...")
        is_auth = current_user.is_authenticated
        logger.warning(f"[LOG 20/40] ✅ Authentication status retrieved: {is_auth}")
        
        # Log extra info despre current_user
        try:
            logger.warning(f"[LOG 21/40] 🔍 current_user.is_anonymous: {current_user.is_anonymous}")
            logger.warning(f"[LOG 22/40] 🔍 current_user.is_active: {current_user.is_active if hasattr(current_user, 'is_active') else 'N/A'}")
            logger.warning(f"[LOG 23/40] 🔍 current_user has email: {hasattr(current_user, 'email')}")
        except Exception as detail_err:
            logger.warning(f"[LOG 24/40] ⚠️ Cannot get current_user details: {detail_err}")
            
    except AttributeError as attr_err:
        logger.warning(f"[LOG 25/40] ⚠️ AttributeError accessing current_user: {attr_err}")
        is_auth = False
    except Exception as user_err:
        logger.warning(f"[LOG 26/40] ⚠️ Exception accessing current_user: {user_err}")
        logger.warning(f"[LOG 27/40] ⚠️ Error type: {type(user_err).__name__}")
        is_auth = False
    
    logger.warning(f"[LOG 28/40] 🔐 Final is_auth value: {is_auth}")
        
        # === LOG 29-35: TOKEN DETECTION ===
        logger.warning(f"[LOG 29/40] 🎫 Checking for token in URL...")
        logger.warning(f"[LOG 30/40] 🎫 Search is None: {search is None}")
        logger.warning(f"[LOG 31/40] 🎫 Search contains 'token=': {'token=' in search if search else False}")
        
        # Verificăm dacă există token în URL (query string search)
        if search and 'token=' in search:
            logger.warning(f"[LOG 32/40] 🎫 TOKEN DETECTED in URL!")
            # Extragem token-ul din URL
            try:
                token = search.split('token=')[1].split('&')[0]
                logger.warning(f"[LOG 33/40] 🎫 Token extracted: {token[:8]}...")
                logger.warning(f"[LOG 34/40] 🎫 Token length: {len(token)}")
                logger.warning(f"[LOG 35/40] 🎫 Validating token...")
                
                # Validăm token-ul
                if patient_links.validate_token(token):
                    logger.warning(f"[LOG 36/40] ✅ Token VALID → returning patient_layout")
                    logger.warning(f"[LOG 37/40] 📊 patient_layout type before return: {type(patient_layout)}")
                    logger.warning(f"[LOG 38/40] 🔚 CALLBACK END (patient path) - SUCCESS")
                    return patient_layout, token
                else:
                    logger.warning(f"[LOG 39/40] ❌ Token INVALID → returning error page")
                    logger.warning(f"[LOG 40/40] 🔚 CALLBACK END (invalid token)")
                    return html.Div([
                        html.H2("❌ Acces Interzis", style={'color': 'red', 'textAlign': 'center', 'marginTop': '50px'}),
                        html.P("Token-ul este invalid sau a expirat. Contactați medicul dumneavoastră.", 
                               style={'textAlign': 'center', 'color': '#666'})
                    ], style={'padding': '50px'}), None
                    
            except Exception as e:
                logger.critical(f"[LOG 35A/40] ❌ Exception extracting token: {e}", exc_info=True)
                # Eroare la parsare token → verificăm autentificare pentru acces medic
                if not is_auth:
                    logger.warning("[LOG 36A/40] ⚠️ Token error + not authenticated → login prompt")
                    return create_login_prompt(), None
                logger.warning("[LOG 37A/40] ⚠️ Token error but authenticated → medical_layout")
                return medical_layout, None
        
        # === LOG 38-40: NO TOKEN PATH (MEDICAL) ===
        logger.warning(f"[LOG 38/40] 🏥 NO TOKEN in URL → Medical path")
        logger.warning(f"[LOG 39/40] 🏥 is_auth = {is_auth}")
        
        # Fără token → Layout pentru medici (NECESITĂ AUTENTIFICARE!)
        if not is_auth:
            logger.warning("[LOG 40/40] 🔐 NOT AUTHENTICATED → Creating login prompt")
            logger.warning("[LOG 41/40] 🔐 Calling create_login_prompt()...")
            
            try:
                login_prompt_layout = create_login_prompt()
                logger.warning("[LOG 42/40] ✅ Login prompt created successfully")
                logger.warning(f"[LOG 43/40] 📊 login_prompt type: {type(login_prompt_layout)}")
                logger.warning(f"[LOG 44/40] 🔚 CALLBACK END (login prompt path) - RETURNING NOW")
                return login_prompt_layout, None
            except Exception as login_err:
                logger.critical(f"[LOG 45/40] ❌ ERROR creating login prompt: {login_err}", exc_info=True)
                return html.Div([
                    html.H1("Error", style={'textAlign': 'center', 'color': 'red'}),
                    html.P(f"Cannot create login: {str(login_err)}", style={'textAlign': 'center'})
                ]), None
        
        # Utilizator autentificat → afișăm layout medical
        logger.warning("[LOG 46/40] 🏥 AUTHENTICATED → returning medical_layout")
        try:
            user_email = current_user.email if hasattr(current_user, 'email') else "unknown"
            logger.warning(f"[LOG 47/40] 🏥 User email: {user_email}")
        except Exception as email_err:
            logger.warning(f"[LOG 48/40] ⚠️ Cannot get email: {email_err}")
        
        logger.warning(f"[LOG 49/40] 📊 medical_layout type before return: {type(medical_layout)}")
        logger.warning(f"[LOG 50/40] 🔚 CALLBACK END (medical path) - RETURNING NOW")
        return medical_layout, None
        
    except Exception as e:
        # === LOG 51-60: EXCEPTION HANDLER ===
        logger.critical(f"[LOG 51/60] ❌❌❌ EXCEPTION IN CALLBACK: {e}")
        logger.critical(f"[LOG 52/60] ❌ Exception type: {type(e).__name__}")
        logger.critical(f"[LOG 53/60] ❌ Exception args: {e.args}")
        logger.critical(f"[LOG 54/60] ❌ Pathname: {pathname}")
        logger.critical(f"[LOG 55/60] ❌ Search: {search}")
        
        # Full traceback
        import traceback
        tb = traceback.format_exc()
        logger.critical(f"[LOG 56/60] ❌ Full traceback:\n{tb}")
        
        # Context info
        logger.critical(f"[LOG 57/60] ❌ is_auth defined: {'is_auth' in locals()}")
        logger.critical(f"[LOG 58/60] ❌ medical_layout defined: {'medical_layout' in locals()}")
        logger.critical(f"[LOG 59/60] ❌ patient_layout defined: {'patient_layout' in locals()}")
        
        error_layout = html.Div([
            html.H1("⚠️ Eroare Callback", style={'color': 'red', 'textAlign': 'center', 'marginTop': '100px'}),
            html.P(f"Aplicația nu s-a putut inițializa.", 
                   style={'textAlign': 'center', 'fontSize': '18px', 'color': '#666'}),
            html.P(f"Eroare: {str(e)}", 
                   style={'textAlign': 'center', 'fontSize': '14px', 'color': '#999', 'fontFamily': 'monospace'}),
            html.P(f"Tip: {type(e).__name__}", 
                   style={'textAlign': 'center', 'fontSize': '12px', 'color': '#ccc', 'fontFamily': 'monospace'})
        ], style={'padding': '50px'})
        
        logger.critical(f"[LOG 60/60] 🔚 CALLBACK END (exception path) - Returning error layout")
        return error_layout, None


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
    """
    from datetime import datetime
    
    # Zile săptămână în română
    days_ro = {
        0: 'Luni', 1: 'Marți', 2: 'Miercuri', 3: 'Joi',
        4: 'Vineri', 5: 'Sâmbătă', 6: 'Duminică'
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
        
        # === ÎNCĂRCĂM CSV-UL ȘI DATELE COMPLETE ===
        csv_content = None
        csv_filename = "Date Pulsoximetrie"
        df = None
        
        # ÎNCERCĂM SĂ ÎNCĂRCĂM CSV DIN RECORDINGS METADATA (R2 SAU LOCAL)
        recordings = patient_links.get_patient_recordings(token)
        
        if recordings and len(recordings) > 0:
            # Folosim prima înregistrare (cea mai recentă)
            recording = recordings[-1]  # Ultima adăugată
            csv_filename = recording.get('original_filename', 'Date Pulsoximetrie')
            storage_type = recording.get('storage_type', 'unknown')
            
            logger.info(f"📊 Încărcare CSV din recording (storage: {storage_type})")
            
            # PRIORITATE 1: Încărcăm din R2 (dacă e disponibil)
            if storage_type == 'r2' and recording.get('r2_url'):
                logger.info(f"☁️ Încărcare CSV din Cloudflare R2...")
                try:
                    from storage_service import download_patient_file
                    
                    # Extragem filename din r2_url sau csv_path
                    csv_path_info = recording.get('csv_path', '')
                    if 'csvs/' in csv_path_info:
                        r2_filename = csv_path_info.split('csvs/')[-1]
                    else:
                        r2_filename = recording.get('original_filename', 'unknown.csv')
                    
                    logger.info(f"📥 Download R2: {token[:8]}... / csvs / {r2_filename}")
                    csv_content = download_patient_file(token, 'csvs', r2_filename)
                    
                    if csv_content:
                        logger.info(f"✅ CSV descărcat din R2: {len(csv_content)} bytes")
                    else:
                        logger.warning(f"⚠️ Download R2 eșuat, încercăm fallback LOCAL")
                        storage_type = 'local'  # Fallback
                except ImportError:
                    logger.warning("⚠️ storage_service nu e disponibil, încercăm LOCAL")
                    storage_type = 'local'
                except Exception as e:
                    logger.error(f"❌ Eroare download R2: {e}", exc_info=True)
                    storage_type = 'local'  # Fallback
            
            # FALLBACK: Încărcăm din LOCAL (dacă R2 a eșuat sau nu e configurat)
            if storage_type == 'local' and not csv_content:
                logger.info(f"💾 Încărcare CSV din stocare LOCALĂ...")
                csv_path = recording.get('csv_path')
                
                if csv_path and os.path.exists(csv_path):
                    try:
                        with open(csv_path, 'rb') as f:
                            csv_content = f.read()
                        logger.info(f"✅ CSV citit LOCAL: {len(csv_content)} bytes")
                    except Exception as e:
                        logger.error(f"❌ Eroare citire CSV local: {e}", exc_info=True)
                else:
                    logger.warning(f"⚠️ CSV LOCAL nu există: {csv_path}")
        
        # FALLBACK FINAL: Căutăm în old-style folder structure (compatibilitate backwards)
        if not csv_content:
            logger.info("🔄 Fallback: Căutare CSV în structura veche (patient_data/token/csvs/)")
            patient_folder = patient_links.get_patient_storage_path(token)
            csv_folder = os.path.join(patient_folder, "csvs")
            
            if os.path.exists(csv_folder):
                csv_files = [f for f in os.listdir(csv_folder) if f.endswith('.csv')]
                
                if csv_files:
                    csv_path = os.path.join(csv_folder, csv_files[0])
                    logger.info(f"✅ CSV găsit în structura veche: {csv_path}")
                    
                    try:
                        with open(csv_path, 'rb') as f:
                            csv_content = f.read()
                        csv_filename = csv_files[0]
                        logger.info(f"✅ CSV citit din fallback: {len(csv_content)} bytes")
                    except Exception as e:
                        logger.error(f"❌ Eroare citire fallback CSV: {e}", exc_info=True)
                else:
                    logger.warning(f"⚠️ Niciun CSV găsit în {csv_folder}")
            else:
                logger.warning(f"⚠️ Folder CSV nu există: {csv_folder}")
        
        # PARSĂM CSV-ul (dacă l-am încărcat)
        if csv_content:
            logger.info(f"📊 Parsare CSV: {len(csv_content)} bytes")
            df = parse_csv_data(csv_content, csv_filename)
            
            if df is not None:
                logger.info(f"✅ DataFrame creat: {len(df)} rânduri")
            else:
                logger.error("❌ Parsare CSV eșuată - DataFrame None")
        else:
            logger.error(f"❌ NU S-A PUTUT ÎNCĂRCA CSV pentru token {token[:8]}... din NICIO SURSĂ!")
            logger.error(f"   - R2: {'Configurat' if os.getenv('R2_ENABLED') == 'True' else 'NU configurat'}")
            logger.error(f"   - Recordings metadata: {len(recordings) if recordings else 0} înregistrări")
        
        # Generăm figura
        if df is not None and not df.empty:
            fig = create_plot(df, file_name=csv_filename)
            
            # Aplicăm logo-ul pe figura interactivă (dacă este configurat)
            try:
                from plot_generator import apply_logo_to_figure
                fig = apply_logo_to_figure(fig)
            except Exception as logo_error:
                logger.warning(f"Nu s-a putut aplica logo pe figura interactivă: {logo_error}")
        else:
            fig = go.Figure()
            fig.update_layout(
                title="⚠️ Graficul nu este disponibil încă",
                xaxis_title="Timp",
                yaxis_title="SpO2 (%)",
                height=500
            )
            
            # Mesaj detaliat pentru debugging
            if not recordings or len(recordings) == 0:
                logger.warning(f"❌ Nicio înregistrare găsită pentru token {token[:8]}...")
            else:
                logger.warning(f"❌ CSV lipsă pentru token {token[:8]}... (recordings: {len(recordings)})")
        
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
            pdfs_section = html.Div([
                html.H3("📄 Rapoarte PDF", style={'color': '#2980b9', 'marginBottom': '15px'}),
                render_pdfs_display(token, all_pdfs)
            ], style={
                'padding': '25px',
                'backgroundColor': '#fff',
                'borderRadius': '10px',
                'boxShadow': '0 2px 8px rgba(0,0,0,0.1)',
                'marginBottom': '20px'
            })
            content_sections.append(pdfs_section)
        
        # Combinăm toate secțiunile
        full_content = html.Div(content_sections)
        
        logger.info(f"✅ Date complete încărcate pentru pacient {token[:8]}...")
        return full_content, fig
        
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
    [Output('admin-batch-local-mode', 'style'),
     Output('admin-batch-upload-mode', 'style')],
    [Input('admin-batch-mode-selector', 'value')]
)
def toggle_batch_mode_display(selected_mode):
    """
    Comută între modul local (folder) și modul upload (fișiere).
    """
    if selected_mode == 'local':
        # Afișează mod local, ascunde upload
        return {'display': 'block', 'marginBottom': '20px'}, {'display': 'none'}
    else:  # 'upload'
        # Afișează upload, ascunde mod local
        return {'display': 'none'}, {'display': 'block', 'marginBottom': '20px'}


@app.callback(
    [Output('admin-batch-uploaded-files-list', 'children'),
     Output('admin-batch-uploaded-files-store', 'data')],
    [Input('admin-batch-file-upload', 'contents')],
    [State('admin-batch-file-upload', 'filename'),
     State('admin-batch-uploaded-files-store', 'data')]
)
def handle_file_upload(list_of_contents, list_of_names, session_id):
    """
    [WORKAROUND v3.0] Salvează fișierele pe disk în loc de dcc.Store.
    PROBLEMA: dcc.Store nu propagă datele corect în Railway production.
    SOLUȚIE: Salvăm pe disk și returnăm doar session_id.
    """
    # Import TempFileManager
    from temp_file_manager import get_manager
    
    logger.warning("=" * 100)
    logger.warning("🔍 [UPLOAD v3] HANDLE_FILE_UPLOAD - WORKAROUND cu disk storage")
    logger.warning("=" * 100)
    
    logger.warning(f"🔍 [UPLOAD v3.1] INPUT list_of_contents: {list_of_contents is not None} (length: {len(list_of_contents) if list_of_contents else 0})")
    logger.warning(f"🔍 [UPLOAD v3.2] STATE list_of_names: {list_of_names}")
    logger.warning(f"🔍 [UPLOAD v3.3] STATE session_id (IN): {session_id}")
    logger.warning("=" * 100)
    
    # LOG 13: Validare DEFENSIVĂ pentru contents
    logger.warning("🔍 [LOG 13/20] START VALIDARE - Verificare list_of_contents")
    
    if not list_of_contents:
        logger.error("❌ [LOG 14/20] VALIDATION FAILED: list_of_contents este None/False - RETURN no_update")
        logger.error(f"❌ [LOG 14.1/20] Detalii: list_of_contents = {list_of_contents}")
        return no_update, no_update
    
    logger.warning("✅ [LOG 14/20] VALIDATION PASSED: list_of_contents există")
    
    # LOG 15: Verificare suplimentară dacă lista este goală
    if isinstance(list_of_contents, list) and len(list_of_contents) == 0:
        logger.error("❌ [LOG 15/20] VALIDATION FAILED: list_of_contents este listă GOALĂ - RETURN no_update")
        return no_update, no_update
    
    logger.warning("✅ [LOG 15/20] VALIDATION PASSED: list_of_contents are elemente")
    
    # LOG 16: Verificare că list_of_names există și are aceeași lungime
    if not list_of_names or len(list_of_names) != len(list_of_contents):
        logger.error(f"❌ [LOG 16/20] VALIDATION FAILED: list_of_names mismatch! contents={len(list_of_contents) if list_of_contents else 0}, names={len(list_of_names) if list_of_names else 0}")
        return no_update, no_update
    
    logger.warning("✅ [UPLOAD v3.4] VALIDATION PASSED - Toate verificările OK")
    
    # [WORKAROUND v3.0] Creează/reutilizează session_id
    import uuid
    if not session_id or not isinstance(session_id, str):
        session_id = str(uuid.uuid4())
        logger.warning(f"🆕 [UPLOAD v3.5] Generat session_id NOU: {session_id}")
    else:
        logger.warning(f"♻️ [UPLOAD v3.5] Reutilizat session_id EXISTENT: {session_id}")
    
    # Inițializează TempFileManager
    manager = get_manager(session_id)
    logger.warning(f"📁 [UPLOAD v3.6] TempFileManager inițializat: {manager.session_folder}")
    
    # Salvează fișierele pe disk
    saved_count = manager.save_uploaded_files(list_of_contents, list_of_names)
    logger.warning(f"💾 [UPLOAD v3.7] Fișiere salvate pe disk: {saved_count}")
    
    # Citește metadata pentru UI (nu returnăm content, doar info)
    all_files = manager.get_uploaded_files()
    logger.warning(f"📊 [UPLOAD v3.8] Metadata citită: {len(all_files)} fișiere")
    logger.warning(f"📋 [UPLOAD v3.9] Filenames: {[f['filename'] for f in all_files]}")
    
    # Generăm UI pentru listă fișiere
    if not all_files:
        return html.P("📭 Nu există fișiere încărcate încă.", style={
            'textAlign': 'center',
            'color': '#95a5a6',
            'padding': '20px',
            'backgroundColor': '#f8f9fa',
            'borderRadius': '5px',
            'border': '1px dashed #bdc3c7'
        }), all_files
    
    # Generăm lista de fișiere cu statistici
    csv_count = sum(1 for f in all_files if f['type'] == 'CSV')
    pdf_count = sum(1 for f in all_files if f['type'] == 'PDF')
    
    files_display = html.Div([
        # Header cu statistici
        html.Div([
            html.Strong(f"📊 Total: {len(all_files)} fișiere", style={'marginRight': '20px'}),
            html.Span(f"📄 CSV: {csv_count}", style={'marginRight': '15px', 'color': '#27ae60'}),
            html.Span(f"📕 PDF: {pdf_count}", style={'color': '#e74c3c'}),
            html.Button(
                '🗑️ Șterge toate',
                id='admin-batch-clear-files-btn',
                n_clicks=0,
                style={
                    'padding': '5px 15px',
                    'fontSize': '12px',
                    'backgroundColor': '#e74c3c',
                    'color': 'white',
                    'border': 'none',
                    'borderRadius': '3px',
                    'cursor': 'pointer',
                    'float': 'right'
                }
            )
        ], style={
            'padding': '12px',
            'backgroundColor': '#ecf0f1',
            'borderRadius': '5px 5px 0 0',
            'borderBottom': '2px solid #bdc3c7',
            'marginBottom': '10px'
        }),
        
        # Lista de fișiere
        html.Div([
            html.Div([
                html.Div([
                    html.Span('📄' if f['type'] == 'CSV' else '📕', style={'fontSize': '20px', 'marginRight': '10px'}),
                    html.Strong(f['filename'], style={'fontSize': '13px'}),
                    html.Small(f" ({_format_file_size(f['size'])})", style={'color': '#7f8c8d', 'marginLeft': '8px'}),
                ], style={'display': 'flex', 'alignItems': 'center'}),
                html.Button(
                    '❌',
                    id={'type': 'delete-uploaded-file', 'index': i},
                    n_clicks=0,
                    style={
                        'padding': '4px 10px',
                        'fontSize': '14px',
                        'backgroundColor': '#e74c3c',
                        'color': 'white',
                        'border': 'none',
                        'borderRadius': '3px',
                        'cursor': 'pointer'
                    }
                )
            ], style={
                'display': 'flex',
                'justifyContent': 'space-between',
                'alignItems': 'center',
                'padding': '10px',
                'marginBottom': '8px',
                'backgroundColor': '#e8f5e9' if f['type'] == 'CSV' else '#ffebee',
                'borderRadius': '4px',
                'border': f"1px solid {'#27ae60' if f['type'] == 'CSV' else '#e74c3c'}"
            })
            for i, f in enumerate(all_files)
        ])
    ], style={
        'padding': '15px',
        'backgroundColor': '#fff',
        'borderRadius': '0 0 5px 5px',
        'border': '1px solid #bdc3c7',
        'maxHeight': '300px',
        'overflowY': 'auto'
    })
    
    # [WORKAROUND v3.0] RETURN: UI + session_id (NU lista de fișiere!)
    logger.warning("=" * 100)
    logger.warning("🔍 [UPLOAD v3.10] PREGĂTIRE RETURN")
    logger.warning(f"🎯 [UPLOAD v3.11] RETURN OUTPUT 1 (UI): files_display TYPE = {type(files_display)}")
    logger.warning(f"🎯 [UPLOAD v3.12] RETURN OUTPUT 2 (STORE): session_id = '{session_id}' (STRING, nu listă!)")
    logger.warning("=" * 100)
    logger.warning("🚀 [UPLOAD v3.13] CALLBACK EXIT - Returnez (files_display, session_id)")
    logger.warning("=" * 100)
    
    # CRITICAL: Returnăm session_id în store, NU lista de fișiere!
    return files_display, session_id


def _format_file_size(size_bytes):
    """Helper pentru formatare dimensiune fișier."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


# ==============================================================================
# [DIAGNOSTIC v2.0] CALLBACK MONITORING STORE - DISABLED (cauza eroare Dash)
# ==============================================================================
# PROBLEMA: dummy-output-for-debug nu există în layout-ul inițial
# Callback-ul referențiază un Output inexistent → Dash ERROR → blochează toate callback-urile
# SOLUȚIE: Dezactivat temporar pentru debugging
# 
# @app.callback(
#     Output('dummy-output-for-debug', 'children'),
#     [Input('admin-batch-uploaded-files-store', 'data')]
# )
# def monitor_store_changes(store_data):
#     """
#     [DIAGNOSTIC] Callback care monitorizează ORICE schimbare în store.
#     Acest callback se va declanșa DE FIECARE DATĂ când store-ul primește date noi.
#     """
#     logger.warning("=" * 100)
#     logger.warning("🔍 [MONITOR LOG 1/5] STORE MONITORING - CALLBACK TRIGGERED!")
#     logger.warning("=" * 100)
#     
#     logger.warning(f"🔍 [MONITOR LOG 2/5] Store data IS_NONE: {store_data is None}")
#     logger.warning(f"🔍 [MONITOR LOG 3/5] Store data TYPE: {type(store_data)}")
#     
#     if store_data:
#         logger.warning(f"✅ [MONITOR LOG 4/5] Store data LENGTH: {len(store_data)}")
#         logger.warning(f"✅ [MONITOR LOG 5/5] Store data FILENAMES: {[f.get('filename', 'N/A') for f in store_data]}")
#     else:
#         logger.error(f"❌ [MONITOR LOG 4/5] Store data este GOLI/NONE!")
#         logger.error(f"❌ [MONITOR LOG 5/5] Store data VALUE: {store_data}")
#     
#     logger.warning("=" * 100)
#     
#     # Return dummy value (nu afectează UI-ul)
#     return ""


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
     Output('admin-batch-session-id', 'data'),
     Output('admin-batch-progress-container', 'style'),
     Output('admin-batch-progress-interval', 'disabled'),
     Output('admin-batch-uploaded-files-store', 'data', allow_duplicate=True)],
    [Input('admin-start-batch-button', 'n_clicks')],
    [State('admin-batch-mode-selector', 'value'),
     State('admin-batch-input-folder', 'value'),
     State('admin-batch-uploaded-files-store', 'data'),
     State('admin-batch-output-folder', 'value'),
     State('admin-batch-window-minutes', 'value')],
    prevent_initial_call=True
)
def admin_run_batch_processing(n_clicks, batch_mode, input_folder, session_id, output_folder, window_minutes):
    """
    Callback pentru procesare batch + generare automată link-uri + tracking progres.
    Suportă AMBELE moduri: local (folder) și upload (fișiere).
    """
    if n_clicks == 0:
        return no_update, no_update, no_update, no_update, no_update, no_update
    
    # [WORKAROUND v3.0] Citim fișierele de pe disk folosind session_id
    logger.warning("=" * 100)
    logger.warning("🔍 [BATCH v3.1] ADMIN_RUN_BATCH_PROCESSING - WORKAROUND cu disk storage")
    logger.warning("=" * 100)
    
    logger.warning(f"🔍 [BATCH v3.2] STATE session_id (IN): {session_id}")
    logger.warning(f"🔍 [BATCH v3.3] STATE batch_mode: {batch_mode}")
    logger.warning(f"🔍 [BATCH v3.4] STATE input_folder: {input_folder}")
    logger.warning("=" * 100)
    
    # === VALIDARE ÎN FUNCȚIE DE MOD ===
    if batch_mode == 'local':
        # Mod local: verificăm folder
        if not input_folder or input_folder.strip() == '':
            return html.Div(
                "⚠️ Specificați folderul de intrare!",
                style={'padding': '15px', 'backgroundColor': '#fff3cd', 'border': '1px solid #ffc107', 'borderRadius': '5px'}
            ), no_update, no_update, no_update, no_update, no_update
        
        processing_folder = input_folder
        logger.warning(f"✅ Procesare LOCALĂ din folder: {input_folder}")
        
    else:  # batch_mode == 'upload'
        # [WORKAROUND v3.0] Citim fișierele de pe disk
        logger.warning(f"🔍 [BATCH v3.5] MOD UPLOAD - Citire fișiere de pe disk...")
        
        # Verificăm session_id
        if not session_id or not isinstance(session_id, str):
            logger.error("=" * 100)
            logger.error("❌ [BATCH v3.6] CRITICAL: session_id este None/invalid!")
            logger.error(f"   Type: {type(session_id)}")
            logger.error(f"   Value: {session_id}")
            logger.error("=" * 100)
            return html.Div([
                html.H4("⚠️ Niciun session_id detectat!", style={'color': '#e67e22', 'marginBottom': '10px'}),
                html.P("Încărcați fișiere CSV + PDF folosind butonul de upload de mai sus.", style={'marginBottom': '10px'}),
                html.Div([
                    html.P("DEBUG INFO [WORKAROUND v3.0]:", style={'fontWeight': 'bold', 'marginBottom': '5px'}),
                    html.P(f"• session_id = {session_id}", style={'fontSize': '11px', 'fontFamily': 'monospace', 'marginBottom': '3px'}),
                    html.P(f"• type = {type(session_id)}", style={'fontSize': '11px', 'fontFamily': 'monospace', 'marginBottom': '3px'}),
                    html.P("• Possible cause: Upload callback nu s-a executat sau session_id nu a fost salvat", style={'fontSize': '11px', 'fontFamily': 'monospace', 'color': '#e74c3c'})
                ], style={'backgroundColor': '#ecf0f1', 'padding': '10px', 'borderRadius': '5px', 'marginTop': '10px'})
            ], style={'padding': '15px', 'backgroundColor': '#fff3cd', 'border': '1px solid #ffc107', 'borderRadius': '5px'}), \
            no_update, no_update, no_update, no_update, no_update
        
        # [WORKAROUND v3.0] Citim fișierele de pe disk folosind TempFileManager
        from temp_file_manager import get_manager
        
        manager = get_manager(session_id)
        logger.warning(f"📁 [BATCH v3.7] TempFileManager inițializat: {manager.session_folder}")
        
        # Verificăm dacă există fișiere
        files_metadata = manager.get_uploaded_files()
        if not files_metadata:
            logger.error("❌ [BATCH v3.8] Nu există fișiere în sesiune!")
            return html.Div([
                html.H4("⚠️ Nu există fișiere în sesiune!", style={'color': '#e67e22', 'marginBottom': '10px'}),
                html.P(f"Session ID: {session_id}", style={'marginBottom': '10px', 'fontSize': '11px', 'fontFamily': 'monospace'}),
                html.P("Fișierele au fost șterse sau sesiunea a expirat.", style={'marginBottom': '10px'}),
                html.P("Încărcați din nou fișiere CSV + PDF.", style={'marginBottom': '10px'})
            ], style={'padding': '15px', 'backgroundColor': '#fff3cd', 'border': '1px solid #ffc107', 'borderRadius': '5px'}), \
            no_update, no_update, no_update, no_update, no_update
        
        # [SUCCESS] Fișiere detectate pe disk
        logger.warning(f"✅ [BATCH v3.9] Fișiere detectate pe disk: {len(files_metadata)}")
        for idx, file_meta in enumerate(files_metadata):
            logger.warning(f"   [{idx}] {file_meta.get('filename', 'N/A')} ({file_meta.get('type', 'N/A')}) - {file_meta.get('size', 0)} bytes")
        
        # Folosim folderul sesiunii ca processing_folder
        processing_folder = str(manager.session_folder)
        logger.warning(f"🚀 [BATCH v3.10] Procesare UPLOAD din folder sesiune: {processing_folder}")
    
    # Folosim folder default pentru output dacă nu e specificat
    if not output_folder or output_folder.strip() == '':
        output_folder = config.OUTPUT_DIR
    
    logger.info(f"📊 Admin pornește procesare batch: {processing_folder} → {output_folder}")
    
    try:
        # Validăm existența folderului de procesare
        if not os.path.exists(processing_folder):
            return html.Div(
                f"❌ Folderul de procesare nu există: {processing_folder}",
                style={'padding': '15px', 'backgroundColor': '#ffdddd', 'border': '1px solid red', 'borderRadius': '5px', 'color': 'red'}
            ), no_update, no_update, no_update, no_update, no_update
        
        # Găsim toate fișierele CSV din folder
        csv_files = [f for f in os.listdir(processing_folder) if f.endswith('.csv')]
        
        if not csv_files:
            return html.Div(
                "⚠️ Nu există fișiere CSV în folderul specificat/uploadat!",
                style={'padding': '15px', 'backgroundColor': '#fff3cd', 'border': '1px solid #ffc107', 'borderRadius': '5px'}
            ), no_update, no_update, no_update, no_update, no_update
        
        # Creăm sesiune batch cu tracking
        session_id = batch_session_manager.create_batch_session(
            total_files=len(csv_files),
            file_list=csv_files
        )
        
        logger.info(f"📊 Sesiune batch creată: {session_id} cu {len(csv_files)} fișiere")
        
        # ACTIVĂM bara de progres și interval-ul de refresh
        progress_style = {'display': 'block', 'marginBottom': '20px'}
        interval_disabled = False
        
        # IMPORTANT: Salvăm session_id pentru ca interval callback-ul să-l poată citi
        # și pornim procesarea într-un thread separat pentru a nu bloca UI-ul
        
        # Rulăm procesarea batch cu session_id pentru tracking
        generated_links = run_batch_job(
            processing_folder,  # Folosim folderul de procesare (local SAU temp upload)
            output_folder, 
            window_minutes,
            session_id=session_id  # Pasăm session_id pentru tracking
        )
        
        # Marcăm sesiunea ca finalizată
        batch_session_manager.mark_session_completed(session_id)
        
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
            ], style={'padding': '20px', 'backgroundColor': '#fff3cd', 'border': '1px solid #ffc107', 'borderRadius': '10px'}), n_clicks, None, {'display': 'none'}, True, files_to_clear
        
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
                                '📋 Copy',
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
                                    'fontSize': '12px',
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
            html.Hr(),
            html.Div(link_rows, style={'maxHeight': '400px', 'overflowY': 'auto'})
        ], style={'padding': '20px', 'backgroundColor': '#d4edda', 'border': '1px solid #28a745', 'borderRadius': '10px'}), n_clicks, session_id, progress_style, interval_disabled, files_to_clear
        
    except Exception as e:
        logger.error(f"Eroare la procesare batch: {e}", exc_info=True)
        return html.Div(
            f"❌ EROARE: {str(e)}",
            style={'padding': '15px', 'backgroundColor': '#ffdddd', 'border': '1px solid red', 'borderRadius': '5px', 'color': 'red'}
        ), no_update, None, {'display': 'none'}, True, no_update


@app.callback(
    [Output('data-view-container', 'children'),
     Output('expanded-row-id', 'data'),
     Output('collapsed-groups-store', 'data')],
    [Input('admin-refresh-data-view', 'n_clicks'),
     Input('admin-refresh-trigger', 'data'),
     Input({'type': 'expand-row-btn', 'index': ALL}, 'n_clicks'),
     Input({'type': 'toggle-group-btn', 'index': ALL}, 'n_clicks'),
     Input('active-date-filter', 'data'),
     Input('date-grouping', 'value')],
    [State('expanded-row-id', 'data'),
     State({'type': 'expand-row-btn', 'index': ALL}, 'id'),
     State({'type': 'toggle-group-btn', 'index': ALL}, 'id'),
     State('collapsed-groups-store', 'data')]
)
def load_data_view_with_accordion(n_clicks_refresh, trigger, expand_clicks, toggle_group_clicks, date_filter, grouping, expanded_id, expand_btn_ids, toggle_group_ids, collapsed_groups):
    """
    Încarcă vizualizarea datelor cu funcționalitate accordion (expandare/colapsare).
    """
    from dash import ctx
    import base64
    
    logger.debug("Callback data-view apelat.")
    
    # LOG: Afișăm ce a trigger-uit callback-ul
    logger.info(f"🔍 Callback trigger: {ctx.triggered_id}")
    logger.info(f"🔍 Trigger type: {type(ctx.triggered_id)}")
    if isinstance(ctx.triggered_id, dict):
        logger.info(f"🔍 Trigger dict keys: {ctx.triggered_id.keys()}")
        logger.info(f"🔍 Trigger 'type': {ctx.triggered_id.get('type')}")
        logger.info(f"🔍 Trigger 'index': {ctx.triggered_id.get('index')}")
    
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
        
        all_links = patient_links.get_all_links_for_admin()
        
        if not all_links:
            return html.Div(
                "📭 Nu există înregistrări încă. Procesați fișiere CSV din tab-ul 'Procesare Batch'.",
                style={'padding': '50px', 'textAlign': 'center', 'color': '#666', 'fontStyle': 'italic', 'backgroundColor': '#f8f9fa', 'borderRadius': '10px'}
            ), current_expanded, collapsed_groups
        
        # === FILTRARE TEMPORALĂ ===
        if date_filter and date_filter.get('start') and date_filter.get('end'):
            start_date = datetime.fromisoformat(date_filter['start']).date()
            end_date = datetime.fromisoformat(date_filter['end']).date()
            filter_label = date_filter.get('label', 'Interval Personalizat')
            
            logger.info(f"🔍 Aplicare filtru temporal: {filter_label} ({start_date} - {end_date})")
            
            # Filtrăm link-urile după dată
            filtered_links = []
            for link in all_links:
                if link.get('recording_date'):
                    try:
                        rec_date = datetime.strptime(link['recording_date'], '%Y-%m-%d').date()
                        if start_date <= rec_date <= end_date:
                            filtered_links.append(link)
                    except:
                        pass  # Ignorăm înregistrările cu dată invalidă
            
            all_links = filtered_links
            logger.info(f"✅ După filtrare: {len(all_links)} înregistrări")
        
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
        
        # Parcurgem fiecare grupă
        for group_name, group_links in sorted(grouped_links.items(), reverse=True):
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
                logger.info(f"  ↳ Creare compact_row pentru {token[:8]}...")
                
                # === RÂND COMPACT (întotdeauna vizibil) - CLICKABIL PE ÎNTREAGA LINIE ===
                compact_row = html.Button(
                    children=[
                        # Info condensată (FĂRĂ iconița play)
                        html.Div([
                            html.Strong(f"📅 {date_display}", style={'fontSize': '16px', 'color': '#2c3e50', 'display': 'block', 'marginBottom': '5px'}),
                            html.Small(f"🔧 {link_data['device_name']} | {view_display}", style={'color': '#7f8c8d', 'display': 'block', 'fontSize': '13px'})
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


# ===== CLIENTSIDE CALLBACK pentru DEBUG în CONSOLĂ BROWSER =====
app.clientside_callback(
    """
    function(toggle_clicks, collapsed_groups) {
        console.log("🔵 [BROWSER DEBUG] Toggle button clicked!");
        console.log("🔵 [BROWSER DEBUG] toggle_clicks:", toggle_clicks);
        console.log("🔵 [BROWSER DEBUG] collapsed_groups:", collapsed_groups);
        return window.dash_clientside.no_update;
    }
    """
)

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
                html.Div([
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
                            'cursor': 'pointer',
                            'marginRight': '10px'
                        }
                    ),
                    html.Button(
                        '🗑️ Șterge',
                        id={'type': 'delete-recording-btn', 'index': rec['id']},
                        style={
                            'padding': '10px 20px',
                            'backgroundColor': '#e74c3c',
                            'color': 'white',
                            'border': 'none',
                            'borderRadius': '5px',
                            'cursor': 'pointer'
                        }
                    )
                ], style={'marginTop': '15px'}),
                # Store pentru token-ul curent (pentru callback-ul de ștergere)
                dcc.Store(id={'type': 'recording-token-store', 'index': rec['id']}, data=token)
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
        
        # Aplicăm logo-ul pe figura interactivă (dacă este configurat)
        try:
            from plot_generator import apply_logo_to_figure
            fig = apply_logo_to_figure(fig)
        except Exception as logo_error:
            logger.warning(f"Nu s-a putut aplica logo pe figura temporară: {logo_error}")
        
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


# ==============================================================================
# CALLBACKS PDF - UPLOAD ȘI AFIȘARE RAPOARTE
# ==============================================================================

@app.callback(
    [Output({'type': 'pdf-upload-feedback', 'index': ALL}, 'children'),
     Output({'type': 'pdf-display-container', 'index': ALL}, 'children')],
    [Input({'type': 'pdf-upload', 'index': ALL}, 'contents')],
    [State({'type': 'pdf-upload', 'index': ALL}, 'filename'),
     State({'type': 'pdf-upload', 'index': ALL}, 'id')],
    prevent_initial_call=True
)
def handle_pdf_upload(contents_list, filenames_list, ids_list):
    """
    Callback pentru upload și procesare PDF-uri (rapoarte Checkme O2).
    Parsează automat PDF-ul și salvează datele extrase.
    """
    from pdf_parser import parse_checkme_o2_report, format_report_for_display, PDF_SUPPORT
    import tempfile
    
    if not any(contents_list):
        return [no_update] * len(contents_list), [no_update] * len(contents_list)
    
    # Verificăm dacă pdfplumber este disponibil
    if not PDF_SUPPORT:
        error_msg = html.Div([
            html.P("❌ Biblioteca pdfplumber nu este instalată!", style={'color': 'red', 'fontWeight': 'bold'}),
            html.P("Rulați în terminal:", style={'marginTop': '10px'}),
            html.Code("pip install pdfplumber", style={'display': 'block', 'padding': '10px', 'backgroundColor': '#f0f0f0', 'borderRadius': '5px'})
        ], style={'padding': '15px', 'backgroundColor': '#ffdddd', 'border': '1px solid red', 'borderRadius': '5px'})
        return [error_msg] * len(contents_list), [no_update] * len(contents_list)
    
    feedback_results = []
    display_results = []
    
    for i, (contents, filename, btn_id) in enumerate(zip(contents_list, filenames_list, ids_list)):
        token = btn_id['index']
        
        if contents is None:
            feedback_results.append(no_update)
            display_results.append(no_update)
            continue
        
        logger.info(f"📤 Upload PDF primit pentru {token[:8]}...: {filename}")
        
        try:
            # Decodăm conținutul PDF
            content_type, content_string = contents.split(',')
            pdf_bytes = base64.b64decode(content_string)
            
            # Salvăm PDF-ul local
            pdf_path = patient_links.save_pdf_for_link(token, pdf_bytes, filename)
            
            if not pdf_path:
                raise Exception("Eroare la salvarea PDF-ului")
            
            # Creăm fișier temporar pentru parsing
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
                tmp_file.write(pdf_bytes)
                tmp_pdf_path = tmp_file.name
            
            try:
                # Parsăm PDF-ul
                logger.info(f"🔍 Parsare PDF: {filename}")
                parsed_data = parse_checkme_o2_report(tmp_pdf_path)
                
                # Salvăm datele parsate
                if patient_links.save_pdf_parsed_data(token, pdf_path, parsed_data):
                    logger.info(f"✅ PDF procesat cu succes: {filename}")
                    
                    # Feedback pozitiv
                    feedback_results.append(
                        html.Div([
                            html.P(f"✅ PDF încărcat și procesat: {filename}", style={'color': 'green', 'fontWeight': 'bold'}),
                            html.Small(f"Salvat în: {pdf_path}", style={'color': '#666'})
                        ], style={'padding': '10px', 'backgroundColor': '#d4edda', 'border': '1px solid #28a745', 'borderRadius': '5px'})
                    )
                    
                    # Actualizăm afișarea PDF-urilor
                    all_pdfs = patient_links.get_all_pdfs_for_link(token)
                    display_results.append(render_pdfs_display(token, all_pdfs))
                else:
                    raise Exception("Eroare la salvarea datelor parsate")
                    
            finally:
                # Ștergem fișierul temporar
                import os
                if os.path.exists(tmp_pdf_path):
                    os.remove(tmp_pdf_path)
            
        except Exception as e:
            logger.error(f"Eroare la procesarea PDF pentru {token[:8]}...: {e}", exc_info=True)
            feedback_results.append(
                html.Div(
                    f"❌ Eroare la procesarea PDF: {str(e)}",
                    style={'padding': '10px', 'backgroundColor': '#ffdddd', 'border': '1px solid red', 'borderRadius': '5px', 'color': 'red'}
                )
            )
            display_results.append(no_update)
    
    return feedback_results, display_results


def render_pdfs_display(token: str, pdfs_list: List[Dict]) -> html.Div:
    """
    Helper pentru rendering lista de PDF-uri existente cu previzualizare vizuală (iframe).
    
    Args:
        token: UUID-ul pacientului
        pdfs_list: Listă cu PDF-uri și metadata
        
    Returns:
        html.Div: Componenta Dash pentru afișare
    """
    from pdf_parser import format_report_for_display, pdf_to_base64
    
    if not pdfs_list:
        return html.Div(
            "📭 Nu există rapoarte PDF încărcate încă.",
            style={'padding': '15px', 'color': '#666', 'fontStyle': 'italic', 'textAlign': 'center', 'backgroundColor': '#f8f9fa', 'borderRadius': '5px'}
        )
    
    pdf_cards = []
    for pdf_info in pdfs_list:
        pdf_path = pdf_info.get('pdf_path', '')
        parsed_data = pdf_info.get('data', {})
        parsed_at = pdf_info.get('parsed_at', '')
        
        # Formatăm datele pentru afișare
        formatted_text = format_report_for_display(parsed_data)
        
        # Statistici quick view
        stats = parsed_data.get('statistics', {})
        quick_stats = []
        if stats.get('avg_spo2'):
            quick_stats.append(f"SpO2 mediu: {stats['avg_spo2']:.1f}%")
        if stats.get('min_spo2'):
            quick_stats.append(f"Min: {stats['min_spo2']:.1f}%")
        if stats.get('max_spo2'):
            quick_stats.append(f"Max: {stats['max_spo2']:.1f}%")
        
        # Card pentru fiecare PDF
        pdf_cards.append(
            html.Div([
                # Header
                html.Div([
                    html.Strong(f"📄 {os.path.basename(pdf_path)}", style={'fontSize': '14px', 'color': '#2c3e50'}),
                    html.Div([
                        html.Button(
                            '📥 Descarcă',
                            id={'type': 'download-pdf-btn', 'index': f"{token}|{pdf_path}"},
                            n_clicks=0,
                            style={
                                'padding': '5px 15px',
                                'backgroundColor': '#3498db',
                                'color': 'white',
                                'border': 'none',
                                'borderRadius': '5px',
                                'cursor': 'pointer',
                                'fontSize': '12px',
                                'marginRight': '10px'
                            }
                        ),
                        html.Button(
                            '🗑️',
                            id={'type': 'delete-pdf-btn', 'index': f"{token}|{pdf_path}"},
                            n_clicks=0,
                            style={
                                'padding': '5px 10px',
                                'backgroundColor': '#e74c3c',
                                'color': 'white',
                                'border': 'none',
                                'borderRadius': '5px',
                                'cursor': 'pointer',
                                'fontSize': '12px'
                            }
                        )
                    ], style={'display': 'inline-block'})
                ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '15px'}),
                
                # Quick stats
                html.Div([
                    html.Div([
                        html.Span(stat, style={
                            'display': 'inline-block',
                            'padding': '5px 10px',
                            'backgroundColor': '#e8f5e9',
                            'borderRadius': '5px',
                            'marginRight': '10px',
                            'marginBottom': '5px',
                            'fontSize': '13px',
                            'color': '#27ae60'
                        })
                        for stat in quick_stats
                    ])
                ], style={'marginBottom': '15px'}),
                
                # === PREVIZUALIZARE VIZUALĂ PDF (IFRAME) ===
                html.Div([
                    html.Strong("🖼️ Previzualizare PDF:", style={'display': 'block', 'marginBottom': '10px', 'color': '#2c3e50'}),
                    html.Iframe(
                        src=pdf_to_base64(pdf_path),
                        style={
                            'width': '100%',
                            'height': '600px',
                            'border': '2px solid #ddd',
                            'borderRadius': '8px',
                            'backgroundColor': '#f8f9fa'
                        }
                    )
                ], style={'marginBottom': '20px'}),
                
                # Date detaliate (formatate) - collapse pentru economie spațiu
                html.Details([
                    html.Summary("📊 Vezi raport text extras (date parsate)", style={'cursor': 'pointer', 'fontWeight': 'bold', 'color': '#2980b9', 'marginBottom': '10px'}),
                    html.Div([
                        html.Pre(
                            formatted_text if formatted_text.strip() else "⚠️ Nu s-au putut extrage date text din PDF (posibil PDF scanat/imagine). Vizualizați previzualizarea vizuală de mai sus.",
                            style={
                                'padding': '15px',
                                'backgroundColor': '#ffffff',
                                'border': '1px solid #ddd',
                                'borderRadius': '5px',
                                'fontSize': '13px',
                                'lineHeight': '1.6',
                                'whiteSpace': 'pre-wrap',
                                'fontFamily': 'Arial, sans-serif',
                                'color': '#555' if formatted_text.strip() else '#999',
                                'fontStyle': 'normal' if formatted_text.strip() else 'italic'
                            }
                        )
                    ], style={'marginTop': '10px'})
                ]),
                
                # Footer cu metadata
                html.Hr(style={'margin': '15px 0'}),
                html.Small(f"Procesat: {parsed_at[:19] if parsed_at else 'N/A'}", style={'color': '#95a5a6', 'fontSize': '11px'})
                
            ], style={
                'padding': '20px',
                'marginBottom': '15px',
                'backgroundColor': '#fff',
                'borderRadius': '8px',
                'border': '2px solid #27ae60',
                'boxShadow': '0 2px 6px rgba(0,0,0,0.1)'
            })
        )
    
    return html.Div(pdf_cards)


@app.callback(
    Output('data-view-container', 'children', allow_duplicate=True),
    [Input({'type': 'delete-pdf-btn', 'index': ALL}, 'n_clicks')],
    [State({'type': 'delete-pdf-btn', 'index': ALL}, 'id')],
    prevent_initial_call=True
)
def handle_pdf_deletion(n_clicks_list, ids_list):
    """
    Callback pentru ștergerea PDF-urilor.
    """
    if not any(n_clicks_list):
        return no_update
    
    from dash import ctx
    
    if not ctx.triggered_id:
        return no_update
    
    triggered_id = ctx.triggered_id['index']
    token, pdf_path = triggered_id.split('|', 1)
    
    logger.info(f"🗑️ Ștergere PDF solicitată: {pdf_path} pentru {token[:8]}...")
    
    try:
        if patient_links.delete_pdf_from_link(token, pdf_path):
            logger.info(f"✅ PDF șters cu succes: {pdf_path}")
            # Refresh data view
            return no_update  # Callback-ul principal de refresh va reîncărca
        else:
            logger.error(f"Eroare la ștergerea PDF: {pdf_path}")
            return no_update
    except Exception as e:
        logger.error(f"Eroare critică la ștergerea PDF: {e}", exc_info=True)
        return no_update


@app.callback(
    Output('expanded-row-id', 'data', allow_duplicate=True),
    [Input('admin-refresh-data-view', 'n_clicks')],
    prevent_initial_call=True
)
def refresh_after_pdf_action(n_clicks):
    """
    Trigger pentru refresh după acțiuni PDF.
    """
    return no_update


# ==============================================================================
# CALLBACKS BATCH SESSION - TRACKING PROGRES & ISTORIC
# ==============================================================================

@app.callback(
    [Output('admin-batch-progress-text', 'children'),
     Output('admin-batch-progress-bar', 'style'),
     Output('admin-batch-status-detail', 'children')],
    [Input('admin-batch-progress-interval', 'n_intervals')],
    [State('admin-batch-session-id', 'data')]
)
def update_batch_progress_display(n_intervals, session_id):
    """
    Actualizează afișarea progresului procesării batch în timp real.
    Citește starea din batch_session_manager.
    """
    if not session_id:
        return "0 / 0 fișiere", {'height': '30px', 'width': '0%', 'backgroundColor': '#27ae60', 'borderRadius': '5px'}, ""
    
    # Obține progres sesiune
    progress_data = batch_session_manager.get_session_progress(session_id)
    
    if not progress_data:
        return "Sesiune nu există", {'height': '30px', 'width': '0%', 'backgroundColor': '#e74c3c', 'borderRadius': '5px'}, ""
    
    metadata = progress_data['metadata']
    processed = metadata.get('processed_files', 0)
    total = metadata.get('total_files', 0)
    failed = metadata.get('failed_files', 0)
    
    # Calculăm procentajul
    percentage = int((processed / total * 100)) if total > 0 else 0
    
    # Text indicator
    progress_text = f"{processed} / {total} fișiere"
    
    # Stil bară progres
    bar_style = {
        'height': '30px',
        'width': f'{percentage}%',
        'backgroundColor': '#27ae60',
        'borderRadius': '5px',
        'transition': 'width 0.3s ease',
        'display': 'flex',
        'alignItems': 'center',
        'justifyContent': 'center',
        'color': 'white',
        'fontWeight': 'bold',
        'fontSize': '12px'
    }
    
    # Status detaliat
    status_detail = html.Div([
        html.Span(f"✅ Procesate: {processed} ", style={'color': 'green', 'marginRight': '15px'}),
        html.Span(f"❌ Erori: {failed} ", style={'color': 'red', 'marginRight': '15px'}) if failed > 0 else "",
        html.Span(f"⏳ Rămase: {total - processed}", style={'color': 'orange'})
    ])
    
    return progress_text, bar_style, status_detail


@app.callback(
    Output('admin-batch-sessions-history', 'children'),
    [Input('url', 'pathname'),  # Refresh la încărcare pagină
     Input('admin-refresh-trigger', 'data')]  # Refresh după procesare
)
def display_batch_sessions_history(pathname, trigger):
    """
    Afișează istoricul sesiunilor batch (ultimele 10).
    """
    sessions = batch_session_manager.get_all_sessions(limit=10)
    
    if not sessions:
        return html.P("🔍 Nu există sesiuni batch încă.", style={'textAlign': 'center', 'color': '#95a5a6', 'padding': '20px'})
    
    session_rows = []
    for session in sessions:
        session_id = session.get('session_id', 'N/A')
        created_at = session.get('created_at', 'N/A')
        status = session.get('status', 'unknown')
        total_files = session.get('total_files', 0)
        processed = session.get('processed_files', 0)
        failed = session.get('failed_files', 0)
        
        # Formatare dată
        try:
            dt = datetime.fromisoformat(created_at)
            formatted_date = dt.strftime("%d/%m/%Y %H:%M:%S")
        except:
            formatted_date = created_at
        
        # Culoare în funcție de status
        status_colors = {
            'completed': '#27ae60',
            'in_progress': '#f39c12',
            'failed': '#e74c3c',
            'pending': '#3498db'
        }
        status_color = status_colors.get(status, '#95a5a6')
        
        # Badge status
        status_text = {
            'completed': '✅ Completă',
            'in_progress': '⏳ În curs',
            'failed': '❌ Eșuată',
            'pending': '🔵 Așteptare'
        }
        status_badge = status_text.get(status, status.upper())
        
        session_rows.append(
            html.Div([
                html.Div([
                    html.Strong(f"📅 {formatted_date}", style={'marginRight': '15px'}),
                    html.Span(status_badge, style={
                        'padding': '4px 10px',
                        'backgroundColor': status_color,
                        'color': 'white',
                        'borderRadius': '12px',
                        'fontSize': '12px',
                        'fontWeight': 'bold'
                    })
                ], style={'marginBottom': '8px'}),
                
                html.Div([
                    html.Span(f"📂 Total: {total_files} fișiere", style={'marginRight': '15px', 'fontSize': '13px'}),
                    html.Span(f"✅ Procesate: {processed}", style={'marginRight': '15px', 'fontSize': '13px', 'color': 'green'}),
                    html.Span(f"❌ Erori: {failed}", style={'fontSize': '13px', 'color': 'red'}) if failed > 0 else ""
                ]),
                
                html.Small(f"ID: {session_id[:16]}...", style={'color': '#95a5a6', 'display': 'block', 'marginTop': '5px', 'fontSize': '11px'})
            ], style={
                'padding': '12px',
                'marginBottom': '10px',
                'backgroundColor': 'white',
                'borderRadius': '6px',
                'border': f'1px solid {status_color}',
                'borderLeft': f'4px solid {status_color}'
            })
        )
    
    return html.Div(session_rows)


# ============================================================================
# FILTRARE TEMPORALĂ - Callback-uri pentru butoane și calendar
# ============================================================================

@app.callback(
    [Output('active-date-filter', 'data'),
     Output('date-picker-start', 'date'),
     Output('date-picker-end', 'date')],
    [Input('filter-today', 'n_clicks'),
     Input('filter-yesterday', 'n_clicks'),
     Input('filter-week', 'n_clicks'),
     Input('filter-month', 'n_clicks'),
     Input('filter-year', 'n_clicks'),
     Input('apply-date-filter', 'n_clicks'),
     Input('clear-date-filter', 'n_clicks')],
    [State('date-picker-start', 'date'),
     State('date-picker-end', 'date')],
    prevent_initial_call=True
)
def update_date_filter(today_clicks, yesterday_clicks, week_clicks, month_clicks, year_clicks, 
                        apply_clicks, clear_clicks, start_date, end_date):
    """
    Actualizează filtrul de date activ bazat pe butoanele apăsate sau calendar.
    """
    from dash import ctx
    from datetime import datetime, timedelta
    
    if not ctx.triggered_id:
        return no_update, no_update, no_update
    
    trigger_id = ctx.triggered_id
    logger.info(f"📅 Filtru temporal: {trigger_id}")
    
    today = datetime.now().date()
    
    # Resetare filtru
    if trigger_id == 'clear-date-filter':
        return None, None, None
    
    # Butoane rapide
    if trigger_id == 'filter-today':
        return {'start': today.isoformat(), 'end': today.isoformat(), 'label': 'Azi'}, today.isoformat(), today.isoformat()
    
    elif trigger_id == 'filter-yesterday':
        yesterday = today - timedelta(days=1)
        return {'start': yesterday.isoformat(), 'end': yesterday.isoformat(), 'label': 'Ieri'}, yesterday.isoformat(), yesterday.isoformat()
    
    elif trigger_id == 'filter-week':
        week_ago = today - timedelta(days=7)
        return {'start': week_ago.isoformat(), 'end': today.isoformat(), 'label': '1 Săptămână'}, week_ago.isoformat(), today.isoformat()
    
    elif trigger_id == 'filter-month':
        month_ago = today - timedelta(days=30)
        return {'start': month_ago.isoformat(), 'end': today.isoformat(), 'label': '1 Lună'}, month_ago.isoformat(), today.isoformat()
    
    elif trigger_id == 'filter-year':
        year_ago = today - timedelta(days=365)
        return {'start': year_ago.isoformat(), 'end': today.isoformat(), 'label': '1 An'}, year_ago.isoformat(), today.isoformat()
    
    # Aplicare interval personalizat
    elif trigger_id == 'apply-date-filter':
        if start_date and end_date:
            return {'start': start_date, 'end': end_date, 'label': 'Interval Personalizat'}, start_date, end_date
        elif start_date:
            return {'start': start_date, 'end': start_date, 'label': 'Interval Personalizat'}, start_date, start_date
        else:
            logger.warning("Nicio dată selectată pentru filtrare")
            return no_update, no_update, no_update
    
    return no_update, no_update, no_update


# ==============================================================================
# CALLBACKS SETĂRI DOCTOR - UPLOAD LOGO & FOOTER
# ==============================================================================

@app.callback(
    [Output('settings-logo-preview-container', 'children'),
     Output('settings-status-notification', 'children')],
    [Input('settings-logo-upload', 'contents')],
    [State('settings-logo-upload', 'filename')]
)
def handle_logo_upload(contents, filename):
    """
    Gestionează upload-ul logo-ului medicului.
    """
    import doctor_settings
    
    if not contents:
        return no_update, no_update
    
    try:
        # Decodăm conținutul base64
        content_type, content_string = contents.split(',')
        logo_bytes = base64.b64decode(content_string)
        
        # Salvăm logo-ul
        logo_path = doctor_settings.save_doctor_logo(logo_bytes, filename)
        
        if logo_path:
            # Creăm preview-ul
            logo_base64 = doctor_settings.get_doctor_logo_base64()
            
            preview = html.Div([
                html.H4("✅ Logo Curent:", style={'color': '#27ae60', 'marginBottom': '10px'}),
                html.Img(
                    src=logo_base64,
                    style={
                        'maxWidth': '300px',
                        'maxHeight': '150px',
                        'border': '2px solid #27ae60',
                        'borderRadius': '8px',
                        'padding': '10px',
                        'backgroundColor': 'white'
                    }
                ),
                html.P(
                    f"📁 {filename}",
                    style={'fontSize': '12px', 'color': '#666', 'marginTop': '10px'}
                )
            ], style={
                'textAlign': 'center',
                'padding': '20px',
                'backgroundColor': '#d4edda',
                'borderRadius': '8px',
                'border': '1px solid #c3e6cb'
            })
            
            notification = html.Div([
                html.Strong("✅ Succes! ", style={'color': '#27ae60'}),
                html.Span("Logo-ul a fost încărcat și salvat cu succes.")
            ], style={
                'padding': '15px',
                'backgroundColor': '#d4edda',
                'border': '1px solid #c3e6cb',
                'borderRadius': '5px',
                'color': '#155724'
            })
            
            logger.info(f"✅ Logo uploadat cu succes: {filename}")
            return preview, notification
        else:
            error_notification = html.Div([
                html.Strong("❌ Eroare! ", style={'color': '#e74c3c'}),
                html.Span("Nu s-a putut salva logo-ul. Verificați formatul imaginii.")
            ], style={
                'padding': '15px',
                'backgroundColor': '#f8d7da',
                'border': '1px solid #f5c6cb',
                'borderRadius': '5px',
                'color': '#721c24'
            })
            
            return no_update, error_notification
            
    except Exception as e:
        logger.error(f"Eroare la upload logo: {e}", exc_info=True)
        
        error_notification = html.Div([
            html.Strong("❌ Eroare! ", style={'color': '#e74c3c'}),
            html.Span(f"Eroare la procesarea fișierului: {str(e)}")
        ], style={
            'padding': '15px',
            'backgroundColor': '#f8d7da',
            'border': '1px solid #f5c6cb',
            'borderRadius': '5px',
            'color': '#721c24'
        })
        
        return no_update, error_notification


@app.callback(
    [Output('settings-logo-preview-container', 'children', allow_duplicate=True),
     Output('settings-status-notification', 'children', allow_duplicate=True)],
    [Input('settings-delete-logo-button', 'n_clicks')],
    prevent_initial_call=True
)
def handle_logo_delete(n_clicks):
    """
    Gestionează ștergerea logo-ului medicului.
    """
    import doctor_settings
    
    if not n_clicks:
        return no_update, no_update
    
    try:
        if doctor_settings.delete_doctor_logo():
            empty_preview = html.P("📭 Nu ați încărcat încă un logo.", style={
                'textAlign': 'center',
                'color': '#95a5a6',
                'padding': '20px',
                'backgroundColor': '#f8f9fa',
                'borderRadius': '5px',
                'border': '1px dashed #bdc3c7'
            })
            
            notification = html.Div([
                html.Strong("✅ Succes! ", style={'color': '#27ae60'}),
                html.Span("Logo-ul a fost șters.")
            ], style={
                'padding': '15px',
                'backgroundColor': '#d4edda',
                'border': '1px solid #c3e6cb',
                'borderRadius': '5px',
                'color': '#155724'
            })
            
            logger.info("🗑️ Logo șters cu succes")
            return empty_preview, notification
        else:
            error_notification = html.Div([
                html.Strong("❌ Eroare! ", style={'color': '#e74c3c'}),
                html.Span("Nu s-a putut șterge logo-ul.")
            ], style={
                'padding': '15px',
                'backgroundColor': '#f8d7da',
                'border': '1px solid #f5c6cb',
                'borderRadius': '5px',
                'color': '#721c24'
            })
            
            return no_update, error_notification
            
    except Exception as e:
        logger.error(f"Eroare la ștergerea logo-ului: {e}", exc_info=True)
        return no_update, no_update


@app.callback(
    Output('settings-status-notification', 'children', allow_duplicate=True),
    [Input('settings-save-footer-button', 'n_clicks'),
     Input('settings-logo-apply-options', 'value')],
    [State('settings-footer-textarea', 'value')],
    prevent_initial_call=True
)
def handle_settings_save(footer_clicks, logo_apply_options, footer_text):
    """
    Gestionează salvarea setărilor (footer și preferințe logo).
    """
    import doctor_settings
    from dash import callback_context
    
    if not callback_context.triggered:
        return no_update
    
    trigger_id = callback_context.triggered[0]['prop_id'].split('.')[0]
    
    try:
        # Salvăm preferințele de aplicare logo
        if logo_apply_options is not None:
            apply_to_images = 'images' in logo_apply_options
            apply_to_pdf = 'pdf' in logo_apply_options
            apply_to_site = 'site' in logo_apply_options
            
            doctor_settings.update_logo_preferences(
                apply_to_images=apply_to_images,
                apply_to_pdf=apply_to_pdf,
                apply_to_site=apply_to_site
            )
        
        # Salvăm footer-ul dacă butonul a fost apăsat
        if trigger_id == 'settings-save-footer-button' and footer_clicks:
            footer_text = footer_text or ""
            
            if doctor_settings.update_footer_info(footer_text):
                notification = html.Div([
                    html.Strong("✅ Succes! ", style={'color': '#27ae60'}),
                    html.Span("Setările au fost salvate cu succes.")
                ], style={
                    'padding': '15px',
                    'backgroundColor': '#d4edda',
                    'border': '1px solid #c3e6cb',
                    'borderRadius': '5px',
                    'color': '#155724'
                })
                
                logger.info("✅ Setări salvate cu succes")
                return notification
            else:
                error_notification = html.Div([
                    html.Strong("❌ Eroare! ", style={'color': '#e74c3c'}),
                    html.Span("Nu s-au putut salva setările.")
                ], style={
                    'padding': '15px',
                    'backgroundColor': '#f8d7da',
                    'border': '1px solid #f5c6cb',
                    'borderRadius': '5px',
                    'color': '#721c24'
                })
                
                return error_notification
        
        # Dacă doar s-au schimbat preferințele logo (fără click pe buton)
        if trigger_id == 'settings-logo-apply-options':
            notification = html.Div([
                html.Strong("✅ Actualizat! ", style={'color': '#2980b9'}),
                html.Span("Preferințele de aplicare au fost salvate.")
            ], style={
                'padding': '15px',
                'backgroundColor': '#d1ecf1',
                'border': '1px solid #bee5eb',
                'borderRadius': '5px',
                'color': '#0c5460'
            })
            
            logger.info("✅ Preferințe logo actualizate")
            return notification
        
        return no_update
        
    except Exception as e:
        logger.error(f"Eroare la salvarea setărilor: {e}", exc_info=True)
        
        error_notification = html.Div([
            html.Strong("❌ Eroare! ", style={'color': '#e74c3c'}),
            html.Span(f"Eroare la salvarea setărilor: {str(e)}")
        ], style={
            'padding': '15px',
            'backgroundColor': '#f8d7da',
            'border': '1px solid #f5c6cb',
            'borderRadius': '5px',
            'color': '#721c24'
        })
        
        return error_notification


@app.callback(
    Output('settings-footer-preview', 'children'),
    [Input('settings-footer-textarea', 'value')]
)
def update_footer_preview(footer_text):
    """
    Actualizează preview-ul footer-ului în timp real pe măsură ce se scrie.
    """
    import doctor_settings
    from dash import dcc as dash_dcc
    
    if not footer_text or footer_text.strip() == "":
        return html.P(
            "Footer-ul va apărea aici după ce scrieți text...", 
            style={'color': '#95a5a6', 'fontStyle': 'italic', 'fontSize': '12px'}
        )
    
    try:
        # Procesăm footer-ul pentru a obține lista de componente Dash
        footer_components = doctor_settings.process_footer_links(footer_text)
        
        # Returnăm un Div cu componentele procesate
        return html.Div(
            children=footer_components,
            style={
                'color': '#555',
                'fontSize': '13px',
                'lineHeight': '1.6',
                'margin': '0',
                'whiteSpace': 'normal'
            }
        )
    except Exception as e:
        logger.error(f"Eroare la preview footer: {e}", exc_info=True)
        return html.P(
            f"⚠️ Eroare la procesarea textului: {str(e)}", 
            style={'color': '#e74c3c', 'fontSize': '12px'}
        )


@app.callback(
    [Output('settings-logo-preview-container', 'children', allow_duplicate=True),
     Output('settings-footer-textarea', 'value'),
     Output('settings-logo-apply-options', 'value')],
    [Input('app-tabs', 'value')],
    prevent_initial_call=True
)
def load_settings_on_tab_open(tab_value):
    """
    Încarcă setările salvate când se deschide tab-ul de setări.
    """
    import doctor_settings
    
    if tab_value != 'tab-settings':
        return no_update, no_update, no_update
    
    try:
        # Încărcăm setările
        settings = doctor_settings.load_doctor_settings()
        
        # Încărcăm logo-ul dacă există
        logo_base64 = doctor_settings.get_doctor_logo_base64()
        
        if logo_base64:
            preview = html.Div([
                html.H4("✅ Logo Curent:", style={'color': '#27ae60', 'marginBottom': '10px'}),
                html.Img(
                    src=logo_base64,
                    style={
                        'maxWidth': '300px',
                        'maxHeight': '150px',
                        'border': '2px solid #27ae60',
                        'borderRadius': '8px',
                        'padding': '10px',
                        'backgroundColor': 'white'
                    }
                ),
                html.P(
                    f"📁 {settings.get('logo_filename', 'Logo')}",
                    style={'fontSize': '12px', 'color': '#666', 'marginTop': '10px'}
                )
            ], style={
                'textAlign': 'center',
                'padding': '20px',
                'backgroundColor': '#d4edda',
                'borderRadius': '8px',
                'border': '1px solid #c3e6cb'
            })
        else:
            preview = html.P("📭 Nu ați încărcat încă un logo.", style={
                'textAlign': 'center',
                'color': '#95a5a6',
                'padding': '20px',
                'backgroundColor': '#f8f9fa',
                'borderRadius': '5px',
                'border': '1px dashed #bdc3c7'
            })
        
        # Încărcăm footer-ul
        footer_text = settings.get('footer_info', '')
        
        # Încărcăm preferințele de aplicare
        apply_options = []
        if settings.get('apply_logo_to_images', True):
            apply_options.append('images')
        if settings.get('apply_logo_to_pdf', True):
            apply_options.append('pdf')
        if settings.get('apply_logo_to_site', True):
            apply_options.append('site')
        
        logger.debug("✅ Setări încărcate pentru afișare în tab")
        return preview, footer_text, apply_options
        
    except Exception as e:
        logger.error(f"Eroare la încărcarea setărilor: {e}", exc_info=True)
        return no_update, no_update, no_update


# ==============================================================================
# CALLBACKS AFIȘARE LOGO & FOOTER PENTRU PACIENȚI
# ==============================================================================

@app.callback(
    [Output('patient-logo-container', 'children'),
     Output('patient-footer-container', 'children')],
    [Input('url-token-detected', 'data')]
)
def display_doctor_branding_for_patient(token):
    """
    Afișează logo-ul și footer-ul medicului pe pagina pacientului.
    """
    import doctor_settings
    
    if not token:
        return None, None
    
    try:
        # Încărcăm setările medicului
        settings = doctor_settings.load_doctor_settings()
        
        # Logo
        logo_component = None
        if doctor_settings.should_apply_logo_to_site():
            logo_base64 = doctor_settings.get_doctor_logo_base64()
            if logo_base64:
                logo_component = html.Img(
                    src=logo_base64,
                    style={
                        'maxWidth': '250px',
                        'maxHeight': '120px',
                        'marginTop': '20px',
                        'marginBottom': '10px',
                        'filter': 'drop-shadow(0 2px 4px rgba(0,0,0,0.1))'
                    }
                )
                logger.debug("✅ Logo afișat pentru pacient")
        
        # Footer
        footer_component = None
        footer_text = doctor_settings.get_footer_info()
        if footer_text:
            # Procesăm footer-ul pentru a obține lista de componente Dash
            footer_components = doctor_settings.process_footer_links(footer_text)
            
            # Creăm containerul footer cu componentele procesate
            footer_component = html.Div(
                children=footer_components,
                style={
                    'textAlign': 'center',
                    'color': '#555',
                    'fontSize': '13px',
                    'padding': '15px',
                    'backgroundColor': '#f8f9fa',
                    'borderRadius': '8px',
                    'border': '1px solid #e0e0e0',
                    'lineHeight': '1.6',
                    'margin': '0',
                    'whiteSpace': 'normal'
                }
            )
            logger.debug("✅ Footer personalizat afișat pentru pacient (cu link-uri procesate)")
        
        return logo_component, footer_component
        
    except Exception as e:
        logger.error(f"Eroare la afișarea branding-ului pentru pacient: {e}", exc_info=True)
        return None, None


@app.callback(
    Output('medical-footer-container', 'children'),
    [Input('url-token-detected', 'data')]
)
def display_footer_for_medical_pages(token):
    """
    Afișează footer-ul medicului pe paginile medicale (admin, batch, etc.).
    Se declanșează la încărcarea paginii (indiferent de prezența token-ului).
    """
    import doctor_settings
    
    try:
        # Încărcăm setările medicului
        footer_text = doctor_settings.get_footer_info()
        
        if not footer_text:
            return None
        
        # Procesăm footer-ul pentru a obține lista de componente Dash
        footer_components = doctor_settings.process_footer_links(footer_text)
        
        # Creăm containerul footer cu componentele procesate
        footer_component = html.Div(
            children=footer_components,
            style={
                'textAlign': 'center',
                'color': '#555',
                'fontSize': '13px',
                'padding': '15px',
                'backgroundColor': '#f8f9fa',
                'borderRadius': '8px',
                'border': '1px solid #e0e0e0',
                'lineHeight': '1.6',
                'margin': '0 auto',
                'maxWidth': '900px',
                'whiteSpace': 'normal'
            }
        )
        
        logger.debug("✅ Footer personalizat afișat pe pagina medicală")
        return footer_component
        
    except Exception as e:
        logger.error(f"Eroare la afișarea footer-ului pe pagina medicală: {e}", exc_info=True)
        return None


# ==============================================================================
# CALLBACKS ȘTERGERE ÎNREGISTRĂRI
# ==============================================================================

@app.callback(
    [Output('delete-confirmation-modal', 'style'),
     Output('delete-confirmation-modal', 'children'),
     Output('delete-recording-store', 'data')],
    [Input({'type': 'delete-recording-btn', 'index': ALL}, 'n_clicks')],
    [State({'type': 'delete-recording-btn', 'index': ALL}, 'id'),
     State({'type': 'recording-token-store', 'index': ALL}, 'data')],
    prevent_initial_call=True
)
def show_delete_confirmation(n_clicks_list, btn_ids, token_list):
    """
    Afișează modal de confirmare pentru ștergerea unei înregistrări.
    """
    from dash import ctx
    
    # Verificăm dacă există click-uri
    if not any(n_clicks_list) or not ctx.triggered_id:
        return {'display': 'none'}, [], None
    
    # Găsim care buton a fost apăsat
    triggered_id = ctx.triggered_id
    recording_id = triggered_id['index']
    
    # Găsim token-ul corespunzător
    token = None
    for i, btn_id in enumerate(btn_ids):
        if btn_id['index'] == recording_id:
            token = token_list[i] if i < len(token_list) else None
            break
    
    if not token:
        logger.error(f"Nu s-a găsit token pentru înregistrarea {recording_id}")
        return {'display': 'none'}, [], None
    
    # Găsim informațiile despre înregistrare
    recordings = patient_links.get_patient_recordings(token)
    recording_info = None
    for rec in recordings:
        if rec['id'] == recording_id:
            recording_info = rec
            break
    
    if not recording_info:
        logger.error(f"Nu s-a găsit înregistrarea {recording_id}")
        return {'display': 'none'}, [], None
    
    logger.info(f"⚠️ Cerere ștergere pentru înregistrarea {recording_id} ({recording_info.get('original_filename')})")
    
    # Creăm modal-ul de confirmare
    modal_content = html.Div([
        html.Div([
            html.Div([
                html.H3("⚠️ Confirmare Ștergere", style={
                    'color': '#e74c3c',
                    'marginBottom': '20px',
                    'textAlign': 'center'
                }),
                html.P([
                    "Sunteți sigur că doriți să ștergeți această înregistrare?",
                    html.Br(),
                    html.Br(),
                    html.Strong(f"📅 Data: {recording_info.get('recording_date')}"),
                    html.Br(),
                    html.Strong(f"⏱️ Interval: {recording_info.get('start_time')} - {recording_info.get('end_time')}"),
                    html.Br(),
                    html.Strong(f"📁 Fișier: {recording_info.get('original_filename')}")
                ], style={
                    'fontSize': '14px',
                    'color': '#555',
                    'lineHeight': '1.8',
                    'marginBottom': '30px'
                }),
                html.Div([
                    html.Strong("⚠️ ATENȚIE: ", style={'color': '#e74c3c'}),
                    "Această acțiune este ",
                    html.Strong("IREVERSIBILĂ", style={'color': '#e74c3c'}),
                    ". Fișierul CSV și toate datele asociate vor fi șterse permanent."
                ], style={
                    'padding': '15px',
                    'backgroundColor': '#fff3cd',
                    'border': '2px solid #ffc107',
                    'borderRadius': '8px',
                    'marginBottom': '30px',
                    'fontSize': '13px',
                    'color': '#856404'
                }),
                html.Div([
                    html.Button(
                        '❌ Da, șterge definitiv',
                        id='confirm-delete-btn',
                        style={
                            'padding': '12px 30px',
                            'backgroundColor': '#e74c3c',
                            'color': 'white',
                            'border': 'none',
                            'borderRadius': '5px',
                            'cursor': 'pointer',
                            'fontSize': '14px',
                            'fontWeight': 'bold',
                            'marginRight': '15px'
                        }
                    ),
                    html.Button(
                        '✅ Anulează',
                        id='cancel-delete-btn',
                        style={
                            'padding': '12px 30px',
                            'backgroundColor': '#95a5a6',
                            'color': 'white',
                            'border': 'none',
                            'borderRadius': '5px',
                            'cursor': 'pointer',
                            'fontSize': '14px',
                            'fontWeight': 'bold'
                        }
                    )
                ], style={'textAlign': 'center'})
            ], style={
                'backgroundColor': 'white',
                'padding': '40px',
                'borderRadius': '15px',
                'boxShadow': '0 10px 40px rgba(0,0,0,0.3)',
                'maxWidth': '550px',
                'margin': '0 auto'
            })
        ], style={
            'position': 'fixed',
            'top': '0',
            'left': '0',
            'right': '0',
            'bottom': '0',
            'backgroundColor': 'rgba(0,0,0,0.5)',
            'display': 'flex',
            'alignItems': 'center',
            'justifyContent': 'center',
            'zIndex': '10000',
            'padding': '20px'
        })
    ])
    
    # Salvăm informațiile în store pentru ștergere
    delete_data = {
        'token': token,
        'recording_id': recording_id,
        'recording_info': recording_info
    }
    
    return {'display': 'block'}, modal_content, delete_data


@app.callback(
    [Output('delete-confirmation-modal', 'style', allow_duplicate=True),
     Output('patient-recordings-list', 'children', allow_duplicate=True),
     Output('global-notification-container', 'children', allow_duplicate=True)],
    [Input('confirm-delete-btn', 'n_clicks'),
     Input('cancel-delete-btn', 'n_clicks')],
    [State('delete-recording-store', 'data'),
     State('current-patient-token', 'data')],
    prevent_initial_call=True
)
def handle_delete_confirmation(confirm_clicks, cancel_clicks, delete_data, current_token):
    """
    Gestionează confirmarea sau anularea ștergerii.
    """
    from dash import ctx
    
    if not ctx.triggered_id:
        return no_update, no_update, no_update
    
    triggered_id = ctx.triggered_id
    
    # Dacă s-a anulat
    if triggered_id == 'cancel-delete-btn':
        logger.info("❌ Ștergere anulată de utilizator")
        return {'display': 'none'}, no_update, no_update
    
    # Dacă s-a confirmat ștergerea
    if triggered_id == 'confirm-delete-btn' and delete_data:
        token = delete_data.get('token')
        recording_id = delete_data.get('recording_id')
        recording_info = delete_data.get('recording_info', {})
        
        logger.info(f"🗑️ Executare ștergere pentru înregistrarea {recording_id}...")
        
        try:
            # Șterge înregistrarea
            success = patient_links.delete_recording(token, recording_id)
            
            if success:
                # Reîncărcăm lista de înregistrări
                recordings = patient_links.get_patient_recordings(token)
                
                # Recreăm cardurile
                if not recordings:
                    new_list = html.Div(
                        "📭 Nu mai aveți înregistrări.",
                        style={'padding': '20px', 'textAlign': 'center', 'color': '#666', 'fontStyle': 'italic'}
                    )
                else:
                    recording_cards = []
                    for rec in recordings:
                        recording_cards.append(
                            html.Div([
                                html.H4(f"📅 {rec['recording_date']}", style={'color': '#2c3e50'}),
                                html.P(f"⏱️ Interval: {rec['start_time']} - {rec['end_time']}"),
                                html.P(f"📊 SaO2: avg={rec['stats']['avg_spo2']:.1f}%, min={rec['stats']['min_spo2']}%, max={rec['stats']['max_spo2']}%"),
                                html.P(f"📁 Fișier: {rec['original_filename']}", style={'fontSize': '12px', 'color': '#7f8c8d'}),
                                html.Div([
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
                                            'cursor': 'pointer',
                                            'marginRight': '10px'
                                        }
                                    ),
                                    html.Button(
                                        '🗑️ Șterge',
                                        id={'type': 'delete-recording-btn', 'index': rec['id']},
                                        style={
                                            'padding': '10px 20px',
                                            'backgroundColor': '#e74c3c',
                                            'color': 'white',
                                            'border': 'none',
                                            'borderRadius': '5px',
                                            'cursor': 'pointer'
                                        }
                                    )
                                ], style={'marginTop': '15px'}),
                                dcc.Store(id={'type': 'recording-token-store', 'index': rec['id']}, data=token)
                            ], style={
                                'padding': '20px',
                                'marginBottom': '15px',
                                'backgroundColor': '#ecf0f1',
                                'borderRadius': '10px',
                                'border': '1px solid #bdc3c7'
                            })
                        )
                    new_list = html.Div(recording_cards)
                
                # Notificare succes
                notification = html.Div([
                    html.Div([
                        html.Strong("✅ Înregistrare ștearsă cu succes!", style={'display': 'block', 'marginBottom': '10px'}),
                        html.P(f"📁 {recording_info.get('original_filename', 'Fișier')}", style={'margin': '0', 'fontSize': '13px'}),
                        html.P(f"📅 {recording_info.get('recording_date', '')} {recording_info.get('start_time', '')}", style={'margin': '0', 'fontSize': '13px'})
                    ], style={
                        'padding': '20px',
                        'backgroundColor': '#d4edda',
                        'border': '1px solid #28a745',
                        'borderRadius': '8px',
                        'color': '#155724',
                        'marginBottom': '20px'
                    })
                ])
                
                logger.info(f"✅ Înregistrare ștearsă cu succes: {recording_id}")
                return {'display': 'none'}, new_list, notification
            else:
                # Eroare la ștergere
                notification = html.Div(
                    "❌ Eroare la ștergerea înregistrării. Încercați din nou.",
                    style={
                        'padding': '20px',
                        'backgroundColor': '#f8d7da',
                        'border': '1px solid #dc3545',
                        'borderRadius': '8px',
                        'color': '#721c24',
                        'marginBottom': '20px'
                    }
                )
                logger.error(f"❌ Eroare la ștergerea înregistrării {recording_id}")
                return {'display': 'none'}, no_update, notification
                
        except Exception as e:
            logger.error(f"Excepție la ștergerea înregistrării: {e}", exc_info=True)
            notification = html.Div(
                f"❌ Eroare: {str(e)}",
                style={
                    'padding': '20px',
                    'backgroundColor': '#f8d7da',
                    'border': '1px solid #dc3545',
                    'borderRadius': '8px',
                    'color': '#721c24',
                    'marginBottom': '20px'
                }
            )
            return {'display': 'none'}, no_update, notification
    
    return no_update, no_update, no_update


# ==============================================================================
# CALLBACKS ȘTERGERE LINK-URI (MEDICI)
# ==============================================================================

@app.callback(
    [Output('delete-confirmation-modal', 'style', allow_duplicate=True),
     Output('delete-confirmation-modal', 'children', allow_duplicate=True),
     Output('delete-recording-store', 'data', allow_duplicate=True)],
    [Input({'type': 'delete-link-btn', 'index': ALL}, 'n_clicks')],
    [State({'type': 'delete-link-btn', 'index': ALL}, 'id')],
    prevent_initial_call=True
)
def show_delete_link_confirmation(n_clicks_list, btn_ids):
    """
    Afișează modal de confirmare pentru ștergerea unui link (înregistrare completă).
    """
    from dash import ctx
    
    # Verificăm dacă există click-uri
    if not any(n_clicks_list) or not ctx.triggered_id:
        return no_update, no_update, no_update
    
    # Găsim care buton a fost apăsat
    triggered_id = ctx.triggered_id
    token = triggered_id['index']
    
    # Obținem informațiile despre link
    link_data = patient_links.get_patient_link(token, track_view=False)
    
    if not link_data:
        logger.error(f"Nu s-a găsit link-ul {token[:8]}...")
        return no_update, no_update, no_update
    
    # Obținem numărul de înregistrări
    recordings = patient_links.get_patient_recordings(token)
    recordings_count = len(recordings) if recordings else 0
    
    logger.info(f"⚠️ Cerere ștergere LINK complet: {token[:8]}... ({link_data.get('device_name')})")
    
    # Creăm modal-ul de confirmare
    modal_content = html.Div([
        html.Div([
            html.Div([
                html.H3("⚠️ ATENȚIE: Ștergere Înregistrare Completă", style={
                    'color': '#c0392b',
                    'marginBottom': '20px',
                    'textAlign': 'center'
                }),
                html.P([
                    "Sunteți pe cale să ștergeți ",
                    html.Strong("ÎNTREAGA ÎNREGISTRARE", style={'color': '#e74c3c', 'fontSize': '16px'}),
                    " pentru acest pacient!",
                    html.Br(),
                    html.Br(),
                    html.Strong(f"🔧 Aparat: {link_data.get('device_name')}"),
                    html.Br(),
                    html.Strong(f"📅 Data: {link_data.get('recording_date', 'N/A')}"),
                    html.Br(),
                    html.Strong(f"📊 Înregistrări CSV: {recordings_count}"),
                    html.Br(),
                    html.Strong(f"🔗 Token: {token[:12]}...")
                ], style={
                    'fontSize': '14px',
                    'color': '#555',
                    'lineHeight': '1.8',
                    'marginBottom': '30px'
                }),
                html.Div([
                    html.Strong("🚨 ACȚIUNE IREVERSIBILĂ:", style={'color': '#c0392b', 'display': 'block', 'marginBottom': '10px'}),
                    html.Ul([
                        html.Li("Toate fișierele CSV vor fi șterse"),
                        html.Li("Toate imaginile generate vor fi șterse"),
                        html.Li("Toate rapoartele PDF vor fi șterse"),
                        html.Li("Toate notițele medicale vor fi șterse"),
                        html.Li("Link-ul pacientului va deveni INACTIV")
                    ], style={'textAlign': 'left', 'fontSize': '13px'})
                ], style={
                    'padding': '20px',
                    'backgroundColor': '#ffdddd',
                    'border': '3px solid #c0392b',
                    'borderRadius': '8px',
                    'marginBottom': '30px'
                }),
                html.Div([
                    html.P(
                        "Această operație NU poate fi anulată! Dacă nu sunteți 100% sigur, apăsați Anulează.",
                        style={'fontSize': '13px', 'color': '#721c24', 'fontWeight': 'bold', 'marginBottom': '0'}
                    )
                ], style={
                    'padding': '15px',
                    'backgroundColor': '#f8d7da',
                    'border': '1px solid #f5c6cb',
                    'borderRadius': '5px',
                    'marginBottom': '30px'
                }),
                html.Div([
                    html.Button(
                        '🗑️ DA, ȘTERGE TOT',
                        id='confirm-delete-link-btn',
                        style={
                            'padding': '12px 30px',
                            'backgroundColor': '#c0392b',
                            'color': 'white',
                            'border': 'none',
                            'borderRadius': '5px',
                            'cursor': 'pointer',
                            'fontSize': '14px',
                            'fontWeight': 'bold',
                            'marginRight': '15px'
                        }
                    ),
                    html.Button(
                        '✅ Anulează (recomand)',
                        id='cancel-delete-link-btn',
                        style={
                            'padding': '12px 30px',
                            'backgroundColor': '#27ae60',
                            'color': 'white',
                            'border': 'none',
                            'borderRadius': '5px',
                            'cursor': 'pointer',
                            'fontSize': '14px',
                            'fontWeight': 'bold'
                        }
                    )
                ], style={'textAlign': 'center'})
            ], style={
                'backgroundColor': 'white',
                'padding': '40px',
                'borderRadius': '15px',
                'boxShadow': '0 10px 40px rgba(0,0,0,0.3)',
                'maxWidth': '650px',
                'margin': '0 auto'
            })
        ], style={
            'position': 'fixed',
            'top': '0',
            'left': '0',
            'right': '0',
            'bottom': '0',
            'backgroundColor': 'rgba(0,0,0,0.7)',
            'display': 'flex',
            'alignItems': 'center',
            'justifyContent': 'center',
            'zIndex': '10000',
            'padding': '20px'
        })
    ])
    
    # Salvăm informațiile în store pentru ștergere
    delete_data = {
        'type': 'link',  # Pentru a diferenția de ștergerea unei înregistrări
        'token': token,
        'link_data': link_data,
        'recordings_count': recordings_count
    }
    
    return {'display': 'block'}, modal_content, delete_data


@app.callback(
    [Output('delete-confirmation-modal', 'style', allow_duplicate=True),
     Output('admin-refresh-trigger', 'data', allow_duplicate=True),
     Output('global-notification-container', 'children', allow_duplicate=True)],
    [Input('confirm-delete-link-btn', 'n_clicks'),
     Input('cancel-delete-link-btn', 'n_clicks')],
    [State('delete-recording-store', 'data')],
    prevent_initial_call=True
)
def handle_delete_link_confirmation(confirm_clicks, cancel_clicks, delete_data):
    """
    Gestionează confirmarea sau anularea ștergerii unui link complet.
    """
    from dash import ctx
    import time
    
    if not ctx.triggered_id:
        return no_update, no_update, no_update
    
    triggered_id = ctx.triggered_id
    
    # Dacă s-a anulat
    if triggered_id == 'cancel-delete-link-btn':
        logger.info("✅ Ștergere link ANULATĂ de utilizator (decizie înțeleaptă!)")
        return {'display': 'none'}, no_update, no_update
    
    # Dacă s-a confirmat ștergerea
    if triggered_id == 'confirm-delete-link-btn' and delete_data and delete_data.get('type') == 'link':
        token = delete_data.get('token')
        link_data = delete_data.get('link_data', {})
        recordings_count = delete_data.get('recordings_count', 0)
        
        logger.warning(f"🗑️ EXECUTARE ȘTERGERE COMPLETĂ pentru link {token[:8]}... ({link_data.get('device_name')})")
        
        try:
            # Șterge link-ul COMPLET (include toate fișierele)
            success = patient_links.delete_patient_link(token)
            
            if success:
                # Notificare succes
                notification = html.Div([
                    html.Div([
                        html.Strong("✅ Înregistrare ștearsă complet!", style={'display': 'block', 'marginBottom': '10px', 'fontSize': '16px'}),
                        html.P(f"🔧 Aparat: {link_data.get('device_name', 'N/A')}", style={'margin': '5px 0', 'fontSize': '13px'}),
                        html.P(f"📅 Data: {link_data.get('recording_date', 'N/A')}", style={'margin': '5px 0', 'fontSize': '13px'}),
                        html.P(f"📊 {recordings_count} înregistrări CSV șterse", style={'margin': '5px 0', 'fontSize': '13px'}),
                        html.P(f"🔗 Token: {token[:12]}... (INVALID acum)", style={'margin': '5px 0', 'fontSize': '13px', 'color': '#666'})
                    ], style={
                        'padding': '20px',
                        'backgroundColor': '#d4edda',
                        'border': '1px solid #28a745',
                        'borderRadius': '8px',
                        'color': '#155724',
                        'marginBottom': '20px'
                    })
                ])
                
                logger.info(f"✅ Link șters cu succes: {token[:8]}... - Toate datele au fost eliminate")
                
                # Trigger refresh pentru a actualiza lista
                refresh_trigger = int(time.time() * 1000)  # Timestamp în milisecunde
                
                return {'display': 'none'}, refresh_trigger, notification
            else:
                # Eroare la ștergere
                notification = html.Div(
                    "❌ Eroare la ștergerea link-ului. Verificați log-urile pentru detalii.",
                    style={
                        'padding': '20px',
                        'backgroundColor': '#f8d7da',
                        'border': '1px solid #dc3545',
                        'borderRadius': '8px',
                        'color': '#721c24',
                        'marginBottom': '20px'
                    }
                )
                logger.error(f"❌ Eroare la ștergerea link-ului {token[:8]}...")
                return {'display': 'none'}, no_update, notification
                
        except Exception as e:
            logger.error(f"Excepție la ștergerea link-ului: {e}", exc_info=True)
            notification = html.Div(
                f"❌ Eroare: {str(e)}",
                style={
                    'padding': '20px',
                    'backgroundColor': '#f8d7da',
                    'border': '1px solid #dc3545',
                    'borderRadius': '8px',
                    'color': '#721c24',
                    'marginBottom': '20px'
                }
            )
            return {'display': 'none'}, no_update, notification
    
    return no_update, no_update, no_update


logger.info("✅ Modulul callbacks_medical.py încărcat cu succes.")


# ==============================================================================
# callbacks/medical_branding_callbacks.py — logo, footer, ștergeri, finalizare
# ------------------------------------------------------------------------------
# ROL: Branding medic pe pagini, footer, confirmări ștergere înregistrări.
#
# RESPECTĂ: .cursorrules - Privacy by Design, Logging comprehensiv
# ==============================================================================

import base64
import pandas as pd
import os
import pathlib
import time
import dash_uploader as du
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
import batch_session_manager
import config
from auth_ui_components import create_auth_header
import data_service  # [NEW] Serviciu centralizat de date


# ==============================================================================
# CALLBACKS AFIȘARE LOGO & FOOTER PENTRU PACIENȚI
# ==============================================================================

@app.callback(
    [Output('patient-logo-container', 'children'),
     Output('patient-footer-container', 'children')],
    [Input('force-routing-trigger', 'n_intervals')]
)
def display_doctor_branding_for_patient(n_intervals):
    """
    [SOLUȚIA A] Afișează logo-ul și footer-ul medicului pe pagina pacientului.
    Token-ul se citește DIRECT din Flask request.args.
    """
    from flask import request
    import doctor_settings
    
    token = request.args.get('token')
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
    [Input('force-routing-trigger', 'n_intervals')]
)
def display_footer_for_medical_pages(n_intervals):
    """
    [SOLUȚIA A] Afișează footer-ul medicului pe paginile medicale (admin, batch, etc.).
    Se declanșează la încărcarea paginii (trigger din force-routing-trigger Interval).
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


logger.info("✅ Modulul callbacks.medical_branding_callbacks încărcat cu succes.")


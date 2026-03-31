# ==============================================================================
# callbacks/patient_view_callbacks.py — UI pacient, PDF upload, explorare CSV
# ------------------------------------------------------------------------------
# ROL: Callback-uri pentru acces pacient, listă înregistrări, PDF, grafic explorare.
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

# ==============================================================================
# app_layout_new.py (VERSIUNEA 3.0 - WORKFLOW MEDICAL)
# ------------------------------------------------------------------------------
# ROL: Definește layout-ul complet cu suport pentru workflow medical:
#      - Tab Vizualizare Interactivă (păstrat din versiunea anterioară)
#      - Tab Admin (pentru medici: generare link-uri, upload bulk)
#      - Tab Pacient (pentru pacienți: înregistrări + explorare)
#
# RESPECTĂ: .cursorrules - 1 PACIENT = 1 LINK PERSISTENT
# ==============================================================================

from dash import dcc, html
import plotly.graph_objects as go
import config

# --- Layout Function (Dash 3.x Best Practice) ---
# CRITICAL: În Dash 3.x, app.layout poate fi o FUNCȚIE care returnează layout-ul
# Aceasta se execută la FIECARE request, permițând routing dinamic fără callback!

def get_layout():
    """
    Returnează layout-ul corespunzător bazat pe context (medic sau pacient).
    Această funcție se execută la fiecare încărcare pagină.
    """
    from flask import request
    from flask_login import current_user
    from logger_setup import logger
    import patient_links
    
    # Verifică dacă există token în URL
    token = request.args.get('token')
    
    logger.warning(f"[LAYOUT FUNCTION] Called for path: {request.path}, token: {token is not None}")
    
    if token:
        # Validare token pacient
        if patient_links.validate_token(token):
            logger.warning(f"[LAYOUT FUNCTION] Valid patient token → returning patient_layout")
            return patient_layout
        else:
            logger.warning(f"[LAYOUT FUNCTION] Invalid token → returning error")
            return html.Div([
                html.H2("❌ Acces Interzis", style={'color': 'red', 'textAlign': 'center', 'marginTop': '50px'}),
                html.P("Token-ul este invalid sau a expirat. Contactați medicul dumneavoastră.", 
                       style={'textAlign': 'center', 'color': '#666'})
            ], style={'padding': '50px'})
    
    # Fără token → verificăm autentificarea pentru medici
    if current_user.is_authenticated:
        logger.warning(f"[LAYOUT FUNCTION] Authenticated user → returning medical_layout")
        return medical_layout
    else:
        logger.warning(f"[LAYOUT FUNCTION] NOT authenticated → returning login prompt")
        # Import login prompt
        from callbacks_medical import create_login_prompt
        return create_login_prompt()

# Backward compatibility: păstrăm 'layout' pentru import-uri existente
layout = get_layout

# --- Layout pentru MEDICI (cu tab-uri complete) ---
# ACEST LAYOUT VA FI AFIȘAT DOAR DUPĂ AUTENTIFICARE!
medical_layout = html.Div([
    # URL tracking pentru callback-uri (update_auth_header, etc.)
    dcc.Location(id='url', refresh=False),
    
    # Header autentificare (afișat dinamic)
    html.Div(id='auth-header-container'),
    
    # Header aplicație
    html.Div(id='app-logo-container', style={'textAlign': 'center', 'marginBottom': '15px'}),
    html.H1(
        "📊 Platformă Pulsoximetrie",
        id="app-title",
        style={'textAlign': 'center', 'color': '#333', 'marginBottom': '30px'}
    ),
    
    # Tabs principale
    dcc.Tabs(
            id="app-tabs",
            value='tab-admin',
            children=[
                # ==========================================
                # TAB 1: PROCESARE BATCH
                # ==========================================
                dcc.Tab(
                    label="📁 Procesare Batch",
                    value='tab-batch-medical',
                    children=[
                        html.Div(
                            className="tab-content",
                            style={'padding': '30px', 'backgroundColor': '#f5f7fa'},
                            children=[
                                html.H2(
                                    "📁 Procesare Batch CSV + Generare Link-uri", 
                                    style={'color': '#2c3e50', 'marginBottom': '10px'}
                                ),
                                html.P(
                                    "Încărcați mai multe fișiere CSV + PDF simultan din același folder. Link-urile se generează AUTOMAT după procesare.",
                                    style={'color': '#7f8c8d', 'marginBottom': '10px', 'fontSize': '14px'}
                                ),
                                
                                # Info box cu instrucțiuni
                                html.Div([
                                    html.Strong("💡 Cum funcționează:", style={'display': 'block', 'marginBottom': '10px', 'color': '#2980b9'}),
                                    html.Ul([
                                        html.Li("Puneți CSV-uri + PDF-uri în același folder (ex: bach data/)"),
                                        html.Li("PDF-urile cu același device number se asociază automat cu CSV-urile"),
                                        html.Li("Sistemul procesează tot și generează link-uri persistente"),
                                        html.Li("Găsiți rezultatele în tab-ul 'Vizualizare Date'")
                                    ], style={'fontSize': '13px', 'color': '#555', 'lineHeight': '1.8'})
                                ], style={
                                    'padding': '15px',
                                    'backgroundColor': '#e8f4f8',
                                    'borderRadius': '8px',
                                    'border': '1px solid #3498db',
                                    'marginBottom': '25px'
                                }),
                                
                                # Store pentru refresh automat
                                dcc.Store(id='admin-refresh-trigger', data=0),
                                
                                # === SELECTOR MOD PROCESARE ===
                                html.Div([
                                    html.H4("🔧 Selectați modul de lucru:", style={'color': '#2c3e50', 'marginBottom': '15px'}),
                                    dcc.RadioItems(
                                        id='admin-batch-mode-selector',
                                        options=[
                                            {'label': '📁 Mod Local (Folder pe disk)', 'value': 'local'},
                                            {'label': '☁️ Mod Online (Upload fișiere)', 'value': 'upload'}
                                        ],
                                        value='upload',  # Default: upload (pentru internet)
                                        inline=True,
                                        style={'marginBottom': '20px'},
                                        labelStyle={'marginRight': '25px', 'fontSize': '14px', 'fontWeight': 'bold'}
                                    )
                                ], style={'marginBottom': '25px', 'padding': '15px', 'backgroundColor': '#f8f9fa', 'borderRadius': '8px', 'border': '1px solid #ddd'}),
                                
                                # === MOD LOCAL (FOLDER) ===
                                html.Div(
                                    id='admin-batch-local-mode',
                                    children=[
                                        html.Label("📂 Folder intrare (CSV + PDF):", style={'fontWeight': 'bold', 'display': 'block', 'marginBottom': '5px'}),
                                        html.Div([
                                            dcc.Input(
                                                id='admin-batch-input-folder',
                                                type='text',
                                                value='',
                                                placeholder='Ex: bach data SAU de modificat reguli',
                                                style={'width': '100%', 'padding': '12px', 'border': '1px solid #bdc3c7', 'borderRadius': '5px 5px 0 0'}
                                            ),
                                            html.Div([
                                                html.Small("💡 Foldere disponibile: ", style={'fontWeight': 'bold', 'marginRight': '10px'}),
                                                html.Code("bach data", style={'padding': '5px 10px', 'backgroundColor': '#e8f4f8', 'borderRadius': '3px', 'marginRight': '5px', 'fontSize': '12px'}),
                                                html.Code("de modificat reguli", style={'padding': '5px 10px', 'backgroundColor': '#e8f4f8', 'borderRadius': '3px', 'marginRight': '5px', 'fontSize': '12px'}),
                                                html.Code("intrare", style={'padding': '5px 10px', 'backgroundColor': '#e8f4f8', 'borderRadius': '3px', 'fontSize': '12px'})
                                            ], style={'padding': '10px', 'backgroundColor': '#f8f9fa', 'borderRadius': '0 0 5px 5px', 'border': '1px solid #bdc3c7', 'borderTop': 'none'})
                                        ], style={'marginBottom': '15px'})
                                    ],
                                    style={'display': 'none'}  # Ascuns inițial
                                ),
                                
                                # === MOD ONLINE (UPLOAD FIȘIERE) ===
                                html.Div(
                                    id='admin-batch-upload-mode',
                                    children=[
                                        html.Label("📤 Selectați fișiere CSV + PDF:", style={'fontWeight': 'bold', 'display': 'block', 'marginBottom': '10px'}),
                                        dcc.Upload(
                                            id='admin-batch-file-upload',
                                            children=html.Div([
                                                html.I(className='fas fa-cloud-upload-alt', style={'fontSize': '48px', 'color': '#3498db', 'marginBottom': '15px'}),
                                                html.H4('📁 Click sau drag & drop fișiere aici', style={'margin': '0', 'color': '#2c3e50'}),
                                                html.P('Suportă CSV + PDF (multiple fișiere simultan)', style={'margin': '10px 0 0 0', 'color': '#7f8c8d', 'fontSize': '13px'}),
                                                html.Small('💡 Încărcați CSV-uri și PDF-uri împreună pentru asociere automată', style={'color': '#95a5a6', 'fontSize': '12px'})
                                            ], style={
                                                'textAlign': 'center',
                                                'padding': '40px',
                                                'border': '2px dashed #3498db',
                                                'borderRadius': '10px',
                                                'backgroundColor': '#ecf0f1',
                                                'cursor': 'pointer',
                                                'transition': 'all 0.3s ease'
                                            }),
                                            multiple=True,  # Upload multiple fișiere
                                            accept='.csv,.pdf',  # Doar CSV și PDF
                                            style={'marginBottom': '20px'}
                                        ),
                                        
                                        # === LISTĂ FIȘIERE UPLOADATE ===
                                        html.Div(
                                            id='admin-batch-uploaded-files-list',
                                            children=[
                                                html.P("📭 Nu există fișiere încărcate încă.", style={
                                                    'textAlign': 'center',
                                                    'color': '#95a5a6',
                                                    'padding': '20px',
                                                    'backgroundColor': '#f8f9fa',
                                                    'borderRadius': '5px',
                                                    'border': '1px dashed #bdc3c7'
                                                })
                                            ]
                                        ),
                                        
                                        # === BUTON ȘTERGERE TOATE FIȘIERELE ===
                                        html.Button(
                                            '🗑️ Șterge toate fișierele',
                                            id='admin-batch-clear-files-btn',
                                            n_clicks=0,
                                            style={
                                                'padding': '8px 16px',
                                                'marginTop': '10px',
                                                'backgroundColor': '#e74c3c',
                                                'color': 'white',
                                                'border': 'none',
                                                'borderRadius': '5px',
                                                'cursor': 'pointer',
                                                'fontSize': '14px',
                                                'fontWeight': 'bold',
                                                'display': 'none'  # Ascuns inițial (apare doar când există fișiere)
                                            }
                                        )
                                    ],
                                    style={'display': 'block', 'marginBottom': '20px'}  # Vizibil inițial
                                ),
                                
                                # === CONFIGURARE GENERALĂ ===
                                html.Label("📂 Folder ieșire imagini:", style={'fontWeight': 'bold', 'display': 'block', 'marginBottom': '5px'}),
                                dcc.Input(
                                    id='admin-batch-output-folder',
                                    type='text',
                                    value='',
                                    placeholder=f'Implicit: .\\{config.OUTPUT_DIR}',
                                    style={'width': '100%', 'padding': '12px', 'marginBottom': '15px', 'border': '1px solid #bdc3c7', 'borderRadius': '5px'}
                                ),
                                
                                html.Div([
                                    html.Label("⏱️ Durată fereastră (minute):", style={'fontWeight': 'bold', 'marginRight': '10px'}),
                                    dcc.Input(
                                        id='admin-batch-window-minutes',
                                        type='number',
                                        value=config.DEFAULT_WINDOW_MINUTES,
                                        min=1,
                                        max=120,
                                        step=1,
                                        style={'padding': '10px', 'width': '80px', 'border': '1px solid #bdc3c7', 'borderRadius': '5px'}
                                    )
                                ], style={'marginBottom': '20px'}),
                                
                                html.Button(
                                    '🚀 Pornește Procesare Batch + Generare Link-uri',
                                    id='admin-start-batch-button',
                                    n_clicks=0,
                                    style={
                                        'width': '100%',
                                        'padding': '15px',
                                        'fontSize': '16px',
                                        'fontWeight': 'bold',
                                        'backgroundColor': '#27ae60',
                                        'color': 'white',
                                        'border': 'none',
                                        'borderRadius': '5px',
                                        'cursor': 'pointer',
                                        'marginBottom': '15px'
                                    }
                                ),
                                
                                # === BARĂ PROGRES + INDICATOR STATUS ===
                                html.Div(
                                            id='admin-batch-progress-container',
                                            children=[
                                                html.Div([
                                                    html.Span("📊 Progres procesare:", style={'fontWeight': 'bold', 'marginRight': '10px'}),
                                                    html.Span(id='admin-batch-progress-text', children="0 / 0 fișiere", style={'fontSize': '14px', 'color': '#2c3e50'})
                                                ], style={'marginBottom': '10px'}),
                                                
                                                # Bară progres vizuală
                                                html.Div([
                                                    html.Div(
                                                        id='admin-batch-progress-bar',
                                                        style={
                                                            'height': '30px',
                                                            'width': '0%',
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
                                                    )
                                                ], style={
                                                    'width': '100%',
                                                    'height': '30px',
                                                    'backgroundColor': '#ecf0f1',
                                                    'borderRadius': '5px',
                                                    'marginBottom': '10px',
                                                    'overflow': 'hidden'
                                                }),
                                                
                                                # Status detaliat
                                                html.Div(id='admin-batch-status-detail', style={
                                                    'fontSize': '13px',
                                                    'color': '#7f8c8d',
                                                    'padding': '10px',
                                                    'backgroundColor': '#f8f9fa',
                                                    'borderRadius': '5px',
                                                    'border': '1px solid #e0e0e0'
                                                })
                                            ],
                                    style={'display': 'none', 'marginBottom': '20px'}  # Ascuns inițial
                                ),
                                
                                dcc.Loading(
                                    id="admin-batch-loading",
                                    type="default",
                                    children=html.Div(id='admin-batch-result', style={'marginTop': '15px'})
                                ),
                                
                                # === ISTORIC SESIUNI BATCH ===
                                html.Div([
                                    html.H4("📜 Istoric Sesiuni Batch", style={'color': '#2c3e50', 'marginTop': '30px', 'marginBottom': '15px'}),
                                    html.P(
                                        "Ultimele sesiuni de procesare. Reluați sesiunile întrerupte cu un click.",
                                        style={'fontSize': '13px', 'color': '#7f8c8d', 'marginBottom': '15px'}
                                    ),
                                    html.Div(id='admin-batch-sessions-history', children=[
                                        html.P("🔍 Nu există sesiuni batch încă.", style={'textAlign': 'center', 'color': '#95a5a6', 'padding': '20px'})
                                    ])
                                ], style={
                                    'marginTop': '30px',
                                    'padding': '20px',
                                    'backgroundColor': '#f8f9fa',
                                    'borderRadius': '8px',
                                    'border': '1px solid #e0e0e0'
                                }),
                                
                                # === INTERVAL PENTRU REFRESH PROGRES ===
                                dcc.Interval(
                                    id='admin-batch-progress-interval',
                                    interval=1000,  # 1 secundă
                                    n_intervals=0,
                                    disabled=True  # Activat doar când procesare activă
                                ),
                                
                                # === STORE PENTRU FIȘIERE UPLOADATE (AFARĂ din toggle display!) ===
                                # [FIX v2] Schimbat storage_type='session' → 'memory' pentru STABILITATE în Railway
                                # [WHY] Session storage poate avea probleme cu cookies/CORS în production
                                dcc.Store(
                                    id='admin-batch-uploaded-files-store',
                                    storage_type='memory',  # În-memory storage (mai stabil)
                                    data=[]  # Inițializare listă goală
                                ),
                                
                                # === STORE PENTRU SESSION ID ===
                                dcc.Store(id='admin-batch-session-id', data=None),
                                
                                # === INTERVAL PENTRU FORCE ROUTING TRIGGER ===
                                # [SOLUȚIA A] Folosit pentru a declansa callback-uri la încărcare pagină
                                dcc.Interval(
                                    id='force-routing-trigger',
                                    interval=100,  # 100ms - trigger la încărcare
                                    n_intervals=0,
                                    max_intervals=1  # Rulează o singură dată
                                )
                            ]
                        )
                    ],
                ),
                
                # ==========================================
                # TAB 2: SETĂRI DOCTOR (NOU)
                # ==========================================
                dcc.Tab(
                    label="⚙️ Setări",
                    value='tab-settings',
                    children=[
                        html.Div(
                            className="tab-content",
                            style={'padding': '30px', 'backgroundColor': '#f5f7fa'},
                            children=[
                                html.H2(
                                    "⚙️ Setări Personalizare", 
                                    style={'color': '#2c3e50', 'marginBottom': '10px'}
                                ),
                                html.P(
                                    "Personalizați aspectul platformei cu sigla cabinetului și informații footer.",
                                    style={'color': '#7f8c8d', 'marginBottom': '30px', 'fontSize': '14px'}
                                ),
                                
                                # === SECȚIUNE LOGO ===
                                html.Div([
                                    html.H3("🖼️ Sigla Cabinetului", style={'color': '#2980b9', 'marginBottom': '15px'}),
                                    html.P(
                                        "Încărcați sigla cabinetului dumneavoastră. Aceasta va fi aplicată pe grafice, imagini și rapoarte PDF.",
                                        style={'color': '#555', 'fontSize': '13px', 'marginBottom': '15px'}
                                    ),
                                    
                                    # Upload logo
                                    html.Div([
                                        html.Label("📤 Selectați fișier imagine:", style={'fontWeight': 'bold', 'display': 'block', 'marginBottom': '10px'}),
                                        dcc.Upload(
                                            id='settings-logo-upload',
                                            children=html.Div([
                                                html.I(className='fas fa-image', style={'fontSize': '36px', 'color': '#3498db', 'marginBottom': '10px'}),
                                                html.H4('📁 Click sau drag & drop logo aici', style={'margin': '0', 'color': '#2c3e50', 'fontSize': '14px'}),
                                                html.P('Suportă: PNG, JPG, GIF, WebP (Max 5MB)', style={'margin': '5px 0 0 0', 'color': '#7f8c8d', 'fontSize': '12px'})
                                            ], style={
                                                'textAlign': 'center',
                                                'padding': '30px',
                                                'border': '2px dashed #3498db',
                                                'borderRadius': '8px',
                                                'backgroundColor': '#ecf0f1',
                                                'cursor': 'pointer'
                                            }),
                                            accept='.png,.jpg,.jpeg,.gif,.webp',
                                            max_size=5*1024*1024  # 5MB
                                        )
                                    ], style={'marginBottom': '20px'}),
                                    
                                    # Preview logo curent
                                    html.Div(id='settings-logo-preview-container', children=[
                                        html.P("📭 Nu ați încărcat încă un logo.", style={
                                            'textAlign': 'center',
                                            'color': '#95a5a6',
                                            'padding': '20px',
                                            'backgroundColor': '#f8f9fa',
                                            'borderRadius': '5px',
                                            'border': '1px dashed #bdc3c7'
                                        })
                                    ], style={'marginBottom': '20px'}),
                                    
                                    # Opțiuni aplicare logo
                                    html.Div([
                                        html.Label("🎯 Unde să se aplice logo-ul:", style={'fontWeight': 'bold', 'display': 'block', 'marginBottom': '10px'}),
                                        dcc.Checklist(
                                            id='settings-logo-apply-options',
                                            options=[
                                                {'label': ' 🖼️ Pe imaginile generate', 'value': 'images'},
                                                {'label': ' 📄 Pe documentele PDF', 'value': 'pdf'},
                                                {'label': ' 🌐 Pe site (deasupra titlului)', 'value': 'site'}
                                            ],
                                            value=['images', 'pdf', 'site'],
                                            style={'fontSize': '14px'},
                                            labelStyle={'display': 'block', 'marginBottom': '8px'}
                                        )
                                    ], style={'marginBottom': '20px'}),
                                    
                                    # Buton ștergere logo
                                    html.Button(
                                        '🗑️ Șterge Logo',
                                        id='settings-delete-logo-button',
                                        n_clicks=0,
                                        style={
                                            'padding': '10px 20px',
                                            'fontSize': '14px',
                                            'backgroundColor': '#e74c3c',
                                            'color': 'white',
                                            'border': 'none',
                                            'borderRadius': '5px',
                                            'cursor': 'pointer'
                                        }
                                    )
                                    
                                ], style={
                                    'padding': '25px',
                                    'backgroundColor': '#fff',
                                    'borderRadius': '10px',
                                    'boxShadow': '0 2px 8px rgba(0,0,0,0.1)',
                                    'marginBottom': '30px'
                                }),
                                
                                # === SECȚIUNE FOOTER ===
                                html.Div([
                                    html.H3("📝 Informații Footer", style={'color': '#2980b9', 'marginBottom': '15px'}),
                                    html.P(
                                        "Adăugați informații care vor apărea în josul fiecărei pagini (contact, adresă, program, etc.).",
                                        style={'color': '#555', 'fontSize': '13px', 'marginBottom': '15px'}
                                    ),
                                    
                                    html.Label("📄 Text footer:", style={'fontWeight': 'bold', 'display': 'block', 'marginBottom': '5px'}),
                                    html.Small([
                                        "💡 Puteți folosi link-uri: ",
                                        html.Code('<a href="https://exemplu.ro">Text link</a>', style={'backgroundColor': '#e8f4f8', 'padding': '2px 5px', 'borderRadius': '3px', 'fontSize': '11px'}),
                                        html.Br(),
                                        "sau scrieți URL-uri direct (vor deveni automat clickable)"
                                    ], style={'color': '#666', 'fontSize': '11px', 'marginBottom': '8px', 'display': 'block'}),
                                    dcc.Textarea(
                                        id='settings-footer-textarea',
                                        placeholder='Ex: Dr. Popescu Ion | Cabinet Medical | Tel: 0721234567 | Website: https://cabinet-medical.ro | Program: Luni-Vineri 9:00-17:00',
                                        style={
                                            'width': '100%',
                                            'height': '120px',
                                            'padding': '12px',
                                            'fontSize': '13px',
                                            'border': '1px solid #bdc3c7',
                                            'borderRadius': '5px',
                                            'fontFamily': 'Arial, sans-serif',
                                            'resize': 'vertical'
                                        }
                                    ),
                                    
                                    # Preview footer
                                    html.Div([
                                        html.Label("👁️ Preview:", style={'fontWeight': 'bold', 'display': 'block', 'marginBottom': '8px', 'marginTop': '15px'}),
                                        html.Div(
                                            id='settings-footer-preview',
                                            children=[
                                                html.P("Footer-ul va apărea aici după ce scrieți text...", 
                                                      style={'color': '#95a5a6', 'fontStyle': 'italic', 'fontSize': '12px'})
                                            ],
                                            style={
                                                'padding': '15px',
                                                'backgroundColor': '#f8f9fa',
                                                'borderRadius': '8px',
                                                'border': '1px solid #e0e0e0',
                                                'minHeight': '50px',
                                                'textAlign': 'center'
                                            }
                                        )
                                    ]),
                                    
                                    html.Button(
                                        '💾 Salvează Footer',
                                        id='settings-save-footer-button',
                                        n_clicks=0,
                                        style={
                                            'padding': '12px 25px',
                                            'fontSize': '14px',
                                            'fontWeight': 'bold',
                                            'backgroundColor': '#27ae60',
                                            'color': 'white',
                                            'border': 'none',
                                            'borderRadius': '5px',
                                            'cursor': 'pointer',
                                            'marginTop': '15px'
                                        }
                                    )
                                    
                                ], style={
                                    'padding': '25px',
                                    'backgroundColor': '#fff',
                                    'borderRadius': '10px',
                                    'boxShadow': '0 2px 8px rgba(0,0,0,0.1)',
                                    'marginBottom': '30px'
                                }),
                                
                                # === SECȚIUNE ADMINISTRARE UTILIZATORI (DOAR ADMIN) ===
                                html.Div(
                                    id='admin-user-management-section',
                                    children=[
                                        html.H3("👥 Administrare Utilizatori", style={'color': '#e74c3c', 'marginBottom': '15px'}),
                                        html.P(
                                            "Gestionați conturile medicilor. Puteți crea, edita și dezactiva utilizatori.",
                                            style={'color': '#555', 'fontSize': '13px', 'marginBottom': '20px'}
                                        ),
                                        
                                        # Butoane acțiuni
                                        html.Div([
                                            html.Button(
                                                '➕ Creare Utilizator Nou',
                                                id='admin-create-user-button',
                                                n_clicks=0,
                                                style={
                                                    'padding': '12px 25px',
                                                    'fontSize': '14px',
                                                    'fontWeight': 'bold',
                                                    'backgroundColor': '#27ae60',
                                                    'color': 'white',
                                                    'border': 'none',
                                                    'borderRadius': '5px',
                                                    'cursor': 'pointer',
                                                    'marginRight': '10px'
                                                }
                                            ),
                                            html.Button(
                                                '🔄 Reîmprospătează Lista',
                                                id='admin-refresh-users-button',
                                                n_clicks=0,
                                                style={
                                                    'padding': '12px 25px',
                                                    'fontSize': '14px',
                                                    'fontWeight': 'bold',
                                                    'backgroundColor': '#3498db',
                                                    'color': 'white',
                                                    'border': 'none',
                                                    'borderRadius': '5px',
                                                    'cursor': 'pointer'
                                                }
                                            )
                                        ], style={'marginBottom': '25px'}),
                                        
                                        # Container pentru formularul de creare/editare utilizator
                                        html.Div(id='admin-user-form-container', style={'marginBottom': '25px'}),
                                        
                                        # Container pentru lista de utilizatori
                                        dcc.Loading(
                                            id="admin-users-loading",
                                            type="default",
                                            children=html.Div(id='admin-users-list-container')
                                        )
                                    ],
                                    style={
                                        'padding': '25px',
                                        'backgroundColor': '#fff9f9',
                                        'borderRadius': '10px',
                                        'boxShadow': '0 2px 8px rgba(231,76,60,0.15)',
                                        'marginBottom': '30px',
                                        'border': '2px solid #e74c3c'
                                    }
                                ),
                                
                                # Notificare status
                                html.Div(id='settings-status-notification', style={'marginTop': '20px'})
                            ]
                        )
                    ]
                ),
                
                # ==========================================
                # TAB 3: VIZUALIZARE DATE (NOU - CU ACCORDION)
                # ==========================================
                dcc.Tab(
                    label="📊 Vizualizare Date",
                    value='tab-data-view',
                    children=[
                        html.Div(
                            className="tab-content",
                            style={'padding': '30px', 'backgroundColor': '#f5f7fa'},
                            children=[
                                html.Div([
                                    html.H2(
                                        "📊 Înregistrări Pacienți - Vizualizare Detaliată", 
                                        style={'color': '#2c3e50', 'marginBottom': '10px', 'display': 'inline-block', 'marginRight': '20px'}
                                    ),
                                    html.Button(
                                        '🔄 Reîmprospătează',
                                        id='admin-refresh-data-view',
                                        n_clicks=0,
                                        style={
                                            'padding': '10px 20px',
                                            'fontSize': '14px',
                                            'backgroundColor': '#3498db',
                                            'color': 'white',
                                            'border': 'none',
                                            'borderRadius': '5px',
                                            'cursor': 'pointer',
                                            'verticalAlign': 'middle'
                                        }
                                    )
                                ], style={'marginBottom': '20px'}),
                                
                                # === PANOU FILTRARE TEMPORALĂ ===
                                html.Div([
                                    html.H4("📅 Filtrare Cronologică", style={'color': '#2980b9', 'marginBottom': '15px'}),
                                    
                                    # Butoane rapide
                                    html.Div([
                                        html.Label("⚡ Acces Rapid:", style={'fontWeight': 'bold', 'display': 'block', 'marginBottom': '10px', 'color': '#555'}),
                                        html.Div([
                                            html.Button('📅 Azi', id='filter-today', n_clicks=0, 
                                                style={'padding': '8px 15px', 'marginRight': '8px', 'backgroundColor': '#27ae60', 'color': 'white', 'border': 'none', 'borderRadius': '5px', 'cursor': 'pointer', 'fontSize': '13px', 'fontWeight': 'bold'}),
                                            html.Button('⏮️ Ieri', id='filter-yesterday', n_clicks=0,
                                                style={'padding': '8px 15px', 'marginRight': '8px', 'backgroundColor': '#3498db', 'color': 'white', 'border': 'none', 'borderRadius': '5px', 'cursor': 'pointer', 'fontSize': '13px', 'fontWeight': 'bold'}),
                                            html.Button('📆 1 Săptămână', id='filter-week', n_clicks=0,
                                                style={'padding': '8px 15px', 'marginRight': '8px', 'backgroundColor': '#9b59b6', 'color': 'white', 'border': 'none', 'borderRadius': '5px', 'cursor': 'pointer', 'fontSize': '13px', 'fontWeight': 'bold'}),
                                            html.Button('📅 1 Lună', id='filter-month', n_clicks=0,
                                                style={'padding': '8px 15px', 'marginRight': '8px', 'backgroundColor': '#e67e22', 'color': 'white', 'border': 'none', 'borderRadius': '5px', 'cursor': 'pointer', 'fontSize': '13px', 'fontWeight': 'bold'}),
                                            html.Button('🗓️ 1 An', id='filter-year', n_clicks=0,
                                                style={'padding': '8px 15px', 'backgroundColor': '#e74c3c', 'color': 'white', 'border': 'none', 'borderRadius': '5px', 'cursor': 'pointer', 'fontSize': '13px', 'fontWeight': 'bold'}),
                                        ], style={'marginBottom': '20px'})
                                    ]),
                                    
                                    # Calendar pentru selecție interval personalizat
                                    html.Div([
                                        html.Label("🗓️ Interval Personalizat:", style={'fontWeight': 'bold', 'display': 'block', 'marginBottom': '10px', 'color': '#555'}),
                                        html.Div([
                                            html.Div([
                                                html.Label("De la:", style={'fontWeight': 'bold', 'marginBottom': '5px', 'display': 'block', 'fontSize': '13px'}),
                                                dcc.DatePickerSingle(
                                                    id='date-picker-start',
                                                    placeholder='Selectează data început',
                                                    display_format='DD/MM/YYYY',
                                                    first_day_of_week=1,
                                                    style={'marginRight': '15px'}
                                                )
                                            ], style={'display': 'inline-block', 'marginRight': '20px'}),
                                            html.Div([
                                                html.Label("Până la:", style={'fontWeight': 'bold', 'marginBottom': '5px', 'display': 'block', 'fontSize': '13px'}),
                                                dcc.DatePickerSingle(
                                                    id='date-picker-end',
                                                    placeholder='Selectează data sfârșit',
                                                    display_format='DD/MM/YYYY',
                                                    first_day_of_week=1
                                                )
                                            ], style={'display': 'inline-block'}),
                                            html.Button(
                                                '🔍 Filtrează',
                                                id='apply-date-filter',
                                                n_clicks=0,
                                                style={
                                                    'padding': '8px 20px',
                                                    'marginLeft': '20px',
                                                    'backgroundColor': '#2ecc71',
                                                    'color': 'white',
                                                    'border': 'none',
                                                    'borderRadius': '5px',
                                                    'cursor': 'pointer',
                                                    'fontSize': '13px',
                                                    'fontWeight': 'bold',
                                                    'verticalAlign': 'bottom'
                                                }
                                            ),
                                            html.Button(
                                                '❌ Resetare',
                                                id='clear-date-filter',
                                                n_clicks=0,
                                                style={
                                                    'padding': '8px 20px',
                                                    'marginLeft': '10px',
                                                    'backgroundColor': '#95a5a6',
                                                    'color': 'white',
                                                    'border': 'none',
                                                    'borderRadius': '5px',
                                                    'cursor': 'pointer',
                                                    'fontSize': '13px',
                                                    'fontWeight': 'bold',
                                                    'verticalAlign': 'bottom'
                                                }
                                            )
                                        ], style={'marginTop': '10px'})
                                    ]),
                                    
                                    # Grupare/Sortare
                                    html.Div([
                                        html.Hr(style={'margin': '20px 0'}),
                                        html.Label("📊 Grupare:", style={'fontWeight': 'bold', 'display': 'block', 'marginBottom': '10px', 'color': '#555'}),
                                        dcc.RadioItems(
                                            id='date-grouping',
                                            options=[
                                                {'label': '📅 Pe Zile', 'value': 'day'},
                                                {'label': '📆 Pe Săptămâni', 'value': 'week'},
                                                {'label': '🗓️ Pe Luni', 'value': 'month'}
                                            ],
                                            value='day',
                                            inline=True,
                                            labelStyle={'marginRight': '20px', 'fontSize': '13px'}
                                        )
                                    ], style={'marginTop': '15px'})
                                    
                                ], style={
                                    'padding': '20px',
                                    'backgroundColor': '#fff',
                                    'borderRadius': '10px',
                                    'boxShadow': '0 2px 8px rgba(0,0,0,0.1)',
                                    'marginBottom': '25px',
                                    'border': '2px solid #3498db'
                                }),
                                
                                html.P(
                                    "Click pe o linie pentru a vedea detaliile complete: grafic, imagini, PDF și notițe.",
                                    style={'color': '#7f8c8d', 'marginBottom': '20px', 'fontSize': '14px'}
                                ),
                                
                                # Store-uri pentru tracking
                                dcc.Store(id='expanded-row-id', data=None),
                                dcc.Store(id='active-date-filter', data=None),
                                
                                # Container pentru lista de înregistrări
                                dcc.Loading(
                                    id="data-view-loading",
                                    type="default",
                                    children=html.Div(id='data-view-container')
                                )
                            ]
                        )
                    ]
                )
            ]
        ),
    
    # Footer cu informații medicului (afișat pe toate paginile medicului)
    html.Div([
        html.Hr(style={'margin': '50px 0 30px 0', 'borderColor': '#e0e0e0'}),
        
        # Footer personalizat medic (va fi populat dinamic)
        html.Div(id='medical-footer-container', style={'marginBottom': '20px'}),
        
        # Footer standard
        html.P(
            "🔒 Platformă securizată conform GDPR - Date anonimizate by design",
            style={'textAlign': 'center', 'color': '#95a5a6', 'fontSize': '12px', 'marginBottom': '5px'}
        ),
        html.P(
            "© 2025 Platformă Pulsoximetrie - Powered by Python + Dash + Plotly",
            style={'textAlign': 'center', 'color': '#bdc3c7', 'fontSize': '11px'}
        )
    ], style={'marginTop': '60px', 'paddingBottom': '30px'}),
    
    # ===== ELEMENT DUMMY pentru DEBUGGING (MEDICAL LAYOUT) =====
    html.Div(id='dummy-output-for-debug', style={'display': 'none'}),
    
    # DUMMY components pentru pattern-matching callbacks (toggle_images_view)
    # Necesare pentru Dash 3.x pattern-matching cu ALL - trebuie să existe măcar 1 componentă
    html.Div(id={'type': 'images-display-container', 'index': 'dummy-medical'}, style={'display': 'none'}),
    html.Button(id={'type': 'view-grid-btn', 'index': 'dummy-medical'}, style={'display': 'none'}),
    html.Button(id={'type': 'view-list-btn', 'index': 'dummy-medical'}, style={'display': 'none'})
]
)

# --- Layout pentru PACIENȚI (simplificat, fără tab-uri) ---
patient_layout = html.Div([
    # URL tracking pentru callback-uri
    dcc.Location(id='url', refresh=False),
    
    # Logo medicului (deasupra headerului) - va fi populat dinamic
    html.Div(id='patient-logo-container', style={'textAlign': 'center', 'marginBottom': '20px'}),
    
    # Header simplificat
    html.Div([
        html.H1(
            "📊 Rezultate Pulsoximetrie",
            style={'textAlign': 'center', 'color': '#2c3e50', 'marginBottom': '10px'}
        ),
        html.P(
            "Vizualizați datele dumneavoastră",
            style={'textAlign': 'center', 'color': '#7f8c8d', 'marginBottom': '30px', 'fontSize': '16px'}
        )
    ]),
    
    # Container pentru datele pacientului
    html.Div(
        id='patient-data-view',
        style={'padding': '20px'}
    ),
    
    # Grafic interactiv pentru explorare
    html.Div([
        html.H3("📈 Grafic Interactiv", style={'color': '#2980b9', 'marginTop': '30px'}),
        html.P("Folosiți mouse-ul pentru zoom și navigare.", style={'color': '#666', 'fontSize': '14px'}),
        dcc.Loading(
            id="patient-graph-loading",
            type="default",
            children=dcc.Graph(
                id='patient-main-graph',
                figure=go.Figure(),
                style={'height': '600px'}
            )
        )
    ], style={
        'padding': '25px',
        'backgroundColor': '#fff',
        'borderRadius': '10px',
        'boxShadow': '0 2px 8px rgba(0,0,0,0.1)',
        'marginTop': '20px'
    }),
    
    # Footer cu informații
    html.Div([
        html.Hr(style={'margin': '40px 0'}),
        
        # Footer personalizat medic (va fi populat dinamic)
        html.Div(id='patient-footer-container', style={'marginBottom': '20px'}),
        
        # Footer standard
        html.P(
            "🔒 Datele dumneavoastră sunt confidențiale și securizate conform GDPR.",
            style={'textAlign': 'center', 'color': '#95a5a6', 'fontSize': '12px'}
        ),
        html.P(
            "Pentru întrebări, contactați medicul dumneavoastră.",
            style={'textAlign': 'center', 'color': '#95a5a6', 'fontSize': '12px'}
        )
    ], style={'marginTop': '40px'}),
    
    # ===== ELEMENT DUMMY pentru DEBUGGING în CONSOLĂ BROWSER =====
    html.Div(id='dummy-output-for-debug', style={'display': 'none'}),
    
    # DUMMY components pentru pattern-matching callbacks (toggle_images_view)
    html.Div(id={'type': 'images-display-container', 'index': 'dummy-patient'}, style={'display': 'none'}),
    html.Button(id={'type': 'view-grid-btn', 'index': 'dummy-patient'}, style={'display': 'none'}),
    html.Button(id={'type': 'view-list-btn', 'index': 'dummy-patient'}, style={'display': 'none'})
])


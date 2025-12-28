from dash import dcc, html
import config
from debug_system import get_debug_footer

def get_medical_layout():
    return html.Div([
        # URL tracking pentru callback-uri
        dcc.Location(id='url', refresh=False),
        
        # Header autentificare (afișat dinamic)
        html.Div(id='auth-header-container'),
        
        # Header aplicație
        html.Div(id='app-logo-container', className="text-center mb-10"),
        html.H1(
            "📊 Platformă Pulsoximetrie",
            id="app-title",
            className="text-center mb-30",
            style={'color': '#333'} 
        ),
        
        # Tabs principale
        dcc.Tabs(
            id="app-tabs",
            value='tab-admin',
            children=[
                _get_batch_tab(),
                _get_settings_tab(),
                _get_data_view_tab()
            ]
        ),
        
        _get_footer(),

        # [NEW] Debug System Footer (Fixed position)
        get_debug_footer()
    ])

import dash_uploader as du

def _get_batch_tab():
    return dcc.Tab(
        label="📁 Procesare Batch",
        value='tab-batch-medical',
        children=[
            html.Div(
                className="tab-content-container",
                children=[
                    html.H2("📁 Procesare Batch CSV + Generare Link-uri", style={'color': '#2c3e50', 'marginBottom': '10px'}),
                    html.P(
                        "Încărcați mai multe fișiere CSV + PDF simultan din același folder. Link-urile se generează AUTOMAT după procesare.",
                        className="text-muted mb-10 text-small"
                    ),
                    
                    # Info box
                    html.Div([
                        html.Strong("💡 Cum funcționează:", className="d-block mb-10", style={'color': '#2980b9'}),
                        html.Ul([
                            html.Li("Puneți CSV-uri + PDF-uri în același folder (ex: bach data/)"),
                            html.Li("PDF-urile cu același device number se asociază automat cu CSV-urile"),
                            html.Li("Sistemul procesează tot și generează link-uri persistente"),
                            html.Li("Găsiți rezultatele în tab-ul 'Vizualizare Date'")
                        ], style={'fontSize': '13px', 'color': '#555', 'lineHeight': '1.8'})
                    ], className="info-box"),
                    
                    # Store pentru refresh automat
                    dcc.Store(id='admin-refresh-trigger', data=0),
                    
                    # === SELECTOR MOD PROCESARE ===
                    html.Div([
                        html.H4("🔧 Selectați modul de lucru:", style={'color': '#2c3e50', 'marginBottom': '15px'}),
                        dcc.RadioItems(
                            id='admin-batch-mode-selector',
                            options=[
                                {'label': '📁 Mod Local (Folder pe disk)', 'value': 'local'},
                                {'label': '☁️ Mod Online (Streaming Upload)', 'value': 'upload'}
                            ],
                            value='upload',
                            inline=True,
                            className="mb-20",
                            labelStyle={'marginRight': '25px', 'fontSize': '14px', 'fontWeight': 'bold'}
                        )
                    ], className="medical-card", style={'padding': '15px', 'backgroundColor': '#f8f9fa', 'border': '1px solid #ddd'}),
                    
                    # === MOD LOCAL (FOLDER) ===
                    html.Div(
                        id='admin-batch-local-mode',
                        children=[
                            html.Label("📂 Folder intrare (CSV + PDF):", className="font-bold d-block mb-10"),
                            html.Div([
                                dcc.Input(
                                    id='admin-batch-input-folder',
                                    type='text',
                                    value='',
                                    placeholder='Ex: bach data SAU de modificat reguli',
                                    className="form-input",
                                    style={'borderRadius': '5px 5px 0 0'}
                                ),
                                html.Div([
                                    html.Small("💡 Foldere disponibile: ", className="font-bold", style={'marginRight': '10px'}),
                                    html.Code("bach data", style={'padding': '5px 10px', 'backgroundColor': '#e8f4f8', 'borderRadius': '3px', 'marginRight': '5px', 'fontSize': '12px'}),
                                    html.Code("de modificat reguli", style={'padding': '5px 10px', 'backgroundColor': '#e8f4f8', 'borderRadius': '3px', 'marginRight': '5px', 'fontSize': '12px'}),
                                    html.Code("intrare", style={'padding': '5px 10px', 'backgroundColor': '#e8f4f8', 'borderRadius': '3px', 'fontSize': '12px'})
                                ], style={'padding': '10px', 'backgroundColor': '#f8f9fa', 'borderRadius': '0 0 5px 5px', 'border': '1px solid #bdc3c7', 'borderTop': 'none'})
                            ], className="mb-20")
                        ],
                        style={'display': 'none'}
                    ),
                    
                    # === MOD ONLINE (UPLOAD FIȘIERE) ===
                    html.Div(
                        id='admin-batch-upload-mode',
                        style={'display': 'block', 'marginBottom': '20px'},
                        children=[
                            html.Label("📤 Selectați fișiere CSV + PDF (Streaming):", className="font-bold d-block mb-10"),
                            
                            # DASH UPLOADER COMPONENT
                            html.Div([
                                du.Upload(
                                    id='admin-batch-file-upload',
                                    text='Click sau Drop aici (CSV + PDF) - Suportă fișiere mari',
                                    text_completed='Încărcat: ',
                                    pause_button=True,
                                    cancel_button=True,
                                    max_file_size=2000,  # 2GB
                                    max_files=100,      # Allow up to 100 files at once
                                    filetypes=['csv', 'pdf'],
                                    default_style={'minHeight': '150px', 'lineHeight': '150px', 'border': '2px dashed #3498db', 'borderRadius': '10px', 'backgroundColor': '#ecf0f1', 'textAlign': 'center'},
                                )
                            ], style={'marginBottom': '20px'}),
                            
                            # === LISTĂ FIȘIERE UPLOADATE ===
                            dcc.Markdown("Note: Fișierele sunt salvate temporar pe server.", style={'fontSize': '12px', 'color': '#7f8c8d'}),
                            
                            html.Div(
                                id='admin-batch-uploaded-files-list',
                                children=[
                                    html.P("📭 Așteptare fișiere...", className="empty-state")
                                ]
                            ),
                            
                            html.Button(
                                '🗑️ Șterge toate fișierele',
                                id='admin-batch-clear-files-btn',
                                n_clicks=0,
                                className="btn-danger mt-10",
                                style={'display': 'none'}
                            )
                        ]
                    ),
                    
                    # === CONFIGURARE GENERALĂ ===
                    html.Label("📂 Folder ieșire imagini:", className="font-bold d-block mb-10"),
                    dcc.Input(
                        id='admin-batch-output-folder',
                        type='text',
                        value='',
                        placeholder=f'Implicit: .\\{config.OUTPUT_DIR}',
                        className="form-input mb-20"
                    ),
                    
                    html.Div([
                        html.Label("⏱️ Durată fereastră (minute):", className="font-bold", style={'marginRight': '10px'}),
                        dcc.Input(
                            id='admin-batch-window-minutes',
                            type='number',
                            value=config.DEFAULT_WINDOW_MINUTES,
                            min=1,
                            max=120,
                            step=1,
                            style={'padding': '10px', 'width': '80px', 'border': '1px solid #bdc3c7', 'borderRadius': '5px'}
                        )
                    ], className="mb-20"),
                    
                    html.Button(
                        '🚀 Pornește Procesare Batch + Generare Link-uri',
                        id='admin-start-batch-button',
                        n_clicks=0,
                        className="btn-success btn-full-width mb-20"
                    ),
                    
                    # === BARĂ PROGRES ===
                    html.Div(
                        id='admin-batch-progress-container',
                        children=[
                            html.Div([
                                html.Span("📊 Progres procesare:", className="font-bold", style={'marginRight': '10px'}),
                                html.Span(id='admin-batch-progress-text', children="0 / 0 fișiere", style={'fontSize': '14px', 'color': '#2c3e50'})
                            ], className="mb-10"),
                            
                            html.Div([
                                html.Div(
                                    id='admin-batch-progress-bar',
                                    className="progress-bar-fill",
                                    style={'width': '0%'}
                                )
                            ], className="progress-container"),
                            
                            html.Div(id='admin-batch-status-detail', style={
                                'fontSize': '13px',
                                'color': '#7f8c8d',
                                'padding': '10px',
                                'backgroundColor': '#f8f9fa',
                                'borderRadius': '5px',
                                'border': '1px solid #e0e0e0'
                            })
                        ],
                        style={'display': 'none', 'marginBottom': '20px'}
                    ),
                    
                    dcc.Loading(
                        id="admin-batch-loading",
                        type="default",
                        children=html.Div(id='admin-batch-result', style={'marginTop': '15px'})
                    ),
                    
                    # === ISTORIC ===
                    html.Div([
                        html.H4("📜 Istoric Sesiuni Batch", style={'color': '#2c3e50', 'marginTop': '30px', 'marginBottom': '15px'}),
                        html.P(
                            "Ultimele sesiuni de procesare. Reluați sesiunile întrerupte cu un click.",
                            className="text-muted text-small mb-20"
                        ),
                        html.Div(id='admin-batch-sessions-history', children=[
                            html.P("🔍 Nu există sesiuni batch încă.", className="empty-state")
                        ])
                    ], className="medical-card", style={'backgroundColor': '#f8f9fa', 'border': '1px solid #e0e0e0'}),
                    
                    # Interval & Stores
                    dcc.Interval(id='admin-batch-progress-interval', interval=1000, n_intervals=0, disabled=True),
                    dcc.Store(id='admin-batch-uploaded-files-store', storage_type='memory', data=[]),
                    dcc.Store(id='admin-batch-session-id', data=None),
                    dcc.Interval(id='force-routing-trigger', interval=100, n_intervals=0, max_intervals=1)
                ]
            )
        ]
    )


def _get_settings_tab():
    from flask_login import current_user
    
    # === CONDITIONAL ADMIN SECTION ===
    # CRITICAL FIX: Admin section must ALWAYS render placeholder divs for callbacks
    # even when user is not admin, otherwise we get KeyError
    admin_section = html.Div(
        id='admin-user-management-section',
        style={'display': 'none'},  # Hidden by default
        children=[
            # Placeholder divs for callback outputs (required even when hidden)
            html.Div(id='admin-user-form-container'),
            html.Div(id='admin-users-list-container')
        ]
    )
    
    # If user is admin, show full admin UI
    if current_user.is_authenticated and current_user.is_admin:
        admin_section = html.Div(
            id='admin-user-management-section',
            children=[
                html.H3("👥 Administrare Utilizatori", style={'color': '#e74c3c', 'marginBottom': '15px'}),
                html.P("Gestionați conturile medicilor.", className="text-small mb-20", style={'color': '#555'}),
                
                html.Div([
                    html.Button('➕ Creare Utilizator Nou', id='admin-create-user-button', n_clicks=0, className="btn-success", style={'marginRight': '10px'}),
                    html.Button('🔄 Reîmprospătează Lista', id='admin-refresh-users-button', n_clicks=0, className="btn-primary")
                ], className="mb-20"),
                
                html.Div(id='admin-user-form-container', className="mb-20"),
                dcc.Loading(id="admin-users-loading", type="default", children=html.Div(id='admin-users-list-container'))
            ],
            className="medical-card",
            style={'backgroundColor': '#fff9f9', 'border': '2px solid #e74c3c'}
        )
    
    return dcc.Tab(
        label="⚙️ Setări",
        value='tab-settings',
        children=[
            html.Div(
                className="tab-content-container",
                children=[
                    html.H2("⚙️ Setări Personalizare", style={'color': '#2c3e50', 'marginBottom': '10px'}),
                    html.P("Personalizați aspectul platformei cu sigla cabinetului și informații footer.", className="text-muted mb-30 text-small"),
                    
                    # LOGO SECTION
                    html.Div([
                        html.H3("🖼️ Sigla Cabinetului", style={'color': '#2980b9', 'marginBottom': '15px'}),
                        html.P("Încărcați sigla cabinetului dumneavoastră.", className="text-small mb-20", style={'color': '#555'}),
                        
                        html.Div([
                            html.Label("📤 Selectați fișier imagine:", className="font-bold d-block mb-10"),
                            dcc.Upload(
                                id='settings-logo-upload',
                                children=html.Div([
                                    html.I(className='fas fa-image', style={'fontSize': '36px', 'color': '#3498db', 'marginBottom': '10px'}),
                                    html.H4('📁 Click sau drag & drop logo aici', style={'margin': '0', 'color': '#2c3e50', 'fontSize': '14px'}),
                                    html.P('Suportă: PNG, JPG, GIF, WebP (Max 5MB)', style={'margin': '5px 0 0 0', 'color': '#7f8c8d', 'fontSize': '12px'})
                                ], style={
                                    'textAlign': 'center', 'padding': '30px', 'border': '2px dashed #3498db',
                                    'borderRadius': '8px', 'backgroundColor': '#ecf0f1', 'cursor': 'pointer'
                                }),
                                accept='.png,.jpg,.jpeg,.gif,.webp',
                                max_size=5*1024*1024
                            )
                        ], className="mb-20"),
                        
                        html.Div(id='settings-logo-preview-container', children=[
                            html.P("📭 Nu ați încărcat încă un logo.", className="empty-state")
                        ], className="mb-20"),
                        
                        html.Div([
                            html.Label("🎯 Unde să se aplice logo-ul:", className="font-bold d-block mb-10"),
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
                        ], className="mb-20"),
                        
                        html.Button('🗑️ Șterge Logo', id='settings-delete-logo-button', n_clicks=0, className="btn-danger")
                        
                    ], className="medical-card"),
                    
                    # FOOTER SECTION
                    html.Div([
                        html.H3("📝 Informații Footer", style={'color': '#2980b9', 'marginBottom': '15px'}),
                        html.P("Adăugați informații care vor apărea în josul fiecărei pagini.", className="text-small mb-20", style={'color': '#555'}),
                        
                        html.Label("📄 Text footer:", className="font-bold d-block mb-10"),
                        dcc.Textarea(
                            id='settings-footer-textarea',
                            placeholder='Ex: Dr. Popescu Ion | Cabinet Medical...',
                            style={'width': '100%', 'height': '120px', 'padding': '12px', 'fontSize': '13px', 'border': '1px solid #bdc3c7', 'borderRadius': '5px'}
                        ),
                        
                        html.Div([
                            html.Label("👁️ Preview:", className="font-bold d-block mb-10 mt-20"),
                            html.Div(
                                id='settings-footer-preview',
                                children=[html.P("Footer-ul va apărea aici...", style={'color': '#95a5a6', 'fontStyle': 'italic', 'fontSize': '12px'})],
                                style={'padding': '15px', 'backgroundColor': '#f8f9fa', 'border': '1px solid #e0e0e0', 'minHeight': '50px', 'textAlign': 'center'}
                            )
                        ]),
                        
                        html.Button('💾 Salvează Footer', id='settings-save-footer-button', n_clicks=0, className="btn-success mt-20")
                        
                    ], className="medical-card"),
                    
                    # USER MANAGEMENT SECTION (conditional)
                    admin_section,
                    
                    html.Div(id='settings-status-notification', className="mt-20")
                ]
            )
        ]
    )


def _get_data_view_tab():
    return dcc.Tab(
        label="📊 Vizualizare Date",
        value='tab-data-view',
        children=[
            html.Div(
                className="tab-content-container",
                children=[
                    html.Div([
                        html.H2("📊 Înregistrări Pacienți - Vizualizare Detaliată", style={'color': '#2c3e50', 'display': 'inline-block', 'marginRight': '20px'}),
                        html.Button('🔄 Reîmprospătează', id='admin-refresh-data-view', n_clicks=0, className="btn-primary", style={'verticalAlign': 'middle'})
                    ], className="mb-20"),
                    
                    # FILTRARE TEMPORALĂ
                    html.Div([
                        html.H4("📅 Filtrare Cronologică", style={'color': '#2980b9', 'marginBottom': '15px'}),
                        
                        # [NEW] MODE SELECTOR - Data procesării vs Data testului
                        html.Div([
                            html.Label("📅 Filtrare după:", className="font-bold d-block mb-10", style={'color': '#2c3e50'}),
                            dcc.RadioItems(
                                id='date-filter-mode',
                                options=[
                                    {'label': ' 📤 Data Procesării (când a fost încărcat)', 'value': 'upload'},
                                    {'label': ' 🏥 Data Testului (înregistrarea medicală)', 'value': 'recording'}
                                ],
                                value='upload',  # Default: upload date
                                inline=False,
                                labelStyle={'display': 'block', 'marginBottom': '8px', 'fontSize': '13px', 'color': '#555'},
                                style={'marginBottom': '20px', 'padding': '15px', 'backgroundColor': '#f8f9fa', 'borderRadius': '8px', 'border': '1px solid #e0e0e0'}
                            ),
                            html.Small([
                                "💡 ",
                                html.Strong("Sfat: ", style={'color': '#e67e22'}),
                                "Pentru a găsi upload-uri recente alegeți 'Data Procesării'. Pentru teste medicale vechi alegeți 'Data Testului'."
                            ], style={'color': '#7f8c8d', 'display': 'block', 'marginTop': '-10px', 'marginBottom': '20px', 'fontSize': '12px'})
                        ]),
                        
                        html.Div([
                            html.Label("⚡ Acces Rapid:", className="font-bold d-block mb-10", style={'color': '#555'}),
                            html.Div([
                                html.Button('📅 Azi', id='filter-today', className="btn-success", style={'marginRight': '8px', 'padding': '8px 15px'}),
                                html.Button('⏮️ Ieri', id='filter-yesterday', className="btn-primary", style={'marginRight': '8px', 'padding': '8px 15px'}),
                                html.Button('📆 1 Săptămână', id='filter-week', style={'marginRight': '8px', 'backgroundColor': '#9b59b6', 'color': 'white', 'border': 'none', 'padding': '8px 15px', 'borderRadius': '5px'}),
                                html.Button('📅 1 Lună', id='filter-month', style={'marginRight': '8px', 'backgroundColor': '#e67e22', 'color': 'white', 'border': 'none', 'padding': '8px 15px', 'borderRadius': '5px'}),
                                html.Button('🗓️ 1 An', id='filter-year', className="btn-danger", style={'padding': '8px 15px'})
                            ], className="mb-20")
                        ]),
                        
                        html.Div([
                            html.Label("🗓️ Interval Personalizat:", className="font-bold d-block mb-10", style={'color': '#555'}),
                            html.Div([
                                html.Div([html.Label("De la:", className="font-bold d-block text-small mb-10"), dcc.DatePickerSingle(id='date-picker-start', display_format='DD/MM/YYYY', first_day_of_week=1, style={'marginRight': '15px'})], style={'display': 'inline-block', 'marginRight': '20px'}),
                                html.Div([html.Label("Până la:", className="font-bold d-block text-small mb-10"), dcc.DatePickerSingle(id='date-picker-end', display_format='DD/MM/YYYY', first_day_of_week=1)], style={'display': 'inline-block'}),
                                html.Button('🔍 Filtrează', id='apply-date-filter', className="btn-success", style={'marginLeft': '20px', 'verticalAlign': 'bottom'}),
                                html.Button('❌ Resetare', id='clear-date-filter', style={'marginLeft': '10px', 'backgroundColor': '#95a5a6', 'color': 'white', 'border': 'none', 'borderRadius': '5px', 'padding': '12px 25px', 'cursor': 'pointer', 'verticalAlign': 'bottom'})
                            ], className="mt-10")
                        ]),
                        
                        html.Div([
                            html.Hr(style={'margin': '20px 0'}),
                            html.Label("📊 Grupare:", className="font-bold d-block mb-10", style={'color': '#555'}),
                            dcc.RadioItems(
                                id='date-grouping',
                                options=[{'label': '📅 Pe Zile', 'value': 'day'}, {'label': '📆 Pe Săptămâni', 'value': 'week'}, {'label': '🗓️ Pe Luni', 'value': 'month'}],
                                value='day', inline=True, labelStyle={'marginRight': '20px', 'fontSize': '13px'}
                            )
                        ], className="mt-20")
                    ], className="medical-card", style={'border': '2px solid #3498db'}),
                    
                    html.P("Click pe o linie pentru a vedea detaliile complete.", className="text-muted mb-20 text-small"),
                    
                    dcc.Store(id='expanded-row-id', data=None),
                    dcc.Store(id='active-date-filter', data=None),
                    dcc.Store(id='collapsed-groups-store', data=[]),  # Added for accordion state
                    
                    dcc.Loading(id="data-view-loading", type="default", children=html.Div(id='data-view-container'))
                ]
            )
        ]
    )

def _get_footer():
    return html.Div([
        html.Hr(style={'margin': '50px 0 30px 0', 'borderColor': '#e0e0e0'}),
        html.Div(id='medical-footer-container', className="mb-20"),
        html.P("🔒 Platformă securizată conform GDPR - Date anonimizate by design", className="text-center text-muted text-small mb-10"),
        html.P("© 2025 Platformă Pulsoximetrie - Powered by Python + Dash + Plotly", style={'textAlign': 'center', 'color': '#bdc3c7', 'fontSize': '11px'})
    ], style={'marginTop': '60px', 'paddingBottom': '30px'})

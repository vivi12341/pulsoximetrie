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

# --- Layout Principal - Condițional Medic/Pacient ---
layout = html.Div(
    id="main-container",
    style={
        'fontFamily': config.GOLDEN_STYLE['layout']['font']['family'],
        'maxWidth': '1400px',
        'margin': 'auto',
        'padding': '20px'
    },
    children=[
        # Detectare URL pentru token
        dcc.Location(id='url', refresh=False),
        
        # Store-uri pentru date
        dcc.Store(id='loaded-data-store'),
        dcc.Store(id='current-patient-token'),
        dcc.Store(id='url-token-detected'),  # Nou: detectare token din URL
        
        # Container notificări globale
        html.Div(id="global-notification-container"),
        
        # Container dinamic - se populează în funcție de prezența token-ului
        html.Div(id='dynamic-layout-container')
    ]
)

# --- Layout pentru MEDICI (cu tab-uri complete) ---
medical_layout = html.Div([
    # Header
    html.H1(
        "📊 Platformă Pulsoximetrie Medicală",
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
                                    "Încărcați mai multe fișiere CSV simultan. Link-urile se generează AUTOMAT după procesare.",
                                    style={'color': '#7f8c8d', 'marginBottom': '30px', 'fontSize': '14px'}
                                ),
                                
                                # Store pentru refresh automat
                                dcc.Store(id='admin-refresh-trigger', data=0),
                                
                                html.Div([
                                    html.Div([
                                        html.Label("📂 Folder intrare CSV:", style={'fontWeight': 'bold', 'display': 'block', 'marginBottom': '5px'}),
                                        dcc.Input(
                                            id='admin-batch-input-folder',
                                            type='text',
                                            value='',
                                            placeholder='Ex: C:\\DateMedicale\\CSV_Intrare',
                                            style={'width': '100%', 'padding': '12px', 'marginBottom': '15px', 'border': '1px solid #bdc3c7', 'borderRadius': '5px'}
                                        ),
                                        
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
                                        
                                        dcc.Loading(
                                            id="admin-batch-loading",
                                            type="default",
                                            children=html.Div(id='admin-batch-result', style={'marginTop': '15px'})
                                        )
                                    ])
                                ], style={
                                    'padding': '25px', 
                                    'backgroundColor': '#fff', 
                                    'borderRadius': '10px',
                                    'boxShadow': '0 2px 8px rgba(0,0,0,0.1)'
                                })
                            ]
                        )
                    ]
                ),
                
                # ==========================================
                # TAB 2: VIZUALIZARE DATE (NOU - CU ACCORDION)
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
                                ], style={'marginBottom': '10px'}),
                                
                                html.P(
                                    "Click pe o linie pentru a vedea detaliile complete: grafic, imagini, PDF și notițe medicale.",
                                    style={'color': '#7f8c8d', 'marginBottom': '30px', 'fontSize': '14px'}
                                ),
                                
                                # Store pentru tracking expandare
                                dcc.Store(id='expanded-row-id', data=None),
                                
                                # Container pentru lista de înregistrări
                                dcc.Loading(
                                    id="data-view-loading",
                                    type="default",
                                    children=html.Div(id='data-view-container')
                                )
                            ]
                        )
                    ]
                ),
                
                # ==========================================
                # TAB 2: PACIENT
                # ==========================================
                dcc.Tab(
                    label="👤 Pacient",
                    value='tab-patient',
                    children=[
                        html.Div(
                            className="tab-content",
                            style={'padding': '30px'},
                            children=[
                                html.H2("Acces Pacient", style={'color': '#2c3e50'}),
                                
                                # Input Token
                                html.Div([
                                    html.P("Introduceți codul primit de la medic pentru a accesa înregistrările:"),
                                    dcc.Input(
                                        id='patient-token-input',
                                        type='text',
                                        value='',
                                        placeholder='Ex: a8f9d2b1-3c4e-4d5e-8f9a...',
                                        style={'width': '100%', 'padding': '15px', 'fontSize': '16px', 'marginBottom': '20px'}
                                    ),
                                    html.Button(
                                        '🔓 Accesează Înregistrări',
                                        id='patient-access-button',
                                        n_clicks=0,
                                        style={
                                            'padding': '15px 30px',
                                            'fontSize': '16px',
                                            'backgroundColor': '#27ae60',
                                            'color': 'white',
                                            'border': 'none',
                                            'borderRadius': '5px',
                                            'cursor': 'pointer'
                                        }
                                    ),
                                    html.Div(id='patient-access-result', style={'marginTop': '20px'})
                                ], style={'padding': '20px', 'backgroundColor': '#ecf0f1', 'borderRadius': '10px', 'marginBottom': '30px'}),
                                
                                # Conținut pacient (afișat după acces)
                                html.Div(
                                    id='patient-content-container',
                                    style={'display': 'none'},
                                    children=[
                                        # Sub-tabs pentru pacient
                                        dcc.Tabs(
                                            id="patient-sub-tabs",
                                            value='patient-recordings',
                                            children=[
                                                # Sub-tab 1: Înregistrările Mele
                                                dcc.Tab(
                                                    label="📁 Înregistrările Mele",
                                                    value='patient-recordings',
                                                    children=[
                                                        html.Div(
                                                            style={'padding': '20px'},
                                                            children=[
                                                                html.H3("Înregistrările Dumneavoastră Stocate"),
                                                                html.Div(id='patient-recordings-list')
                                                            ]
                                                        )
                                                    ]
                                                ),
                                                
                                                # Sub-tab 2: Explorează CSV
                                                dcc.Tab(
                                                    label="🔍 Explorează CSV",
                                                    value='patient-explore',
                                                    children=[
                                                        html.Div(
                                                            style={'padding': '20px'},
                                                            children=[
                                                                html.H3("Explorare CSV Temporară"),
                                                                html.P("Încărcați un fișier CSV pentru vizualizare temporară (nu se salvează)."),
                                                                
                                                                dcc.Upload(
                                                                    id='patient-explore-upload',
                                                                    children=html.Div([
                                                                        '📁 Trageți CSV aici sau click pentru selectare'
                                                                    ]),
                                                                    style={
                                                                        'width': '100%',
                                                                        'height': '80px',
                                                                        'lineHeight': '80px',
                                                                        'borderWidth': '2px',
                                                                        'borderStyle': 'dashed',
                                                                        'borderRadius': '10px',
                                                                        'textAlign': 'center',
                                                                        'backgroundColor': '#fff3cd',
                                                                        'marginBottom': '20px'
                                                                    },
                                                                    multiple=False
                                                                ),
                                                                
                                                                html.Div(
                                                                    "⚠️ Graficul este temporar și nu va fi salvat.",
                                                                    style={
                                                                        'padding': '10px',
                                                                        'backgroundColor': '#fff3cd',
                                                                        'border': '1px solid #ffc107',
                                                                        'borderRadius': '5px',
                                                                        'marginBottom': '20px'
                                                                    }
                                                                ),
                                                                
                                                                dcc.Loading(
                                                                    id="patient-explore-loading",
                                                                    type="default",
                                                                    children=dcc.Graph(
                                                                        id='patient-explore-graph',
                                                                        figure=go.Figure()
                                                                    )
                                                                )
                                                            ]
                                                        )
                                                    ]
                                                )
                                            ]
                                        )
                                    ]
                                )
                            ]
                        )
                    ]
                ),
                
                # ==========================================
                # TAB 3: VIZUALIZARE INTERACTIVĂ (ORIGINAL)
                # ==========================================
                dcc.Tab(
                    label="📈 Vizualizare Interactivă",
                    value='tab-visualize',
                    children=[
                        html.Div(
                            className="tab-content",
                            style={'padding': '20px'},
                            children=[
                                html.H4("Pas 1: Încărcați un fișier CSV", style={'marginTop': '20px'}),
                                dcc.Upload(
                                    id='upload-data-component',
                                    children=html.Div([
                                        'Trageți și plasați sau ',
                                        html.A('Selectați un fișier CSV')
                                    ]),
                                    style={
                                        'width': '100%', 'height': '60px', 'lineHeight': '60px',
                                        'borderWidth': '1px', 'borderStyle': 'dashed',
                                        'borderRadius': '5px', 'textAlign': 'center', 'margin': '10px 0'
                                    },
                                    multiple=False
                                ),
                                html.Div(id='output-filename-container'),
                                
                                html.Hr(),

                                html.H4("Pas 2: Analizați graficul", style={'marginTop': '20px'}),
                                
                                dcc.Loading(
                                    id="loading-spinner",
                                    type="default",
                                    children=dcc.Graph(
                                        id='interactive-graph',
                                        figure=go.Figure()
                                    )
                                )
                            ]
                        )
                    ]
                ),
                
                # ==========================================
                # TAB 4: PROCESARE ÎN LOT (ORIGINAL)
                # ==========================================
                dcc.Tab(
                    label="🔄 Procesare în Lot (Batch)",
                    value='tab-batch',
                    children=[
                        html.Div(
                            className="tab-content",
                            style={'padding': '20px'},
                            children=[
                                html.H4("Pas 1: Specificați căile folderelor", style={'marginTop': '20px'}),
                                html.P("Introduceți căile complete către folderele de intrare și ieșire."),
                                
                                dcc.Input(
                                    id='input-folder-path',
                                    type='text',
                                    value='',
                                    placeholder='Cale folder intrare (ex: C:\\DateOximetrie\\Intrare)',
                                    style={'width': '100%', 'padding': '10px', 'marginBottom': '10px'}
                                ),
                                dcc.Input(
                                    id='output-folder-path',
                                    type='text',
                                    value='',
                                    placeholder=f'Cale folder ieșire (implicit: .\\{config.OUTPUT_DIR})',
                                    style={'width': '100%', 'padding': '10px', 'marginBottom': '20px'}
                                ),

                                html.H4("Pas 2: Configurați durata ferestrei", style={'marginTop': '20px'}),
                                html.Div(style={'display': 'flex', 'alignItems': 'center'}, children=[
                                    dcc.Input(
                                        id='window-minutes-input',
                                        type='number',
                                        value=config.DEFAULT_WINDOW_MINUTES,
                                        min=1,
                                        max=120,
                                        step=1,
                                        style={'padding': '10px', 'width': '100px'}
                                    ),
                                    html.Span("minute", style={'marginLeft': '10px'})
                                ]),

                                html.Hr(style={'margin': '30px 0'}),

                                html.H4("Pas 3: Porniți procesarea", style={'marginTop': '20px'}),
                                html.Button(
                                    'Pornește Procesarea în Lot',
                                    id='start-batch-button',
                                    n_clicks=0,
                                    style={
                                        'width': '100%', 'padding': '15px', 'fontSize': '18px',
                                        'backgroundColor': '#28a745', 'color': 'white',
                                        'border': 'none', 'borderRadius': '5px', 'cursor': 'pointer'
                                    }
                                ),
                                
                                html.Div(
                                    id='batch-status-container',
                                    style={'marginTop': '20px', 'padding': '15px', 'border': '1px solid #ddd', 'borderRadius': '5px', 'backgroundColor': '#f8f9fa', 'whiteSpace': 'pre-wrap'}
                                )
                            ]
                        )
                    ]
                )
            ]
        )
    ]
)

# --- Layout pentru PACIENȚI (simplificat, fără tab-uri) ---
patient_layout = html.Div([
    # Header simplificat
    html.Div([
        html.H1(
            "📊 Rezultate Pulsoximetrie",
            style={'textAlign': 'center', 'color': '#2c3e50', 'marginBottom': '10px'}
        ),
        html.P(
            "Vizualizați datele dumneavoastră medicale",
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
        html.P(
            "🔒 Datele dumneavoastră sunt confidențiale și securizate conform GDPR.",
            style={'textAlign': 'center', 'color': '#95a5a6', 'fontSize': '12px'}
        ),
        html.P(
            "Pentru întrebări, contactați medicul dumneavoastră.",
            style={'textAlign': 'center', 'color': '#95a5a6', 'fontSize': '12px'}
        )
    ], style={'marginTop': '40px'})
])


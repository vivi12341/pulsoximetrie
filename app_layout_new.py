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

# --- Layout Principal cu 4 Tabs ---
layout = html.Div(
    id="main-container",
    style={
        'fontFamily': config.GOLDEN_STYLE['layout']['font']['family'],
        'maxWidth': '1400px',
        'margin': 'auto',
        'padding': '20px'
    },
    children=[
        # Header
        html.H1(
            "📊 Platformă Pulsoximetrie Medicală",
            id="app-title",
            style={'textAlign': 'center', 'color': '#333', 'marginBottom': '30px'}
        ),

        # Container notificări globale
        html.Div(id="global-notification-container"),

        # Store-uri pentru date
        dcc.Store(id='loaded-data-store'),
        dcc.Store(id='current-patient-token'),

        # Tabs principale
        dcc.Tabs(
            id="app-tabs",
            value='tab-admin',
            children=[
                # ==========================================
                # TAB 1: ADMIN (PENTRU MEDICI)
                # ==========================================
                dcc.Tab(
                    label="👨‍⚕️ Admin (Medic)",
                    value='tab-admin',
                    children=[
                        html.Div(
                            className="tab-content",
                            style={'padding': '30px'},
                            children=[
                                html.H2("Panou Admin - Gestionare Pacienți", style={'color': '#2c3e50'}),
                                
                                # Secțiune 1: Creare Link Nou
                                html.Div([
                                    html.H3("🔗 Creare Link Nou Pacient", style={'marginTop': '30px'}),
                                    html.P("Generați un link persistent pentru un pacient nou."),
                                    
                                    html.Label("Nume Aparat:", style={'fontWeight': 'bold'}),
                                    dcc.Input(
                                        id='admin-device-name-input',
                                        type='text',
                                        value='',
                                        placeholder='Ex: Checkme O2 #3539',
                                        style={'width': '100%', 'padding': '10px', 'marginBottom': '10px'}
                                    ),
                                    
                                    html.Label("Notițe Medicale (opțional):", style={'fontWeight': 'bold'}),
                                    dcc.Textarea(
                                        id='admin-notes-input',
                                        value='',
                                        placeholder='Ex: Apnee severă, follow-up săptămânal',
                                        style={'width': '100%', 'padding': '10px', 'marginBottom': '20px', 'minHeight': '80px'}
                                    ),
                                    
                                    html.Button(
                                        '🔗 Generează Link Nou',
                                        id='admin-create-link-button',
                                        n_clicks=0,
                                        style={
                                            'padding': '15px 30px',
                                            'fontSize': '16px',
                                            'backgroundColor': '#3498db',
                                            'color': 'white',
                                            'border': 'none',
                                            'borderRadius': '5px',
                                            'cursor': 'pointer'
                                        }
                                    ),
                                    
                                    html.Div(id='admin-link-creation-result', style={'marginTop': '20px'})
                                ], style={'marginBottom': '40px', 'padding': '20px', 'backgroundColor': '#ecf0f1', 'borderRadius': '10px'}),
                                
                                html.Hr(),
                                
                                # Secțiune 2: Upload CSV pentru Pacient Existent
                                html.Div([
                                    html.H3("📤 Upload CSV pentru Pacient", style={'marginTop': '30px'}),
                                    html.P("Încărcați un fișier CSV pentru un pacient existent."),
                                    
                                    html.Label("Selectați Pacient:", style={'fontWeight': 'bold'}),
                                    dcc.Dropdown(
                                        id='admin-patient-selector',
                                        options=[],
                                        placeholder='Selectați un pacient din listă...',
                                        style={'marginBottom': '20px'}
                                    ),
                                    
                                    dcc.Upload(
                                        id='admin-upload-csv',
                                        children=html.Div([
                                            '📁 Trageți și plasați CSV aici sau ',
                                            html.A('click pentru selectare')
                                        ]),
                                        style={
                                            'width': '100%',
                                            'height': '80px',
                                            'lineHeight': '80px',
                                            'borderWidth': '2px',
                                            'borderStyle': 'dashed',
                                            'borderRadius': '10px',
                                            'textAlign': 'center',
                                            'backgroundColor': '#f8f9fa'
                                        },
                                        multiple=False
                                    ),
                                    
                                    html.Div(id='admin-upload-result', style={'marginTop': '20px'})
                                ], style={'marginBottom': '40px', 'padding': '20px', 'backgroundColor': '#e8f5e9', 'borderRadius': '10px'}),
                                
                                html.Hr(),
                                
                                # Secțiune 3: Listă Pacienți Activi
                                html.Div([
                                    html.H3("👥 Pacienți Activi", style={'marginTop': '30px'}),
                                    html.Button(
                                        '🔄 Reîmprospătează Listă',
                                        id='admin-refresh-button',
                                        n_clicks=0,
                                        style={
                                            'padding': '10px 20px',
                                            'marginBottom': '20px',
                                            'backgroundColor': '#95a5a6',
                                            'color': 'white',
                                            'border': 'none',
                                            'borderRadius': '5px',
                                            'cursor': 'pointer'
                                        }
                                    ),
                                    html.Div(id='admin-patients-list')
                                ])
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


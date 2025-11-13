# ==============================================================================
# app_layout.py (VERSIUNEA 2.1 - FIX WARNING-URI CONSOLĂ)
# ------------------------------------------------------------------------------
# ROL: Definește structura vizuală (layout-ul) completă a aplicației Dash.
#
# MODIFICĂRI CHEIE (v2.1):
#  - [FIX] Plotly warning: Inițializare grafic cu go.Figure() valid (nu dict gol)
#  - [FIX] React warning: Input-uri controlled de la început (value='')
#  - [WHY] Elimină warning-uri din consolă pentru profesionalism și debugging curat
#
# MODIFICĂRI ANTERIOARE (v2.0):
#  - ÎMBUNĂTĂȚIT: S-a adăugat o componentă `dcc.Loading` în jurul graficului
#    interactiv. Acum, un indicator vizual de încărcare ("spinner") este
#    afișat automat în timpul procesării fișierelor, îmbunătățind
#    experiența utilizatorului.
# ==============================================================================

from dash import dcc, html
import plotly.graph_objects as go
import config

# --- Definirea Layout-ului Principal ---
layout = html.Div(
    id="main-container",
    style={'fontFamily': config.GOLDEN_STYLE['layout']['font']['family'], 'maxWidth': '1280px', 'margin': 'auto'},
    children=[
        
        html.H1(
            "Analizator Pulsoximetrie Nocturnă",
            id="app-title",
            style={'textAlign': 'center', 'color': '#333'}
        ),

        html.Div(id="global-notification-container"),

        dcc.Store(id='loaded-data-store'),

        dcc.Tabs(
            id="app-tabs",
            value='tab-visualize',
            children=[
                dcc.Tab(
                    label="Vizualizare Interactivă",
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
                                
                                # --- MODIFICAREA CHEIE AICI ---
                                # Am învelit graficul în dcc.Loading pentru a oferi feedback vizual
                                # [FIX v2.1] Folosim go.Figure() valid pentru a preveni warning Plotly
                                dcc.Loading(
                                    id="loading-spinner",
                                    type="default", # Puteți alege "graph", "cube", "circle", "dot"
                                    children=dcc.Graph(
                                        id='interactive-graph',
                                        figure=go.Figure()  # [FIX] Figură Plotly validă goală (nu dict)
                                    )
                                )
                            ]
                        )
                    ]
                ),

                dcc.Tab(
                    label="Procesare în Lot (Batch)",
                    value='tab-batch',
                    children=[
                        html.Div(
                            className="tab-content",
                            style={'padding': '20px'},
                            children=[
                                html.H4("Pas 1: Specificați căile folderelor", style={'marginTop': '20px'}),
                                html.P("Introduceți căile complete către folderele de intrare și ieșire."),
                                
                                # [FIX v2.1] Adăugat value='' pentru controlled inputs (previne React warning)
                                # [WHY] React recomandă ca toate input-urile să fie controlled de la început
                                dcc.Input(
                                    id='input-folder-path',
                                    type='text',
                                    value='',  # [FIX] Controlled input de la început
                                    placeholder='Cale folder intrare (ex: C:\\DatePulsoximetrie\\Intrare)',
                                    style={'width': '100%', 'padding': '10px', 'marginBottom': '10px'}
                                ),
                                dcc.Input(
                                    id='output-folder-path',
                                    type='text',
                                    value='',  # [FIX] Controlled input de la început
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
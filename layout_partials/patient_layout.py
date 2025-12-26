from dash import dcc, html
import plotly.graph_objects as go

def get_patient_layout():
    return html.Div([
        dcc.Location(id='url', refresh=False),
        
        # [CRITICAL FIX] Trigger pentru încărcarea automată a datelor pacientului
        # Fără această componentă, callback-ul load_patient_data_from_token() nu se declanșează
        # Pattern identic cu cel din medical_layout.py:L229
        dcc.Interval(id='force-routing-trigger', interval=100, n_intervals=0, max_intervals=1),
        
        html.Div(id='patient-logo-container', className="text-center mb-20"),
        
        # Header simplificat
        html.Div([
            html.H1("📊 Rezultate Pulsoximetrie", className="text-center mb-10", style={'color': '#2c3e50'}),
            html.P("Vizualizați datele dumneavoastră rapid și simplu", className="text-center text-muted mb-30", style={'fontSize': '16px'})
        ]),
        
        # Container pentru datele pacientului
        html.Div(id='patient-data-view', style={'padding': '20px'}),
        
        # Grafic interactiv
        html.Div([
            html.H3("📈 Grafic Interactiv", style={'color': '#2980b9', 'marginTop': '10px'}),
            html.P("Folosiți mouse-ul pentru zoom și navigare.", className="text-muted text-small"),
            dcc.Loading(
                id="patient-graph-loading",
                type="default",
                children=dcc.Graph(
                    id='patient-main-graph',
                    figure=go.Figure(),
                    style={'height': '600px'}
                )
            )
        ], className="medical-card", style={'marginTop': '20px'}),
        
        # Footer
        html.Div([
            html.Hr(style={'margin': '40px 0'}),
            html.Div(id='patient-footer-container', className="mb-20"),
            html.P("🔒 Datele dumneavoastră sunt confidențiale și securizate conform GDPR.", className="text-center text-muted text-small"),
            html.P("Pentru întrebări, contactați medicul dumneavoastră.", className="text-center text-muted text-small")
        ], style={'marginTop': '40px'}),
        
        html.Div(id='dummy-output-for-debug', style={'display': 'none'})
    ])

def get_error_layout():
    """
    Layout pentru erori (Token invalid) - Design empatic (Psiholog)
    """
    return html.Div([
        html.Div([
            html.H2("😕 Nu am găsit fișa dumneavoastră", className="error-title"),
            html.P([
                "Se pare că link-ul folosit a expirat sau este incomplet. ",
                html.Br(),
                "Vă rugăm să solicitați un link nou medicului dumneavoastră."
            ], className="error-message"),
            html.Div([
                html.I(className="fas fa-user-md", style={'fontSize': '48px', 'color': '#3498db', 'marginTop': '20px'})
            ])
        ], className="error-page-container")
    ], style={'backgroundColor': '#f5f7fa', 'minHeight': '100vh', 'padding': '20px'})

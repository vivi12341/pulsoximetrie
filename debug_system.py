import logging
import collections
from dash import html, dcc, Output, Input, State, callback, clientside_callback, no_update

# ==============================================================================
# CONFIG & STATE
# ==============================================================================

MAX_LOGS = 2000

class MemoryLogHandler(logging.Handler):
    """
    Un handler de logging custom care păstrează ultimele N mesaje în memorie.
    """
    def __init__(self, maxlen=MAX_LOGS):
        super().__init__()
        self.logs = collections.deque(maxlen=maxlen)
        # Format similar cu cel din fișier, dar poate fi simplificat pentru UI
        self.formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - [%(module)s] - %(message)s',
            datefmt='%H:%M:%S'
        )

    def emit(self, record):
        try:
            msg = self.format(record)
            self.logs.append(msg)
        except Exception:
            self.handleError(record)

    def get_logs_text(self):
        """Returnează toate log-urile ca un singur string."""
        return "\n".join(self.logs)

# Instanța globală (Singleton)
memory_handler = MemoryLogHandler()
memory_handler.setLevel(logging.INFO) # Capturăm INFO și mai sus

# ==============================================================================
# UI COMPONENTS
# ==============================================================================

def get_debug_footer():
    """
    Returnează componenta UI pentru subsolul de debug.
    """
    return html.Div(
        id='debug-system-container',
        style={
            'position': 'fixed',
            'bottom': '0',
            'left': '0',
            'width': '100%',
            'zIndex': '9999',
            'fontFamily': 'monospace',
            'backgroundColor': '#2c3e50', # Dark slate blue
            'color': '#ecf0f1',
            'borderTop': '3px solid #e74c3c'
        },
        children=[
            # Header Bar (Always Visible)
            html.Div(
                id='debug-header-bar',
                style={
                    'padding': '5px 15px',
                    'display': 'flex',
                    'justifyContent': 'space-between',
                    'alignItems': 'center',
                    'cursor': 'pointer',
                    'userSelect': 'none',
                    'backgroundColor': '#34495e'
                },
                children=[
                    html.Div([
                        html.Span("🐞 SYSTEM DEBUG CONSOLE", style={'fontWeight': 'bold', 'color': '#f1c40f'}),
                        html.Span(" | ", style={'margin': '0 10px', 'color': '#7f8c8d'}),
                        html.Span(id='debug-status-indicator', children="Waiting...", style={'fontSize': '12px', 'color': '#2ecc71'})
                    ]),
                    html.Div([
                        html.Button("📋 COPY LOGS", id='debug-copy-btn', n_clicks=0, style={
                            'backgroundColor': '#2980b9', 'color': 'white', 'border': 'none',
                            'padding': '2px 10px', 'borderRadius': '3px', 'marginRight': '10px',
                            'cursor': 'pointer', 'fontSize': '11px', 'fontWeight': 'bold'
                        }),
                         html.Button("❌ CLEAR", id='debug-clear-btn', n_clicks=0, style={
                            'backgroundColor': '#c0392b', 'color': 'white', 'border': 'none',
                            'padding': '2px 10px', 'borderRadius': '3px', 'marginRight': '10px',
                            'cursor': 'pointer', 'fontSize': '11px', 'fontWeight': 'bold'
                        }),
                        html.Button("🔼/🔽 TOGGLE", id='debug-toggle-btn', n_clicks=0, style={
                            'backgroundColor': 'transparent', 'color': '#bdc3c7', 'border': '1px solid #7f8c8d',
                            'padding': '2px 10px', 'borderRadius': '3px',
                            'cursor': 'pointer', 'fontSize': '11px'
                        }),
                    ])
                ]
            ),
            
            # Log Body (Collapsible)
            html.Div(
                id='debug-body-collapsible',
                style={'display': 'none'}, # Hidden by default
                children=[
                    dcc.Textarea(
                        id='debug-log-display',
                        value="Loading logs...",
                        readOnly=True,
                        style={
                            'width': '100%',
                            'height': '300px',
                            'backgroundColor': '#1e272e', # Very dark
                            'color': '#2ecc71', # Terminal green
                            'border': 'none',
                            'resize': 'vertical',
                            'padding': '10px',
                            'fontSize': '12px',
                            'outline': 'none',
                            'whiteSpace': 'pre'
                        }
                    )
                ]
            ),
            
            # Hidden Components for Logic
            dcc.Interval(id='debug-refresh-interval', interval=2000, n_intervals=0, disabled=False), # Poll every 2s
            dcc.Store(id='debug-is-open-store', data=False), # Persist open/closed state
            dcc.Clipboard(id='debug-clipboard', target_id='debug-log-display')
        ]
    )


# ==============================================================================
# CALLBACKS REGISTRATION
# ==============================================================================

def register_debug_callbacks(app):
    
    # 1. Toggle Visibility (Minimize/Maximize)
    @app.callback(
        [Output('debug-body-collapsible', 'style'),
         Output('debug-is-open-store', 'data'),
         Output('debug-refresh-interval', 'disabled')],
        [Input('debug-toggle-btn', 'n_clicks'),
         Input('debug-header-bar', 'n_clicks')], # Allow clicking anywhere on header
        [State('debug-is-open-store', 'data')],
        prevent_initial_call=True
    )
    def toggle_debug_panel(n1, n2, is_open):
        new_state = not is_open
        
        if new_state:
            # Open
            return {'display': 'block'}, True, False # Enable interval when open
        else:
            # Closed
            return {'display': 'none'}, False, True # Disable interval when closed to save resources

    # 2. Update Logs (Polling)
    @app.callback(
        [Output('debug-log-display', 'value'),
         Output('debug-status-indicator', 'children')],
        [Input('debug-refresh-interval', 'n_intervals')],
        prevent_initial_call=False
    )
    def update_logs(n):
        logs = memory_handler.get_logs_text()
        count = len(memory_handler.logs)
        status = f"Active | {count} records | Last update: {n}"
        return logs, status

    # 3. Clear Logs
    @app.callback(
        Output('debug-log-display', 'value', allow_duplicate=True),
        [Input('debug-clear-btn', 'n_clicks')],
        prevent_initial_call=True
    )
    def clear_logs(n):
        memory_handler.logs.clear()
        return "Logs cleared."

    # 4. Copy to Clipboard (Server-side trigger logic handled by dcc.Clipboard, UI feedback custom)
    # dcc.Clipboard handles the copying natively from the target_id.
    # We just explicitly hooked it in the layout.
    
    # Optional: Client-side feedback for copy
    app.clientside_callback(
        """
        function(n_clicks) {
            if (n_clicks > 0) {
                alert('Logs copied to clipboard!');
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output('debug-copy-btn', 'children'), # Dummy output
        Input('debug-copy-btn', 'n_clicks'),
        prevent_initial_call=True
    )


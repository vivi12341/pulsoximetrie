import logging
import collections
import threading
from dash import html, dcc, Output, Input, State, callback, clientside_callback, no_update

logger = logging.getLogger(__name__)

MAX_LOGS = 300


class MemoryLogHandler(logging.Handler):
    """
    Handler care păstrează ultimele N mesaje în memorie (thread-safe).
    """
    def __init__(self, maxlen=MAX_LOGS):
        super().__init__()
        self.logs = collections.deque(maxlen=maxlen)
        self.lock = threading.RLock()

        self.formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - [%(module)s] - %(message)s',
            datefmt='%H:%M:%S'
        )

    def emit(self, record):
        try:
            msg = self.format(record)
            if len(msg) > 1000:
                msg = msg[:1000] + " ... [TRUNCATED]"

            with self.lock:
                self.logs.append(msg)
        except Exception:
            self.handleError(record)

    def get_logs_text(self):
        with self.lock:
            return "\n".join(list(self.logs))


memory_handler = MemoryLogHandler()
memory_handler.setLevel(logging.INFO)


def get_debug_footer():
    """Returnează componenta UI pentru subsolul de debug."""
    return html.Div(
        id='debug-system-container',
        style={
            'position': 'fixed',
            'bottom': '0',
            'left': '0',
            'width': '100%',
            'zIndex': '9999',
            'fontFamily': 'monospace',
            'backgroundColor': '#2c3e50',
            'color': '#ecf0f1',
            'borderTop': '3px solid #e74c3c'
        },
        children=[
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
            html.Div(
                id='debug-body-collapsible',
                style={'display': 'none'},
                children=[
                    dcc.Textarea(
                        id='debug-log-display',
                        value="Loading logs...",
                        readOnly=True,
                        style={
                            'width': '100%',
                            'height': '300px',
                            'backgroundColor': '#1e272e',
                            'color': '#2ecc71',
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
            dcc.Interval(id='debug-refresh-interval', interval=2000, n_intervals=0, disabled=True),
            dcc.Store(id='debug-is-open-store', data=False),
            dcc.Clipboard(id='debug-clipboard', target_id='debug-log-display')
        ]
    )


def register_debug_callbacks(app):

    @app.callback(
        [Output('debug-body-collapsible', 'style'),
         Output('debug-is-open-store', 'data'),
         Output('debug-refresh-interval', 'disabled')],
        [Input('debug-toggle-btn', 'n_clicks'),
         Input('debug-header-bar', 'n_clicks')],
        [State('debug-is-open-store', 'data')],
        prevent_initial_call=True
    )
    def toggle_debug_panel(n1, n2, is_open):
        new_state = not is_open

        if new_state:
            return {'display': 'block'}, True, True
        else:
            return {'display': 'none'}, False, True

    @app.callback(
        [Output('debug-log-display', 'value'),
         Output('debug-status-indicator', 'children')],
        [Input('debug-refresh-interval', 'n_intervals')],
        prevent_initial_call=False
    )
    def update_logs(n):
        try:
            logs = memory_handler.get_logs_text()
            with memory_handler.lock:
                count = len(memory_handler.logs)
            status = f"Active | {count} records | Last update: {n}"
            return logs, status
        except Exception as e:
            logger.error(f"Debug System Error: {e}")
            return f"Error fetching logs: {str(e)}", "Error"

    @app.callback(
        Output('debug-log-display', 'value', allow_duplicate=True),
        [Input('debug-clear-btn', 'n_clicks')],
        prevent_initial_call=True
    )
    def clear_logs(n):
        memory_handler.logs.clear()
        return "Logs cleared."

    app.clientside_callback(
        """
        function(n_clicks) {
            if (n_clicks > 0) {
                alert('Logs copied to clipboard!');
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output('debug-copy-btn', 'children'),
        Input('debug-copy-btn', 'n_clicks'),
        prevent_initial_call=True
    )

# ==============================================================================
# auth/decorators.py
# ------------------------------------------------------------------------------
# ROL: Decoratori pentru protejarea callback-urilor Dash cu autentificare:
#      - @login_required - necesită autentificare
#      - @admin_required - necesită rol admin
#
# RESPECTĂ: .cursorrules - Logging comprehensiv
# ==============================================================================

from functools import wraps
from flask_login import current_user
from dash import no_update, html
from logger_setup import logger


# ==============================================================================
# DECORATORI AUTENTIFICARE
# ==============================================================================

def login_required(f):
    """
    Decorator pentru callback-uri Dash care necesită autentificare.
    
    UTILIZARE:
    ```python
    @app.callback(...)
    @login_required
    def my_callback(...):
        ...
    ```
    
    Dacă utilizatorul NU este autentificat, returnează un mesaj de eroare
    în loc să execute callback-ul.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            logger.warning("⚠️ Callback accesat fără autentificare - redirect la login")
            
            # Returnăm un mesaj de eroare vizibil în UI
            return html.Div([
                html.H3("🔒 Acces Interzis", style={'color': '#e74c3c', 'textAlign': 'center'}),
                html.P(
                    "Trebuie să te autentifici pentru a accesa această funcționalitate.",
                    style={'textAlign': 'center', 'color': '#666'}
                ),
                html.Div([
                    html.A(
                        "🔐 Autentifică-te",
                        href='/login',
                        style={
                            'display': 'inline-block',
                            'padding': '10px 20px',
                            'background': '#3498db',
                            'color': 'white',
                            'textDecoration': 'none',
                            'borderRadius': '5px',
                            'marginTop': '20px'
                        }
                    )
                ], style={'textAlign': 'center'})
            ], style={
                'padding': '50px',
                'maxWidth': '600px',
                'margin': '0 auto',
                'background': '#f9f9f9',
                'borderRadius': '10px',
                'border': '2px solid #e74c3c'
            })
        
        # Utilizatorul este autentificat - executăm callback-ul normal
        return f(*args, **kwargs)
    
    return decorated_function


def admin_required(f):
    """
    Decorator pentru callback-uri Dash care necesită rol de admin.
    
    UTILIZARE:
    ```python
    @app.callback(...)
    @admin_required
    def admin_callback(...):
        ...
    ```
    
    Verifică:
    1. Utilizatorul este autentificat
    2. Utilizatorul are rol admin (is_admin=True)
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            logger.warning("⚠️ Callback admin accesat fără autentificare")
            
            return html.Div([
                html.H3("🔒 Acces Interzis", style={'color': '#e74c3c', 'textAlign': 'center'}),
                html.P(
                    "Trebuie să te autentifici pentru a accesa această funcționalitate.",
                    style={'textAlign': 'center', 'color': '#666'}
                ),
                html.Div([
                    html.A(
                        "🔐 Autentifică-te",
                        href='/login',
                        style={
                            'display': 'inline-block',
                            'padding': '10px 20px',
                            'background': '#3498db',
                            'color': 'white',
                            'textDecoration': 'none',
                            'borderRadius': '5px',
                            'marginTop': '20px'
                        }
                    )
                ], style={'textAlign': 'center'})
            ], style={
                'padding': '50px',
                'maxWidth': '600px',
                'margin': '0 auto',
                'background': '#f9f9f9',
                'borderRadius': '10px',
                'border': '2px solid #e74c3c'
            })
        
        if not current_user.is_admin:
            logger.warning(f"⚠️ Callback admin accesat de utilizator non-admin: {current_user.email}")
            
            return html.Div([
                html.H3("🚫 Acces Interzis", style={'color': '#e74c3c', 'textAlign': 'center'}),
                html.P(
                    "Nu ai permisiuni de administrator pentru această funcționalitate.",
                    style={'textAlign': 'center', 'color': '#666'}
                ),
                html.P(
                    "Contactează administratorul platformei dacă ai nevoie de acces.",
                    style={'textAlign': 'center', 'color': '#999', 'fontSize': '14px'}
                )
            ], style={
                'padding': '50px',
                'maxWidth': '600px',
                'margin': '0 auto',
                'background': '#f9f9f9',
                'borderRadius': '10px',
                'border': '2px solid #e74c3c'
            })
        
        # Utilizatorul este admin - executăm callback-ul normal
        return f(*args, **kwargs)
    
    return decorated_function


def optional_auth(f):
    """
    Decorator pentru callback-uri care pot funcționa cu SAU fără autentificare.
    
    UTILIZARE:
    ```python
    @app.callback(...)
    @optional_auth
    def my_callback(...):
        # Verificăm manual în callback dacă current_user.is_authenticated
        if current_user.is_authenticated:
            # Logică pentru utilizatori autentificați
        else:
            # Logică pentru vizitatori anonimi
    ```
    
    Callback-ul primește informația despre autentificare dar nu forțează login.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Nu facem nicio verificare - doar executăm callback-ul
        # (utilizatorul poate verifica manual current_user.is_authenticated)
        return f(*args, **kwargs)
    
    return decorated_function


# ==============================================================================
# FUNCȚII HELPER
# ==============================================================================

def get_current_doctor_info() -> dict:
    """
    Returnează informații despre doctorul curent autentificat.
    
    Returns:
        dict: Informații doctor sau dict gol dacă nu e autentificat
    """
    if not current_user.is_authenticated:
        return {}
    
    return {
        'id': current_user.id,
        'email': current_user.email,
        'full_name': current_user.full_name,
        'is_admin': current_user.is_admin,
        'last_login_at': current_user.last_login_at.isoformat() if current_user.last_login_at else None,
        'last_login_ip': current_user.last_login_ip
    }


def create_auth_header_component():
    """
    Creează un component Dash pentru header-ul de autentificare.
    Afișează informații despre utilizatorul curent.
    
    Returns:
        html.Div: Component Dash cu informații autentificare
    """
    if not current_user.is_authenticated:
        return html.Div([
            html.A(
                "🔐 Autentifică-te",
                href='/login',
                style={
                    'padding': '8px 16px',
                    'background': '#3498db',
                    'color': 'white',
                    'textDecoration': 'none',
                    'borderRadius': '5px',
                    'fontSize': '14px'
                }
            )
        ], style={'textAlign': 'right', 'padding': '10px'})
    
    # Utilizator autentificat
    return html.Div([
        html.Span(
            f"👨‍⚕️ {current_user.full_name}",
            style={'marginRight': '15px', 'fontSize': '14px', 'color': '#333'}
        ),
        html.Span(
            f"({current_user.email})",
            style={'marginRight': '15px', 'fontSize': '12px', 'color': '#777'}
        ),
        html.A(
            "👋 Deconectare",
            href='/logout',
            style={
                'padding': '8px 16px',
                'background': '#e74c3c',
                'color': 'white',
                'textDecoration': 'none',
                'borderRadius': '5px',
                'fontSize': '14px'
            }
        )
    ], style={
        'textAlign': 'right',
        'padding': '10px',
        'background': '#f0f0f0',
        'borderBottom': '2px solid #3498db'
    })


def create_unauthorized_message(message: str = "Acces interzis") -> html.Div:
    """
    Creează un mesaj de eroare standard pentru acces neautorizat.
    
    Args:
        message: Mesajul custom de afișat
        
    Returns:
        html.Div: Component Dash cu mesaj de eroare
    """
    return html.Div([
        html.H3("🔒 " + message, style={'color': '#e74c3c', 'textAlign': 'center'}),
        html.P(
            "Nu ai permisiunile necesare pentru a accesa această funcționalitate.",
            style={'textAlign': 'center', 'color': '#666'}
        ),
        html.Div([
            html.A(
                "🔐 Autentifică-te",
                href='/login',
                style={
                    'display': 'inline-block',
                    'padding': '10px 20px',
                    'background': '#3498db',
                    'color': 'white',
                    'textDecoration': 'none',
                    'borderRadius': '5px',
                    'marginTop': '20px',
                    'marginRight': '10px'
                }
            ),
            html.A(
                "🏠 Pagina Principală",
                href='/',
                style={
                    'display': 'inline-block',
                    'padding': '10px 20px',
                    'background': '#95a5a6',
                    'color': 'white',
                    'textDecoration': 'none',
                    'borderRadius': '5px',
                    'marginTop': '20px'
                }
            )
        ], style={'textAlign': 'center'})
    ], style={
        'padding': '50px',
        'maxWidth': '600px',
        'margin': '50px auto',
        'background': '#f9f9f9',
        'borderRadius': '10px',
        'border': '2px solid #e74c3c'
    })


logger.info("✅ Modulul decorators.py inițializat cu succes.")


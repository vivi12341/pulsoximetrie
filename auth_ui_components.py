# ==============================================================================
# auth_ui_components.py
# ------------------------------------------------------------------------------
# ROL: Componente UI Dash pentru autentificare:
#      - Header cu status autentificare
#      - Informații utilizator curent
#      - Butoane login/logout
#
# RESPECTĂ: .cursorrules - Design UI/UX medical
# ==============================================================================

from dash import html
from flask_login import current_user
from logger_setup import logger


# ==============================================================================
# COMPONENTE UI
# ==============================================================================

def create_auth_header():
    """
    Creează header-ul de autentificare pentru aplicația Dash.
    Afișează diferit pentru utilizatori autentificați vs. neautentificați.
    
    Returns:
        html.Div: Component Dash cu header autentificare
    """
    if not current_user.is_authenticated:
        # Utilizator neautentificat - buton login
        return html.Div([
            html.Div([
                html.Span("👋 Bine ai venit!", style={
                    'marginRight': '15px',
                    'fontSize': '14px',
                    'color': '#555'
                }),
                html.A(
                    "🔐 Autentifică-te",
                    href='/login',
                    style={
                        'padding': '8px 20px',
                        'background': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                        'color': 'white',
                        'textDecoration': 'none',
                        'borderRadius': '25px',
                        'fontSize': '14px',
                        'fontWeight': '600',
                        'boxShadow': '0 2px 10px rgba(102, 126, 234, 0.3)',
                        'transition': 'all 0.3s ease'
                    }
                )
            ], style={
                'display': 'flex',
                'alignItems': 'center',
                'justifyContent': 'flex-end'
            })
        ], style={
            'padding': '15px 30px',
            'background': '#ffffff',
            'borderBottom': '2px solid #f0f0f0',
            'boxShadow': '0 2px 5px rgba(0,0,0,0.05)'
        })
    
    # Utilizator autentificat
    doctor_name = current_user.full_name
    doctor_email = current_user.email
    is_admin = current_user.is_admin
    
    return html.Div([
        html.Div([
            # Informații utilizator
            html.Div([
                html.Div([
                    html.Span("👨‍⚕️", style={'fontSize': '24px', 'marginRight': '10px'}),
                    html.Div([
                        html.Div(doctor_name, style={
                            'fontSize': '15px',
                            'fontWeight': '600',
                            'color': '#2c3e50',
                            'lineHeight': '1.2'
                        }),
                        html.Div([
                            html.Span(doctor_email, style={
                                'fontSize': '12px',
                                'color': '#7f8c8d'
                            }),
                            html.Span(
                                "👑 ADMIN",
                                style={
                                    'marginLeft': '10px',
                                    'padding': '2px 8px',
                                    'background': 'linear-gradient(135deg, #f39c12 0%, #e67e22 100%)',
                                    'color': 'white',
                                    'fontSize': '10px',
                                    'fontWeight': 'bold',
                                    'borderRadius': '10px',
                                    'textTransform': 'uppercase'
                                }
                            ) if is_admin else None
                        ])
                    ])
                ], style={
                    'display': 'flex',
                    'alignItems': 'center'
                })
            ], style={'flex': '1'}),
            
            # Butoane acțiuni
            html.Div([
                html.A(
                    "⚙️ Setări",
                    href='#',
                    style={
                        'padding': '8px 16px',
                        'background': '#ecf0f1',
                        'color': '#2c3e50',
                        'textDecoration': 'none',
                        'borderRadius': '20px',
                        'fontSize': '13px',
                        'fontWeight': '600',
                        'marginRight': '10px',
                        'transition': 'all 0.3s ease'
                    }
                ),
                html.A(
                    "👋 Deconectare",
                    href='/logout',
                    style={
                        'padding': '8px 20px',
                        'background': 'linear-gradient(135deg, #e74c3c 0%, #c0392b 100%)',
                        'color': 'white',
                        'textDecoration': 'none',
                        'borderRadius': '20px',
                        'fontSize': '13px',
                        'fontWeight': '600',
                        'boxShadow': '0 2px 10px rgba(231, 76, 60, 0.3)',
                        'transition': 'all 0.3s ease'
                    }
                )
            ], style={
                'display': 'flex',
                'alignItems': 'center'
            })
        ], style={
            'display': 'flex',
            'alignItems': 'center',
            'justifyContent': 'space-between',
            'maxWidth': '1400px',
            'margin': '0 auto'
        })
    ], style={
        'padding': '15px 30px',
        'background': 'linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%)',
        'borderBottom': '3px solid #667eea',
        'boxShadow': '0 3px 10px rgba(0,0,0,0.08)'
    })


def create_login_required_message():
    """
    Creează mesaj pentru utilizatori neautentificați care încearcă să acceseze
    resurse protejate.
    
    Returns:
        html.Div: Component Dash cu mesaj de eroare
    """
    return html.Div([
        html.Div([
            html.Div("🔒", style={
                'fontSize': '64px',
                'marginBottom': '20px',
                'textAlign': 'center'
            }),
            html.H2(
                "Autentificare Necesară",
                style={
                    'color': '#2c3e50',
                    'marginBottom': '15px',
                    'textAlign': 'center',
                    'fontSize': '28px'
                }
            ),
            html.P(
                "Trebuie să te autentifici pentru a accesa această funcționalitate.",
                style={
                    'color': '#7f8c8d',
                    'marginBottom': '30px',
                    'textAlign': 'center',
                    'fontSize': '16px',
                    'lineHeight': '1.6'
                }
            ),
            html.Div([
                html.A(
                    "🔐 Autentifică-te Acum",
                    href='/login',
                    style={
                        'display': 'inline-block',
                        'padding': '15px 40px',
                        'background': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                        'color': 'white',
                        'textDecoration': 'none',
                        'borderRadius': '50px',
                        'fontSize': '16px',
                        'fontWeight': '600',
                        'boxShadow': '0 4px 15px rgba(102, 126, 234, 0.4)',
                        'transition': 'all 0.3s ease'
                    }
                )
            ], style={'textAlign': 'center'})
        ], style={
            'background': 'white',
            'padding': '60px 40px',
            'borderRadius': '15px',
            'boxShadow': '0 10px 40px rgba(0,0,0,0.1)',
            'maxWidth': '500px',
            'margin': '0 auto'
        })
    ], style={
        'minHeight': '60vh',
        'display': 'flex',
        'alignItems': 'center',
        'justifyContent': 'center',
        'padding': '40px 20px'
    })


def create_user_info_card():
    """
    Creează card cu informații despre utilizatorul curent.
    Util pentru dashboard-ul de setări.
    
    Returns:
        html.Div: Component Dash cu card informații utilizator
    """
    if not current_user.is_authenticated:
        return create_login_required_message()
    
    last_login = current_user.last_login_at
    last_login_formatted = last_login.strftime("%d %B %Y, %H:%M") if last_login else "Niciodată"
    
    return html.Div([
        html.H3("👤 Informații Cont", style={
            'color': '#2c3e50',
            'marginBottom': '20px',
            'fontSize': '22px'
        }),
        
        html.Div([
            # Nume
            html.Div([
                html.Strong("Nume complet:", style={'color': '#7f8c8d', 'fontSize': '13px'}),
                html.Div(current_user.full_name, style={
                    'fontSize': '16px',
                    'color': '#2c3e50',
                    'marginTop': '5px',
                    'fontWeight': '600'
                })
            ], style={'marginBottom': '20px'}),
            
            # Email
            html.Div([
                html.Strong("Email:", style={'color': '#7f8c8d', 'fontSize': '13px'}),
                html.Div(current_user.email, style={
                    'fontSize': '16px',
                    'color': '#2c3e50',
                    'marginTop': '5px'
                })
            ], style={'marginBottom': '20px'}),
            
            # Rol
            html.Div([
                html.Strong("Rol:", style={'color': '#7f8c8d', 'fontSize': '13px'}),
                html.Div(
                    "Administrator" if current_user.is_admin else "Medic",
                    style={
                        'fontSize': '16px',
                        'color': '#2c3e50',
                        'marginTop': '5px',
                        'fontWeight': '600' if current_user.is_admin else 'normal'
                    }
                )
            ], style={'marginBottom': '20px'}),
            
            # Ultima autentificare
            html.Div([
                html.Strong("Ultima autentificare:", style={'color': '#7f8c8d', 'fontSize': '13px'}),
                html.Div(last_login_formatted, style={
                    'fontSize': '14px',
                    'color': '#2c3e50',
                    'marginTop': '5px'
                }),
                html.Div(
                    f"IP: {current_user.last_login_ip or 'N/A'}",
                    style={
                        'fontSize': '12px',
                        'color': '#95a5a6',
                        'marginTop': '3px'
                    }
                )
            ], style={'marginBottom': '20px'}),
            
            # Divider
            html.Hr(style={'margin': '25px 0', 'border': 'none', 'borderTop': '1px solid #ecf0f1'}),
            
            # Acțiuni
            html.Div([
                html.A(
                    "🔑 Schimbă Parola",
                    href='/request-reset',
                    style={
                        'display': 'inline-block',
                        'padding': '10px 20px',
                        'background': '#3498db',
                        'color': 'white',
                        'textDecoration': 'none',
                        'borderRadius': '8px',
                        'fontSize': '14px',
                        'fontWeight': '600',
                        'marginRight': '10px'
                    }
                ),
                html.A(
                    "👋 Deconectare",
                    href='/logout',
                    style={
                        'display': 'inline-block',
                        'padding': '10px 20px',
                        'background': '#e74c3c',
                        'color': 'white',
                        'textDecoration': 'none',
                        'borderRadius': '8px',
                        'fontSize': '14px',
                        'fontWeight': '600'
                    }
                )
            ])
        ])
    ], style={
        'background': 'white',
        'padding': '30px',
        'borderRadius': '12px',
        'boxShadow': '0 2px 10px rgba(0,0,0,0.08)',
        'maxWidth': '600px'
    })


logger.info("✅ Modulul auth_ui_components.py inițializat cu succes.")


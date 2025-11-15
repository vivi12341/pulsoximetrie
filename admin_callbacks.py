# ==============================================================================
# admin_callbacks.py
# ------------------------------------------------------------------------------
# ROL: Callback-uri Dash pentru administrarea utilizatorilor (doar pentru admini)
#
# RESPECTĂ: .cursorrules - Zero date personale în log-uri, GDPR compliant
# ==============================================================================

from dash import html, dcc, callback, Input, Output, State, no_update, ALL
from flask_login import current_user
from logger_setup import logger
from auth.models import db, Doctor
from auth.password_manager import hash_password, validate_password_strength
from datetime import datetime
import json


# ==============================================================================
# CALLBACK: Control vizibilitate secțiune admin (doar pentru admini)
# ==============================================================================

@callback(
    Output('admin-user-management-section', 'style'),
    Input('url', 'pathname')
)
def toggle_admin_section(pathname):
    """
    Afișează secțiunea de administrare utilizatori doar pentru admini.
    
    Args:
        pathname: URL-ul curent (pentru a declanșa callback-ul)
        
    Returns:
        dict: Style pentru secțiunea admin (display: block/none)
    """
    # Verificăm dacă utilizatorul este admin
    if not current_user.is_authenticated:
        return {'display': 'none'}
    
    if not current_user.is_admin:
        return {'display': 'none'}
    
    # Admin autentificat - afișăm secțiunea
    return {
        'display': 'block',
        'padding': '25px',
        'backgroundColor': '#fff9f9',
        'borderRadius': '10px',
        'boxShadow': '0 2px 8px rgba(231,76,60,0.15)',
        'marginBottom': '30px',
        'border': '2px solid #e74c3c'
    }


# ==============================================================================
# CALLBACK: Afișare listă utilizatori
# ==============================================================================

@callback(
    Output('admin-users-list-container', 'children'),
    [Input('admin-refresh-users-button', 'n_clicks'),
     Input('url', 'pathname')],
    prevent_initial_call=False
)
def display_users_list(n_clicks, pathname):
    """
    Afișează lista tuturor utilizatorilor din sistem.
    
    Args:
        n_clicks: Numărul de click-uri pe butonul refresh
        pathname: URL-ul curent
        
    Returns:
        html.Div: Listă cu toți utilizatorii
    """
    # Verificăm dacă utilizatorul este admin
    if not current_user.is_authenticated or not current_user.is_admin:
        return html.Div()
    
    try:
        # Obținem toți utilizatorii
        all_users = Doctor.query.order_by(Doctor.created_at.desc()).all()
        
        if not all_users:
            return html.Div([
                html.P("📭 Nu există utilizatori în sistem.", style={
                    'textAlign': 'center',
                    'color': '#95a5a6',
                    'padding': '30px',
                    'fontSize': '14px'
                })
            ])
        
        # Creăm carduri pentru fiecare utilizator
        user_cards = []
        
        for user in all_users:
            # Determinăm culoarea status-ului
            status_color = '#27ae60' if user.is_active else '#e74c3c'
            status_text = '✅ Activ' if user.is_active else '❌ Dezactivat'
            
            # Determinăm badge-ul de rol
            role_badge = None
            if user.is_admin:
                role_badge = html.Span(
                    '👑 ADMIN',
                    style={
                        'padding': '4px 10px',
                        'background': 'linear-gradient(135deg, #f39c12 0%, #e67e22 100%)',
                        'color': 'white',
                        'fontSize': '11px',
                        'fontWeight': 'bold',
                        'borderRadius': '12px',
                        'marginLeft': '10px'
                    }
                )
            
            # Protecție: nu putem edita propriul cont (pentru a preveni auto-dezactivare)
            is_own_account = (user.id == current_user.id)
            
            user_card = html.Div([
                # Header cu nume și rol
                html.Div([
                    html.Div([
                        html.Span(user.full_name, style={
                            'fontSize': '16px',
                            'fontWeight': '600',
                            'color': '#2c3e50'
                        }),
                        role_badge if role_badge else None
                    ], style={'display': 'flex', 'alignItems': 'center'}),
                    
                    html.Div([
                        html.Span(user.email, style={
                            'fontSize': '13px',
                            'color': '#7f8c8d'
                        })
                    ], style={'marginTop': '5px'})
                ], style={'flex': '1'}),
                
                # Informații despre cont
                html.Div([
                    html.Div([
                        html.Strong('Status: ', style={'fontSize': '12px', 'color': '#555'}),
                        html.Span(status_text, style={
                            'fontSize': '12px',
                            'color': status_color,
                            'fontWeight': 'bold'
                        })
                    ], style={'marginTop': '10px'}),
                    
                    html.Div([
                        html.Strong('Creat: ', style={'fontSize': '12px', 'color': '#555'}),
                        html.Span(
                            user.created_at.strftime('%d.%m.%Y %H:%M') if user.created_at else 'N/A',
                            style={'fontSize': '12px', 'color': '#666'}
                        )
                    ], style={'marginTop': '5px'}),
                    
                    html.Div([
                        html.Strong('Ultimul login: ', style={'fontSize': '12px', 'color': '#555'}),
                        html.Span(
                            user.last_login_at.strftime('%d.%m.%Y %H:%M') if user.last_login_at else 'Niciodată',
                            style={'fontSize': '12px', 'color': '#666'}
                        )
                    ], style={'marginTop': '5px'}),
                    
                    html.Div([
                        html.Strong('Login-uri eșuate: ', style={'fontSize': '12px', 'color': '#555'}),
                        html.Span(
                            str(user.failed_login_attempts),
                            style={
                                'fontSize': '12px',
                                'color': '#e74c3c' if user.failed_login_attempts > 0 else '#27ae60',
                                'fontWeight': 'bold'
                            }
                        )
                    ], style={'marginTop': '5px'})
                ]),
                
                # Butoane acțiuni
                html.Div([
                    html.Button(
                        '✏️ Editează',
                        id={'type': 'admin-edit-user', 'index': user.id},
                        n_clicks=0,
                        disabled=is_own_account,
                        style={
                            'padding': '8px 16px',
                            'fontSize': '13px',
                            'backgroundColor': '#3498db' if not is_own_account else '#95a5a6',
                            'color': 'white',
                            'border': 'none',
                            'borderRadius': '5px',
                            'cursor': 'pointer' if not is_own_account else 'not-allowed',
                            'marginRight': '8px'
                        }
                    ),
                    
                    html.Button(
                        '🔒 Deblocă' if user.is_locked() else ('❌ Dezactivează' if user.is_active else '✅ Activează'),
                        id={'type': 'admin-toggle-user', 'index': user.id},
                        n_clicks=0,
                        disabled=is_own_account,
                        style={
                            'padding': '8px 16px',
                            'fontSize': '13px',
                            'backgroundColor': '#f39c12' if user.is_locked() else ('#e74c3c' if user.is_active else '#27ae60'),
                            'color': 'white',
                            'border': 'none',
                            'borderRadius': '5px',
                            'cursor': 'pointer' if not is_own_account else 'not-allowed',
                            'marginRight': '8px'
                        }
                    ),
                    
                    html.Button(
                        '👑 Admin' if not user.is_admin else '👤 Medic',
                        id={'type': 'admin-toggle-admin-role', 'index': user.id},
                        n_clicks=0,
                        disabled=is_own_account,
                        style={
                            'padding': '8px 16px',
                            'fontSize': '13px',
                            'backgroundColor': '#9b59b6' if not is_own_account else '#95a5a6',
                            'color': 'white',
                            'border': 'none',
                            'borderRadius': '5px',
                            'cursor': 'pointer' if not is_own_account else 'not-allowed'
                        }
                    )
                ], style={'marginTop': '15px', 'display': 'flex', 'gap': '5px'}),
                
                # Avertisment pentru propriul cont
                html.Div([
                    html.P(
                        '⚠️ Acesta este contul tău. Nu poți modifica propriul cont.',
                        style={
                            'fontSize': '11px',
                            'color': '#e67e22',
                            'marginTop': '10px',
                            'fontStyle': 'italic'
                        }
                    )
                ], style={'display': 'block' if is_own_account else 'none'})
                
            ], style={
                'padding': '20px',
                'backgroundColor': '#f8f9fa' if not is_own_account else '#fff3cd',
                'borderRadius': '8px',
                'marginBottom': '15px',
                'border': f'2px solid {status_color}',
                'boxShadow': '0 2px 5px rgba(0,0,0,0.08)'
            })
            
            user_cards.append(user_card)
        
        # Statistici
        total_users = len(all_users)
        active_users = len([u for u in all_users if u.is_active])
        admin_users = len([u for u in all_users if u.is_admin])
        
        stats = html.Div([
            html.H4(f"📊 Statistici: {total_users} utilizatori totali | {active_users} activi | {admin_users} administratori", style={
                'color': '#2c3e50',
                'fontSize': '14px',
                'marginBottom': '20px',
                'padding': '12px',
                'backgroundColor': '#e8f4f8',
                'borderRadius': '6px',
                'textAlign': 'center'
            })
        ])
        
        return html.Div([stats] + user_cards)
        
    except Exception as e:
        logger.error(f"❌ Eroare la afișarea listei de utilizatori: {e}")
        return html.Div([
            html.P(f"❌ Eroare la încărcarea listei de utilizatori: {str(e)}", style={
                'color': '#e74c3c',
                'padding': '20px',
                'textAlign': 'center'
            })
        ])


# ==============================================================================
# CALLBACK: Afișare formular creare utilizator
# ==============================================================================

@callback(
    Output('admin-user-form-container', 'children'),
    [Input('admin-create-user-button', 'n_clicks'),
     Input({'type': 'admin-edit-user', 'index': ALL}, 'n_clicks')],
    [State({'type': 'admin-edit-user', 'index': ALL}, 'id')],
    prevent_initial_call=True
)
def display_user_form(create_clicks, edit_clicks, edit_ids):
    """
    Afișează formularul pentru crearea/editarea unui utilizator.
    
    Args:
        create_clicks: Click-uri pe butonul de creare
        edit_clicks: Click-uri pe butoanele de editare
        edit_ids: ID-urile butoanelor de editare
        
    Returns:
        html.Div: Formular de creare/editare utilizator
    """
    from dash import ctx
    
    # Verificăm cine a declanșat callback-ul
    if not ctx.triggered:
        return no_update
    
    triggered_id = ctx.triggered[0]['prop_id']
    
    # Verificăm dacă e buton de creare
    if 'admin-create-user-button' in triggered_id:
        return create_user_form()
    
    # Verificăm dacă e buton de editare
    if 'admin-edit-user' in triggered_id:
        # Extragem user_id din triggered_id
        import json
        trigger_dict = json.loads(triggered_id.split('.')[0])
        user_id = trigger_dict['index']
        
        # Găsim utilizatorul
        user = Doctor.query.get(user_id)
        if not user:
            return html.Div([
                html.P(f"❌ Utilizatorul cu ID {user_id} nu a fost găsit.", style={'color': '#e74c3c'})
            ])
        
        return edit_user_form(user)
    
    return no_update


def create_user_form():
    """Creează formularul pentru adăugarea unui utilizator nou."""
    return html.Div([
        html.H4("➕ Creare Utilizator Nou", style={'color': '#27ae60', 'marginBottom': '15px'}),
        
        html.Div([
            html.Label("Nume Complet:", style={'fontWeight': 'bold', 'marginBottom': '5px', 'display': 'block', 'fontSize': '13px'}),
            dcc.Input(
                id='admin-user-fullname-input',
                type='text',
                placeholder='Ex: Dr. Popescu Ion',
                style={
                    'width': '100%',
                    'padding': '10px',
                    'border': '2px solid #e0e0e0',
                    'borderRadius': '5px',
                    'fontSize': '14px'
                }
            )
        ], style={'marginBottom': '15px'}),
        
        html.Div([
            html.Label("Email:", style={'fontWeight': 'bold', 'marginBottom': '5px', 'display': 'block', 'fontSize': '13px'}),
            dcc.Input(
                id='admin-user-email-input',
                type='email',
                placeholder='exemplu@medical.ro',
                style={
                    'width': '100%',
                    'padding': '10px',
                    'border': '2px solid #e0e0e0',
                    'borderRadius': '5px',
                    'fontSize': '14px'
                }
            )
        ], style={'marginBottom': '15px'}),
        
        html.Div([
            html.Label("Parolă:", style={'fontWeight': 'bold', 'marginBottom': '5px', 'display': 'block', 'fontSize': '13px'}),
            dcc.Input(
                id='admin-user-password-input',
                type='password',
                placeholder='Minimum 8 caractere (litere, cifre, caractere speciale)',
                style={
                    'width': '100%',
                    'padding': '10px',
                    'border': '2px solid #e0e0e0',
                    'borderRadius': '5px',
                    'fontSize': '14px'
                }
            )
        ], style={'marginBottom': '15px'}),
        
        html.Div([
            dcc.Checklist(
                id='admin-user-isadmin-checkbox',
                options=[{'label': ' Cont Administrator', 'value': 'admin'}],
                value=[],
                style={'fontSize': '13px'}
            )
        ], style={'marginBottom': '15px'}),
        
        html.Div([
            html.Button(
                '💾 Salvează Utilizator',
                id='admin-save-new-user-button',
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
                '❌ Anulează',
                id='admin-cancel-user-form-button',
                n_clicks=0,
                style={
                    'padding': '12px 25px',
                    'fontSize': '14px',
                    'backgroundColor': '#95a5a6',
                    'color': 'white',
                    'border': 'none',
                    'borderRadius': '5px',
                    'cursor': 'pointer'
                }
            )
        ]),
        
        html.Div(id='admin-user-form-status', style={'marginTop': '15px'})
        
    ], style={
        'padding': '20px',
        'backgroundColor': '#f0fff4',
        'borderRadius': '8px',
        'border': '2px solid #27ae60'
    })


def edit_user_form(user):
    """
    Creează formularul pentru editarea unui utilizator existent.
    
    Args:
        user: Obiectul Doctor de editat
    """
    return html.Div([
        html.H4(f"✏️ Editare Utilizator: {user.full_name}", style={'color': '#3498db', 'marginBottom': '15px'}),
        
        # Store pentru user_id
        dcc.Store(id='admin-edit-user-id-store', data=user.id),
        
        html.Div([
            html.Label("Nume Complet:", style={'fontWeight': 'bold', 'marginBottom': '5px', 'display': 'block', 'fontSize': '13px'}),
            dcc.Input(
                id='admin-user-fullname-input',
                type='text',
                value=user.full_name,
                style={
                    'width': '100%',
                    'padding': '10px',
                    'border': '2px solid #e0e0e0',
                    'borderRadius': '5px',
                    'fontSize': '14px'
                }
            )
        ], style={'marginBottom': '15px'}),
        
        html.Div([
            html.Label("Email:", style={'fontWeight': 'bold', 'marginBottom': '5px', 'display': 'block', 'fontSize': '13px'}),
            dcc.Input(
                id='admin-user-email-input',
                type='email',
                value=user.email,
                style={
                    'width': '100%',
                    'padding': '10px',
                    'border': '2px solid #e0e0e0',
                    'borderRadius': '5px',
                    'fontSize': '14px'
                }
            )
        ], style={'marginBottom': '15px'}),
        
        html.Div([
            html.Label("Parolă Nouă (lasă gol pentru a păstra parola actuală):", style={'fontWeight': 'bold', 'marginBottom': '5px', 'display': 'block', 'fontSize': '13px'}),
            dcc.Input(
                id='admin-user-password-input',
                type='password',
                placeholder='Lasă gol pentru a păstra parola actuală',
                style={
                    'width': '100%',
                    'padding': '10px',
                    'border': '2px solid #e0e0e0',
                    'borderRadius': '5px',
                    'fontSize': '14px'
                }
            )
        ], style={'marginBottom': '15px'}),
        
        html.Div([
            dcc.Checklist(
                id='admin-user-isadmin-checkbox',
                options=[{'label': ' Cont Administrator', 'value': 'admin'}],
                value=['admin'] if user.is_admin else [],
                style={'fontSize': '13px'}
            )
        ], style={'marginBottom': '15px'}),
        
        html.Div([
            html.Button(
                '💾 Salvează Modificări',
                id='admin-save-edit-user-button',
                n_clicks=0,
                style={
                    'padding': '12px 25px',
                    'fontSize': '14px',
                    'fontWeight': 'bold',
                    'backgroundColor': '#3498db',
                    'color': 'white',
                    'border': 'none',
                    'borderRadius': '5px',
                    'cursor': 'pointer',
                    'marginRight': '10px'
                }
            ),
            html.Button(
                '❌ Anulează',
                id='admin-cancel-user-form-button',
                n_clicks=0,
                style={
                    'padding': '12px 25px',
                    'fontSize': '14px',
                    'backgroundColor': '#95a5a6',
                    'color': 'white',
                    'border': 'none',
                    'borderRadius': '5px',
                    'cursor': 'pointer'
                }
            )
        ]),
        
        html.Div(id='admin-user-form-status', style={'marginTop': '15px'})
        
    ], style={
        'padding': '20px',
        'backgroundColor': '#f0f8ff',
        'borderRadius': '8px',
        'border': '2px solid #3498db'
    })


# ==============================================================================
# CALLBACK: Salvare utilizator nou
# ==============================================================================

@callback(
    [Output('admin-user-form-status', 'children'),
     Output('admin-refresh-users-button', 'n_clicks', allow_duplicate=True)],
    Input('admin-save-new-user-button', 'n_clicks'),
    [State('admin-user-fullname-input', 'value'),
     State('admin-user-email-input', 'value'),
     State('admin-user-password-input', 'value'),
     State('admin-user-isadmin-checkbox', 'value')],
    prevent_initial_call=True
)
def save_new_user(n_clicks, fullname, email, password, is_admin_list):
    """
    Salvează un utilizator nou în baza de date.
    """
    if not n_clicks:
        return no_update, no_update
    
    # Verificăm dacă utilizatorul curent este admin
    if not current_user.is_authenticated or not current_user.is_admin:
        return html.Div([
            html.P("❌ Nu ai permisiunea să creezi utilizatori.", style={'color': '#e74c3c'})
        ]), no_update
    
    # Validări
    if not fullname or not email or not password:
        return html.Div([
            html.P("❌ Te rugăm să completezi toate câmpurile.", style={'color': '#e74c3c'})
        ]), no_update
    
    # Validare parolă
    is_valid, message = validate_password_strength(password)
    if not is_valid:
        return html.Div([
            html.P(f"❌ {message}", style={'color': '#e74c3c'})
        ]), no_update
    
    # Verificăm dacă email-ul există deja
    existing_user = Doctor.query.filter_by(email=email.strip().lower()).first()
    if existing_user:
        return html.Div([
            html.P("❌ Există deja un utilizator cu acest email.", style={'color': '#e74c3c'})
        ]), no_update
    
    # Creăm utilizatorul
    try:
        is_admin = 'admin' in (is_admin_list or [])
        
        new_user = Doctor(
            email=email.strip().lower(),
            password_hash=hash_password(password),
            full_name=fullname.strip(),
            is_admin=is_admin,
            is_active=True
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        logger.info(f"✅ Admin {current_user.email} a creat utilizatorul {email}")
        
        return html.Div([
            html.P(f"✅ Utilizatorul {fullname} ({email}) a fost creat cu succes!", style={'color': '#27ae60', 'fontWeight': 'bold'})
        ]), 1  # Trigger refresh
        
    except Exception as e:
        logger.error(f"❌ Eroare la crearea utilizatorului: {e}")
        db.session.rollback()
        return html.Div([
            html.P(f"❌ Eroare la crearea utilizatorului: {str(e)}", style={'color': '#e74c3c'})
        ]), no_update


# ==============================================================================
# CALLBACK: Salvare modificări utilizator
# ==============================================================================

@callback(
    [Output('admin-user-form-status', 'children', allow_duplicate=True),
     Output('admin-refresh-users-button', 'n_clicks', allow_duplicate=True)],
    Input('admin-save-edit-user-button', 'n_clicks'),
    [State('admin-edit-user-id-store', 'data'),
     State('admin-user-fullname-input', 'value'),
     State('admin-user-email-input', 'value'),
     State('admin-user-password-input', 'value'),
     State('admin-user-isadmin-checkbox', 'value')],
    prevent_initial_call=True
)
def save_edit_user(n_clicks, user_id, fullname, email, password, is_admin_list):
    """
    Salvează modificările la un utilizator existent.
    """
    if not n_clicks or not user_id:
        return no_update, no_update
    
    # Verificăm dacă utilizatorul curent este admin
    if not current_user.is_authenticated or not current_user.is_admin:
        return html.Div([
            html.P("❌ Nu ai permisiunea să editezi utilizatori.", style={'color': '#e74c3c'})
        ]), no_update
    
    # Nu putem edita propriul cont
    if user_id == current_user.id:
        return html.Div([
            html.P("❌ Nu poți edita propriul cont.", style={'color': '#e74c3c'})
        ]), no_update
    
    # Găsim utilizatorul
    user = Doctor.query.get(user_id)
    if not user:
        return html.Div([
            html.P(f"❌ Utilizatorul cu ID {user_id} nu a fost găsit.", style={'color': '#e74c3c'})
        ]), no_update
    
    # Validări
    if not fullname or not email:
        return html.Div([
            html.P("❌ Te rugăm să completezi toate câmpurile obligatorii.", style={'color': '#e74c3c'})
        ]), no_update
    
    # Dacă se schimbă parola, o validăm
    if password:
        is_valid, message = validate_password_strength(password)
        if not is_valid:
            return html.Div([
                html.P(f"❌ {message}", style={'color': '#e74c3c'})
            ]), no_update
    
    # Verificăm dacă email-ul există deja (la alt utilizator)
    existing_user = Doctor.query.filter_by(email=email.strip().lower()).first()
    if existing_user and existing_user.id != user_id:
        return html.Div([
            html.P("❌ Există deja un utilizator cu acest email.", style={'color': '#e74c3c'})
        ]), no_update
    
    # Salvăm modificările
    try:
        user.full_name = fullname.strip()
        user.email = email.strip().lower()
        
        if password:
            user.password_hash = hash_password(password)
        
        is_admin = 'admin' in (is_admin_list or [])
        user.is_admin = is_admin
        
        db.session.commit()
        
        logger.info(f"✅ Admin {current_user.email} a modificat utilizatorul {user.email}")
        
        return html.Div([
            html.P(f"✅ Utilizatorul {user.full_name} a fost actualizat cu succes!", style={'color': '#27ae60', 'fontWeight': 'bold'})
        ]), 1  # Trigger refresh
        
    except Exception as e:
        logger.error(f"❌ Eroare la actualizarea utilizatorului: {e}")
        db.session.rollback()
        return html.Div([
            html.P(f"❌ Eroare la actualizarea utilizatorului: {str(e)}", style={'color': '#e74c3c'})
        ]), no_update


# ==============================================================================
# CALLBACK: Anulare formular
# ==============================================================================

@callback(
    Output('admin-user-form-container', 'children', allow_duplicate=True),
    Input('admin-cancel-user-form-button', 'n_clicks'),
    prevent_initial_call=True
)
def cancel_user_form(n_clicks):
    """Anulează formularul de creare/editare utilizator."""
    if not n_clicks:
        return no_update
    return html.Div()


# ==============================================================================
# CALLBACK: Toggle activare/dezactivare utilizator
# ==============================================================================

@callback(
    Output('admin-refresh-users-button', 'n_clicks', allow_duplicate=True),
    Input({'type': 'admin-toggle-user', 'index': ALL}, 'n_clicks'),
    State({'type': 'admin-toggle-user', 'index': ALL}, 'id'),
    prevent_initial_call=True
)
def toggle_user_status(n_clicks_list, button_ids):
    """
    Activează/dezactivează sau deblochează un utilizator.
    """
    from dash import ctx
    
    if not ctx.triggered:
        return no_update
    
    # Găsim butonul care a declanșat callback-ul
    triggered_id = ctx.triggered[0]['prop_id']
    
    # Extragem user_id
    import json
    trigger_dict = json.loads(triggered_id.split('.')[0])
    user_id = trigger_dict['index']
    
    # Verificăm dacă utilizatorul curent este admin
    if not current_user.is_authenticated or not current_user.is_admin:
        return no_update
    
    # Nu putem dezactiva propriul cont
    if user_id == current_user.id:
        return no_update
    
    # Găsim utilizatorul
    user = Doctor.query.get(user_id)
    if not user:
        return no_update
    
    try:
        # Verificăm dacă e blocat
        if user.is_locked():
            user.unlock_account()
            logger.info(f"✅ Admin {current_user.email} a deblocat utilizatorul {user.email}")
        else:
            # Toggle activare/dezactivare
            user.is_active = not user.is_active
            db.session.commit()
            status_text = "activat" if user.is_active else "dezactivat"
            logger.info(f"✅ Admin {current_user.email} a {status_text} utilizatorul {user.email}")
        
        return 1  # Trigger refresh
        
    except Exception as e:
        logger.error(f"❌ Eroare la schimbarea status-ului utilizatorului: {e}")
        db.session.rollback()
        return no_update


# ==============================================================================
# CALLBACK: Toggle rol admin
# ==============================================================================

@callback(
    Output('admin-refresh-users-button', 'n_clicks', allow_duplicate=True),
    Input({'type': 'admin-toggle-admin-role', 'index': ALL}, 'n_clicks'),
    State({'type': 'admin-toggle-admin-role', 'index': ALL}, 'id'),
    prevent_initial_call=True
)
def toggle_admin_role(n_clicks_list, button_ids):
    """
    Acordă/retrage rol de administrator.
    """
    from dash import ctx
    
    if not ctx.triggered:
        return no_update
    
    # Găsim butonul care a declanșat callback-ul
    triggered_id = ctx.triggered[0]['prop_id']
    
    # Extragem user_id
    import json
    trigger_dict = json.loads(triggered_id.split('.')[0])
    user_id = trigger_dict['index']
    
    # Verificăm dacă utilizatorul curent este admin
    if not current_user.is_authenticated or not current_user.is_admin:
        return no_update
    
    # Nu putem schimba propriul rol
    if user_id == current_user.id:
        return no_update
    
    # Găsim utilizatorul
    user = Doctor.query.get(user_id)
    if not user:
        return no_update
    
    try:
        # Toggle rol admin
        user.is_admin = not user.is_admin
        db.session.commit()
        
        role_text = "administrator" if user.is_admin else "medic"
        logger.info(f"✅ Admin {current_user.email} a setat utilizatorul {user.email} ca {role_text}")
        
        return 1  # Trigger refresh
        
    except Exception as e:
        logger.error(f"❌ Eroare la schimbarea rolului utilizatorului: {e}")
        db.session.rollback()
        return no_update


logger.info("✅ Modulul admin_callbacks.py inițializat cu succes.")


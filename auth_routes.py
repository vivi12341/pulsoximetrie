# ==============================================================================
# auth_routes.py
# ------------------------------------------------------------------------------
# ROL: Flask routes pentru autentificare:
#      - /health (GET) - health check pentru Railway
#      - /login (GET + POST)
#      - /logout (GET)
#      - /request-reset (POST) - cerere reset parolă
#      - /reset-password (GET + POST) - form reset parolă cu token
#
# RESPECTĂ: .cursorrules - Zero date personale în log-uri
# ==============================================================================

from flask import request, redirect, url_for, render_template_string, jsonify, session
from datetime import datetime, timedelta
import os

from logger_setup import logger
from auth.models import db, Doctor, PasswordResetToken
from auth.auth_manager import authenticate_doctor, logout_doctor, is_authenticated
from auth.password_manager import hash_password, validate_password_strength, generate_reset_token_with_expiry
from auth.email_service import send_password_reset_email, send_password_changed_email
from auth.rate_limiter import (
    check_rate_limit, check_reset_rate_limit, record_reset_attempt,
    get_remaining_attempts, get_remaining_reset_attempts, get_reset_cooldown_minutes
)


# ==============================================================================
# ROUTE: /health (Health Check pentru Railway)
# ==============================================================================

def route_health(app_server):
    """
    Configurează route-ul /health pentru monitoring (Railway).
    
    Args:
        app_server: Instanța Flask (app.server)
    """
    
    @app_server.route('/health', methods=['GET'])
    def health_check():
        """
        Health check endpoint - verifică dacă aplicația rulează corect.
        Verifică: Database connection, Storage access, Application status.
        
        Returns:
            JSON cu status și timestamp (200 OK sau 503 Service Unavailable)
        """
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'checks': {
                'service': 'pulsoximetrie'
            }
        }
        
        # Check 1: Database connection
        try:
            db.session.execute(db.text('SELECT 1'))
            health_status['checks']['database'] = 'ok'
        except Exception as e:
            health_status['status'] = 'unhealthy'
            health_status['checks']['database'] = f'error: {str(e)[:100]}'
            logger.error(f"❌ Health check: Database error - {e}")
        
        # Check 2: Storage write/read (defensive - nu blochează dacă fail)
        try:
            import os
            test_file = 'output/LOGS/.health_check'
            with open(test_file, 'w') as f:
                f.write('ok')
            os.remove(test_file)
            health_status['checks']['storage'] = 'ok'
        except Exception as e:
            # Storage failure nu e critic (aplicația poate continua)
            health_status['checks']['storage'] = f'degraded: {str(e)[:50]}'
            logger.warning(f"⚠️ Health check: Storage warning - {e}")
        
        # Check 3: Application callbacks (informațional)
        try:
            from app_instance import app as dash_app
            health_status['checks']['callbacks'] = len(dash_app.callback_map)
        except Exception:
            health_status['checks']['callbacks'] = 'unknown'
        
        status_code = 200 if health_status['status'] == 'healthy' else 503
        return jsonify(health_status), status_code
    
    @app_server.route('/debug-info', methods=['GET'])
    def debug_info():
        """
        Debug endpoint - informații despre aplicație (doar pentru troubleshooting).
        """
        import os
        
        info = {
            "environment": os.getenv('RAILWAY_ENVIRONMENT', 'local'),
            "flask_env": os.getenv('FLASK_ENV', 'development'),
            "port": os.getenv('PORT', 'not set'),
            "database_connected": False,
            "folders_exist": {
                "output": os.path.exists('output'),
                "patient_data": os.path.exists('patient_data'),
                "batch_sessions": os.path.exists('batch_sessions'),
                "doctor_settings": os.path.exists('doctor_settings')
            },
            "files_exist": {
                "patient_links.json": os.path.exists('patient_links.json'),
                "settings.json": os.path.exists('doctor_settings/default/settings.json')
            }
        }
        
        try:
            db.session.execute(db.text('SELECT 1'))
            info["database_connected"] = True
        except Exception as e:
            info["database_error"] = str(e)
        
        return jsonify(info), 200


# ==============================================================================
# ROUTE: /login (autentificare)
# ==============================================================================

def route_login(app_server):
    """
    Configurează route-ul /login pe server-ul Flask.
    
    Args:
        app_server: Instanța Flask (app.server)
    """
    
    @app_server.route('/login', methods=['GET', 'POST'])
    def login():
        """
        Handler pentru autentificare.
        
        GET: Afișează formularul de login
        POST: Procesează autentificarea
        """
        # Dacă utilizatorul e deja autentificat, redirect la homepage
        if is_authenticated():
            logger.debug(f"Utilizator deja autentificat - redirect la /")
            return redirect('/')
        
        if request.method == 'POST':
            # Extragem datele din formular
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            remember_me = request.form.get('remember_me') == 'on'
            
            if not email or not password:
                logger.warning("Tentativă login cu câmpuri goale")
                return render_login_page(error="Te rugăm să completezi toate câmpurile.")
            
            # Verificăm rate limiting
            ip_address = request.remote_addr
            remaining = get_remaining_attempts(email, ip_address)
            
            if remaining <= 0:
                logger.warning(f"🚨 Rate limit depășit: {email[:3]}*** din {ip_address}")
                return render_login_page(
                    error="Prea multe încercări eșuate. Contul este blocat temporar (15 minute)."
                )
            
            # Încercăm autentificarea
            success, doctor, message = authenticate_doctor(email, password, remember_me)
            
            if success:
                logger.info(f"✅ Login reușit: {email} din {ip_address}")
                
                # Redirect la pagina de origine sau homepage
                next_page = request.args.get('next', '/')
                return redirect(next_page)
            else:
                # Login eșuat
                remaining_after = get_remaining_attempts(email, ip_address)
                
                if remaining_after > 0:
                    error_msg = f"{message} (Mai ai {remaining_after} încercări.)"
                else:
                    error_msg = message
                
                logger.debug(f"❌ Login eșuat: {email[:3]}*** - {message}")
                return render_login_page(error=error_msg, email=email)
        
        # GET request - afișăm formularul
        # Verificăm dacă există mesaj de succes în URL
        success_param = request.args.get('success', '')
        success_message = None
        
        if success_param == 'account_created':
            success_message = "Contul tău a fost creat cu succes! Poți să te autentifici acum."
        elif success_param == 'password_reset':
            success_message = "Parola a fost schimbată cu succes! Poți să te autentifici acum."
        elif success_param == 'disconnected':
            success_message = "Te-ai deconectat cu succes."
        
        return render_login_page(success=success_message)


def render_login_page(error=None, email='', success=None):
    """
    Renderizează pagina de login cu template HTML.
    
    Args:
        error: Mesaj de eroare (opțional)
        email: Email pre-completat (opțional)
        success: Mesaj de succes (opțional)
        
    Returns:
        HTML string
    """
    template = """
    <!DOCTYPE html>
    <html lang="ro">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Autentificare - Platformă Pulsoximetrie</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }
            .login-container {
                background: white;
                padding: 40px;
                border-radius: 15px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                width: 100%;
                max-width: 420px;
            }
            .logo {
                text-align: center;
                margin-bottom: 30px;
            }
            .logo h1 {
                color: #667eea;
                font-size: 28px;
                margin-bottom: 10px;
            }
            .logo p {
                color: #777;
                font-size: 14px;
            }
            .form-group {
                margin-bottom: 20px;
            }
            .form-group label {
                display: block;
                margin-bottom: 8px;
                color: #333;
                font-weight: 600;
                font-size: 14px;
            }
            .form-group input[type="email"],
            .form-group input[type="password"] {
                width: 100%;
                padding: 12px 15px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                font-size: 15px;
                transition: all 0.3s ease;
            }
            .form-group input:focus {
                outline: none;
                border-color: #667eea;
                box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
            }
            .remember-me {
                display: flex;
                align-items: center;
                margin-bottom: 20px;
            }
            .remember-me input[type="checkbox"] {
                margin-right: 8px;
                width: 18px;
                height: 18px;
                cursor: pointer;
            }
            .remember-me label {
                font-size: 14px;
                color: #555;
                cursor: pointer;
            }
            .btn-login {
                width: 100%;
                padding: 14px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
            }
            .btn-login:hover {
                transform: translateY(-2px);
                box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
            }
            .btn-login:active {
                transform: translateY(0);
            }
            .error-message {
                background: #fee;
                border-left: 4px solid #e74c3c;
                padding: 12px;
                margin-bottom: 20px;
                border-radius: 5px;
                color: #c0392b;
                font-size: 14px;
            }
            .success-message {
                background: #efe;
                border-left: 4px solid #27ae60;
                padding: 12px;
                margin-bottom: 20px;
                border-radius: 5px;
                color: #27ae60;
                font-size: 14px;
            }
            .forgot-password {
                text-align: center;
                margin-top: 20px;
            }
            .forgot-password a {
                color: #667eea;
                text-decoration: none;
                font-size: 14px;
                font-weight: 600;
            }
            .forgot-password a:hover {
                text-decoration: underline;
            }
            .divider {
                text-align: center;
                margin: 25px 0;
                color: #999;
                font-size: 13px;
            }
        </style>
    </head>
    <body>
        <div class="login-container">
            <div class="logo">
                <h1>🔐 Autentificare</h1>
                <p>Platformă Pulsoximetrie</p>
            </div>
            
            {% if error %}
            <div class="error-message">
                ❌ {{ error }}
            </div>
            {% endif %}
            
            {% if success %}
            <div class="success-message">
                ✅ {{ success }}
            </div>
            {% endif %}
            
            <form method="POST" action="/login">
                <div class="form-group">
                    <label for="email">Email</label>
                    <input 
                        type="email" 
                        id="email" 
                        name="email" 
                        value="{{ email }}"
                        placeholder="exemplu@medical.ro"
                        required 
                        autofocus
                    >
                </div>
                
                <div class="form-group">
                    <label for="password">Parolă</label>
                    <input 
                        type="password" 
                        id="password" 
                        name="password" 
                        placeholder="••••••••"
                        required
                    >
                </div>
                
                <div class="remember-me">
                    <input type="checkbox" id="remember_me" name="remember_me">
                    <label for="remember_me">Ține-mă minte (30 zile)</label>
                </div>
                
                <button type="submit" class="btn-login">
                    🔐 Autentifică-te
                </button>
            </form>
            
            <div class="forgot-password">
                <a href="/request-reset">Am uitat parola</a>
            </div>
            
            <div class="divider">
                Nu ai cont? <a href="/signup" style="color: #667eea; text-decoration: none; font-weight: 600;">Înregistrează-te</a>
            </div>
            
            <div class="divider" style="margin-top: 10px;">
                © 2025 Platformă Pulsoximetrie
            </div>
        </div>
    </body>
    </html>
    """
    
    from jinja2 import Template
    return Template(template).render(error=error, email=email, success=success)


# ==============================================================================
# ROUTE: /logout (deconectare)
# ==============================================================================

def route_logout(app_server):
    """
    Configurează route-ul /logout pe server-ul Flask.
    
    Args:
        app_server: Instanța Flask
    """
    
    @app_server.route('/logout')
    def logout():
        """Deconectează utilizatorul curent."""
        if is_authenticated():
            logout_doctor(deactivate_all_sessions=False)
            logger.info("👋 Utilizator deconectat")
        
        return redirect('/login?success=disconnected')


# ==============================================================================
# ROUTE: /request-reset (cerere reset parolă)
# ==============================================================================

def route_request_reset(app_server):
    """
    Configurează route-ul /request-reset pentru cereri de resetare parolă.
    
    Args:
        app_server: Instanța Flask
    """
    
    @app_server.route('/request-reset', methods=['GET', 'POST'])
    def request_reset():
        """
        Handler pentru cerere reset parolă.
        
        GET: Afișează formularul
        POST: Trimite email cu token reset
        """
        if request.method == 'POST':
            email = request.form.get('email', '').strip().lower()
            
            if not email:
                return render_reset_request_page(error="Te rugăm să introduci adresa de email.")
            
            # Verificăm rate limiting
            if not check_reset_rate_limit(email):
                cooldown = get_reset_cooldown_minutes(email)
                return render_reset_request_page(
                    error=f"Ai depășit limita de cereri. Încearcă din nou în {cooldown} minute."
                )
            
            # Căutăm doctorul
            doctor = Doctor.query.filter_by(email=email).first()
            
            # IMPORTANT: NU dezvăluim dacă email-ul există sau nu (securitate)
            # Întotdeauna afișăm mesaj de succes
            
            if doctor and doctor.is_active:
                # Generăm token reset
                token, expires_at = generate_reset_token_with_expiry(doctor.id, hours=1)
                
                # Salvăm în database
                reset_token = PasswordResetToken(
                    token=token,
                    doctor_id=doctor.id,
                    expires_at=expires_at,
                    ip_address=request.remote_addr
                )
                db.session.add(reset_token)
                db.session.commit()
                
                # Trimitem email
                send_password_reset_email(
                    doctor_email=doctor.email,
                    doctor_name=doctor.full_name,
                    reset_token=token,
                    expires_hours=1
                )
                
                logger.info(f"📧 Email reset parolă trimis către {email[:3]}***")
            else:
                logger.debug(f"Cerere reset pentru email inexistent/inactiv: {email[:3]}***")
            
            # Înregistrăm încercarea
            record_reset_attempt(email)
            
            # Mesaj generic de succes (nu dezvăluim dacă email-ul există)
            return render_reset_request_page(
                success="Dacă adresa de email este înregistrată în sistem, vei primi un email cu instrucțiuni de resetare."
            )
        
        # GET request
        return render_reset_request_page()


def render_reset_request_page(error=None, success=None):
    """Renderizează pagina de cerere reset parolă."""
    template = """
    <!DOCTYPE html>
    <html lang="ro">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Resetare Parolă</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }
            .container {
                background: white;
                padding: 40px;
                border-radius: 15px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                width: 100%;
                max-width: 450px;
            }
            h1 { color: #667eea; font-size: 26px; margin-bottom: 10px; text-align: center; }
            p { color: #666; font-size: 14px; margin-bottom: 25px; text-align: center; line-height: 1.6; }
            .form-group { margin-bottom: 20px; }
            .form-group label { display: block; margin-bottom: 8px; color: #333; font-weight: 600; font-size: 14px; }
            .form-group input[type="email"] {
                width: 100%;
                padding: 12px 15px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                font-size: 15px;
                transition: all 0.3s ease;
            }
            .form-group input:focus {
                outline: none;
                border-color: #667eea;
                box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
            }
            .btn { width: 100%; padding: 14px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                   color: white; border: none; border-radius: 8px; font-size: 16px; font-weight: 600;
                   cursor: pointer; transition: all 0.3s ease; }
            .btn:hover { transform: translateY(-2px); box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4); }
            .error-message { background: #fee; border-left: 4px solid #e74c3c; padding: 12px;
                            margin-bottom: 20px; border-radius: 5px; color: #c0392b; font-size: 14px; }
            .success-message { background: #efe; border-left: 4px solid #27ae60; padding: 12px;
                              margin-bottom: 20px; border-radius: 5px; color: #27ae60; font-size: 14px; }
            .back-link { text-align: center; margin-top: 20px; }
            .back-link a { color: #667eea; text-decoration: none; font-size: 14px; font-weight: 600; }
            .back-link a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔐 Resetare Parolă</h1>
            <p>Introdu adresa de email asociată contului tău și vei primi instrucțiuni de resetare.</p>
            
            {% if error %}
            <div class="error-message">❌ {{ error }}</div>
            {% endif %}
            
            {% if success %}
            <div class="success-message">✅ {{ success }}</div>
            {% endif %}
            
            <form method="POST" action="/request-reset">
                <div class="form-group">
                    <label for="email">Adresa de Email</label>
                    <input type="email" id="email" name="email" placeholder="exemplu@medical.ro" required autofocus>
                </div>
                <button type="submit" class="btn">📧 Trimite Link Reset</button>
            </form>
            
            <div class="back-link">
                <a href="/login">← Înapoi la autentificare</a>
            </div>
        </div>
    </body>
    </html>
    """
    from jinja2 import Template
    return Template(template).render(error=error, success=success)


# ==============================================================================
# ROUTE: /reset-password (form reset cu token)
# ==============================================================================

def route_reset_password(app_server):
    """
    Configurează route-ul /reset-password pentru resetare efectivă.
    
    Args:
        app_server: Instanța Flask
    """
    
    @app_server.route('/reset-password', methods=['GET', 'POST'])
    def reset_password():
        """
        Handler pentru resetare parolă cu token.
        
        GET: Afișează formularul (verifică token)
        POST: Salvează parola nouă
        """
        token = request.args.get('token', '')
        
        if not token:
            return render_reset_password_page(error="Token invalid sau lipsă.")
        
        # Verificăm token-ul
        reset_token = PasswordResetToken.query.filter_by(token=token).first()
        
        if not reset_token or not reset_token.is_valid():
            logger.warning(f"Tentativă folosire token invalid/expirat")
            return render_reset_password_page(
                error="Token invalid sau expirat. Solicită un nou link de resetare."
            )
        
        if request.method == 'POST':
            new_password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')
            
            # Validări
            if not new_password or not confirm_password:
                return render_reset_password_page(
                    token=token,
                    error="Te rugăm să completezi ambele câmpuri."
                )
            
            if new_password != confirm_password:
                return render_reset_password_page(
                    token=token,
                    error="Parolele nu coincid."
                )
            
            # Validare putere parolă
            is_valid, message = validate_password_strength(new_password)
            if not is_valid:
                return render_reset_password_page(token=token, error=message)
            
            # Salvăm parola nouă
            doctor = reset_token.doctor
            doctor.password_hash = hash_password(new_password)
            doctor.unlock_account()  # Deblocăm contul dacă era blocat
            
            # Marcăm token-ul ca folosit
            reset_token.mark_as_used()
            
            db.session.commit()
            
            # Trimitem email de confirmare
            send_password_changed_email(doctor.email, doctor.full_name)
            
            logger.info(f"✅ Parolă resetată cu succes pentru {doctor.email}")
            
            # Redirect la login cu mesaj de succes
            return redirect('/login?success=password_reset')
        
        # GET request - afișăm formularul
        return render_reset_password_page(token=token)


def render_reset_password_page(token='', error=None):
    """Renderizează pagina de setare parolă nouă."""
    template = """
    <!DOCTYPE html>
    <html lang="ro">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Setare Parolă Nouă</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }
            .container {
                background: white;
                padding: 40px;
                border-radius: 15px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                width: 100%;
                max-width: 450px;
            }
            h1 { color: #667eea; font-size: 26px; margin-bottom: 10px; text-align: center; }
            p { color: #666; font-size: 14px; margin-bottom: 25px; text-align: center; line-height: 1.6; }
            .form-group { margin-bottom: 20px; }
            .form-group label { display: block; margin-bottom: 8px; color: #333; font-weight: 600; font-size: 14px; }
            .form-group input[type="password"] {
                width: 100%;
                padding: 12px 15px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                font-size: 15px;
                transition: all 0.3s ease;
            }
            .form-group input:focus {
                outline: none;
                border-color: #667eea;
                box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
            }
            .btn { width: 100%; padding: 14px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                   color: white; border: none; border-radius: 8px; font-size: 16px; font-weight: 600;
                   cursor: pointer; transition: all 0.3s ease; }
            .btn:hover { transform: translateY(-2px); box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4); }
            .error-message { background: #fee; border-left: 4px solid #e74c3c; padding: 12px;
                            margin-bottom: 20px; border-radius: 5px; color: #c0392b; font-size: 14px; }
            .requirements { background: #f0f8ff; border: 1px solid #b3d9ff; padding: 15px;
                           border-radius: 8px; margin-bottom: 20px; font-size: 13px; }
            .requirements ul { margin: 10px 0 0 20px; }
            .requirements li { color: #555; line-height: 1.8; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔑 Setare Parolă Nouă</h1>
            <p>Alege o parolă sigură pentru contul tău.</p>
            
            {% if error %}
            <div class="error-message">❌ {{ error }}</div>
            {% endif %}
            
            <div class="requirements">
                <strong>📋 Cerințe parolă:</strong>
                <ul>
                    <li>Minimum 8 caractere</li>
                    <li>Cel puțin o literă mare (A-Z)</li>
                    <li>Cel puțin o literă mică (a-z)</li>
                    <li>Cel puțin o cifră (0-9)</li>
                    <li>Cel puțin un caracter special (!@#$...)</li>
                </ul>
            </div>
            
            <form method="POST" action="/reset-password?token={{ token }}">
                <div class="form-group">
                    <label for="password">Parolă Nouă</label>
                    <input type="password" id="password" name="password" placeholder="••••••••" required autofocus>
                </div>
                
                <div class="form-group">
                    <label for="confirm_password">Confirmă Parola</label>
                    <input type="password" id="confirm_password" name="confirm_password" placeholder="••••••••" required>
                </div>
                
                <button type="submit" class="btn">✅ Salvează Parola</button>
            </form>
        </div>
    </body>
    </html>
    """
    from jinja2 import Template
    return Template(template).render(token=token, error=error)


# ==============================================================================
# ROUTE: /signup (înregistrare utilizator nou)
# ==============================================================================

def route_signup(app_server):
    """
    Configurează route-ul /signup pentru înregistrare utilizatori noi.
    
    Args:
        app_server: Instanța Flask
    """
    
    @app_server.route('/signup', methods=['GET', 'POST'])
    def signup():
        """
        Handler pentru înregistrare utilizator nou.
        
        GET: Afișează formularul de înregistrare
        POST: Creează contul nou
        """
        # Verificăm dacă sign up-ul este activat (poate fi controlat prin variabilă de mediu)
        signup_enabled = os.getenv('ALLOW_PUBLIC_SIGNUP', 'true').lower() == 'true'
        
        if not signup_enabled:
            return render_signup_page(
                error="Înregistrarea publică este dezactivată. Contactați administratorul pentru a crea un cont."
            )
        
        if request.method == 'POST':
            # Extragem datele din formular
            full_name = request.form.get('full_name', '').strip()
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')
            
            # Validări de bază
            if not full_name or not email or not password or not confirm_password:
                logger.warning("Tentativă înregistrare cu câmpuri goale")
                return render_signup_page(
                    error="Te rugăm să completezi toate câmpurile.",
                    full_name=full_name,
                    email=email
                )
            
            # Verificăm dacă parolele coincid
            if password != confirm_password:
                return render_signup_page(
                    error="Parolele nu coincid.",
                    full_name=full_name,
                    email=email
                )
            
            # Validare putere parolă
            is_valid, message = validate_password_strength(password)
            if not is_valid:
                return render_signup_page(
                    error=message,
                    full_name=full_name,
                    email=email
                )
            
            # Verificăm dacă email-ul există deja
            existing_doctor = Doctor.query.filter_by(email=email).first()
            if existing_doctor:
                logger.warning(f"Tentativă înregistrare cu email existent: {email[:3]}***")
                return render_signup_page(
                    error="Există deja un cont cu acest email. Te rugăm să te autentifici sau să resetezi parola.",
                    full_name=full_name
                )
            
            # Creăm contul nou
            try:
                new_doctor = Doctor(
                    email=email,
                    password_hash=hash_password(password),
                    full_name=full_name,
                    is_admin=False,  # Conturile noi NU sunt admin by default
                    is_active=True
                )
                
                db.session.add(new_doctor)
                db.session.commit()
                
                logger.info(f"✅ Cont nou creat: {email}")
                
                # Redirect la login cu mesaj de succes
                return redirect('/login?success=account_created')
                
            except Exception as e:
                logger.error(f"❌ Eroare la crearea contului: {e}")
                db.session.rollback()
                return render_signup_page(
                    error="A apărut o eroare la crearea contului. Te rugăm să încerci din nou.",
                    full_name=full_name,
                    email=email
                )
        
        # GET request - afișăm formularul
        return render_signup_page()


def render_signup_page(error=None, full_name='', email=''):
    """
    Renderizează pagina de înregistrare cu template HTML.
    
    Args:
        error: Mesaj de eroare (opțional)
        full_name: Nume pre-completat (opțional)
        email: Email pre-completat (opțional)
        
    Returns:
        HTML string
    """
    template = """
    <!DOCTYPE html>
    <html lang="ro">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Înregistrare - Platformă Pulsoximetrie</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }
            .signup-container {
                background: white;
                padding: 40px;
                border-radius: 15px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                width: 100%;
                max-width: 480px;
            }
            .logo {
                text-align: center;
                margin-bottom: 30px;
            }
            .logo h1 {
                color: #667eea;
                font-size: 28px;
                margin-bottom: 10px;
            }
            .logo p {
                color: #777;
                font-size: 14px;
            }
            .form-group {
                margin-bottom: 20px;
            }
            .form-group label {
                display: block;
                margin-bottom: 8px;
                color: #333;
                font-weight: 600;
                font-size: 14px;
            }
            .form-group input[type="text"],
            .form-group input[type="email"],
            .form-group input[type="password"] {
                width: 100%;
                padding: 12px 15px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                font-size: 15px;
                transition: all 0.3s ease;
            }
            .form-group input:focus {
                outline: none;
                border-color: #667eea;
                box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
            }
            .btn-signup {
                width: 100%;
                padding: 14px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
            }
            .btn-signup:hover {
                transform: translateY(-2px);
                box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
            }
            .btn-signup:active {
                transform: translateY(0);
            }
            .error-message {
                background: #fee;
                border-left: 4px solid #e74c3c;
                padding: 12px;
                margin-bottom: 20px;
                border-radius: 5px;
                color: #c0392b;
                font-size: 14px;
            }
            .password-requirements {
                background: #f0f8ff;
                border: 1px solid #b3d9ff;
                padding: 12px;
                border-radius: 8px;
                margin-bottom: 20px;
                font-size: 12px;
            }
            .password-requirements ul {
                margin: 8px 0 0 20px;
            }
            .password-requirements li {
                color: #555;
                line-height: 1.6;
            }
            .login-link {
                text-align: center;
                margin-top: 20px;
            }
            .login-link a {
                color: #667eea;
                text-decoration: none;
                font-size: 14px;
                font-weight: 600;
            }
            .login-link a:hover {
                text-decoration: underline;
            }
            .divider {
                text-align: center;
                margin: 25px 0;
                color: #999;
                font-size: 13px;
            }
        </style>
    </head>
    <body>
        <div class="signup-container">
            <div class="logo">
                <h1>✨ Înregistrare</h1>
                <p>Platformă Pulsoximetrie</p>
            </div>
            
            {% if error %}
            <div class="error-message">
                ❌ {{ error }}
            </div>
            {% endif %}
            
            <form method="POST" action="/signup">
                <div class="form-group">
                    <label for="full_name">Nume Complet</label>
                    <input 
                        type="text" 
                        id="full_name" 
                        name="full_name" 
                        value="{{ full_name }}"
                        placeholder="Ex: Dr. Popescu Ion"
                        required 
                        autofocus
                    >
                </div>
                
                <div class="form-group">
                    <label for="email">Email</label>
                    <input 
                        type="email" 
                        id="email" 
                        name="email" 
                        value="{{ email }}"
                        placeholder="exemplu@medical.ro"
                        required
                    >
                </div>
                
                <div class="password-requirements">
                    <strong>📋 Cerințe parolă:</strong>
                    <ul>
                        <li>Minimum 8 caractere</li>
                        <li>Cel puțin o literă mare (A-Z)</li>
                        <li>Cel puțin o literă mică (a-z)</li>
                        <li>Cel puțin o cifră (0-9)</li>
                        <li>Cel puțin un caracter special (!@#$...)</li>
                    </ul>
                </div>
                
                <div class="form-group">
                    <label for="password">Parolă</label>
                    <input 
                        type="password" 
                        id="password" 
                        name="password" 
                        placeholder="••••••••"
                        required
                    >
                </div>
                
                <div class="form-group">
                    <label for="confirm_password">Confirmă Parola</label>
                    <input 
                        type="password" 
                        id="confirm_password" 
                        name="confirm_password" 
                        placeholder="••••••••"
                        required
                    >
                </div>
                
                <button type="submit" class="btn-signup">
                    ✨ Creează Cont
                </button>
            </form>
            
            <div class="login-link">
                Ai deja cont? <a href="/login">Autentifică-te</a>
            </div>
            
            <div class="divider">
                © 2025 Platformă Pulsoximetrie
            </div>
        </div>
    </body>
    </html>
    """
    
    from jinja2 import Template
    return Template(template).render(error=error, full_name=full_name, email=email)


# ==============================================================================
# FUNCȚIE INIȚIALIZARE - APELATĂ DIN run_medical.py
# ==============================================================================

def init_auth_routes(app):
    """
    Inițializează toate route-urile de autentificare + health check.
    
    Args:
        app: Instanța Dash (cu app.server = Flask)
    """
    route_health(app.server)
    route_login(app.server)
    route_logout(app.server)
    route_signup(app.server)
    route_request_reset(app.server)
    route_reset_password(app.server)
    
    logger.info("✅ Route-uri inițializate: /health, /login, /logout, /signup, /request-reset, /reset-password")


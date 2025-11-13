# ==============================================================================
# auth/email_service.py
# ------------------------------------------------------------------------------
# ROL: Serviciu trimitere email-uri prin Brevo API (ex-Sendinblue)
#      - Reset parolă
#      - Notificări login (opțional)
#      - Welcome emails
#
# RESPECTĂ: .cursorrules - Zero date personale în log-uri
# ==============================================================================

import os
import requests
from typing import Optional, Dict
from logger_setup import logger
from jinja2 import Template


# === CONFIGURARE BREVO API ===
BREVO_API_KEY = os.getenv('BREVO_API_KEY', '')
BREVO_API_URL = 'https://api.brevo.com/v3/smtp/email'
SENDER_EMAIL = os.getenv('SENDER_EMAIL', 'noreply@pulsoximetrie.ro')
SENDER_NAME = os.getenv('SENDER_NAME', 'Platformă Pulsoximetrie')
APP_URL = os.getenv('APP_URL', 'http://localhost:8050')


# ==============================================================================
# FUNCȚII CORE - TRIMITERE EMAIL
# ==============================================================================

def send_email(to_email: str, to_name: str, subject: str, 
               html_content: str, text_content: Optional[str] = None) -> bool:
    """
    Trimite un email prin Brevo API.
    
    Args:
        to_email: Email destinatar
        to_name: Numele destinatarului
        subject: Subject-ul email-ului
        html_content: Conținutul HTML
        text_content: Conținutul plain text (opțional, fallback)
        
    Returns:
        bool: True dacă trimiterea a reușit
    """
    if not BREVO_API_KEY:
        logger.error("❌ BREVO_API_KEY nu este setat! Email-ul NU poate fi trimis.")
        logger.warning("💡 Setați BREVO_API_KEY în .env pentru trimiterea email-urilor.")
        return False
    
    headers = {
        'accept': 'application/json',
        'api-key': BREVO_API_KEY,
        'content-type': 'application/json'
    }
    
    payload = {
        'sender': {
            'name': SENDER_NAME,
            'email': SENDER_EMAIL
        },
        'to': [
            {
                'email': to_email,
                'name': to_name
            }
        ],
        'subject': subject,
        'htmlContent': html_content
    }
    
    # Adăugăm text content dacă e disponibil
    if text_content:
        payload['textContent'] = text_content
    
    try:
        response = requests.post(BREVO_API_URL, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 201:
            logger.info(f"✅ Email trimis cu succes către {to_email[:3]}***@{to_email.split('@')[1]}")
            return True
        else:
            logger.error(f"❌ Eroare trimitere email: {response.status_code} - {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        logger.error("❌ Timeout la trimiterea email-ului (>10s)")
        return False
    except Exception as e:
        logger.error(f"❌ Eroare neașteptată la trimiterea email-ului: {e}", exc_info=True)
        return False


# ==============================================================================
# FUNCȚII SPECIFICE - TIPURI DE EMAIL-URI
# ==============================================================================

def send_password_reset_email(doctor_email: str, doctor_name: str, 
                              reset_token: str, expires_hours: int = 1) -> bool:
    """
    Trimite email de reset parolă cu token securizat.
    
    Args:
        doctor_email: Email-ul doctorului
        doctor_name: Numele doctorului
        reset_token: Token-ul de reset generat
        expires_hours: Validitate în ore (default: 1)
        
    Returns:
        bool: True dacă trimiterea a reușit
    """
    # Construim link-ul de reset
    reset_link = f"{APP_URL}/reset-password?token={reset_token}"
    
    # Încărcăm template-ul HTML
    template_path = os.path.join('templates', 'email_reset_password.html')
    
    if os.path.exists(template_path):
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
    else:
        # Fallback - template inline simplu
        logger.warning(f"⚠️ Template {template_path} nu există - folosesc template inline")
        template_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: #3498db; color: white; padding: 20px; text-align: center; }
                .content { background: #f9f9f9; padding: 30px; }
                .button { display: inline-block; padding: 12px 30px; background: #2ecc71; 
                         color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }
                .footer { text-align: center; color: #777; font-size: 12px; margin-top: 30px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔐 Resetare Parolă</h1>
                </div>
                <div class="content">
                    <p>Bună, <strong>{{ doctor_name }}</strong>!</p>
                    
                    <p>Am primit o cerere de resetare a parolei pentru contul tău 
                       (<strong>{{ doctor_email }}</strong>).</p>
                    
                    <p>Dacă ai solicitat această resetare, apasă pe butonul de mai jos:</p>
                    
                    <center>
                        <a href="{{ reset_link }}" class="button">
                            🔑 Resetează Parola
                        </a>
                    </center>
                    
                    <p style="color: #e74c3c; margin-top: 20px;">
                        <strong>⚠️ IMPORTANT:</strong> Acest link este valabil doar 
                        <strong>{{ expires_hours }} oră</strong> și poate fi folosit o singură dată.
                    </p>
                    
                    <p>Dacă nu ai solicitat resetarea parolei, ignoră acest email. 
                       Parola ta rămâne neschimbată.</p>
                    
                    <hr style="margin: 30px 0; border: none; border-top: 1px solid #ddd;">
                    
                    <p style="font-size: 12px; color: #777;">
                        <strong>Link alternativ:</strong> Dacă butonul nu funcționează, 
                        copiază acest link în browser:<br>
                        <code>{{ reset_link }}</code>
                    </p>
                </div>
                <div class="footer">
                    <p>© 2025 Platformă Pulsoximetrie - Toate drepturile rezervate</p>
                    <p>Acest email a fost trimis automat. Nu răspunde la acest mesaj.</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    # Renderizăm template-ul
    template = Template(template_content)
    html_content = template.render(
        doctor_name=doctor_name,
        doctor_email=doctor_email,
        reset_link=reset_link,
        expires_hours=expires_hours
    )
    
    # Text version (fallback)
    text_content = f"""
    Bună, {doctor_name}!
    
    Am primit o cerere de resetare a parolei pentru contul tău ({doctor_email}).
    
    Dacă ai solicitat această resetare, accesează link-ul de mai jos:
    {reset_link}
    
    ⚠️ IMPORTANT: Acest link este valabil doar {expires_hours} oră și poate fi folosit o singură dată.
    
    Dacă nu ai solicitat resetarea parolei, ignoră acest email.
    
    ---
    © 2025 Platformă Pulsoximetrie
    """
    
    subject = "🔐 Resetare Parolă - Platformă Pulsoximetrie"
    
    return send_email(doctor_email, doctor_name, subject, html_content, text_content)


def send_welcome_email(doctor_email: str, doctor_name: str, 
                      temporary_password: Optional[str] = None) -> bool:
    """
    Trimite email de bun venit la crearea contului.
    
    Args:
        doctor_email: Email-ul doctorului
        doctor_name: Numele doctorului
        temporary_password: Parolă temporară (opțional)
        
    Returns:
        bool: True dacă trimiterea a reușit
    """
    login_link = f"{APP_URL}/login"
    
    # Template simplu inline
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: #2ecc71; color: white; padding: 20px; text-align: center; }}
            .content {{ background: #f9f9f9; padding: 30px; }}
            .button {{ display: inline-block; padding: 12px 30px; background: #3498db; 
                     color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
            .footer {{ text-align: center; color: #777; font-size: 12px; margin-top: 30px; }}
            .code {{ background: #e8f4f8; padding: 10px; border-left: 4px solid #3498db; 
                    font-family: monospace; margin: 15px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎉 Bun Venit!</h1>
            </div>
            <div class="content">
                <p>Bună, <strong>{doctor_name}</strong>!</p>
                
                <p>Contul tău a fost creat cu succes pe <strong>Platforma Pulsoximetrie</strong>.</p>
                
                <p><strong>Email:</strong> {doctor_email}</p>
                
                {f'<div class="code"><strong>Parolă temporară:</strong> <code>{temporary_password}</code></div>' if temporary_password else ''}
                
                {f'<p style="color: #e74c3c;"><strong>⚠️ IMPORTANT:</strong> Schimbă această parolă temporară la prima autentificare!</p>' if temporary_password else ''}
                
                <center>
                    <a href="{login_link}" class="button">
                        🔐 Autentifică-te Acum
                    </a>
                </center>
                
                <p>Dacă întâmpini probleme, contactează administratorul platformei.</p>
            </div>
            <div class="footer">
                <p>© 2025 Platformă Pulsoximetrie - Toate drepturile rezervate</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text_content = f"""
    Bună, {doctor_name}!
    
    Contul tău a fost creat cu succes pe Platforma Pulsoximetrie.
    
    Email: {doctor_email}
    {'Parolă temporară: ' + temporary_password if temporary_password else ''}
    
    {'⚠️ IMPORTANT: Schimbă această parolă temporară la prima autentificare!' if temporary_password else ''}
    
    Autentifică-te la: {login_link}
    
    ---
    © 2025 Platformă Pulsoximetrie
    """
    
    subject = "🎉 Bun venit pe Platforma Pulsoximetrie!"
    
    return send_email(doctor_email, doctor_name, subject, html_content, text_content)


def send_login_notification_email(doctor_email: str, doctor_name: str, 
                                  ip_address: str, timestamp: str, 
                                  is_new_ip: bool = False) -> bool:
    """
    Trimite notificare de login (opțional, pentru securitate).
    
    Args:
        doctor_email: Email-ul doctorului
        doctor_name: Numele doctorului
        ip_address: IP-ul de unde s-a autentificat
        timestamp: Data și ora autentificării
        is_new_ip: Dacă e un IP nou (alert)
        
    Returns:
        bool: True dacă trimiterea a reușit
    """
    alert_message = ""
    if is_new_ip:
        alert_message = """
        <div style="background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0;">
            <strong>⚠️ ALERTĂ:</strong> Acesta este un IP nou din care te-ai autentificat. 
            Dacă nu ai fost tu, schimbă-ți parola imediat!
        </div>
        """
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: #3498db; color: white; padding: 20px; text-align: center; }}
            .content {{ background: #f9f9f9; padding: 30px; }}
            .footer {{ text-align: center; color: #777; font-size: 12px; margin-top: 30px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔐 Notificare Autentificare</h1>
            </div>
            <div class="content">
                <p>Bună, <strong>{doctor_name}</strong>!</p>
                
                <p>Contul tău (<strong>{doctor_email}</strong>) a fost accesat recent:</p>
                
                <ul>
                    <li><strong>Data și ora:</strong> {timestamp}</li>
                    <li><strong>Adresa IP:</strong> {ip_address}</li>
                </ul>
                
                {alert_message}
                
                <p>Dacă tu ai fost, poți ignora acest mesaj.</p>
                
                <p>Dacă nu recunoști această activitate, 
                   <strong style="color: #e74c3c;">schimbă-ți parola imediat</strong> 
                   și contactează administratorul.</p>
            </div>
            <div class="footer">
                <p>© 2025 Platformă Pulsoximetrie</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    subject = "🔐 Notificare Autentificare" + (" - IP NOU!" if is_new_ip else "")
    
    return send_email(doctor_email, doctor_name, subject, html_content)


def send_password_changed_email(doctor_email: str, doctor_name: str) -> bool:
    """
    Trimite confirmare schimbare parolă.
    
    Args:
        doctor_email: Email-ul doctorului
        doctor_name: Numele doctorului
        
    Returns:
        bool: True dacă trimiterea a reușit
    """
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: #2ecc71; color: white; padding: 20px; text-align: center; }}
            .content {{ background: #f9f9f9; padding: 30px; }}
            .footer {{ text-align: center; color: #777; font-size: 12px; margin-top: 30px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>✅ Parolă Schimbată</h1>
            </div>
            <div class="content">
                <p>Bună, <strong>{doctor_name}</strong>!</p>
                
                <p>Parola contului tău (<strong>{doctor_email}</strong>) a fost schimbată cu succes.</p>
                
                <p>Dacă nu ai efectuat tu această modificare, 
                   <strong style="color: #e74c3c;">contactează imediat administratorul</strong>!</p>
            </div>
            <div class="footer">
                <p>© 2025 Platformă Pulsoximetrie</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    subject = "✅ Parola ta a fost schimbată"
    
    return send_email(doctor_email, doctor_name, subject, html_content)


# ==============================================================================
# FUNCȚII UTILITARE
# ==============================================================================

def test_email_configuration() -> bool:
    """
    Testează configurarea Brevo API (rulat la pornirea aplicației).
    
    Returns:
        bool: True dacă configurarea e OK
    """
    if not BREVO_API_KEY:
        logger.error("❌ BREVO_API_KEY nu este setat!")
        logger.warning("💡 Email-urile NU vor fi trimise până când setați cheia API în .env")
        return False
    
    # Verificăm validitatea cheii (fără a trimite email)
    headers = {
        'accept': 'application/json',
        'api-key': BREVO_API_KEY
    }
    
    try:
        response = requests.get('https://api.brevo.com/v3/account', headers=headers, timeout=5)
        
        if response.status_code == 200:
            account_data = response.json()
            logger.info(f"✅ Brevo API configurată corect (Email: {account_data.get('email', 'N/A')})")
            return True
        else:
            logger.error(f"❌ Brevo API key invalid: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Eroare verificare Brevo API: {e}")
        return False


# Testăm configurarea la import (doar dacă BREVO_API_KEY este setat)
if BREVO_API_KEY:
    test_email_configuration()
else:
    logger.warning("⚠️ BREVO_API_KEY nu este setat - email-urile vor fi dezactivate")

logger.info("✅ Modulul email_service.py inițializat cu succes.")


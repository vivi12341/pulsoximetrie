# 🔐 SISTEM AUTENTIFICARE - Platformă Pulsoximetrie

## 📋 Cuprins
- [Prezentare Generală](#-prezentare-generală)
- [Arhitectură Tehnică](#-arhitectură-tehnică)
- [Instalare & Setup](#-instalare--setup)
- [Configurare](#-configurare)
- [Utilizare](#-utilizare)
- [Securitate](#-securitate)
- [API & Integrări](#-api--integrări)
- [Troubleshooting](#-troubleshooting)
- [FAQ](#-faq)

---

## 🎯 Prezentare Generală

Sistemul de autentificare implementat oferă:

✅ **Autentificare Email + Parolă** pentru medici  
✅ **Recuperare Parolă prin Email** (token securizat, valid 1h)  
✅ **Rate Limiting** (protecție brute-force)  
✅ **Session Management** (30 zile cu "Remember me")  
✅ **Tracking Login-uri** (IP, timestamp, device)  
✅ **GDPR Compliant** (zero date personale în log-uri)  

### 🔑 Concepte Cheie

- **MEDICI** = Autentificare obligatorie (login/parolă)
- **PACIENȚI** = Acces prin token UUID (fără autentificare) - **NEAFECTAT**
- **ADMIN** = Rol special cu permisiuni extinse

---

## 🏗️ Arhitectură Tehnică

### Stack Tehnologic

```
┌─────────────────────────────────────────────────┐
│           FRONTEND (Dash + HTML)                │
│  - Login Form (/login)                          │
│  - Reset Password Form (/request-reset)         │
│  - Dashboard Medical (protejat)                 │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│        BACKEND (Flask + Flask-Login)            │
│  - Route-uri: /login, /logout, /reset-password │
│  - Middleware: @login_required                  │
│  - Session Management                           │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│         DATABASE (PostgreSQL)                   │
│  - Tabele: doctors, password_reset_tokens,      │
│            login_sessions                       │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│          EMAIL SERVICE (Brevo API)              │
│  - Reset parolă                                 │
│  - Notificări (opțional)                        │
└─────────────────────────────────────────────────┘
```

### Structură Fișiere

```
pulsoximetrie/
├── auth/                              # Modul autentificare
│   ├── __init__.py
│   ├── models.py                      # SQLAlchemy models
│   ├── auth_manager.py                # Flask-Login integration
│   ├── password_manager.py            # Argon2 hashing
│   ├── email_service.py               # Brevo API
│   ├── rate_limiter.py                # Protecție brute-force
│   └── decorators.py                  # @login_required
│
├── templates/                         # Template-uri email HTML
│   ├── email_reset_password.html
│   └── email_welcome.html
│
├── migrations/                        # Database migrations
│   └── migrate_json_to_postgres.py
│
├── auth_routes.py                     # Flask routes (/login, /logout, /reset)
├── run_medical.py                     # Entry point (actualizat cu auth)
├── env_template.txt                   # Template variabile mediu
└── README_AUTH.md                     # Această documentație
```

---

## 🚀 Instalare & Setup

### 1. Instalare Dependențe

```bash
pip install -r requirements.txt
```

**Dependențe noi adăugate:**
- `Flask-Login==0.6.3` - Session management
- `argon2-cffi==23.1.0` - Password hashing
- `Flask-SQLAlchemy==3.1.1` - ORM PostgreSQL
- `psycopg2-binary==2.9.9` - PostgreSQL driver
- `Flask-Migrate==4.0.5` - Database migrations
- `sib-api-v3-sdk==7.6.0` - Brevo API
- `python-dotenv==1.0.0` - Variabile mediu

### 2. Setup PostgreSQL

#### Opțiunea A: PostgreSQL Local (Development)

```bash
# Instalare PostgreSQL
# Windows: https://www.postgresql.org/download/windows/
# Linux: sudo apt install postgresql postgresql-contrib

# Creare database
psql -U postgres
CREATE DATABASE pulsoximetrie;
\q
```

#### Opțiunea B: Railway (Production)

1. Creați cont pe [Railway.app](https://railway.app)
2. Creați un nou proiect PostgreSQL
3. Copiați `DATABASE_URL` din Railway Dashboard

### 3. Configurare Variabile de Mediu

```bash
# Copiați template-ul
cp env_template.txt .env

# Editați .env cu valorile reale
nano .env
```

**Variabile OBLIGATORII:**

```env
SECRET_KEY=<generați-cu-python-secrets>
DATABASE_URL=postgresql://user:pass@host:port/db
BREVO_API_KEY=xkeysib-your-api-key
```

**Generare SECRET_KEY securizat:**

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 4. Setup Email Service (Brevo)

1. Creați cont gratuit pe [Brevo.com](https://www.brevo.com) (ex-Sendinblue)
2. Navigați la **Settings > API Keys**
3. Generați o nouă cheie API
4. Adăugați cheia în `.env` ca `BREVO_API_KEY`
5. Verificați email-ul sender în **Settings > Senders**

**Plan Gratuit Brevo:** 300 email-uri/zi (suficient!)

### 5. Migrare Database & Creare Admin

```bash
# Rulați scriptul de migrare
python migrations/migrate_json_to_postgres.py
```

**Output așteptat:**

```
✅ UTILIZATOR ADMIN CREAT CU SUCCES!
📧 Email: admin@pulsoximetrie.ro
🔑 Parolă: <parolă-generată>
```

**⚠️ IMPORTANT:** Salvați credențialele din `ADMIN_CREDENTIALS.txt` și ștergeți fișierul!

---

## ⚙️ Configurare

### Variabile de Mediu (.env)

| Variabilă | Descriere | Exemplu | Obligatoriu |
|-----------|-----------|---------|-------------|
| `SECRET_KEY` | Cheie secretă Flask (64 caractere) | `abc123...` | ✅ Da |
| `DATABASE_URL` | Connection string PostgreSQL | `postgresql://...` | ✅ Da |
| `BREVO_API_KEY` | Cheia API Brevo pentru email-uri | `xkeysib-...` | ✅ Da |
| `SENDER_EMAIL` | Email-ul de trimitere | `noreply@...` | ✅ Da |
| `SENDER_NAME` | Numele afișat în email-uri | `Platformă Pulsox.` | ❌ Nu |
| `APP_URL` | URL public al aplicației | `http://localhost:8050` | ❌ Nu |
| `FLASK_ENV` | Mediu rulare (dev/production) | `development` | ❌ Nu |

### Parametri Securitate

**În `auth/password_manager.py`:**

```python
# Argon2 - Parametrii OWASP 2024
time_cost=2           # Număr iterații
memory_cost=102400    # 100 MB memorie
parallelism=8         # 8 thread-uri
hash_len=32           # 32 bytes hash
salt_len=16           # 16 bytes salt
```

**În `auth/rate_limiter.py`:**

```python
MAX_LOGIN_ATTEMPTS = 5         # Încercări eșuate înainte de blocare
LOGIN_WINDOW_MINUTES = 15      # Durata blocare (minute)
MAX_RESET_ATTEMPTS = 3         # Cereri reset parolă/oră
RESET_WINDOW_HOURS = 1         # Fereastră timp reset
```

---

## 💻 Utilizare

### Pornire Aplicație

```bash
python run_medical.py
```

**Server disponibil la:** `http://localhost:8050`

### Workflow Autentificare

#### 1. Login Medic

```
1. Accesați http://localhost:8050/login
2. Introduceți email + parolă
3. (Opțional) Bifați "Ține-mă minte" → sesiune 30 zile
4. Click "Autentifică-te"
5. Redirect la dashboard medical
```

#### 2. Recuperare Parolă

```
1. Click "Am uitat parola" pe pagina login
2. Introduceți email-ul
3. Verificați inbox-ul (spam/promotions dacă nu apare)
4. Click pe link-ul din email (valid 1h)
5. Setați parolă nouă (cerințe: 8+ caractere, majusculă, cifră, special)
6. Redirect la login
```

#### 3. Logout

```
1. Click "Deconectare" din header
2. Sau accesați direct: http://localhost:8050/logout
```

### Acces Pacienți (NEAFECTAT)

**Pacienții accesează în continuare fără autentificare:**

```
http://localhost:8050/?token=<uuid-pacient>
```

✅ Token-urile UUID rămân valabile  
✅ Sistemul actual de link-uri persistente NESCHIMBAT  
✅ Privacy by Design păstrat  

---

## 🔒 Securitate

### Caracteristici Implementate

#### 1. Password Hashing - Argon2

- **Algoritm:** Argon2id (câștigător Password Hashing Competition)
- **Mai sigur decât:** bcrypt, PBKDF2, scrypt
- **Parametrii:** OWASP 2024 recommendations
- **Auto-rehash:** Parolele vechi se re-hash-uiesc automat cu parametri noi

#### 2. Rate Limiting

**Login:**
- 5 încercări eșuate → blocare 15 minute (per email ȘI per IP)
- Contorul se resetează după login reușit

**Reset Parolă:**
- 3 cereri/oră per email
- Mesaj generic (nu dezvăluie dacă email-ul există)

#### 3. Token-uri Reset Parolă

- **Generare:** `secrets.token_hex(32)` (criptografic sigur)
- **Valabilitate:** 1 oră
- **Folosire:** O singură dată (marcat ca `used_at`)
- **Cleanup:** Ștergere automată token-uri expirate

#### 4. Session Management

- **Cookie securizat:** `HttpOnly=True`, `SameSite=Lax`
- **HTTPS:** `Secure=True` în producție
- **Durata:** 1 zi (fără "Remember me"), 30 zile (cu "Remember me")
- **Tracking:** IP, User-Agent, timestamp login

#### 5. GDPR Compliance

✅ **Zero date personale în log-uri**  
✅ **Email-uri anonimizate** (ex: `ab***@gmail.com`)  
✅ **IP-uri partiale** în log-uri publice  
✅ **Dreptul de a fi uitat** (funcție `delete_patient_link`)  

### Best Practices

#### Cerințe Parolă

```
✅ Minimum 8 caractere
✅ Cel puțin o literă mare (A-Z)
✅ Cel puțin o literă mică (a-z)
✅ Cel puțin o cifră (0-9)
✅ Cel puțin un caracter special (!@#$%^&*...)
❌ Parolele comune sunt respinse (top 100)
```

#### Recomandări Producție

```env
# .env production
FLASK_ENV=production
SESSION_COOKIE_SECURE=True
DATABASE_URL=<railway-postgresql-url>
APP_URL=https://pulsoximetrie.up.railway.app
```

---

## 🔌 API & Integrări

### Route-uri Flask

| Route | Method | Descriere | Autentificare |
|-------|--------|-----------|---------------|
| `/login` | GET, POST | Pagina de autentificare | ❌ Public |
| `/logout` | GET | Deconectare | ✅ Protejat |
| `/request-reset` | GET, POST | Cerere reset parolă | ❌ Public |
| `/reset-password` | GET, POST | Form reset cu token | ❌ Public (cu token) |

### Decoratori Python

#### @login_required

**Protejează callback-uri Dash:**

```python
from auth.decorators import login_required

@app.callback(...)
@login_required
def admin_callback(...):
    # Cod executat DOAR pentru utilizatori autentificați
    pass
```

#### @admin_required

**Protejează funcții admin:**

```python
from auth.decorators import admin_required

@app.callback(...)
@admin_required
def super_admin_callback(...):
    # Cod executat DOAR pentru admini
    pass
```

### Funcții Utilitare

```python
from flask_login import current_user
from auth.auth_manager import is_authenticated, get_current_doctor

# Verifică dacă e autentificat
if current_user.is_authenticated:
    print(f"Utilizator: {current_user.email}")

# Preia doctorul curent
doctor = get_current_doctor()
if doctor:
    print(f"Admin: {doctor.is_admin}")

# Verifică rol admin
if current_user.is_admin:
    print("Are permisiuni admin")
```

---

## 🛠️ Troubleshooting

### Probleme Comune

#### 1. "ModuleNotFoundError: No module named 'auth'"

**Cauză:** Dependențele nu sunt instalate.

**Soluție:**
```bash
pip install -r requirements.txt
```

#### 2. "BREVO_API_KEY nu este setat"

**Cauză:** `.env` nu este configurat sau lipsește cheia API.

**Soluție:**
```bash
# Verificați .env
cat .env | grep BREVO_API_KEY

# Adăugați cheia
echo "BREVO_API_KEY=xkeysib-your-key" >> .env
```

#### 3. "Connection refused" la PostgreSQL

**Cauză:** PostgreSQL nu rulează sau `DATABASE_URL` este greșit.

**Soluție:**
```bash
# Verificați status PostgreSQL
# Linux:
sudo systemctl status postgresql

# Windows:
# Services > PostgreSQL > Start

# Testați conexiunea
psql -U postgres -d pulsoximetrie
```

#### 4. Email-urile nu sunt primite

**Verificări:**
1. Verificați `BREVO_API_KEY` în `.env`
2. Verificați sender email în Brevo Dashboard
3. Verificați spam/promotions folder
4. Verificați log-urile: `output/LOGS/app_activity.log`

```python
# Test manual în Python console
from auth.email_service import test_email_configuration
test_email_configuration()
```

#### 5. "Prea multe încercări eșuate"

**Cauză:** Rate limiting activat după 5 încercări greșite.

**Soluție:**
```python
# Așteptați 15 minute SAU
# Deblocați manual (doar development):
from auth.rate_limiter import reset_all_limits
reset_all_limits()
```

---

## ❓ FAQ

### Întrebări Generale

**Q: Trebuie să migrez datele pacienților din JSON?**  
A: NU! `patient_links.json` rămâne NESCHIMBAT. PostgreSQL este doar pentru autentificare medici.

**Q: Token-urile UUID ale pacienților mai funcționează?**  
A: DA! Sistemul de acces pacienți este 100% NEAFECTAT.

**Q: Cât costă sistemul de autentificare?**  
A: **$0/lună** cu Railway (512MB PostgreSQL gratuit) + Brevo (300 email/zi gratuit).

**Q: Pot adăuga mai mulți medici?**  
A: DA! Adminul poate crea conturi noi din dashboard (funcționalitate în viitoarea versiune) sau prin Python:

```python
from auth.models import Doctor, db, create_admin_user

create_admin_user(
    email='medic@spital.ro',
    password='SecurePass123!',
    full_name='Dr. Ion Popescu'
)
```

**Q: Cum schimb parola adminului?**  
A: Accesați `/request-reset` și introduceți email-ul admin. Veți primi link de reset.

### Securitate

**Q: Este sigur Argon2?**  
A: DA! Argon2 este recomandat de OWASP (2024) și a câștigat Password Hashing Competition (2015).

**Q: Ce se întâmplă dacă cineva fură database-ul?**  
A: Parolele sunt hash-uite cu Argon2 (extremely slow to crack). Un atacator ar avea nevoie de ani pentru a crăpa o parolă de 12+ caractere.

**Q: Este GDPR compliant?**  
A: DA! Zero date personale în log-uri, email-uri anonimizate, posibilitate ștergere completă date.

### Development

**Q: Cum rulez testele?**  
A: Modulul `password_manager.py` rulează automat self-tests la import. Pentru teste complete:

```bash
pytest tests/  # (dacă există suite de teste)
```

**Q: Cum activez debug mode?**  
A:
```env
# .env
FLASK_ENV=development
```

```python
# run_medical.py (linia finală)
app.run(debug=True)
```

**Q: Pot folosi SQLite în loc de PostgreSQL?**  
A: DA, pentru development:

```env
DATABASE_URL=sqlite:///pulsoximetrie.db
```

⚠️ **NU recomandat pentru producție** (Railway are filesystem efemer).

---

## 📚 Resurse

### Documentație Oficială

- **Flask-Login:** https://flask-login.readthedocs.io/
- **Argon2:** https://argon2-cffi.readthedocs.io/
- **SQLAlchemy:** https://docs.sqlalchemy.org/
- **Brevo API:** https://developers.brevo.com/
- **OWASP Password Storage:** https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html

### Ghiduri Securitate

- **NIST SP 800-63B:** https://pages.nist.gov/800-63-3/sp800-63b.html
- **OWASP Top 10:** https://owasp.org/www-project-top-ten/

---

## 📞 Suport

**Probleme tehnice?**
- Verificați log-urile: `output/LOGS/app_activity.log`
- Rulați: `python migrations/migrate_json_to_postgres.py` pentru re-setup

**Bug-uri sau feature requests?**
- Creați un issue în repository sau contactați dezvoltatorul

---

## 📄 Licență

© 2025 Platformă Pulsoximetrie - Toate drepturile rezervate

---

**Versiune:** 1.0  
**Data:** Noiembrie 2025  
**Autor:** Echipa de Dezvoltare Virtuală (21 membri)  
**Stack:** Python + Dash + Flask + PostgreSQL + Argon2 + Brevo  


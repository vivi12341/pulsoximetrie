# 🚂 Configurare Railway - Platformă Pulsoximetrie

## 🚨 DACĂ APLICAȚIA CRASHEAZĂ ACUM

**Eroare: "connection to server at localhost failed"?**

👉 **Citește urgent:** [`RAILWAY_DATABASE_SETUP.md`](RAILWAY_DATABASE_SETUP.md)

**Soluția scurtă:** Adaugă PostgreSQL în Railway Dashboard (30 secunde):
1. Click pe proiect → `+ New` → `Database` → `Add PostgreSQL`
2. Railway setează automat `DATABASE_URL`
3. Aplicația repornește automat și funcționează! ✅

---

## 📋 CREDENȚIALE GENERATE PENTRU TINE

Am generat automat următoarele credențiale:

### 🔑 SECRET_KEY (GENERAT AUTOMAT - SIGUR)
```
59c000b06aec1abba3d430179706eb29d47d78e2910db340d58e186aca053a4a
```

### 👤 ADMIN DEFAULT (SCHIMBĂ DUPĂ PRIMA AUTENTIFICARE!)
- **Email:** `admin@pulsoximetrie.ro`
- **Parolă:** `Admin123` ⚠️ SCHIMBĂ URGENT!
- **Nume:** Administrator

---

## 🎯 PAȘI PENTRU CONFIGURARE RAILWAY

### 1️⃣ Adaugă PostgreSQL Database

În Railway dashboard:
1. Click pe proiectul tău `pulsoximetrie`
2. Click `+ New` → `Database` → `Add PostgreSQL`
3. Railway va crea automat variabila `DATABASE_URL` ✅

### 2️⃣ Setează Variabilele de Environment

Click pe serviciul tău → Tab `Variables` → Adaugă următoarele:

```bash
# === CRITICAL - SECRET KEY ===
SECRET_KEY=59c000b06aec1abba3d430179706eb29d47d78e2910db340d58e186aca053a4a

# === ADMIN (credențiale inițiale - SCHIMBĂ parola după login!) ===
ADMIN_EMAIL=admin@pulsoximetrie.ro
ADMIN_PASSWORD=Admin123!Change
ADMIN_NAME=Administrator

# === SESIUNI ===
SESSION_COOKIE_SECURE=True
PERMANENT_SESSION_LIFETIME=30

# === OPȚIONAL - EMAIL BREVO (pentru reset parolă) ===
BREVO_API_KEY=xkeysib-your-key-here
SENDER_EMAIL=noreply@pulsoximetrie.ro
SENDER_NAME=Platformă Pulsoximetrie

# === OPȚIONAL - Actualizează după deploy ===
APP_URL=https://pulsoximetrie-production.up.railway.app
FLASK_ENV=production
```

**✅ VARIABILE SETATE AUTOMAT DE RAILWAY:**
- `DATABASE_URL` - Setat automat când adaugi PostgreSQL ✅
- `PORT` - Setat automat (nu trebuie adăugat manual) ✅
- `RAILWAY_ENVIRONMENT` - Setat automat la "production" ✅

**⚠️ IMPORTANT:**
- Aplicația detectează AUTOMAT Railway prin `RAILWAY_ENVIRONMENT`
- `FLASK_ENV=production` este OPȚIONAL (aplicația funcționează și fără el)

### 3️⃣ Verifică Fișierele de Configurare

Am creat automat:
- ✅ `Procfile` - Spune Railway cum să pornească aplicația
- ✅ `railway.json` - Configurare Railway
- ✅ `run_medical.py` - Modificat pentru a suporta production mode

### 4️⃣ Deploy

```bash
# Commit fișierele noi
git add Procfile railway.json run_medical.py RAILWAY_SETUP.md
git commit -m "feat: Adaugă configurare Railway + production mode"
git push origin master
```

Railway va detecta push-ul și va redeploya automat! 🚀

---

## 🔍 VERIFICARE DUPĂ DEPLOY

### 1. Verifică Logs
În Railway: Tab `Deployments` → Click pe ultimul deploy → `Deploy Logs`

Ar trebui să vezi:
```
🏥 PORNIRE SERVER MEDICAL - PLATFORMĂ PULSOXIMETRIE
⚙️  Mod: PRODUCTION (debug OFF)
✅ Flask-Login inițializat cu succes.
✅ Database inițializat cu succes.
```

### 2. Testează Aplicația

Accesează URL-ul generat de Railway (ex: `https://pulsoximetrie-production.up.railway.app`)

1. **Login Admin:**
   - Mergi la `/login`
   - Email: `admin@pulsoximetrie.ro`
   - Parolă: `Admin123!Change`

2. **⚠️ SCHIMBĂ PAROLA IMEDIAT!**
   - După login, mergi la Setări
   - Schimbă parola în ceva sigur

3. **Testează Upload CSV**
   - Tab Admin → Upload CSV
   - Generează link pentru pacient

---

## 🐛 TROUBLESHOOTING

### ❌ Eroare: "No start command was found"
✅ **Rezolvat:** Am creat `Procfile` și `railway.json`

### ❌ Eroare: "Database connection failed"
**Cauză:** Railway nu a setat `DATABASE_URL`

**Soluție:**
1. Verifică că ai adăugat PostgreSQL în proiect
2. Verifică variabila `DATABASE_URL` în tab Variables
3. Redeploy dacă e necesar

### ❌ Eroare: "Port already in use"
**Cauză:** Railway setează automat `PORT`

**Soluție:** ✅ Deja rezolvat în `run_medical.py` (linia 111)

### ❌ Aplicația se oprește după câteva minute
**Cauză:** Free tier Railway adormi inactive apps după 500h/lună

**Soluție:** 
- Upgrade la plan plătit (~$5/lună)
- SAU folosește un ping service pentru keep-alive

---

## 📊 COSTURI ESTIMATE

| Serviciu | Free Tier | După Limită |
|----------|-----------|-------------|
| **Railway App Hosting** | 500h/lună (suficient pt start) | $0.000231/h (~$5/lună) |
| **PostgreSQL Database** | Inclus în plan | Stocare: $0.25/GB |
| **Total Lună 1-3** | **€0** | Suficient free tier |
| **După 100+ pacienți** | €5-15/lună | În funcție de trafic |

---

## ✅ CHECKLIST FINALIZARE

- [ ] PostgreSQL adăugat în Railway
- [ ] Variabile de environment setate (vezi mai sus)
- [ ] Fișiere commit și push (Procfile, railway.json)
- [ ] Deploy reușit (verifică logs)
- [ ] Login cu admin funcționează
- [ ] **PAROLĂ ADMIN SCHIMBATĂ!** ⚠️ CRITIC!
- [ ] APP_URL actualizat în Variables cu URL real Railway
- [ ] Test upload CSV + generare link pacient
- [ ] Test acces pacient cu token

---

## 🎉 GATA!

Aplicația ta rulează acum pe Railway în mod PRODUCTION! 

**Next Steps:**
1. Schimbă parola adminului
2. Testează funcționalitățile
3. Adaugă medici noi (dacă e necesar)
4. Înregistrează domeniu personalizat (opțional)

---

**Documentație Railway:** https://docs.railway.app/  
**Support:** https://railway.app/discord


# ⏱️ MONITORING DEPLOYMENT RAILWAY - GHID RAPID

**Status:** 🚀 DEPLOYMENT ÎN CURS (2 fix-uri critice push-uite)  
**Ora push:** 15 Nov 2025, 12:35 PM  
**ETA Completare:** ~2 minute (build + deploy)

---

## ✅ CE AM REPARAT (2 PROBLEME CRITICE)

### 1. **Crash Loop** (AssertionError: endpoint duplicat)
- ❌ Problema: `/health` endpoint definit în 2 locuri
- ✅ Soluție: Eliminat duplicatul, păstrat unul singur îmbunătățit

### 2. **Development Server** (Flask în production)
- ❌ Problema: `nixpacks.toml` override-uia `Procfile`
- ✅ Soluție: `nixpacks.toml` folosește Gunicorn (4 workers)

---

## 🔍 VERIFICARE ACUM (URGENT - URMĂREȘTE PAȘII)

### ⏱️ MINUTE 0-1: Build Phase

**Unde:** Railway Dashboard → `pulsoximetrie` → **Build Logs**

**Caută (în ordine):**
```
1. ✅ "load build definition from Dockerfile"
2. ✅ "Installing gunicorn==21.2.0" (în pip install)
3. ✅ "Successfully installed ... gunicorn-21.2.0 ..."
4. ✅ "=== Successfully Built! ===" (la final)
```

**Dacă vezi EROARE:** Screenshot + trimite în chat

---

### ⏱️ MINUTE 1-2: Deploy Phase

**Unde:** Railway Dashboard → `pulsoximetrie` → **Deploy Logs**

**Caută (CRITICAL!):**
```
✅ "Starting Container"
✅ "Booting worker with pid: 123" (Gunicorn worker 1)
✅ "Booting worker with pid: 124" (Gunicorn worker 2)
✅ "Booting worker with pid: 125" (Gunicorn worker 3)
✅ "Booting worker with pid: 126" (Gunicorn worker 4)
✅ "Listening at: http://0.0.0.0:8080 (pid: XXX)"
✅ "⚙️  PRODUCTION MODE: Logging level = WARNING"
```

**NU mai trebuie să apară:**
```
❌ "AssertionError: View function mapping is overwriting"
❌ "Traceback (most recent call last):"
❌ "WARNING: This is a development server"
❌ "Deployment crashed"
❌ "Deployment restarted" (repetitiv)
```

**Dacă vezi erori:** Screenshot + trimite în chat URGENT

---

### ⏱️ MINUT 2: Health Check Test

**Comandă (cmd/PowerShell):**
```bash
curl https://pulsoximetrie.cardiohelpteam.ro/health
```

**Răspuns AȘTEPTAT (200 OK):**
```json
{
  "status": "healthy",
  "timestamp": "2025-11-15T12:37:00.000000",
  "checks": {
    "database": "ok",
    "storage": "ok",
    "callbacks": 40,
    "service": "pulsoximetrie"
  }
}
```

**Dacă vezi "unhealthy" sau timeout:**
- Check PostgreSQL service (Railway Dashboard → Postgres → trebuie Active)
- Screenshot health check response + Deploy Logs

---

### ⏱️ MINUT 3: Site Principal Test

**URL:** https://pulsoximetrie.cardiohelpteam.ro

**Test rapid (1 minut):**
1. ✅ Pagina se încarcă (homepage visible, nu 502/503)
2. ✅ Click tab "Admin" → Login form apare
3. ✅ Login cu credențiale admin (test autentificare)
4. ✅ Upload CSV (drag & drop test fișier)
5. ✅ Grafic se generează (SpO2 + Puls vizibil)

**Dacă ORICE nu merge:** Screenshot + Deploy Logs + trimite în chat

---

## 🎯 SUCCESS CRITERIA (ALL MUST PASS)

- [ ] **Build completat** fără erori
- [ ] **4 Gunicorn workers** boot-ate (nu Flask dev server)
- [ ] **Zero crash-uri** sau restart-uri repetitive
- [ ] **Health check** returnează 200 OK cu "healthy"
- [ ] **Site accesibil** + login funcționează
- [ ] **Upload CSV** + grafic funcționează

**Dacă TOATE ✅:** Deployment SUCCESS! 🎉  
**Dacă ORICE ❌:** Screenshot + loguri + trimite în chat pentru debug

---

## 📊 MONITORING 24H (după success initial)

### Check #1: Postgres Connection Errors (IMPORTANT!)
**Unde:** Railway Dashboard → `Postgres` → Deploy Logs

**Caută:**
```
❌ "could not receive data from client: Connection reset by peer"
```

**Așteptat:** ZERO mesaje de acest tip (connection pooling rezolvă)  
**Dacă vezi:** Raportează numărul de erori per oră

---

### Check #2: Memory/CPU Stability
**Unde:** Railway Dashboard → `pulsoximetrie` → **Metrics**

**Monitorizare:**
- **Memory:** Trebuie stabil ~300-500MB (nu creștere liniară)
- **CPU:** Distribuit 25-50% (nu spike-uri 100%)

**Dacă vezi anomalii:** Screenshot Metrics + Deploy Logs

---

### Check #3: Response Time
**Unde:** Railway Dashboard → `pulsoximetrie` → **HTTP Logs**

**Așteptat:**
- GET `/` → < 200ms avg
- GET `/health` → < 50ms avg
- POST upload CSV → < 3000ms (pentru 10,000 records)

**Dacă vezi timeout-uri frecvente:** Raportează în chat

---

## 🚨 ERORI POSIBILE & SOLUȚII RAPIDE

### Error 1: "gunicorn: command not found"
**Cauză:** Railway nu a instalat gunicorn  
**Soluție:**
```bash
# Verifică requirements.txt are:
gunicorn==21.2.0

# Dacă lipsește, adaugă și push:
echo "gunicorn==21.2.0" >> requirements.txt
git add requirements.txt
git commit -m "Add gunicorn dependency"
git push origin master
```

---

### Error 2: "AssertionError: View function mapping"
**Cauză:** Endpoint duplicat ÎNCĂ în cod  
**Soluție:**
```bash
# Verifică că run_medical.py NU are @app.server.route('/health')
grep -n "route.*health" run_medical.py

# Dacă găsește ceva, șterge manual și push
```

---

### Error 3: "Connection to database failed"
**Cauză:** DATABASE_URL lipsește sau PostgreSQL down  
**Soluție:**
1. Railway Dashboard → `Postgres` → Verifică status (trebuie Active)
2. Railway Dashboard → `pulsoximetrie` → Variables → Verifică DATABASE_URL
3. Dacă lipsește DATABASE_URL: Adaugă PostgreSQL service (+ New → Database)

---

### Error 4: Site returnează 502 Bad Gateway
**Cauză:** Aplicația crashuiește după boot  
**Soluție:**
1. Check Deploy Logs pentru stack trace complet
2. Screenshot eroarea + trimite în chat
3. Posibil: Revert la commit anterior (git revert)

---

## 📞 CONTACT & ESCALATION

**Dacă deployment-ul EȘUEAZĂ după 5 minute:**
1. Screenshot **Build Logs** (scroll la final pentru erori)
2. Screenshot **Deploy Logs** (ultimele 50 linii)
3. Screenshot **Health Check** response (dacă accesibil)
4. Trimite în chat cu mesaj: "DEPLOYMENT FAILED - vezi screenshots"

**NU face manual:**
- ❌ Nu șterge servicii din Railway
- ❌ Nu schimba DATABASE_URL manual
- ❌ Nu forța rebuild (asteaptă 5 minute)

**Railway auto-rollback:** Dacă deploy-ul eșuează complet, Railway va reveni automat la versiunea anterioară funcțională.

---

## ⏱️ TIMELINE AȘTEPTAT

```
00:00 - Push completat (git push origin master)
00:30 - Railway detectează push
01:00 - Build phase start (installing dependencies)
01:30 - Build completat (Successfully Built!)
02:00 - Deploy phase start (Starting Container)
02:30 - Gunicorn boot (4 workers active)
03:00 - Health check accessible (200 OK)
03:30 - Site accesibil (homepage loads)
```

**Status curent:** Verifică Railway Dashboard ACUM!

---

**Creat:** 15 Nov 2025, 12:35 PM  
**Autor:** AI Assistant (Claude Sonnet 4.5)  
**Severity:** P0 - CRITICAL (Production Down → Recovery)  
**Action:** MONITOR Railway Dashboard NEXT 3 MINUTES


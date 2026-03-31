# ⚡ Cloudflare R2 - Quick Start (5 Minute Setup)

## 🎯 Quick Summary

**Ce este?** Storage cloud GRATUIT pentru fișierele pacienților (CSV, PDF, PNG)

**De ce R2 în loc de Syncthing?**
- ✅ **Persistent**: Fișierele NU dispar la redeploy Railway
- ✅ **Gratuit**: 10GB storage + bandwidth NELIMITAT
- ✅ **Simplu**: 4 pași configurare (5 minute)
- ❌ **Syncthing**: Necesită volume persistent pe Railway (€€€) + complexitate mare

---

## 🚀 Setup în 4 Pași (5 minute)

### 📋 Pasul 1: Creează Cont Cloudflare (30 secunde)

1. Mergi la: https://dash.cloudflare.com/sign-up
2. Creează cont gratuit
3. Verifică email-ul

### ☁️ Pasul 2: Activează R2 și Creează Bucket (1 minut)

1. Login Cloudflare → Click **"R2"** (stânga)
2. Click **"Purchase R2"** → Confirm **FREE plan**
3. Click **"Create bucket"** → Nume: `pulsoximetrie-files`

### 🔑 Pasul 3: Generează API Token (2 minute)

1. Click **"Manage R2 API Tokens"** (dreapta sus)
2. Click **"Create API token"**
3. Configurează:
   - **Name**: `railway-pulsoximetrie`
   - **Permissions**: ✅ **Object Read & Write**
   - **Buckets**: Selectează `pulsoximetrie-files`
4. Click **"Create API Token"**

**⚠️ IMPORTANT:** Copiază credențialele (SE ARATĂ O SINGURĂ DATĂ!):

```
Access Key ID: abc123def456...
Secret Access Key: XyZ789AbC123...
Endpoint: https://1234567890.r2.cloudflarestorage.com
```

### 🚂 Pasul 4: Configurează Railway (2 minute)

1. Railway Dashboard → Proiect `pulsoximetrie` → Tab **Variables**
2. Adaugă variabilele:

```bash
R2_ENABLED=True
R2_ENDPOINT=https://1234567890.r2.cloudflarestorage.com
R2_ACCESS_KEY_ID=abc123def456...
R2_SECRET_ACCESS_KEY=XyZ789AbC123...
R2_BUCKET_NAME=pulsoximetrie-files
R2_REGION=auto
```

3. Salvează → Railway va redeploya automat (60 secunde)

---

## ✅ Test Funcționalitate

După redeploy Railway:

1. Login aplicație: https://pulsoximetrie.cardiohelpteam.ro/
2. Upload CSV în **"Procesare Batch"**
3. Verifică Cloudflare Dashboard → R2 → `pulsoximetrie-files`
4. Ar trebui să vezi fișierele uploadate! ✅

---

## 💰 Costuri (FREE!)

| Resursă | FREE Tier | Cost După Limită |
|---------|-----------|------------------|
| **Stocare** | 10 GB | $0.015/GB |
| **Operații Write** | 1 milion/lună | $4.50/milion |
| **Operații Read** | 10 milioane/lună | $0.36/milion |
| **Bandwidth (download)** | ♾️ **NELIMITAT GRATUIT!** | **€0** |

**Pentru 100 pacienți:** ~2-3 GB → **€0/lună** ✅

---

## 🐛 Probleme?

### Eroare: "Could not connect to R2"
→ Verifică `R2_ENDPOINT`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY` în Railway Variables

### Eroare: "Access Denied"
→ Token-ul R2 nu are permisiuni la bucket. Editează token în Cloudflare → adaugă permisiuni

### Fișierele nu apar în R2
→ Verifică că `R2_ENABLED=True` în Railway → Forțează redeploy

---

## 📖 Documentație Completă

Pentru configurare avansată și detalii tehnice, vezi:
- **[CLOUDFLARE_R2_SETUP.md](./CLOUDFLARE_R2_SETUP.md)** - Ghid complet pas-cu-pas
- **[storage_service.py](./storage_service.py)** - Implementare tehnică

---

**Setup completat? Testează acum:** 🚀

```bash
# Verifică status R2 în aplicație (în Python console)
python storage_service.py
```

**Data ultimei actualizări:** 15 Noiembrie 2025


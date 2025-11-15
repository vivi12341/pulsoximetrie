# ✅ CHECKLIST VERIFICARE CLOUDFLARE R2 RAILWAY

**Data:** 15 Noiembrie 2025, 20:15  
**Status:** Codul DEJA are integrare R2 → Trebuie verificat setup Railway  
**Severitate:** HIGH - Storage ephemeral = pierdere date la fiecare redeploy

---

## 🔍 DIAGNOSTIC RAPID

### ✅ Cod Integrat R2
**Status:** ✅ **IMPLEMENTAT ÎN COD**

Fișiere cu integrare R2:
- `storage_service.py` - Client R2 complet funcțional (linii 15-491)
- `patient_links.py` - Upload CSV cu R2 + fallback local (linii 345-370)
- `test_r2_connection.py` - Script test conexiune R2

**Cod verificat:**
```python
# patient_links.py (linia 345-370)
if r2_available:
    logger.info(f"☁️ Salvare CSV în Cloudflare R2 pentru {token[:8]}...")
    r2_url = upload_patient_csv(token, csv_content, r2_filename)
    
    if r2_url:
        logger.info(f"✅ CSV salvat în R2: {r2_url}")
        csv_path = f"r2://{token}/csvs/{r2_filename}"
    else:
        logger.warning(f"⚠️ Upload R2 eșuat, folosim fallback LOCAL")
```

---

## 🚨 PROBLEMA IDENTIFICATĂ

### Test Local Arată:
```
❌ R2_ENABLED: False
❌ R2_ENDPOINT: N/A
⚠️ Mode: Local Storage (Fallback)
```

### Cauze Posibile (Priority Order):

#### **1. R2_ENABLED lipsește sau e False (MOST LIKELY)**
**Verificare Railway:**
```
Dashboard → pulsoximetrie → Variables → Caută "R2_ENABLED"
```

**Trebuie să fie:**
```bash
R2_ENABLED=True  # NU "true" (case-sensitive în Python!)
```

**⚠️ CRITICAL:** Python `os.getenv('R2_ENABLED', 'False').lower() == 'true'`
- Dacă lipsește → default: `'False'` → R2 DEZACTIVAT
- Dacă e `True` (uppercase) → convertit la `'true'` (lowercase) → ✅ ACTIVAT

---

#### **2. boto3 nu e instalat (CRITICAL)**
**Verificare:**
```bash
requirements.txt → Linia cu "boto3"
```

**Test Local:**
```python
python -c "import boto3; print('✅ boto3 OK')"
```

**Railway Deploy Logs:**
```
Caută în Build Logs: "Installing boto3..."
```

---

#### **3. Credențiale R2 incomplete**
**Verificare Railway Variables (TOATE 6 trebuie prezente):**

```bash
R2_ENABLED=True
R2_ENDPOINT=https://[ACCOUNT_ID].r2.cloudflarestorage.com
R2_ACCESS_KEY_ID=[32-64 caractere]
R2_SECRET_ACCESS_KEY=[32-64 caractere]
R2_BUCKET_NAME=pulsoximetrie-files
R2_REGION=auto
```

**⚠️ ATENȚIE:**
- Endpoint trebuie să înceapă cu `https://`
- Access Keys sunt case-sensitive
- Bucket name fără spații

---

## 🔧 PLAN DE ACȚIUNE (10 minute)

### PASUL 1: Verifică boto3 în requirements.txt (2 min)

**Verificare:**
```bash
grep "^boto3" requirements.txt
```

**Dacă LIPSEȘTE → ADAUGĂ:**
```bash
boto3==1.28.85
botocore==1.31.85
```

**Push la Railway:**
```powershell
git add requirements.txt
git commit -m "feat: Add boto3 for Cloudflare R2 storage"
git push
```

**Railway va reface build-ul automat cu boto3 instalat!**

---

### PASUL 2: Verifică Variables în Railway (3 min)

**Acces:**
1. https://railway.app/ → Login
2. Proiect **"pulsoximetrie"**
3. Click serviciu **"pulsoximetrie"** (NU PostgreSQL!)
4. Tab **"Variables"** (jos stânga)

**Verificare CRITICĂ:**

| Variabilă | Valoare Așteptată | Status |
|-----------|-------------------|--------|
| `R2_ENABLED` | **True** (uppercase T!) | ❓ |
| `R2_ENDPOINT` | `https://...r2.cloudflarestorage.com` | ❓ |
| `R2_ACCESS_KEY_ID` | 32-64 caractere | ❓ |
| `R2_SECRET_ACCESS_KEY` | 32-64 caractere | ❓ |
| `R2_BUCKET_NAME` | `pulsoximetrie-files` | ❓ |
| `R2_REGION` | `auto` | ❓ |

**Dacă LIPSEȘTE una → ADAUGĂ cu "New Variable"**

---

### PASUL 3: Verifică Railway Deploy Logs (3 min)

**După push/variabile actualizate:**
1. Railway Dashboard → Tab **"Deployments"**
2. Click pe deployment **"Active"** (cel mai recent)
3. Click **"Deploy Logs"**

**Log-uri AȘTEPTATE (SUCCESS):**

```bash
# Build Phase:
Installing boto3==1.28.85 ✅
Installing botocore==1.31.85 ✅

# Startup Phase:
[APP_INSTANCE 1/10] 📦 Initializing Dash 3.x libraries...
[APP_INSTANCE 8/10] ✅ dash_table library CONFIRMED registered!
[INIT 30/30] ✅ Application FULLY INITIALIZED

# R2 Connection:
✅ Cloudflare R2 conectat cu succes! Bucket: pulsoximetrie-files ✅✅✅
```

**Log-uri PROBLEME (FAILURE):**

```bash
# boto3 lipsește:
ModuleNotFoundError: No module named 'boto3' ❌

# R2 dezactivat:
⚠️ Cloudflare R2 DEZACTIVAT - folosim stocare LOCALĂ ❌

# Credențiale greșite:
❌ Bucket R2 'pulsoximetrie-files' nu există! ❌
❌ Acces refuzat la bucket 'pulsoximetrie-files'. ❌
```

---

### PASUL 4: Test Upload CSV (2 min)

**După deploy SUCCESS:**

1. Accesează: https://pulsoximetrie.cardiohelpteam.ro/
2. Login: `viorelmada1@gmail.com`
3. Tab: **"Procesare Batch"**
4. Mod: ☁️ **Online (Upload fișiere)**
5. Upload: 1 CSV de test (ex: `Checkme O2 0331_20251015203510.csv`)

**Railway Logs (timp real) - Caută:**

```bash
# SUCCESS (R2 funcționează):
☁️ Salvare CSV în Cloudflare R2 pentru abc123... ✅
✅ CSV salvat în R2: https://...r2.cloudflarestorage.com/... ✅
✅ Înregistrare adăugată pentru abc123... → ☁️ R2 (PERSISTENT) ✅

# FAILURE (R2 nu funcționează):
💾 Salvare CSV LOCAL (EPHEMERAL - va dispărea la redeploy Railway!) ❌
⚠️ CSV salvat LOCAL: /app/patient_data/abc123/recording_xyz.csv ❌
```

---

## 🔍 DEBUG RAPID (1 minut)

**Dacă problema persistă după Pașii 1-4:**

### Test R2 Connection Direct:

**Adaugă endpoint temporar în `wsgi.py` (după linia 333):**

```python
@application.route('/debug/r2-status')
def debug_r2_status():
    """Debug endpoint pentru verificare status R2 în producție."""
    from flask import jsonify
    from storage_service import get_storage_status
    import os
    
    status = get_storage_status()
    
    # Mascare credențiale (securitate!)
    env_vars = {
        'R2_ENABLED': os.getenv('R2_ENABLED', 'NOT_SET'),
        'R2_ENDPOINT': os.getenv('R2_ENDPOINT', 'NOT_SET')[:50] + '...' if os.getenv('R2_ENDPOINT') else 'NOT_SET',
        'R2_ACCESS_KEY_ID': os.getenv('R2_ACCESS_KEY_ID', 'NOT_SET')[:8] + '...' if os.getenv('R2_ACCESS_KEY_ID') else 'NOT_SET',
        'R2_SECRET_ACCESS_KEY': '***HIDDEN***' if os.getenv('R2_SECRET_ACCESS_KEY') else 'NOT_SET',
        'R2_BUCKET_NAME': os.getenv('R2_BUCKET_NAME', 'NOT_SET'),
        'R2_REGION': os.getenv('R2_REGION', 'NOT_SET')
    }
    
    return jsonify({
        'storage_status': status,
        'environment_vars': env_vars,
        'timestamp': datetime.now().isoformat()
    })
```

**Push + Accesează:**
```
https://pulsoximetrie.cardiohelpteam.ro/debug/r2-status
```

**Răspuns AȘTEPTAT (SUCCESS):**
```json
{
  "storage_status": {
    "r2_enabled": true,
    "r2_endpoint": "https://...r2.cloudflarestorage.com",
    "r2_bucket": "pulsoximetrie-files",
    "mode": "Cloudflare R2"
  },
  "environment_vars": {
    "R2_ENABLED": "True",
    "R2_ENDPOINT": "https://...r2.cloudflarestorage.com",
    "R2_ACCESS_KEY_ID": "abc123de...",
    "R2_SECRET_ACCESS_KEY": "***HIDDEN***",
    "R2_BUCKET_NAME": "pulsoximetrie-files",
    "R2_REGION": "auto"
  }
}
```

**Răspuns PROBLEME (FAILURE):**
```json
{
  "storage_status": {
    "r2_enabled": false,
    "mode": "Local Storage (Fallback)"
  },
  "environment_vars": {
    "R2_ENABLED": "NOT_SET",  ← PROBLEMA!
    "R2_ENDPOINT": "NOT_SET",
    ...
  }
}
```

---

## 📊 TROUBLESHOOTING RAPID

| Problemă | Cauză | Soluție |
|----------|-------|---------|
| `ModuleNotFoundError: boto3` | boto3 nu e în requirements.txt | Adaugă boto3==1.28.85 + push |
| `R2_ENABLED: False` | Variabila lipsește/greșită | Setează `R2_ENABLED=True` (uppercase!) |
| `R2_ENDPOINT: NOT_SET` | Variabilă lipsește | Adaugă endpoint Cloudflare |
| `Access Denied` | Permisiuni token R2 greșite | Regenerează token cu Read+Write |
| `Bucket not found` | Bucket name greșit | Verifică exact `pulsoximetrie-files` |
| `☁️ Salvare...` NU apare | R2 dezactivat în cod | Verifică toate 6 variabile |

---

## ✅ SUCCESS CRITERIA

### Railway Deploy Logs:
```
✅ Cloudflare R2 conectat cu succes! Bucket: pulsoximetrie-files
```

### Upload CSV Logs:
```
☁️ Salvare CSV în Cloudflare R2 pentru abc123...
✅ CSV salvat în R2: https://...
✅ Înregistrare adăugată pentru abc123... → ☁️ R2 (PERSISTENT)
```

### Debug Endpoint:
```json
{
  "storage_status": {
    "r2_enabled": true,
    "mode": "Cloudflare R2"
  }
}
```

### Test Pacient:
- Link pacient → Grafic se încarcă ✅
- Railway logs → `📥 Download R2: ... / csvs / ...` ✅

---

## 🎯 NEXT STEPS (După R2 funcționează)

1. ✅ **Șterge debug endpoint** (`/debug/r2-status`)
2. ✅ **Re-upload CSV-uri vechi** (cele de dinainte erau local-ephemeral)
3. ✅ **Test comprehensive** (test1) pentru validare completă
4. ✅ **Monitor Cloudflare R2 Dashboard** (usage statistics)

---

**Status:** ⏳ AWAITING RAILWAY VERIFICATION  
**ETA Fix:** 5-10 minute (după verificare + boto3 install dacă lipsește)  
**Priority:** HIGH - Fără R2 = pierdere date la fiecare redeploy!


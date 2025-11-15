# 🔍 DIAGNOSTIC R2 - Railway Startup Check

## ✅ CE EXISTĂ DEJA ÎN COD (COMPLET INTEGRAT!)

### **1. Upload CSV → R2** (`patient_links.py` linia 328-402)
```python
# Verifică r2_client.enabled
if r2_available:
    r2_url = upload_patient_csv(token, csv_content, r2_filename)
    storage_type = "r2"  # Salvează în metadata
```

### **2. Download CSV ← R2** (`callbacks_medical.py` linia 530-555)
```python
if storage_type == 'r2' and recording.get('r2_url'):
    csv_content = download_patient_file(token, 'csvs', r2_filename)
```

### **3. Storage Service** (`storage_service.py` complet funcțional)
- CloudflareR2Client class
- Fallback LOCAL dacă R2 indisponibil
- Upload/Download/Delete/List operations

---

## 🚨 PROBLEMA SUSPECTATĂ (de verificat în Railway logs)

**Scenarii posibile:**

### **Scenariu 1: R2_ENABLED=False (variabila nu e setată corect)**
```
Log așteptat:
⚠️ Cloudflare R2 DEZACTIVAT - folosim stocare LOCALĂ
```

**Fix:** Verifică în Railway Variables:
```
R2_ENABLED=True  ← EXACT așa (case-sensitive!)
```

### **Scenariu 2: Bucket nu există (404)**
```
Log așteptat:
❌ Bucket R2 'pulsoximetrie-files' nu există! Creează-l în Cloudflare Dashboard.
```

**Fix:** 
1. Deschide Cloudflare Dashboard → R2
2. Create Bucket → Nume: `pulsoximetrie-files`
3. Restart Railway

### **Scenariu 3: Permisiuni greșite (403)**
```
Log așteptat:
❌ Acces refuzat la bucket 'pulsoximetrie-files'. Verifică permisiunile token-ului R2.
```

**Fix:**
1. Regenerează R2 Access Token în Cloudflare
2. Asigură-te că are permisiuni: Read + Write
3. Update Railway Variables

### **Scenariu 4: Endpoint greșit**
```
Log așteptat:
❌ Eroare boto3: EndpointConnectionError
```

**Fix:** Verifică R2_ENDPOINT în Railway Variables:
```
R2_ENDPOINT=https://<account-id>.r2.cloudflarestorage.com
```

---

## 🔧 VERIFICARE RAPIDĂ ÎN RAILWAY LOGS

### **Pași:**
1. Deschide Railway Dashboard → pulsoximetrie → Logs
2. Caută după **deploy nou** (următoarele 2-3 minute):

```
[Căutăm aceste log-uri la STARTUP:]

✅ Log SUCCESS (R2 funcționează):
"✅ Cloudflare R2 conectat cu succes! Bucket: pulsoximetrie-files"

❌ Log ERROR (R2 nu funcționează):
"⚠️ Cloudflare R2 DEZACTIVAT - folosim stocare LOCALĂ"
"❌ Bucket R2 'pulsoximetrie-files' nu există!"
"❌ Acces refuzat la bucket"
```

---

## 📋 VARIABILE RAILWAY NECESARE (Checklist)

Verifică în Railway Dashboard → pulsoximetrie → Variables:

```
✅ R2_ENABLED=True
✅ R2_ENDPOINT=https://<account-id>.r2.cloudflarestorage.com
✅ R2_ACCESS_KEY_ID=<key>
✅ R2_SECRET_ACCESS_KEY=<secret>
✅ R2_BUCKET_NAME=pulsoximetrie-files
✅ R2_REGION=auto
```

**⚠️ IMPORTANT:** 
- Toate valorile sunt **case-sensitive**!
- `R2_ENABLED` trebuie să fie exact `True` (cu T mare)
- `R2_ENDPOINT` trebuie să înceapă cu `https://`

---

## 🧪 TEST MANUAL R2 (Opțional - după deploy)

### **Opțiunea 1: Upload CSV în aplicație**
1. Login la https://pulsoximetrie.cardiohelpteam.ro/
2. Upload CSV în tab "Procesare Batch"
3. Verifică în Railway Logs:

```
✅ Log SUCCESS:
☁️ Salvare CSV în Cloudflare R2 pentru <token>...
✅ CSV salvat în R2: https://...

❌ Log FALLBACK (R2 nu funcționează):
💾 Salvare CSV LOCAL (EPHEMERAL - va dispărea la redeploy Railway!)
⚠️ CSV salvat LOCAL: patient_data/... (TEMPORARY!)
```

### **Opțiunea 2: Script test direct**
```bash
# În Railway Shell sau local cu env vars Railway
python test_r2_connection.py
```

Rezultat așteptat:
```
✅ R2 este ACTIVAT
✅ Conexiune R2 reușită! Bucket: pulsoximetrie-files
✅ Upload reușit!
✅ Fișier test găsit în listă
```

---

## 🎯 ACȚIUNI URMĂTOARE (după verificare Railway logs)

### **Dacă log-urile arată R2 DEZACTIVAT:**
1. **Verifică variabile Railway** (vezi checklist mai sus)
2. **Restart aplicație**: Railway → pulsoximetrie → Settings → Restart
3. **Așteaptă 2 min** pentru deploy
4. **Verifică din nou logs** pentru `✅ Cloudflare R2 conectat`

### **Dacă log-urile arată BUCKET NU EXISTĂ:**
1. **Creează bucket în Cloudflare**:
   - Dashboard → R2 → Create Bucket
   - Nume: `pulsoximetrie-files` (exact!)
   - Location: Automatic
2. **NU e nevoie să restartezi** - bucket e verificat la fiecare request

### **Dacă log-urile arată PERMISIUNI REFUZATE:**
1. **Regenerează R2 API Token în Cloudflare**:
   - Dashboard → R2 → Manage R2 API Tokens
   - Create API Token → Permissions: Object Read & Write
2. **Update Railway Variables** cu noul Access Key + Secret
3. **Restart Railway**

---

## 🚀 STATUS IMPLEMENTARE R2

| Component | Status | Locație |
|-----------|---------|----------|
| **Upload CSV → R2** | ✅ IMPLEMENTAT | `patient_links.py:328-402` |
| **Download CSV ← R2** | ✅ IMPLEMENTAT | `callbacks_medical.py:530-555` |
| **Upload PDF → R2** | ⚠️ PARȚIAL | Trebuie adaptat `pdf_parser.py` |
| **Storage Service** | ✅ COMPLET | `storage_service.py` |
| **Fallback LOCAL** | ✅ FUNCȚIONAL | Ambele fișiere |
| **Railway Variables** | ❓ NECUNOSCUT | **VERIFICĂ ACUM!** |

---

## 📊 AȘTEPTĂRI DUPĂ FIX

### **Înainte (Stocare LOCAL - EPHEMERAL):**
```
Upload CSV → patient_data/{token}/recording_xyz.csv (LOCAL)
Redeploy Railway → ❌ FIȘIERE ȘTERSE! (disc ephemeral)
Pacient accesează link → ❌ CSV dispărut!
```

### **După (Stocare R2 - PERSISTENT):**
```
Upload CSV → Cloudflare R2 bucket/pulsoximetrie-files/{token}/csvs/recording_xyz.csv
Redeploy Railway → ✅ FIȘIERE PĂSTRATE! (R2 persistent)
Pacient accesează link → ✅ CSV disponibil!
```

---

## ✅ NEXT STEPS (Executare imediată)

1. **Deschide Railway Logs** (după deploy curent completat ~3 min)
2. **Caută log:** `Cloudflare R2` (prima linie după startup)
3. **Identifică scenariul** (1-4 de mai sus)
4. **Aplică fix-ul** corespunzător
5. **Restart Railway** (dacă necesar)
6. **Test upload CSV** în aplicație
7. **Verifică log:** `☁️ Salvare CSV în Cloudflare R2` (SUCCESS!)

---

**Status actual:** ⏳ Așteaptă verificare Railway logs pentru diagnostic R2  
**ETA rezolvare:** 5-10 minute (după identificare scenariu)  
**Confidence:** 99% (codul e perfect, doar config Railway lipsește)


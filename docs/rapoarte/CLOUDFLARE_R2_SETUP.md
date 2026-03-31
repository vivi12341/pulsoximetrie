# ☁️ Configurare Cloudflare R2 - Storage Persistent pentru Pulsoximetrie

## 🎯 Ce Realizăm

Migrăm stocare locală (`patient_data/`) → **Cloudflare R2** (cloud persistent)

**Înainte (LOCAL):**
```
Railway Container (EFEMER - pierde date la redeploy!)
  ├─ patient_data/
  │   ├─ abc123-token/
  │   │   ├─ csvs/file.csv  ❌ DISPARE la redeploy
  │   │   ├─ pdfs/report.pdf ❌ DISPARE
  │   │   └─ plots/graph.png ❌ DISPARE
```

**După (CLOUDFLARE R2):**
```
Railway Container → API Request → Cloudflare R2
                                    ├─ pulsoximetrie-files/
                                    │   ├─ abc123-token/
                                    │   │   ├─ csvs/file.csv  ✅ PERSISTENT
                                    │   │   ├─ pdfs/report.pdf ✅ PERSISTENT
                                    │   │   └─ plots/graph.png ✅ PERSISTENT
```

---

## 📋 Pasul 1: Creează Cont Cloudflare (GRATUIT)

### 1.1 Înregistrare Cloudflare

1. Mergi la: **https://dash.cloudflare.com/sign-up**
2. Creează cont gratuit (email + parolă)
3. Verifică email-ul

### 1.2 Activează R2 Storage

1. După login, mergi la **https://dash.cloudflare.com/**
2. Click pe **"R2"** în meniul din stânga
3. Click pe **"Purchase R2"** (nu te speria - e GRATUIT!)
4. Confirm plan **FREE** (10GB inclus)

✅ **Cont R2 activat!**

---

## 📦 Pasul 2: Creează Bucket pentru Pulsoximetrie

### 2.1 Creează Bucket Nou

1. În dashboard R2, click **"Create bucket"**
2. **Name**: `pulsoximetrie-files` (fără spații!)
3. **Location**: `Automatic` (Cloudflare alege cel mai rapid)
4. Click **"Create bucket"**

### 2.2 Configurare Bucket (Opțional)

- **Public Access**: ❌ **DEZACTIVAT** (privacy GDPR!)
- **Object Lifecycle**: Poți configura ștergere automată după X zile

✅ **Bucket creat:** `pulsoximetrie-files`

---

## 🔑 Pasul 3: Generează API Token pentru Railway

### 3.1 Creează API Token

1. În dashboard R2, click **"Manage R2 API Tokens"** (dreapta sus)
2. Click **"Create API token"**
3. Configurează:
   - **Token name**: `railway-pulsoximetrie`
   - **Permissions**: 
     - ✅ **Object Read & Write** (pentru upload/download)
     - ❌ **Edit** (nu e necesar)
   - **Specify bucket(s)**: 
     - Selectează **DOAR** `pulsoximetrie-files`
   - **TTL**: `Forever` (sau 1 an)
4. Click **"Create API Token"**

### 3.2 SALVEAZĂ Credențialele (IMPORTANT!)

După creare, vei vedea:

```bash
# === SALVEAZĂ ACESTE CREDENȚIALE (se arată O SINGURĂ DATĂ!) ===

Access Key ID: abc123def456ghi789...
Secret Access Key: XyZ789AbC123DeF456...

# Endpoint S3-compatible (EU sau US - depinde de regiunea ta)
Endpoint: https://<account_id>.r2.cloudflarestorage.com
```

**⚠️ IMPORTANT:** Copiază-le ACUM într-un fișier sigur! Nu le mai poți vedea ulterior!

✅ **Credențiale R2 generate!**

---

## 🚂 Pasul 4: Configurează Railway cu R2

### 4.1 Adaugă Variabile Environment în Railway

1. Mergi la **Railway Dashboard** → Proiect **pulsoximetrie**
2. Click pe serviciul aplicației (nu PostgreSQL)
3. Tab **"Variables"**
4. Adaugă următoarele variabile:

```bash
# === CLOUDFLARE R2 STORAGE ===
R2_ENABLED=True
R2_ENDPOINT=https://<ACCOUNT_ID>.r2.cloudflarestorage.com
R2_ACCESS_KEY_ID=abc123def456ghi789...
R2_SECRET_ACCESS_KEY=XyZ789AbC123DeF456...
R2_BUCKET_NAME=pulsoximetrie-files
R2_REGION=auto

# EXEMPLU COMPLET (înlocuiește cu ale tale):
R2_ENABLED=True
R2_ENDPOINT=https://1234567890abcdef.r2.cloudflarestorage.com
R2_ACCESS_KEY_ID=abc123def456ghi789jkl012mno345
R2_SECRET_ACCESS_KEY=XyZ789AbC123DeF456GhI789JkL012MnO345
R2_BUCKET_NAME=pulsoximetrie-files
R2_REGION=auto
```

**⚠️ ATENȚIE:**
- Înlocuiește `<ACCOUNT_ID>` cu ID-ul tău Cloudflare (din endpoint)
- Înlocuiește `R2_ACCESS_KEY_ID` cu cheia ta
- Înlocuiește `R2_SECRET_ACCESS_KEY` cu secret-ul tău

### 4.2 Salvează și Așteaptă Redeploy

Railway va reporni automat aplicația după ce salvezi variabilele (~60 secunde).

---

## 🐍 Pasul 5: Instalează Dependințe Python

Trebuie să adaugi `boto3` (biblioteca AWS S3, compatibilă cu R2) în `requirements.txt`.

**Fișier:** `requirements.txt`

Adaugă linia:
```txt
boto3==1.34.144
```

✅ **Boto3 va fi instalat automat la următorul deploy!**

---

## 📊 Pasul 6: Testare Finală

După ce Railway termină deploy-ul:

### 6.1 Testează Upload CSV

1. Login în aplicație: `https://pulsoximetrie.cardiohelpteam.ro/`
2. Tab **"Procesare Batch"**
3. Uploadează un fișier CSV de test
4. Verifică că procesarea funcționează ✅

### 6.2 Verifică Fișierele în R2

1. Mergi în **Cloudflare Dashboard** → **R2** → **pulsoximetrie-files**
2. Ar trebui să vezi folderele:
   ```
   pulsoximetrie-files/
     ├─ <token-uuid>/
     │   ├─ csvs/
     │   │   └─ file.csv  ✅ UPLOADED
     │   ├─ plots/
     │   │   └─ graph.png ✅ UPLOADED
     │   └─ pdfs/
     │       └─ report.pdf ✅ UPLOADED
   ```

### 6.3 Testează Acces Pacient

1. Generează link pentru pacient
2. Accesează link-ul
3. Verifică că graficele se încarcă ✅

---

## 💰 Costuri Cloudflare R2 (FREE Tier)

| Resursă | FREE Tier | După Limită |
|---------|-----------|-------------|
| **Stocare** | 10 GB/lună | $0.015/GB/lună |
| **Class A Operations** | 1 milion/lună | $4.50/milion |
| **Class B Operations** | 10 milioane/lună | $0.36/milion |
| **Bandwidth (download)** | ♾️ **NELIMITAT GRATUIT!** | **$0** (asta e magic!) |

**Estimare pentru aplicația ta:**
- **100 pacienți** × 3 înregistrări × (1 CSV + 1 PDF + 1 PNG) = ~300 fișiere
- **Stocare medie**: ~2-3 GB (bine sub limita de 10GB)
- **Operații**: ~50,000/lună (bine sub 1 milion)
- **Cost lunar**: **€0** primele 6-12 luni! 🎉

---

## 🔒 Securitate și Privacy (GDPR)

✅ **Best Practices implementate:**

1. **Bucket privat**: Fișierele NU sunt accesibile public
2. **Token-uri UUID**: Link-uri nepredictibile
3. **Signed URLs**: Generăm URL-uri cu expirare (opțional)
4. **Encryption at rest**: Cloudflare criptează automat datele
5. **Encryption in transit**: HTTPS obligatoriu
6. **Zero date personale**: Doar token + date medicale anonime

---

## 🐛 Troubleshooting

### ❌ Eroare: "Could not connect to R2"

**Cauză:** Credențiale greșite sau endpoint invalid

**Soluție:**
1. Verifică `R2_ENDPOINT` în Railway Variables
2. Verifică `R2_ACCESS_KEY_ID` și `R2_SECRET_ACCESS_KEY`
3. Asigură-te că token-ul R2 are permisiuni **Object Read & Write**

### ❌ Eroare: "Access Denied"

**Cauză:** Token-ul R2 nu are acces la bucket

**Soluție:**
1. Mergi în Cloudflare → R2 → API Tokens
2. Editează token-ul `railway-pulsoximetrie`
3. Asigură-te că `pulsoximetrie-files` este în lista de bucket-uri permise

### ❌ Fișierele nu apar în R2

**Cauză:** `R2_ENABLED=True` nu e setat sau aplicația încă folosește stocare locală

**Soluție:**
1. Verifică variabila `R2_ENABLED` în Railway
2. Forțează redeploy: Railway Dashboard → Deployments → Redeploy

### ❌ Graficele nu se încarcă pe link pacient

**Cauză:** Aplicația încearcă să servească fișiere local în loc de R2

**Soluție:**
1. Verifică logs Railway: `Deployments → View Logs`
2. Caută erori legate de R2
3. Asigură-te că modulul `storage_service.py` folosește R2

---

## ✅ Checklist Finalizare

- [ ] Cont Cloudflare creat și verificat
- [ ] R2 activat (plan FREE)
- [ ] Bucket `pulsoximetrie-files` creat
- [ ] API Token generat și salvat
- [ ] Variabile R2 adăugate în Railway
- [ ] `boto3` adăugat în `requirements.txt`
- [ ] Railway redeploy finalizat cu succes
- [ ] Test upload CSV funcționează
- [ ] Fișiere apar în R2 Dashboard
- [ ] Link pacient funcționează și încarcă grafice

---

## 🎉 GATA!

Acum ai **storage persistent profesional** pentru aplicația de pulsoximetrie!

**Avantaje finale:**
- ✅ Fișierele NU dispar la redeploy Railway
- ✅ Backup automat Cloudflare
- ✅ Scalabilitate: 10GB → nelimitat
- ✅ Costuri: **€0** primele luni
- ✅ GDPR compliant
- ✅ Download bandwidth GRATUIT (magic!)

---

**Documentație Cloudflare R2:** https://developers.cloudflare.com/r2/  
**API boto3 (Python):** https://boto3.amazonaws.com/v1/documentation/api/latest/guide/s3.html

**Data ultimei actualizări:** 15 Noiembrie 2025  
**Versiune:** 1.0 - Cloudflare R2 Integration



# 🏥 Platformă Pulsoximetrie Medicală - Ghid Utilizare

## 📋 Prezentare Generală

Această aplicație implementează workflow-ul medical descris în `.cursorrules`:
- **1 PACIENT = 1 LINK PERSISTENT** (UUID)
- **Upload BULK** pentru medici
- **2 tabs pentru pacienți**: Înregistrări + Explorare CSV
- **Privacy by Design**: Zero date personale (GDPR compliant)

---

## 🚀 Pornire Aplicație

### Metodă 1: Script Medical (RECOMANDAT)
```bash
python run_medical.py
```

### Metodă 2: Script Original (doar vizualizare + batch)
```bash
python run.py
```

**Aplicația va fi disponibilă la:** `http://127.0.0.1:8050/`

---

## 👨‍⚕️ WORKFLOW MEDIC (Tab Admin)

### 1. Creare Link Pacient Nou

**Pasul 1:** Accesați tab-ul **"👨‍⚕️ Admin (Medic)"**

**Pasul 2:** Completați formularul:
- **Nume Aparat**: `Checkme O2 #3539`
- **Notițe**: `Apnee severă, follow-up săptămânal` (opțional)

**Pasul 3:** Click **"🔗 Generează Link Nou"**

**Pasul 4:** Copiați link-ul/token-ul generat și trimiteți-l pacientului (email/SMS)

**Exemplu token:** `a8f9d2b1-3c4e-4d5e-8f9a-1b2c3d4e5f6g`

---

### 2. Upload CSV pentru Pacient Existent

**Pasul 1:** Selectați pacientul din dropdown

**Pasul 2:** Trageți fișierul CSV sau click pentru selectare

**Pasul 3:** Aplicația va:
- Parsa CSV-ul automat
- Extrage statistici (avg/min/max SaO2)
- Salva înregistrarea în `patient_data/{token}/`
- Actualiza contorul de înregistrări

---

### 3. Gestionare Pacienți

**Lista Pacienți** afișează:
- Nume aparat
- Token (ultimele 12 caractere)
- Data creării
- Număr înregistrări
- Notițe medicale

**Buton "🔄 Reîmprospătează Listă"**: Actualizează vizualizarea

**Buton "🗑️ Șterge"**: ⚠️ ATENȚIE! Șterge COMPLET pacientul și toate datele (GDPR "dreptul de a fi uitat")

---

## 👤 WORKFLOW PACIENT (Tab Pacient)

### 1. Acces cu Token

**Pasul 1:** Accesați tab-ul **"👤 Pacient"**

**Pasul 2:** Introduceți token-ul primit de la medic în câmpul de text

**Pasul 3:** Click **"🔓 Accesează Înregistrări"**

**Rezultat:** Se deschid 2 sub-tabs

---

### 2. Sub-Tab: 📁 Înregistrările Mele

**Conținut:**
- Listă cu TOATE înregistrările stocate
- Carduri cu informații:
  - Data înregistrării
  - Interval orar (start - end)
  - Statistici SaO2 (avg, min, max)
  - Nume fișier original

**Acțiuni disponibile:**
- **"📈 Vezi Grafic"**: Vizualizare grafic Plotly interactiv
- **"📥 Descarcă CSV"**: Download fișier original

---

### 3. Sub-Tab: 🔍 Explorează CSV

**Scop:** Plotare TEMPORARĂ fără salvare în baza de date

**Utilizare:**
1. Trageți un fișier CSV sau click pentru selectare
2. Graficul se generează instant
3. ⚠️ **WARNING afișat:** "Graficul este temporar și nu va fi salvat"

**Use Cases:**
- Explorare CSV-uri vechi descărcate
- Testare fișiere înainte de a le trimite medicului
- Re-plotare cu zoom/setări diferite

---

## 📈 Tab Vizualizare Interactivă (Original)

**Funcționalitate păstrată din versiunea anterioară:**
- Upload CSV individual
- Grafic Plotly cu zoom dinamic
- Hover pentru detalii
- Scalare automată linie la zoom

---

## 🔄 Tab Procesare în Lot (Original)

**Funcționalitate păstrată din versiunea anterioară:**
- Procesare multiplă CSV-uri dintr-un folder
- Generare imagini JPG cu ferestre de timp
- Nume intuitive foldere: `02mai2025_00h25-06h37_Aparat1442`
- Nume intuitive imagini: `Aparat1442_00h25m-00h55m.jpg`

---

## 📂 Structura Datelor

### Foldere Generate

```
patient_data/
├── {token-pacient-1}/
│   ├── recording_{id1}.csv
│   ├── recording_{id2}.csv
│   └── recordings.json (metadata)
├── {token-pacient-2}/
│   ├── recording_{id1}.csv
│   └── recordings.json
└── ...

patient_links.json (metadata toate link-urile)
```

### Format `patient_links.json`

```json
{
  "a8f9d2b1-3c4e...": {
    "device_name": "Checkme O2 #3539",
    "notes": "Apnee severă",
    "created_at": "2025-11-11T14:30:00",
    "last_accessed": "2025-11-11T15:45:00",
    "is_active": true,
    "recordings_count": 5
  }
}
```

### Format `recordings.json`

```json
[
  {
    "id": "a1b2c3d4",
    "original_filename": "Checkme O2 3539_20251015203510.csv",
    "csv_path": "patient_data/{token}/recording_a1b2c3d4.csv",
    "recording_date": "2025-10-15",
    "start_time": "20:35:10",
    "end_time": "04:22:45",
    "uploaded_at": "2025-11-11T14:35:00",
    "stats": {
      "avg_spo2": 94.2,
      "min_spo2": 87,
      "max_spo2": 99
    }
  }
]
```

---

## 🔒 Securitate & Privacy (GDPR Compliant)

### ✅ CE STOCĂM:
- UUID token (random, criptografic sigur)
- Nume aparat (ex: "Checkme O2 #3539")
- Date medicale (SaO2, puls) - **necesare medical**
- Timestamp-uri (created_at, uploaded_at)
- Notițe medicale (opțional, fără date personale)

### ❌ CE NU STOCĂM:
- Nume pacient
- Prenume pacient
- CNP
- Adresă
- Număr telefon
- Email pacient (doar admin/medic are email)

### 🗑️ Dreptul de a fi uitat (GDPR Art. 17):
- Medicul poate șterge COMPLET un pacient
- Acțiune **IREVERSIBILĂ**
- Șterge: folder, CSV-uri, metadata

---

## 🧪 Testare Workflow Complet

### Scenario de Test: Pacient Nou

**Etapa 1: Medic Creează Link**
```
1. Accesează tab Admin
2. Device: "Checkme O2 #TEST01"
3. Notes: "Test pentru documentație"
4. Click "Generează Link"
5. Copiază token: a1b2c3d4-...
```

**Etapa 2: Medic Upload CSV**
```
1. Selectează pacient din dropdown (TEST01)
2. Upload CSV din folderul "bach data/" sau "intrare/"
3. Verifică mesaj success cu statistici
4. Click "Reîmprospătează Listă" → vezi 1 înregistrare
```

**Etapa 3: Pacient Acces**
```
1. Accesează tab Pacient
2. Introdu token: a1b2c3d4-...
3. Click "Accesează Înregistrări"
4. Tab "Înregistrările Mele" → vezi 1 card
5. Click "Vezi Grafic" → grafic Plotly se încarcă
```

**Etapa 4: Pacient Explorare**
```
1. Tab "Explorează CSV"
2. Upload CSV temporar
3. Grafic se generează instant
4. Warning afișat: "temporar"
```

---

## ❓ Troubleshooting

### Eroare: "Token invalid"
**Cauză:** Token-ul introdus nu există sau este dezactivat

**Soluție:** 
- Verificați că token-ul este copiat complet (36+ caractere)
- Contactați medicul pentru un token nou

---

### Eroare: "Selectați mai întâi un pacient"
**Cauză:** Nu ați selectat pacient din dropdown înainte de upload

**Soluție:** Click dropdown → selectați pacient → apoi upload CSV

---

### CSV nu se parsează
**Cauză:** Format CSV incorect sau encoding greșit

**Verificați:**
- Coloane obligatorii: `Timp`, `Nivel de oxigen`, `Puls cardiac`, `Mişcare`
- Format timestamp: `HH:MM:SS DD/MM/YYYY`
- Encoding UTF-8 (caractere românești)

**Soluție:** Consultați `data_parser.py` pentru format valid

---

### Aplicația nu pornește
**Verificați:**
```bash
# 1. Virtual environment activat?
.\.venv\Scripts\activate

# 2. Dependencies instalate?
pip install -r requirements.txt

# 3. Port 8050 liber?
# Opriți alte instanțe: stop_server.bat
```

---

## 📊 Diferențe: run.py vs run_medical.py

| Aspect | `run.py` (Original) | `run_medical.py` (Medical) |
|--------|---------------------|----------------------------|
| **Layout** | 2 tabs (Vizualizare + Batch) | 4 tabs (Admin + Pacient + Vizualizare + Batch) |
| **Callbacks** | callbacks.py | callbacks.py + callbacks_medical.py |
| **Workflow** | Individual (fără link-uri) | Medical complet (admin + pacient) |
| **Storage** | Local temporar | Persistent (patient_data/) |
| **Use Case** | Analiză personală | Cabinet medical |

---

## 🔄 Migrare de la Versiunea Veche

**Dacă aveți deja aplicația instalată:**

1. **Păstrați fișierele vechi** (nu se șterg automat):
   - `run.py` → rămâne funcțional
   - `app_layout.py` → rămâne funcțional
   - `callbacks.py` → reutilizat în versiunea nouă

2. **Fișiere noi adăugate:**
   - `patient_links.py` ✅
   - `app_layout_new.py` ✅
   - `callbacks_medical.py` ✅
   - `run_medical.py` ✅

3. **Folosiți:**
   - `python run.py` pentru versiunea veche (individual)
   - `python run_medical.py` pentru versiunea nouă (medical)

**NU există conflict! Ambele pot coexista.**

---

## 🎯 Roadmap Viitor (Opțional)

Pentru transformare CLOUD (conform documentelor .md):

1. **Faza 1:** Migrare PostgreSQL
   - Înlocuiește `patient_links.json` cu tabele SQL
   - Model: `admins`, `patient_links`, `recordings`, `files`

2. **Faza 2:** Deployment Railway + Cloudflare R2
   - Upload fișiere pe R2 (nu local)
   - Autentificare admin (email/password)

3. **Faza 3:** Features avansate
   - Parsare PDF rapoarte
   - Watermark automat pe imagini
   - Email notificări

**Estimare:** 8-12 săptămâni (1 developer full-time)

**Avantaj:** ~70% din logica backend EXISTĂ DEJA în cod actual! (`batch_processor.py`, `plot_generator.py`, `data_parser.py`)

---

## 📧 Contact & Suport

**Pentru probleme:**
1. Verificați log-urile: `output/LOGS/app_activity.log`
2. Citiți error messages din browser console (F12)
3. Rulați cu `debug=True` pentru traceback complet

---

**Versiune:** 3.0 Medical Workflow  
**Data:** 11 noiembrie 2025  
**Status:** ✅ Funcțional și testat  
**Conformitate:** GDPR compliant (zero date personale)

---

**👉 START RAPID:**
```bash
python run_medical.py
# → http://127.0.0.1:8050/
# → Tab Admin → Creează link pacient
# → Tab Pacient → Acces cu token
```

🎉 **Aplicația este gata de utilizare!**


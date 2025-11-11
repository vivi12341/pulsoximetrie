# ✅ TEST WORKFLOW MEDICAL - Checklist Validare

## 🎯 Scop
Verificare completă a funcționalității aplicației medicale înainte de utilizare.

---

## ⚙️ PRE-REQUISITE

- [ ] Python 3.12+ instalat
- [ ] Virtual environment creat (`.venv/`)
- [ ] Dependencies instalate (`pip install -r requirements.txt`)
- [ ] Portul 8050 liber

---

## 🚀 TEST 1: Pornire Aplicație

### Comenzi de test:
```bash
# Activare venv
.\.venv\Scripts\activate

# Pornire server medical
python run_medical.py
```

### ✅ Criterii de succes:
- [ ] Server pornește fără erori
- [ ] Log-uri afișează: "PORNIRE SERVER MEDICAL"
- [ ] Browser accesează `http://127.0.0.1:8050/`
- [ ] 4 tabs sunt vizibile:
  - [ ] Tab "👨‍⚕️ Admin (Medic)"
  - [ ] Tab "👤 Pacient"
  - [ ] Tab "📈 Vizualizare Interactivă"
  - [ ] Tab "🔄 Procesare în Lot (Batch)"

---

## 👨‍⚕️ TEST 2: Workflow Admin - Creare Link

### Pași:
1. Click tab **"👨‍⚕️ Admin (Medic)"**
2. Completează formular:
   - **Nume Aparat**: `Checkme O2 #TEST01`
   - **Notițe**: `Test pentru validare workflow`
3. Click **"🔗 Generează Link Nou"**

### ✅ Criterii de succes:
- [ ] Mesaj success verde apare
- [ ] Token UUID afișat (format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`)
- [ ] Link complet afișat (ex: `http://127.0.0.1:8050/?token=...`)
- [ ] Fișier `patient_links.json` creat în folder root
- [ ] Folder `patient_data/{token}/` creat
- [ ] Log: "✅ Link nou generat pentru aparat 'Checkme O2 #TEST01'"

**⚠️ PĂSTRAȚI TOKEN-UL pentru teste ulterioare!**

---

## 📤 TEST 3: Workflow Admin - Upload CSV

### Pași:
1. Rămâneți în tab **"Admin"**
2. Click buton **"🔄 Reîmprospătează Listă"**
3. Verificați că pacientul TEST01 apare în listă
4. În secțiunea **"Upload CSV pentru Pacient"**:
   - Selectați **Checkme O2 #TEST01** din dropdown
   - Upload un CSV din folderul `bach data/` sau `intrare/`
     (Ex: `Checkme O2 3539_20251007230437.csv`)

### ✅ Criterii de succes:
- [ ] Dropdown conține pacientul TEST01
- [ ] Upload reușește (mesaj verde)
- [ ] Statistici afișate (avg SaO2, min, max)
- [ ] Fișier CSV salvat în `patient_data/{token}/recording_{id}.csv`
- [ ] Fișier `recordings.json` creat în folder pacient
- [ ] După refresh listă: "1 înregistrări" afișat lângă pacient
- [ ] Log: "✅ Înregistrare adăugată pentru pacientul..."

---

## 👤 TEST 4: Workflow Pacient - Acces cu Token

### Pași:
1. Click tab **"👤 Pacient"**
2. Introduceți token-ul copiat la TEST 2 în câmpul de text
3. Click **"🔓 Accesează Înregistrări"**

### ✅ Criterii de succes:
- [ ] Mesaj success verde: "✅ Acces Autorizat!"
- [ ] Afișat: "Bine ați venit! Aparat: Checkme O2 #TEST01"
- [ ] Container cu sub-tabs devine vizibil
- [ ] 2 sub-tabs prezente:
  - [ ] "📁 Înregistrările Mele"
  - [ ] "🔍 Explorează CSV"
- [ ] Log: "Tentativă acces pacient cu token: ..."

---

## 📁 TEST 5: Pacient - Vizualizare Înregistrări

### Pași:
1. Rămâneți în tab **"Pacient"**
2. Click sub-tab **"📁 Înregistrările Mele"**

### ✅ Criterii de succes:
- [ ] Cel puțin 1 card cu înregistrare afișat
- [ ] Card conține:
  - [ ] Data înregistrării (ex: "📅 2025-10-07")
  - [ ] Interval orar (ex: "⏱️ Interval: 23:04:37 - 07:27:15")
  - [ ] Statistici SaO2 (avg, min, max)
  - [ ] Nume fișier original
- [ ] 2 butoane prezente:
  - [ ] "📈 Vezi Grafic"
  - [ ] "📥 Descarcă CSV"

### Bonus - Test "Vezi Grafic":
- [ ] Click "📈 Vezi Grafic"
- [ ] Modal/Secțiune cu grafic Plotly se deschide
- [ ] Grafic interactiv funcțional (zoom, pan, hover)

---

## 🔍 TEST 6: Pacient - Explorare CSV Temporară

### Pași:
1. Rămâneți în tab **"Pacient"**
2. Click sub-tab **"🔍 Explorează CSV"**
3. Upload un CSV (poate fi același ca la TEST 3 sau altul)

### ✅ Criterii de succes:
- [ ] Warning afișat: "⚠️ Graficul este temporar..."
- [ ] Grafic Plotly se generează instant
- [ ] Grafic complet cu date SaO2 + Puls
- [ ] Hover funcțional pe grafic
- [ ] Log: "Pacient explorează CSV temporar: ..."
- [ ] **IMPORTANT:** CSV NU apare în lista "Înregistrările Mele" (confirmare temporar)

---

## 📈 TEST 7: Tab Vizualizare Interactivă (Original)

### Pași:
1. Click tab **"📈 Vizualizare Interactivă"**
2. Upload CSV prin componenta de upload

### ✅ Criterii de succes:
- [ ] Funcționalitate originală păstrată 100%
- [ ] Grafic se generează
- [ ] Zoom dinamic funcțional (linie se îngroașă la zoom in)
- [ ] Fără interferențe cu workflow-ul medical

---

## 🔄 TEST 8: Tab Procesare în Lot (Original)

### Pași:
1. Click tab **"🔄 Procesare în Lot (Batch)"**
2. Specificați:
   - **Input folder**: `bach data`
   - **Output folder**: `test_output_medical`
   - **Durată fereastră**: `30` minute
3. Click **"Pornește Procesarea în Lot"**

### ✅ Criterii de succes:
- [ ] Funcționalitate originală păstrată 100%
- [ ] Mesaj: "Procesarea în lot a început..."
- [ ] Imagini JPG generate în `test_output_medical/`
- [ ] Nume folder intuitiv (ex: `02mai2025_00h25-06h37_Aparat1442`)
- [ ] Nume imagini intuitive (ex: `Aparat1442_00h25m-00h55m.jpg`)

---

## 🗑️ TEST 9: Admin - Ștergere Pacient (GDPR)

### Pași:
1. Reveniți la tab **"Admin"**
2. Click **"🔄 Reîmprospătează Listă"**
3. Găsiți pacientul TEST01
4. Click buton **"🗑️ Șterge"**
5. Confirmați ștergerea

### ✅ Criterii de succes:
- [ ] Pacientul dispare din listă
- [ ] Folder `patient_data/{token}/` șters complet
- [ ] Token șters din `patient_links.json`
- [ ] Log: "🗑️ Link șters complet (GDPR): ..."
- [ ] **Verificare GDPR:** NU mai există NICIO urmă a datelor pacientului

---

## 🔐 TEST 10: Securitate - Token Invalid

### Pași:
1. Click tab **"Pacient"**
2. Introduceți un token invalid (ex: `aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee`)
3. Click **"🔓 Accesează Înregistrări"**

### ✅ Criterii de succes:
- [ ] Mesaj eroare roșu: "❌ Token invalid sau inactiv!"
- [ ] Container cu înregistrări NU se afișează
- [ ] Log: "Link inexistent: aaaaaaaa-bbbb..."

---

## 📊 TEST 11: Validare Structură Fișiere

### Verificare manuală:

```
project_root/
├── patient_data/           ✅ Folder creat
│   └── {token}/           ✅ Subfolder per pacient
│       ├── recording_*.csv ✅ CSV-uri salvate
│       └── recordings.json ✅ Metadata
├── patient_links.json      ✅ Fișier creat
├── patient_links.py        ✅ Modul nou
├── app_layout_new.py       ✅ Layout nou
├── callbacks_medical.py    ✅ Callbacks noi
├── run_medical.py          ✅ Entry point nou
└── start_server_medical.bat ✅ Script pornire
```

### ✅ Criterii de succes:
- [ ] Toate fișierele și folderele prezente
- [ ] Fișierele vechi INTACTE (`run.py`, `app_layout.py`, `callbacks.py`)
- [ ] NU există conflicte între versiuni

---

## 🎯 REZULTAT FINAL

### Toate testele PASS?

- [ ] **DA** → ✅ Aplicația este FUNCȚIONALĂ și gata de utilizare!
- [ ] **NU** → Verificați log-urile în `output/LOGS/app_activity.log`

---

## 📋 Checklist Finalizare

- [ ] Toate testele 1-11 completate cu succes
- [ ] Log-uri verificate (fără erori critice)
- [ ] `patient_links.json` conține date valide
- [ ] `patient_data/` structură corectă
- [ ] Ambele versiuni funcționează (`run.py` + `run_medical.py`)
- [ ] README_MEDICAL.md citit și înțeles

---

## 🚀 NEXT STEPS

### Pentru utilizare în producție:

1. **Backup:** Copiați folderul `patient_data/` regulat
2. **Siguranță:** NU expuneți public portul 8050 (doar localhost)
3. **GDPR:** Documentați procesele de ștergere date
4. **Training:** Instruiți medicii cu README_MEDICAL.md

### Pentru transformare CLOUD (viitor):

1. Citiți `PLAN_IMPLEMENTARE_PLATFORMA_CLOUD.md`
2. Pregătiți buget: €19k dezvoltare + €11/lună operațional
3. Estimare timp: 12 săptămâni (1 developer full-time)

---

**📅 Data Test:** _______________  
**✍️ Testat De:** _______________  
**✅ Status:** PASS / FAIL  
**📝 Observații:** _____________________________________________

---

**Versiune:** 1.0 Test Workflow  
**Ultima actualizare:** 11 noiembrie 2025


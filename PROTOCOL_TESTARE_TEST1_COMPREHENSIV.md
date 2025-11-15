# 🧪 PROTOCOL TESTARE EXTENSIVĂ (test1) - COMPREHENSIV

**Data:** 15 Noiembrie 2025, 18:40  
**Trigger:** Comanda "test1" utilizator  
**Context:** Post force redeploy (commit 5c7d4a5) pentru fix Railway cache  
**Durată estimată:** 45-60 minute  

---

## 📋 CHECKLIST TESTARE (Completează ✓ pe măsură ce testezi)

### FAZA 0: VERIFICARE DEPLOYMENT ✅ (5 min)
- [ ] Railway Activity → "Deployment successful" (commit 5c7d4a5)
- [ ] Railway Deploy Logs → mesaj "Dash 3.x syntax" prezent
- [ ] Railway HTTP Logs → zero erori 500
- [ ] Browser → Hard refresh (Ctrl+Shift+R)
- [ ] Browser Console (F12) → Zero erori "dash_html_components not found"
- [ ] Network Tab → `dash_html_components.min.js` → 200 OK

**DACĂ oricare ❌ → STOP ȘI RAPORTEAZĂ!**

---

## 1️⃣ BROWSER TESTING (15 min)

### A. Asset Loading - Railway HTTP Logs
**Instrucțiuni:**
1. Railway Dashboard → HTTP Logs
2. Filter timeline: ultimele 5 minute
3. Verifică requests după hard refresh

**Checklist Assets (TOATE trebuie 200 OK):**
```
- [ ] GET / → 200 (< 100ms)
- [ ] GET /assets/style.css → 200
- [ ] GET /_dash-component-suites/dash/deps/react@18.*.min.js → 200
- [ ] GET /_dash-component-suites/dash/deps/react-dom@18.*.min.js → 200
- [ ] GET /_dash-component-suites/dash/deps/polyfill@7.*.min.js → 200
- [ ] GET /_dash-component-suites/dash/deps/prop-types@15.*.min.js → 200
- [ ] GET /_dash-component-suites/dash/html/dash_html_components.*.min.js → 200 ✅ CRITICAL!
- [ ] GET /_dash-component-suites/dash/dcc/dash_core_components.*.js → 200
- [ ] GET /_dash-component-suites/dash/dcc/dash_core_components-shared.*.js → 200
- [ ] GET /_dash-component-suites/dash/dash_table/bundle.*.js → 200
- [ ] GET /_dash-component-suites/dash/dash-renderer/build/dash_renderer.*.min.js → 200
- [ ] GET /_dash-layout → 200
- [ ] GET /_dash-dependencies → 200
```

**Asset Timestamp Check:**
- Current timestamp: `v3_0_5m________` (notează numărul)
- Expected: > 1763224319 (deployment post-force redeploy)
- **DACĂ timestamp < 1763224319 → Railway încă folosește deployment vechi!**

---

### B. Browser Console (Edge/Chrome)
**Instrucțiuni:**
1. Deschide https://pulsoximetrie.cardiohelpteam.ro
2. F12 → Console Tab
3. Hard refresh (Ctrl+Shift+R)

**Checklist Console (Zero erori acceptate!):**
```
✅ TREBUIE SĂ APARĂ:
- [ ] "[app/index] local: {debug: false, locale: 'en'}" 

❌ NU TREBUIE SĂ APARĂ:
- [ ] "Error: dash_html_components was not found" → DACĂ APARE = FIX NU E ACTIV!
- [ ] "GET ...dash_html_components... 500" → DACĂ APARE = FIX NU E ACTIV!

⚠️ ACCEPTABLE (non-blocking):
- [ ] "A callback is missing Inputs" (Dash internal warning - OK)
- [ ] Edge extension errors (password manager - NU din app)
```

**DACĂ vezi erori dash_html_components → STOP ȘI RAPORTEAZĂ IMEDIAT!**

---

### C. Network Tab Analysis
**Instrucțiuni:**
1. F12 → Network Tab
2. Hard refresh (Ctrl+Shift+R)
3. Filter: "dash"

**Metrics Target:**
```
- [ ] Total requests: 15-20
- [ ] Failed requests (status 4xx/5xx): 0 ✅
- [ ] Page load time: < 5s (first load) sau < 2s (cached)
- [ ] Largest asset: dash_renderer.min.js (~234KB)
```

**Performance Check:**
```
Asset                          | Size    | Time   | Status
-------------------------------|---------|--------|--------
dash_html_components.min.js    | 208KB   | ?      | 200 ✅
dash_core_components.js        | 695KB   | ?      | 200
dash_renderer.min.js           | 234KB   | ?      | 200
react-dom.min.js               | 132KB   | ?      | 200
```

**⚠️ Performance Warning Levels:**
- 🟢 < 1s per asset = EXCELLENT
- 🟡 1-5s per asset = ACCEPTABLE (Railway cold start)
- 🔴 > 10s per asset = SLOW (investigate)

---

## 2️⃣ FUNCȚIONALITATE LOGIN + DASHBOARD (10 min)

### A. Login Test
**Instrucțiuni:**
1. Accesează https://pulsoximetrie.cardiohelpteam.ro
2. Verifică că apare formular login (NU loading blocat!)

**Checklist Login UI:**
```
- [ ] Formular login afișat corect (email + parolă)
- [ ] Logo aplicație (dacă există)
- [ ] Buton "Autentifică-te" vizibil
- [ ] Placeholder text corect în input-uri
- [ ] Design responsive (nu overflow)
```

**Test Login:**
```
Email: viorelmada1@gmail.com
Parolă: [parola ta]

- [ ] Click "Autentifică-te"
- [ ] Redirect către Dashboard (NU rămâi pe login!)
- [ ] Mesaj "Autentificare cu succes" sau similar
- [ ] Header shows nume doctor + "Deconectare"
```

---

### B. Dashboard Medical
**Instrucțiuni:** După login SUCCESS

**Checklist Tabs:**
```
- [ ] Tab "Gestiune Date" (sau similar) afișat
- [ ] Tab "Upload în Lot" afișat
- [ ] Tab "Dashboard" afișat
- [ ] Tab "Setări" afișat
- [ ] Tab "Administrare Utilizatori" (dacă admin)
```

**Test Tab Switching:**
```
- [ ] Click pe fiecare tab → schimbă conținut (NU freeze!)
- [ ] Tab activ highlighted
- [ ] Conținut tab se încarcă (NU loading infinit)
```

**Checklist Tab "Gestiune Date":**
```
- [ ] Tabel pacienți afișat (sau mesaj "Niciun pacient")
- [ ] Coloane: Nume/Link/Data/etc.
- [ ] Butoane acțiuni (vizualizare, ștergere, etc.)
- [ ] Search/filter functional (dacă există)
```

---

## 3️⃣ UPLOAD CSV + GRAFIC (15 min)

### A. Pregătire Test CSV
**Creează CSV test cu format CORECT:**

```csv
Timp,Nivel de oxigen,Puls cardiac,Mişcare
20:35:10 15/10/2025,92,78,0
20:35:14 15/10/2025,92,78,0
20:35:18 15/10/2025,93,78,0
20:35:22 15/10/2025,94,77,0
20:35:26 15/10/2025,92,76,1
20:35:30 15/10/2025,88,75,2
```

**Salvează ca:** `test_checkme_o2.csv` (UTF-8 encoding!)

---

### B. Upload Single CSV Test
**Instrucțiuni:**
1. Tab "Gestiune Date" (sau "Vizualizare Interactivă")
2. Găsește zona "Upload CSV" sau "Drag & Drop"
3. Upload `test_checkme_o2.csv`

**Checklist Upload:**
```
- [ ] Upload area highlighted la hover
- [ ] Progress indicator la upload (spinner/progress bar)
- [ ] Mesaj success "Fișier încărcat cu succes" (sau similar)
- [ ] Preview date (tabel cu primele rânduri)
```

---

### C. Grafic Generation Test
**După upload SUCCESS:**

**Checklist Grafic Afișat:**
```
- [ ] Grafic Plotly interactiv generat
- [ ] Axa X: Timp (ore:minute)
- [ ] Axa Y stânga: SpO2 (%) - linie albastră/roșie
- [ ] Axa Y dreapta: Puls (bpm) - linie verde/portocalie
- [ ] Titlu grafic: conține data + aparat (dacă detectat)
- [ ] Legendă afișată (SpO2, Puls)
```

**Checklist Interactivitate Grafic:**
```
- [ ] Hover → tooltip cu valori exacte (timp, SpO2, Puls)
- [ ] Zoom (drag pe grafic) → funcționează
- [ ] Pan (shift+drag) → funcționează
- [ ] Reset zoom (double click) → funcționează
- [ ] Download grafic (buton Plotly) → funcționează
```

**Test Zoom Dinamic (IMPORTANT!):**
```
- [ ] Zoom IN pe o regiune mică (ex: 10 minute)
- [ ] Verifică că linia devine MAI GROASĂ (responsive line width)
- [ ] Zoom OUT → linia devine MAI SUBȚIRE
```

**DACĂ zoom dinamic NU funcționează → NOTE în raport, nu e critical**

---

## 4️⃣ EXPORT GRAFIC (5 min)

### A. Export PNG/JPG Test
**Instrucțiuni:**
1. După generare grafic SUCCESS
2. Găsește buton "Export PNG" sau "Download Grafic"

**Checklist Export:**
```
- [ ] Click "Export PNG" → download începe
- [ ] Fișier descărcat: format .png sau .jpg
- [ ] Dimensiune: 50-500KB (rezonabil)
- [ ] Nume fișier: descriptiv (ex: "15oct2025_20h35_Aparat0331.png")
```

**Verificare Imagine Exportată:**
```
- [ ] Deschide imaginea → se afișează corect
- [ ] Rezoluție: min 1200x800 px (verifică proprietăți fișier)
- [ ] Watermark: logo clinică + telefon + adresă (în footer imagine)
- [ ] Grafic lizibil (text, linii, legendă)
```

**Privacy Check (CRITICAL!):**
```
- [ ] Click dreapta pe imagine → Proprietăți → Details
- [ ] Metadata EXIF: NU conține nume pacient, CNP, telefon
- [ ] Metadata OK: doar date tehnice (dimensiuni, format, data export)
```

---

## 5️⃣ BULK UPLOAD TEST (10 min)

### A. Pregătire Multiple Fișiere
**Creează 3 CSV-uri test:**

```
test_patient1_15oct.csv  (date 15 Oct, aparat 0331)
test_patient2_16oct.csv  (date 16 Oct, aparat 3539)
test_patient1_17oct.csv  (date 17 Oct, aparat 0331 - ACELAȘI pacient!)
```

---

### B. Bulk Upload + Asociere
**Instrucțiuni:**
1. Tab "Upload în Lot"
2. Upload toate 3 fișiere simultan (Ctrl+click sau drag all)

**Checklist Bulk Upload:**
```
- [ ] Toate 3 fișiere apar în listă "Fișiere încărcate"
- [ ] Preview pentru fiecare (nume, dimensiune, status)
- [ ] Buton "Procesează" sau "Generează Link-uri" activ
```

**Test Asociere Manuală:**
```
- [ ] Click "Procesează"
- [ ] Dialog apare: "Selectați pacient pentru fiecare test"
- [ ] Pentru test_patient1_15oct:
    → Opțiune "Creează Link NOU" selectabilă
    → Input nume pacient: "Ion Popescu Test"
    → Generează link: https://...?token=abc123...
- [ ] Pentru test_patient2_16oct:
    → Opțiune "Creează Link NOU"
    → Input nume: "Maria Ionescu Test"
    → Generează link diferit
- [ ] Pentru test_patient1_17oct:
    → Opțiune "Adaugă la Link EXISTENT" selectabilă
    → Dropdown listă: vede "Ion Popescu Test (abc123...)"
    → Selectează → adaugă la același link
```

**DACĂ dialog asociere NU apare → NOTE în raport (feature posibil lipsă)**

---

## 6️⃣ PAGINĂ PACIENT + LINK PERSISTENT (10 min)

### A. Accesare Link Pacient
**Instrucțiuni:**
1. Copiază link generat (ex: https://pulsoximetrie.cardiohelpteam.ro/?token=abc123...)
2. Deschide în tab nou (sau incognito pentru test fără login)

**Checklist Pagină Pacient:**
```
- [ ] Pagina se încarcă (NU login required!)
- [ ] Header: "Înregistrările Tale" (fără nume pacient!)
- [ ] Logo clinică afișat (dacă medicul l-a setat)
- [ ] Footer clinică: telefon, adresă (dacă setat)
```

**Test Multiple Înregistrări (pentru pacient cu 2 teste):**
```
- [ ] Secțiune 1: "Înregistrare din Marți 15 Octombrie 2025..."
    → Grafic interactiv afișat
    → Butoane download (CSV, PNG)
    → Raport PDF (dacă există)
- [ ] Secțiune 2: "Înregistrare din Joi 17 Octombrie 2025..."
    → Grafic SEPARAT (NU același cu secțiunea 1!)
    → Date diferite (verifică valori tooltip)
```

**Test Persistență Link:**
```
- [ ] Închide tab-ul
- [ ] Redeschide același link după 5 minute
- [ ] Verifică: datele ÎNCĂ vizibile (link NU expirat!)
```

---

## 7️⃣ ERROR SCENARIOS (10 min)

### A. CSV Format Greșit - Coloane în Engleză
**Test CSV invalid:**
```csv
Time,Oxygen Level,Heart Rate,Movement
20:35:10 15/10/2025,92,78,0
```

**Test:**
```
- [ ] Upload CSV invalid
- [ ] Verifică mesaj eroare: "Coloane obligatorii lipsă" (sau similar)
- [ ] Aplicația NU crash-uiește
- [ ] Poate încărca alt CSV după eroare
```

---

### B. CSV Coloane Lipsă
**Test CSV incomplet:**
```csv
Timp,Nivel de oxigen
20:35:10 15/10/2025,92
```

**Test:**
```
- [ ] Upload CSV fără "Puls cardiac"
- [ ] Mesaj eroare specific: "Coloană 'Puls cardiac' lipsește"
- [ ] NU se generează grafic incomplet
```

---

### C. CSV cu Date Personale (PRIVACY TEST!)
**Test CSV cu date interzise:**
```csv
Timp,Nivel de oxigen,Puls cardiac,Nume,CNP
20:35:10 15/10/2025,92,78,Ion Popescu,1234567890123
```

**Test CRITICAL:**
```
- [ ] Upload CSV cu coloane "Nume", "CNP"
- [ ] Verifică: sistem RESPINGE automat (sau șterge coloane)
- [ ] Mesaj eroare: "Date personale detectate" (sau similar)
- [ ] CSV NU se procesează
```

**⚠️ DACĂ CSV cu date personale e ACCEPTAT → REPORT IMEDIAT (privacy violation!)

---

### D. Timestamp Invalid
**Test CSV cu format dată greșit:**
```csv
Timp,Nivel de oxigen,Puls cardiac
2025-10-15 20:35:10,92,78
```

**Test:**
```
- [ ] Upload CSV cu format timestamp greșit
- [ ] Mesaj eroare: "Format dată invalid" (sau similar)
- [ ] Specifică format așteptat: HH:MM:SS DD/MM/YYYY
```

---

### E. Valori Medicale Invalide
**Test CSV cu valori imposibile:**
```csv
Timp,Nivel de oxigen,Puls cardiac
20:35:10 15/10/2025,150,500
```

**Test:**
```
- [ ] Upload CSV cu SpO2=150% (imposibil!)
- [ ] Sistem filtrează rânduri invalide SAU respinge CSV
- [ ] Warning log: "Valori medicale invalide detectate"
```

---

## 8️⃣ PERFORMANCE METRICS (5 min)

### A. Railway Logs Analysis
**Instrucțiuni:**
1. Railway → Deploy Logs
2. Search: "CALLBACK" sau "route_layout"

**Verifică Log-uri Callback Principal:**
```
- [ ] [LOG 1/40] CALLBACK START - pathname=/
- [ ] [LOG 8/40] app_layout_new imported successfully
- [ ] [LOG 20/40] Authentication status retrieved
- [ ] [LOG 40/40] NOT AUTHENTICATED → Creating login prompt (sau medical_layout)
```

**DACĂ log-uri LIPSESC → callback NU se execută (PROBLEMA SERIOASĂ!)

---

### B. Response Time Check
**Railway HTTP Logs:**
```
Request              | Target Time | Actual | Status
---------------------|-------------|--------|--------
GET /                | < 100ms     | ?      | 200
GET /_dash-layout    | < 50ms      | ?      | 200
GET assets           | < 500ms     | ?      | 200
POST upload CSV      | < 3s        | ?      | 200
```

---

## 9️⃣ PRIVACY AUDIT (5 min)

### A. Railway Logs Privacy Check
**Instrucțiuni:**
1. Railway → Deploy Logs
2. Search: pacient nume (ex: "Ion Popescu")

**Verifică:**
```
- [ ] Zero rezultate pentru nume pacienți în logs
- [ ] Zero CNP-uri în logs
- [ ] Zero telefoane în logs
- [ ] Logs conțin DOAR: token-uri (partial: abc123...), device numbers, technical data
```

---

### B. Browser Network Tab Privacy
**Instrucțiuni:**
1. F12 → Network Tab
2. Verifică request payloads

**Verifică:**
```
- [ ] Request URLs: NU conțin nume pacienți (doar token-uri)
- [ ] Request bodies: NU conțin date personale plain text
- [ ] Response bodies: Date medicale OK, date personale NU
```

---

## 🔟 MOBILE RESPONSIVE TEST (5 min)

### A. Device Mode Test
**Instrucțiuni:**
1. F12 → Toggle Device Mode (Ctrl+Shift+M)
2. Selectează "iPhone 12 Pro" sau "Samsung Galaxy S20"

**Checklist Mobile:**
```
- [ ] Login form: afișat corect (nu overflow)
- [ ] Dashboard tabs: scrollable orizontal (dacă nu încap)
- [ ] Grafic: responsive (scală la dimensiune mică)
- [ ] Butoane: touchable (min 44x44px)
- [ ] Text: lizibil (font size min 14px)
- [ ] Upload area: funcțional pe touch
```

---

## 📊 RAPORT FINAL TEST1

### Template Raport (Completează și trimite-mi):

```markdown
# RAPORT TESTARE TEST1 - [Data/Ora]

## ✅ TESTS PASSED
- [ ] FAZA 0: Deployment verificat
- [ ] 1. Browser Testing (assets 200 OK)
- [ ] 2. Login + Dashboard
- [ ] 3. Upload CSV + Grafic
- [ ] 4. Export grafic
- [ ] 5. Bulk upload
- [ ] 6. Pagină pacient
- [ ] 7. Error scenarios
- [ ] 8. Performance
- [ ] 9. Privacy audit
- [ ] 10. Mobile responsive

## ❌ TESTS FAILED
[Listează ce NU a funcționat]

## ⚠️ WARNINGS
[Listează probleme minore]

## 📊 METRICS
- Page load time: [X] secunde
- Asset loading: [minim - maxim] secunde
- Grafic generation: [X] secunde
- CSV parsing: [X] secunde

## 🔍 CONSOLE ERRORS
[Screenshot sau copy-paste erori]

## 📝 OBSERVAȚII
[Orice altceva observat]

## 🎯 VERDICT FINAL
[PASS / PARTIAL PASS / FAIL]
```

---

## 🚀 DUPĂ TESTARE

**Dacă PASS:**
✅ Marchează aplicația ca PRODUCTION READY
✅ Notify stakeholders (medici)
✅ Enable monitoring (Sentry/analytics)

**Dacă PARTIAL PASS:**
⚠️ Documentează issues non-critice
⚠️ Plan follow-up fixes (sprint viitor)
⚠️ Deploy cu warnings documentate

**Dacă FAIL:**
❌ Identifică issue critical (ex: eroare 500 încă există)
❌ Rollback la deployment anterior (dacă posibil)
❌ Debug cu prioritate P0

---

**Durată totală estimată:** 60 minute  
**Prioritate:** 🔴 CRITICAL (validare post-fix)  
**Documentație:** Acest fișier + RAPORT_TEST1_DASH_3X_FIX_COMPLETE.md  

**Start Testing:** ACUM! 🚀


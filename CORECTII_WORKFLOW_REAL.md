# 🔄 CORECȚII WORKFLOW REAL - Update Documentație

## ⚠️ CLARIFICARE IMPORTANTĂ

**Workflow-ul REAL (confirmat de utilizator) este DIFERIT de cel presupus inițial!**

---

## 📋 WORKFLOW REAL CONFIRMAT

**🔄 ULTIMELE UPDATE-URI (11 NOV 2025):**

1. **✅ Download cu Watermark** - toate PNG-urile downloadate includ automat logo + telefon + adresă clinică (configurabil de admin)

2. **✅ Selector Interval pentru Download** - când se apasă "Download PNG", apare dialog cu 3 opțiuni:
   - Grafic complet (toată înregistrarea)
   - Ferestre de timp (15, 30, 60, 120, 180 min) → ZIP cu multiple imagini
   - Interval personalizat (selectează oră start + oră final) → 1 imagine
   
   Beneficii: analiză detaliată, printare ușoară, partajare selectivă

3. **⚡ IMPORTANT:** Funcționalitatea de generare grafice pe intervale **EXISTĂ DEJA** în `batch_processor.py`!
   - ✅ ~70% din logica backend poate fi reutilizată
   - ✅ Economie ~10 zile de dezvoltare (doar adaptare pentru cloud, nu creare de la zero)
   - ✅ Cod battle-tested pe date reale
   - ✅ Nume fișiere intuitive deja implementate

4. **🔒 LINK-URI PERSISTENTE** - link-urile generate de medic nu expiră NICIODATĂ:
   - ✅ Pacientul poate reveni la link oricând (chiar și după luni/ani)
   - ✅ **Link = PACIENT** (nu aparat!) - un pacient poate folosi aparate diferite
   - ✅ Medicul adaugă date noi la link existent (același pacient, aparat diferit sau același aparat)
   - ✅ Fără dată de expirare automată (doar admin poate dezactiva manual)
   - ✅ Merge links păstrează persistența (target link rămâne activ)

---

### 1. **Cine Uploadează Datele?**

❌ **GREȘIT (în documentația inițială):**
```
Pacientul uploadează CSV-urile sale de acasă
```

✅ **CORECT (workflow real):**
```
MEDICUL uploadează BULK după ce pacientul aduce aparatul la cabinet
- Medic descarcă datele din aparat (software propriu aparatului)
- Medic uploadează simultan: 5-10 zile × (1 CSV + 1 PDF raport) = 10-20 fișiere
- Sistem procesează automat și generează link-uri
```

---

### 2. **Tipuri Fișiere Uploadate**

✅ **2 TIPURI per înregistrare:**

#### A. **CSV (Date Brute)**
```
Checkme O2 3539_20251007230437.csv
- Conține: Date, Time, SpO2, PR (reading la fiecare secundă)
- Folosit pentru: Generare grafic Plotly interactiv
- Stocare: Cloudflare R2 (fișier original păstrat)
```

#### B. **PDF Raport (Interpretat de Aparat)**
```
Checkme O2 3539_20251007_Report.pdf
- Conține: Statistici calculate de aparat (avg, min, max, evenimente)
- Format: Text + tabele + mini-grafice (generat de soft aparat)

❌ NU stocăm PDF ca fișier!
✅ PARSĂM PDF → Extragem text/date → Stocăm în DB (JSON)
✅ Afișăm raportul frumos formatat pe site (HTML)
```

**Exemplu structură PDF raport:**
```
═══════════════════════════════════════
  RAPORT PULSOXIMETRIE - Checkme O2
═══════════════════════════════════════
Aparat: Checkme O2 #3539
Data: 7 octombrie 2025
Ora start: 23:04:37
Durată: 8h 23min

STATISTICI:
- SpO2 mediu: 94.2%
- SpO2 minim: 87%
- SpO2 maxim: 99%
- Puls mediu: 72 bpm
- Puls minim: 58 bpm
- Puls maxim: 95 bpm

EVENIMENTE DETECTATE:
- Desaturări (SpO2 < 90%): 23 evenimente
- Durată totală desaturări: 45 minute
- Cea mai lungă desaturare: 3min 15s

INTERPRETARE AUTOMATĂ:
⚠️ Desaturări moderate detectate
→ Recomandare: Consultație pneumologie
═══════════════════════════════════════
```

**Stocare în DB:**
```json
{
  "device_id": "Checkme O2 #3539",
  "date": "2025-10-07",
  "start_time": "23:04:37",
  "duration_minutes": 503,
  "stats": {
    "spo2_avg": 94.2,
    "spo2_min": 87,
    "spo2_max": 99,
    "pulse_avg": 72,
    "pulse_min": 58,
    "pulse_max": 95
  },
  "events": {
    "desaturations_count": 23,
    "desaturations_total_duration": 45,
    "longest_desaturation": 195
  },
  "auto_interpretation": "Desaturări moderate detectate. Recomandare: Consultație pneumologie."
}
```

---

### 3. **Generare Link-uri (AUTOMAT!)**

❌ **GREȘIT (în documentația inițială):**
```
1. Admin creează manual link pentru pacient
2. Completează formular: nume aparat, dată start, notițe
3. Link generat: https://app.com/p/a8f9d2b1
4. Admin trimite link către pacient
```

✅ **CORECT (workflow real):**
```
1. Admin uploadează BULK folder cu fișiere:
   /uploads/
     ├─ Checkme O2 3539_20251007230437.csv
     ├─ Checkme O2 3539_20251007_Report.pdf
     ├─ Checkme O2 3539_20251014203224.csv
     ├─ Checkme O2 3539_20251014_Report.pdf
     ├─ Checkme O2 3541_20251007202217.csv  ← Aparat DIFERIT!
     ├─ Checkme O2 3541_20251007_Report.pdf
     └─ ... (10-20 fișiere)

2. Sistem procesează AUTOMAT:
   - Parsează nume fișier → extrage: device_id + date
   - Grupează: CSV + PDF cu același device_id + date
   - Creează recording în DB
   - Generează grafic din CSV
   - Parsează PDF → JSON în DB

3. Sistem generează AUTOMAT link-uri:
   - 1 link per APARAT (nu per înregistrare!)
   - Link 1: https://app.com/p/a8f9d2b1 (Checkme O2 #3539 - 2 înregistrări)
   - Link 2: https://app.com/p/x7y8z9w0 (Checkme O2 #3541 - 1 înregistrare)

4. Admin vede dialog: "Selectați link sau creați nou"
   ┌────────────────────────────────────────────────────────┐
   │ 📤 UPLOAD COMPLET - Selectați Pacient                  │
   │                                                         │
   │ 10 înregistrări procesate (5 aparate, 7 date diferite)│
   │                                                         │
   │ ⚪ Creează link NOU (pacient nou)                       │
   │                                                         │
   │ ⚫ Adaugă la link EXISTENT:                             │
   │   ┌─────────────────────────────────────────────────┐ │
   │   │ 🔍 Caută link: [_______________] 🔎            │ │
   │   └─────────────────────────────────────────────────┘ │
   │                                                         │
   │   Link-uri recente:                                    │
   │   ☑️ ...a8f9d2b1 | 5 înreg | Ultima: 14 oct          │
   │   ☐ ...x7y8z9w0 | 3 înreg | Ultima: 7 oct            │
   │   ☐ ...b2c3d4e5 | 12 înreg | Ultima: 1 nov           │
   │                                                         │
   │ [Confirmare] [Anulează]                                │
   └────────────────────────────────────────────────────────┘

5. Admin confirmă → Rezultat:
   ┌────────────────────────────────────────────────────────┐
   │ ✅ Upload complet!                                      │
   │                                                         │
   │ 10 înregistrări adăugate la link: ...a8f9d2b1         │
   │                                                         │
   │ Detalii:                                               │
   │ • 7 oct | Aparat #3539                                 │
   │ • 14 oct | Aparat #3539                                │
   │ • 21 oct | Aparat #3541 (aparat diferit!)              │
   │ • 5 nov | Aparat #3542 (aparat diferit!)               │
   │                                                         │
   │ Total înregistrări link: 15 (5 vechi + 10 noi)        │
   │                                                         │
   │ Link: https://clinica.ro/p/a8f9d2b1                   │
   │ [📋 Copiază] [📧 Trimite Email] [👁️ Vezi Pagină]      │
   └────────────────────────────────────────────────────────┘

6. Admin trimite link către pacient (doar dacă link NOU sau la cerere)
```

**Logică generare link (CU PERSISTENȚĂ - Link = PACIENT!):**
```python
def generate_links_from_bulk_upload(files, admin_id, patient_link_id=None):
    """
    Generează link-uri după upload bulk
    
    🔒 LINK-URI PERSISTENTE:
    - Link = PACIENT (nu aparat!)
    - Același pacient poate folosi aparate diferite (#3539, #3541, etc.)
    - Același aparat poate fi folosit de pacienți diferiți
    - Medicul specifică dacă uploadează pentru link existent sau creează link nou
    
    Args:
        files: Lista fișiere uploadate
        admin_id: ID admin care uploadează
        patient_link_id: (Optional) Link existent pentru care se adaugă date
                         Dacă None → creează link-uri noi
    """
    # Grupare fișiere per (aparat, dată)
    groups = {}
    
    for file in files:
        # Parse filename: "Checkme O2 3539_20251007230437.csv"
        device_id = extract_device_id(file.name)  # "Checkme O2 #3539"
        date = extract_date(file.name)  # 2025-10-07
        
        key = (device_id, date)
        if key not in groups:
            groups[key] = {'csv': None, 'pdf': None}
        
        if file.name.endswith('.csv'):
            groups[key]['csv'] = file
        elif file.name.endswith('.pdf'):
            groups[key]['pdf'] = file
    
    # Dacă medicul a specificat link existent
    if patient_link_id:
        # ✅ ADAUGĂ TOATE DATELE LA LINK EXISTENT (același pacient)
        link = PatientLink.query.get(patient_link_id)
        
        if not link or link.created_by != admin_id:
            raise ValueError("Invalid patient link")
        
        # Procesează toate grupurile pentru acest link
        for (device_id, date), files_dict in groups.items():
            process_recording_group(link, device_id, date, files_dict)
        
        logger.info(f"Adăugate {len(groups)} înregistrări la link existent {link.token}")
        return [link]
    
    else:
        # ✅ CREEAZĂ LINK-URI NOI (unul per grup sau manual specificat)
        # UI-ul va permite medicului să specifice cum vrea să grupeze
        
        # Opțiune 1: UN LINK pentru toate datele (pacient unic)
        # Opțiune 2: Link-uri separate per aparat
        # Opțiune 3: Link-uri separate per dată
        
        # Exemplu: UN LINK pentru toate (presupunem același pacient)
        token = secrets.token_urlsafe(16)
        link = PatientLink(
            token=token,
            created_by=admin_id,
            created_at=datetime.now(),
            is_active=True,
            # ⚠️ IMPORTANT: Fără expires_at! Link persistente
            # ⚠️ IMPORTANT: Fără device_name! Link = pacient, nu aparat
        )
        db.session.add(link)
        db.session.flush()
        
        # Procesează toate înregistrările pentru acest link
        for (device_id, date), files_dict in groups.items():
            process_recording_group(link, device_id, date, files_dict)
        
        db.session.commit()
        logger.info(f"Creat link NOU {token} cu {len(groups)} înregistrări")
        return [link]


def process_recording_group(link, device_id, date, files_dict):
    """
    Procesează un grup (device, date) și creează Recording
    """
    # Upload CSV
    csv_file = files_dict.get('csv')
    if csv_file:
        # ... (logica de upload & procesare CSV)
        pass
    
    # Parse PDF
    pdf_file = files_dict.get('pdf')
    report_data = None
    if pdf_file:
        report_data = pdf_parser.parse_report_pdf(pdf_file)
    
    # Creează Recording cu device_name
    recording = Recording(
        patient_link_id=link.id,
        device_name=device_id,  # ✅ Device la nivel de RECORDING, nu LINK!
        recording_date=date,
        # ... alte câmpuri
    )
    db.session.add(recording)
```

**🔒 Avantaje Link-uri Persistente (Link = PACIENT!):**

1. **UX Excelent pentru Pacient - Un Pacient, Multiple Aparate:**
   ```
   Pacient Maria Popescu primește link: https://clinica.ro/p/a8f9d2b1
   
   Timeline:
   7 Oct 2025  → Folosește aparat #3539 | Click link → Vezi 1 înregistrare
   14 Oct 2025 → Folosește aparat #3539 | Click link → Vezi 2 înregistrări
   21 Oct 2025 → Folosește aparat #3541 | Click link → Vezi 3 înregistrări (aparat diferit!)
   5 Ian 2026  → Folosește aparat #3542 | Click link → Vezi 6 înregistrări (după 3 luni!)
   
   ✅ Maria salvează link-ul o singură dată (bookmark browser)
   ✅ Verifică oricând evoluția (aparate diferite, același link!)
   ✅ Un singur link pentru TOT istoricul medical
   ```

2. **Simplu pentru Medic - Control Total:**
   ```
   Upload 1 (7 oct, aparat #3539):
   ├─ Medic: "Pacient nou" → sistem creează link a8f9d2b1
   └─ Medic trimite link către Maria (email/SMS)
   
   Upload 2 (14 oct, aparat #3539 din nou):
   ├─ Medic: Selectează link a8f9d2b1 existent
   └─ Date adăugate la ACELAȘI link (NU trimite link din nou!)
   
   Upload 3 (21 oct, aparat #3541 - aparat DIFERIT!):
   ├─ Medic: Selectează link a8f9d2b1 existent
   └─ Date adăugate la ACELAȘI link (Maria vede tot!)
   
   ✅ Medicul controlează: "Date noi pentru pacient X → selectez link X"
   ✅ NU contează ce aparat (#3539, #3541, #3542)
   ✅ Un singur link per pacient
   ```

3. **Același Aparat, Pacienți Diferiți:**
   ```
   Aparat #3539 folosit de:
   
   Maria Popescu:
   ├─ Link: https://clinica.ro/p/a8f9d2b1
   ├─ Înregistrări: 7 oct (aparat #3539), 14 oct (aparat #3539)
   └─ Total: 2 înregistrări cu aparat #3539
   
   Ion Ionescu:
   ├─ Link: https://clinica.ro/p/x7y8z9w0 (link DIFERIT!)
   ├─ Înregistrări: 20 oct (aparat #3539), 21 oct (aparat #3539)
   └─ Total: 2 înregistrări cu aparat #3539
   
   ✅ Același aparat, link-uri diferite (pacienți diferiți)
   ✅ Maria NU vede datele lui Ion (chiar dacă același aparat!)
   ```

4. **Partajare Permanentă:**
   ```
   Pacient partajează link cu:
   - Alt medic pentru second opinion (link rămâne valid)
   - Asigurare pentru documentație (link rămâne valid)
   - Familie pentru transparență (link rămâne valid)
   
   ✅ Link-ul nu devine "mort" după X zile
   ✅ Include TOATE aparatele folosite de pacient
   ```

---

### 4. **Aparate Diferite Pentru Același Pacient**

✅ **WORKFLOW CORECT (Link = PACIENT):**
```
Pacientul Maria - Prima vizită (7 oct):
├─ Aparat folosit: #3539
├─ Medic uploadează date
├─ Medic: Selectează "Creează link NOU" (pacient nou)
├─ Sistem: Generează link https://clinica.ro/p/a8f9d2b1
└─ Medic: Trimite link către Maria (SMS/email)

Pacientul Maria - Control (14 oct):
├─ Aparat folosit: #3539 (același)
├─ Medic uploadează date
├─ Medic: Selectează link a8f9d2b1 existent (din listă)
├─ Sistem: Adaugă înregistrări la ACELAȘI link
└─ Medic: NU trimite link (Maria îl are deja!)

Pacientul Maria - Control (21 oct):
├─ Aparat folosit: #3541 (DIFERIT!)
├─ Medic uploadează date
├─ Medic: Selectează link a8f9d2b1 existent (același pacient!)
├─ Sistem: Adaugă înregistrări la ACELAȘI link
└─ Maria: Click link → vede TOATE datele (aparate #3539 + #3541)

✅ Rezultat:
Link a8f9d2b1 conține:
├─ 7 oct (aparat #3539)
├─ 14 oct (aparat #3539)
└─ 21 oct (aparat #3541) ← Aparat diferit, ACELAȘI link!
```

**Feature "Merge Links" (când medicul greșește):**

```
Scenariu: Medicul a creat din greșeală 2 link-uri pentru Maria

Upload 1 (7 oct, aparat #3539):
└─ Medic: Creează link NOU → Link 1 (a8f9d2b1)

Upload 2 (21 oct, aparat #3541):
└─ Medic: GREȘIT! Creează link NOU → Link 2 (x7y8z9w0)
    (trebuia să selecteze Link 1 existent!)

PROBLEM: Maria are 2 link-uri pentru același pacient!

SOLUȚIE: Admin merge links
1. Admin selectează Link 1 + Link 2
2. Click "Contopește Link-uri"
3. Sistem:
   - Mută toate înregistrările Link 2 → Link 1
   - Marchează Link 2 ca "merged_into: link_1"
   - Link 2 redirect automat la Link 1
   
4. Rezultat:
   Link 1 (a8f9d2b1): TOATE înregistrările (aparate #3539 + #3541)
   Link 2 (x7y8z9w0): Redirect permanent la Link 1
```

**Cod merge:**
```python
def merge_patient_links(source_link_id, target_link_id):
    """
    Contopește toate înregistrările de la source → target
    Source link devine invalid (redirect la target)
    """
    source = PatientLink.query.get(source_link_id)
    target = PatientLink.query.get(target_link_id)
    
    # Mută toate înregistrările
    Recording.query.filter_by(patient_link_id=source.id).update({
        'patient_link_id': target.id
    })
    
    # Marchează source ca merged
    source.is_active = False
    source.merged_into = target.id
    source.merged_at = datetime.now()
    
    db.session.commit()
    
    logger.info(f"Merged link {source.token} → {target.token}")
    return target
```

---

### 5. **Interfață Pacient (2 TABURI)**

✅ **Tab 1: "Înregistrările Mele"** (date stocate, read-only)
```
┌─────────────────────────────────────────────────────────┐
│ 📊 Monitorizare Saturație Oxigen                        │
│                                                         │
│ [Înregistrările Mele] [Explorează CSV]  ← TABS         │
│                                                         │
│ 📁 Înregistrările mele (5):  [🔽 Filtrează: Toate aparatele]│
│ ┌─────────────────────────────────────────────────────┐ │
│ │ 📅 7 oct | Aparat: #3539 | ⏱️ 8h23m | 💚 94.2%     │ │
│ │ [👁️ Vezi Grafic Complet] [📥 Download PNG] [📥 CSV] [📄 Raport]│ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ 📅 14 oct | Aparat: #3539 | ⏱️ 7h12m | 💚 93.8%    │ │
│ │ [👁️ Vezi Grafic Complet] [📥 Download PNG] [📥 CSV] [📄 Raport]│ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ 📅 21 oct | Aparat: #3541 ← DIFERIT! | ⏱️ 7h45m | 💚 91.5%│ │
│ │ [👁️ Vezi Grafic Complet] [📥 Download PNG] [📥 CSV] [📄 Raport]│ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ ... (2 mai multe, aparate #3541 și #3542) ...         │
│                                                         │
│ ℹ️ Aparate folosite: #3539 (2 înreg), #3541 (2 înreg), #3542 (1 înreg)│
│                                                         │
│ ℹ️ Pentru adăugare înregistrări noi, contactați medicul│
└─────────────────────────────────────────────────────────┘
```

**Click "Download PNG" → Dialog Selector Interval:**
```
┌─────────────────────────────────────────────────────────┐
│ 📥 DOWNLOAD GRAFIC - 7 octombrie 2025                   │
│                                                         │
│ Înregistrare: 23:04 - 07:27 (8h 23min total)           │
│                                                         │
│ Selectați interval pentru download:                    │
│                                                         │
│ ⚪ Grafic complet (8h 23min)                            │
│                                                         │
│ ⚫ Ferestre de timp:                                    │
│   └─ Dimensiune fereastră:                             │
│      [30 min ▼] (opțiuni: 15, 30, 60, 120, 180 min)   │
│                                                         │
│   └─ Interval personalizat:                            │
│      De la: [23:04] până la: [07:27]                   │
│                                                         │
│ Rezultat:                                              │
│ └─ Va genera: 17 imagini PNG (ferestre de 30 min)     │
│    sau 1 imagine PNG (interval personalizat)          │
│                                                         │
│ Format: PNG 1280x720 cu watermark clinică             │
│                                                         │
│ [📥 Download] [❌ Anulează]                             │
└─────────────────────────────────────────────────────────┘
```

**După click "Download":**
```
┌─────────────────────────────────────────────────────────┐
│ ⏳ Se generează graficele...                            │
│                                                         │
│ [████████████████████░░░] 85% (15/17 imagini)          │
│                                                         │
│ Proces:                                                │
│ ✅ grafic_7oct_2304-2334.png                            │
│ ✅ grafic_7oct_2334-0004.png                            │
│ ... (13 mai multe)                                     │
│ ⏳ grafic_7oct_0634-0704.png (în curs...)              │
│ ⏹️ grafic_7oct_0704-0727.png (în așteptare)            │
│                                                         │
│ ⚠️ Nu închideți această fereastră până la finalizare   │
└─────────────────────────────────────────────────────────┘

↓ După finalizare ↓

┌─────────────────────────────────────────────────────────┐
│ ✅ Download complet!                                    │
│                                                         │
│ 17 imagini generate și descărcate:                    │
│                                                         │
│ 📦 Arhivă ZIP: grafice_7oct_23h04-07h27.zip (8.5 MB)   │
│                                                         │
│ Conținut:                                              │
│ • grafic_7oct_2304-2334.png (500 KB)                   │
│ • grafic_7oct_2334-0004.png (500 KB)                   │
│ • ... (15 mai multe)                                   │
│ • grafic_7oct_0704-0727.png (350 KB) [ultim, parțial] │
│                                                         │
│ ℹ️ Toate imaginile includ watermark clinică            │
│                                                         │
│ [📁 Deschide Folder] [🔄 Download Alt Interval]        │
└─────────────────────────────────────────────────────────┘
```

✅ **Tab 2: "Explorează CSV"** (upload temporar, plotare, NU salvează în DB)
```
┌─────────────────────────────────────────────────────────┐
│ 📊 Monitorizare Saturație Oxigen                        │
│                                                         │
│ [Înregistrările Mele] [Explorează CSV]  ← Tab activ    │
│                                                         │
│ 📤 Încarcă CSV pentru Explorare                         │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ ╔═══════════════════════════════════════════════╗   │ │
│ │ ║   📁  Trageți fișierul CSV aici               ║   │ │
│ │ ║      sau click pentru a selecta               ║   │ │
│ │ ║                                                ║   │ │
│ │ ║   Graficul va fi generat instant               ║   │ │
│ │ ║   (fără salvare în baza de date)              ║   │ │
│ │ ╚═══════════════════════════════════════════════╝   │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ ℹ️ Folosiți acest tab pentru:                          │
│ • Explorare CSV-uri vechi descărcate                   │
│ • Testare fișiere înainte de a le trimite medicului    │
│ • Re-plotare cu zoom/setări diferite                   │
│                                                         │
│ ⚠️ Fișierul NU va fi salvat permanent!                 │
│    Pentru stocare, trimiteți CSV-ul către medic.       │
└─────────────────────────────────────────────────────────┘
```

**După upload CSV în Tab 2:**
```
┌─────────────────────────────────────────────────────────┐
│ 📊 Explorare CSV - O2 3539_20251007.csv                 │
│                                                         │
│ [Înregistrările Mele] [Explorează CSV]                 │
│                                                         │
│ ✅ Fișier procesat: 28,800 măsurători (8h)             │
│                                                         │
│ ┌─────────────────────────────────────────────────────┐ │
│ │                                                     │ │
│ │  [GRAFIC PLOTLY INTERACTIV]                         │ │
│ │                                                     │ │
│ │  100% ┌───────────────────────────────────┐         │ │
│ │   95% │  ╱╲    ╱╲   ╱╲   ╱╲              │         │ │
│ │   90% │ ╱  ╲  ╱  ╲ ╱  ╲ ╱  ╲  ╱╲         │         │ │
│ │   85% │╱    ╲╱    ╲    ╲    ╲╱  ╲        │         │ │
│ │       └───────────────────────────────────┘         │ │
│ │       23:00  01:00  03:00  05:00  07:00            │ │
│ │                                                     │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ Statistici rapide:                                     │
│ • SpO2 mediu: 94.2%                                    │
│ • SpO2 minim: 87%                                      │
│ • SpO2 maxim: 99%                                      │
│                                                         │
│ [📥 Download PNG (cu selector interval)] [🔄 Încarcă Alt CSV]│
│                                                         │
│ ⚠️ Graficul este temporar (nu salvat în cont)          │
│ ℹ️ Imaginile downloadate vor include sigla clinicii    │
└─────────────────────────────────────────────────────────┘
```

**Click "Download PNG" (Tab Explorare) → Același selector interval:**
```
┌─────────────────────────────────────────────────────────┐
│ 📥 DOWNLOAD GRAFIC EXPLORARE                            │
│                                                         │
│ CSV: O2 3539_20251007.csv                              │
│ Interval: 23:04 - 07:27 (8h 23min)                     │
│                                                         │
│ Selectați interval:                                    │
│ ⚪ Grafic complet                                       │
│ ⚫ Ferestre: [30 min ▼]                                 │
│ ⚪ Personalizat: [23:04] - [07:27]                      │
│                                                         │
│ [📥 Download] [❌ Anulează]                             │
└─────────────────────────────────────────────────────────┘
```

**Click "Vezi Raport" → Raport parseat afișat frumos:**
```html
<div class="report-container">
  <h2>Raport Pulsoximetrie - 7 octombrie 2025</h2>
  <p><strong>Aparat:</strong> Checkme O2 #3539</p>
  <p><strong>Durată:</strong> 8h 23min (23:04 - 07:27)</p>
  
  <h3>Statistici</h3>
  <table>
    <tr><td>SpO2 mediu</td><td>94.2%</td></tr>
    <tr><td>SpO2 minim</td><td>87%</td></tr>
    <tr><td>SpO2 maxim</td><td>99%</td></tr>
    <tr><td>Puls mediu</td><td>72 bpm</td></tr>
  </table>
  
  <h3>Evenimente Detectate</h3>
  <p>⚠️ <strong>23 desaturări</strong> (SpO2 < 90%)</p>
  <p>Durată totală: 45 minute</p>
  <p>Cea mai lungă: 3min 15s</p>
  
  <h3>Interpretare Automată</h3>
  <div class="alert alert-warning">
    Desaturări moderate detectate. 
    Recomandare: Consultație pneumologie.
  </div>
</div>
```

---

### 6. **Interfață Admin (ACTUALIZATĂ)**

#### A. **Upload Bulk (Feature Principal)**

```
┌─────────────────────────────────────────────────────────┐
│ 📤 UPLOAD BULK ÎNREGISTRĂRI                             │
│                                                         │
│ Selectați folderul cu fișiere CSV + PDF:               │
│ ╔═══════════════════════════════════════════════════╗   │
│ ║                                                   ║   │
║ ║   📁 Trageți folderul aici                        ║   │
│ ║      sau click pentru a selecta                   ║   │
│ ║                                                   ║   │
│ ╚═══════════════════════════════════════════════════╝   │
│                                                         │
│ Fișiere detectate (14):                                │
│ ✓ Checkme O2 3539_20251007230437.csv                   │
│ ✓ Checkme O2 3539_20251007_Report.pdf                  │
│ ✓ Checkme O2 3539_20251014203224.csv                   │
│ ✓ Checkme O2 3539_20251014_Report.pdf                  │
│ ✓ Checkme O2 3541_20251007202217.csv                   │
│ ✓ Checkme O2 3541_20251007_Report.pdf                  │
│ ... (8 mai multe)                                       │
│                                                         │
│ [🚀 Procesează și Generează Link-uri]                   │
└─────────────────────────────────────────────────────────┘

↓ După procesare ↓

┌─────────────────────────────────────────────────────────┐
│ ✅ Procesare completă!                                  │
│                                                         │
│ 📊 Rezultate:                                           │
│ - 7 înregistrări procesate                             │
│ - 3 link-uri generate (2 noi, 1 existent actualizat)  │
│ - 7 grafice create                                     │
│ - 7 rapoarte parsate                                   │
│                                                         │
│ 🔗 Link-uri generate:                                   │
│                                                         │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ 🆕 LINK NOU: https://app.com/p/a8f9d2b1             │ │
│ │    Aparat: Checkme O2 #3539                         │ │
│ │    Înregistrări: 3 (7, 14, 15 oct)                  │ │
│ │    [📋 Copiază] [📧 Email Pacient] [👁️ Previzualizare]│ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ 🆕 LINK NOU: https://app.com/p/x7y8z9w0             │ │
│ │    Aparat: Checkme O2 #3541                         │ │
│ │    Înregistrări: 2 (20, 21 oct)                     │ │
│ │    [📋 Copiază] [📧 Email Pacient] [👁️ Previzualizare]│ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ 🔄 ACTUALIZAT: https://app.com/p/b2c3d4e5           │ │
│ │    Aparat: Checkme O2 #3540                         │ │
│ │    Înregistrări: 5 (2 noi adăugate)                │ │
│ │    [📋 Copiază] [📧 Email Pacient] [👁️ Previzualizare]│ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ ⚠️ ATENȚIE: Verificați dacă link-urile aparțin         │
│    aceluiași pacient. Folosiți "Contopește Link-uri"   │
│    pentru a le merge.                                   │
└─────────────────────────────────────────────────────────┘
```

#### B. **Setări Clinică (Watermark Configuration)**

```
┌─────────────────────────────────────────────────────────┐
│ ⚙️ SETĂRI CLINICĂ                                       │
│                                                         │
│ Informațiile de mai jos vor apărea pe toate graficele: │
│                                                         │
│ Nume clinică:                                          │
│ [Clinica Pneumologie Dr. Popescu__________________]    │
│                                                         │
│ Număr telefon:                                         │
│ [+40 21 123 4567______________________________]        │
│                                                         │
│ Adresă:                                                │
│ [Str. Sănătății nr. 10, București____________]         │
│                                                         │
│ Logo clinică (PNG, max 1MB):                           │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ [Logo actual: logo_clinica.png]                     │ │
│ │ [📤 Schimbă Logo]                                   │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ Preview watermark:                                     │
│ ┌─────────────────────────────────────────────────────┐ │
│ │                                                     │ │
│ │  [GRAFIC EXEMPLU]                                   │ │
│ │                                                     │ │
│ │  ┌─────────────────────────────────────────────┐   │ │
│ │  │ 🏥 Logo                                       │   │ │
│ │  │ Clinica Pneumologie Dr. Popescu              │   │ │
│ │  │ ☎ +40 21 123 4567                            │   │ │
│ │  │ 📍 Str. Sănătății nr. 10, București          │   │ │
│ │  └─────────────────────────────────────────────┘   │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ [💾 Salvează Setări]                                    │
└─────────────────────────────────────────────────────────┘
```

#### C. **Dashboard cu Feature "Merge"**

```
┌─────────────────────────────────────────────────────────┐
│ 👥 LINK-URI PACIENȚI                   [🔍 Căutare...] │
│                                                         │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ ☐ Link: ...a8f9d2b1 | #3539 | 3 înreg | 7-15 oct   │ │
│ │    [👁️ Vezi] [📤 +Upload] [🗑️ Șterge]                │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ ☐ Link: ...x7y8z9w0 | #3541 | 2 înreg | 20-21 oct  │ │
│ │    [👁️ Vezi] [📤 +Upload] [🗑️ Șterge]                │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ ⬇️ Selectați 2+ link-uri pentru a le contopi ⬇️         │
│                                                         │
│ [🔀 Contopește Link-urile Selectate]                    │
└─────────────────────────────────────────────────────────┘
```

**După selectare 2 link-uri + click "Contopește":**
```
┌─────────────────────────────────────────────────────────┐
│ 🔀 CONTOPIRE LINK-URI                                   │
│                                                         │
│ Link Sursă (va fi invalidat):                          │
│ 🔗 ...x7y8z9w0 | Aparat #3541 | 2 înregistrări         │
│                                                         │
│ Link Țintă (va primi toate înregistrările):            │
│ 🔗 ...a8f9d2b1 | Aparat #3539 | 3 înregistrări         │
│                                                         │
│ Rezultat după contopire:                               │
│ 🔗 ...a8f9d2b1 | Aparate #3539 + #3541 | 5 înreg      │
│                                                         │
│ ⚠️ Link ...x7y8z9w0 va redirecționa automat la ...a8f9d2b1│
│                                                         │
│ [✅ Confirmare] [❌ Anulează]                            │
└─────────────────────────────────────────────────────────┘
```

---

## 📊 SELECTOR INTERVAL PENTRU DOWNLOAD GRAFICE

⚡ **IMPORTANT:** Această funcționalitate **EXISTĂ DEJA** în aplicația locală!

**Cod Existent:** `batch_processor.py` (linia 178-287) - funcția `run_batch_job()`
- ✅ Împarte înregistrările în ferestre de X minute (configurabil)
- ✅ Generează grafice pentru fiecare fereastră
- ✅ Nume intuitive pentru imagini (`Aparat1442_00h25m-00h55m.jpg`)
- ✅ Nume intuitive pentru foldere (`02mai2025_00h25-06h37_Aparat1442`)
- ✅ Detectare automată test peste miezul nopții

**Ce Se Schimbă pentru Cloud:**
- ❌ NU mai salvăm pe disk → ✅ Returnăm figuri Plotly în memorie
- ❌ NU mai creăm foldere → ✅ Creăm ZIP în memorie (io.BytesIO)
- ✅ ADĂUGĂM watermark pe fiecare imagine
- ✅ PĂSTRĂM logica de feliere și denumire (IDENTICĂ!)

---

### De Ce Este Important?

**Problema:** O înregistrare de 8h (28,800 puncte) generează un grafic foarte dens:
- ❌ Detalii greu de observat când vizualizezi tot graficul dintr-o dată
- ❌ Fișier PNG mare (2-3 MB)
- ❌ Greu de printat (informații comprimate)
- ❌ Dificil de analizat periodic (ex: "Cum a fost între 02:00-04:00?")

**Soluția:** Download în ferestre de timp:
- ✅ Detalii clare pe fiecare perioadă
- ✅ Fișiere PNG mai mici (500 KB/fereastră)
- ✅ Ușor de printat (o pagină = o fereastră de 30 min)
- ✅ Analiză focusată pe perioade problematice

### Use Cases Reale:

#### 1. **Medic: Analiză Detaliată**
```
Scenariu: Pacient raportează "Am simțit că nu pot respira bine între 3-5 dimineața"

Workflow:
1. Medic vizualizează grafic complet → Identifică zona 03:00-05:00
2. Download interval personalizat: 03:00 - 05:00 (2h)
3. Grafic detaliat cu 7,200 puncte (doar perioada relevantă)
4. Observă: 15 desaturări în 2h → Diagnostic: Apnee severă
5. Include graficul în raport medical (PDF cu watermark clinică)
```

#### 2. **Pacient: Partajare cu Alt Medic**
```
Scenariu: Pacient vrea second opinion de la alt pneumolog

Workflow:
1. Pacient: Download ferestre 30 min → ZIP cu 17 imagini
2. Selectează cele mai relevante (ex: 5 imagini cu desaturări)
3. Trimite email către al doilea medic
4. Toate imaginile au watermark cu contact clinică inițială
5. Al doilea medic poate contacta clinica pentru date complete
```

#### 3. **Documentație Medicală: Printare**
```
Scenariu: Pacient trebuie să printeze raport pentru asigurare

Workflow:
1. Download ferestre 60 min → 8 imagini PNG
2. Fiecare imagine se printează clar pe o pagină A4
3. Watermark vizibil pe fiecare pagină (contact clinică)
4. Raport complet: 8 pagini cu grafice + raport text parseat din PDF
5. Asigurare acceptă documentația (semnat și stampilat de clinică)
```

#### 4. **Monitorizare Longitudinală: Comparație Zile**
```
Scenariu: Pacient vrea să compare evoluția pe 7 nopți

Workflow:
1. Descarcă interval 02:00-04:00 pentru toate cele 7 înregistrări
2. Observă: Prima noapte - multe desaturări, noapte 7 - îmbunătățire
3. Partajează cu medicul: "Tratamentul funcționează!"
4. Medic confirmă: SaO2 mediu crescut de la 89% → 95%
```

### Opțiuni Selector Interval:

| Opțiune | Use Case | Rezultat Download |
|---------|----------|-------------------|
| **Grafic Complet** | Overview general, prezentări | 1 PNG (2-3 MB) |
| **Ferestre 15 min** | Analiză foarte detaliată, identificare evenimente | ZIP 30+ imagini |
| **Ferestre 30 min** | Echilibru detaliu/cantitate (RECOMANDAT) | ZIP 15-20 imagini |
| **Ferestre 60 min** | Analiză pe ore, trend-uri | ZIP 8-10 imagini |
| **Ferestre 120 min** | Overview pe perioade lungi | ZIP 4-5 imagini |
| **Ferestre 180 min** | Comparație perioade (începutul/mijlocul/sfârșitul nopții) | ZIP 3-4 imagini |
| **Interval Personalizat** | Analiză zone problematice identificate | 1 PNG (variabil) |

### Exemple Concrete Dimensiuni:

```
Înregistrare: 8h 23min (23:04 - 07:27)

Ferestre 30 min:
├─ 17 imagini PNG
├─ Total ZIP: 8.5 MB
├─ Per imagine: ~500 KB
└─ Nume: grafice_2025-10-07_ferestre_30min.zip

Conținut ZIP:
├─ grafic_2304-2334.png
├─ grafic_2334-0004.png
├─ grafic_0004-0034.png
├─ ... (14 mai multe)
└─ grafic_0704-0727.png (ultima, 23 min)
```

---

## 🎨 EXEMPLU WATERMARK PE GRAFIC

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     GRAFIC PULSOXIMETRIE                                │
│                     Data: 7 octombrie 2025                              │
│                                                                         │
│  100% ┌──────────────────────────────────────────────────────────────┐ │
│   95% │    ╱╲      ╱╲    ╱╲   ╱╲                                     │ │
│   90% │  ╱    ╲  ╱    ╲╱    ╲╱    ╲   ╱╲                             │ │
│   85% │╱      ╲╱                  ╲╱    ╲                            │ │
│   80% │                                    ╲                          │ │
│   75% └──────────────────────────────────────────────────────────────┘ │
│       23:00    01:00    03:00    05:00    07:00                        │
│                                                                         │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │  🏥 [Logo Clinică]                                             │    │
│  │  Clinica Pneumologie Dr. Popescu                              │    │
│  │  ☎ +40 21 123 4567                                            │    │
│  │  📍 Str. Sănătății nr. 10, București                          │    │
│  └────────────────────────────────────────────────────────────────┘    │
│        ↑ WATERMARK AUTOMAT (footer, semi-transparent)                  │
└─────────────────────────────────────────────────────────────────────────┘

CARACTERISTICI WATERMARK:
├─ Poziție: Footer (jos stânga)
├─ Logo: Max 60px înălțime (păstrare aspect ratio)
├─ Font: Arial, 2% din înălțimea imaginii
├─ Transparență: 80-90% (vizibil dar non-intruziv)
├─ Culoare text: Negru (RGB 0,0,0)
├─ Format ieșire: PNG (quality 95%)
└─ Aplicare: On-the-fly la download (nu se stochează cu watermark)

USE CASES:
• Pacient downloadează pentru records personale
• Medic downloadează pentru prezentări/rapoarte
• Imagine partajată cu alți medici (contact vizibil)
• Protecție IP (clinica e vizibilă pe toate graficele)
```

---

## 🗄️ SCHEMA DATABASE ACTUALIZATĂ

### Modificări Necesare:

#### 1. **Tabel `admins`** (Minor additions pentru watermark)

```sql
CREATE TABLE admins (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    
    -- ✅ ADĂUGAT: Informații clinică pentru watermark
    clinic_name VARCHAR(255),           -- Ex: "Clinica Pneumologie Dr. Popescu"
    clinic_phone VARCHAR(50),           -- Ex: "+40 21 123 4567"
    clinic_address TEXT,                -- Ex: "Str. Sănătății nr. 10, București"
    clinic_logo_file_id INTEGER REFERENCES files(id),  -- Logo pentru watermark
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);
```

#### 2. **Tabel `patient_links`** (Major changes - CU PERSISTENȚĂ!)

```sql
CREATE TABLE patient_links (
    id SERIAL PRIMARY KEY,
    token VARCHAR(64) UNIQUE NOT NULL,
    
    -- ❌ NU există device_name! Link = PACIENT, nu aparat!
    -- ✅ device_name este în recordings (un pacient poate folosi aparate diferite)
    
    notes TEXT,  -- Note medic despre pacient (optional)
    created_by INTEGER REFERENCES admins(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    
    -- 🔒 PERSISTENȚĂ: NU există expires_at!
    -- Link-urile rămân active PERMANENT (doar admin le poate dezactiva manual)
    
    -- ✅ ADĂUGAT pentru feature "Merge"
    merged_into INTEGER REFERENCES patient_links(id),
    merged_at TIMESTAMP,
    
    INDEX idx_token (token),
    INDEX idx_created_by (created_by, is_active)
);

-- 🔒 NOTE IMPORTANTE:
-- 1. Link = PACIENT (identificat prin token unic)
-- 2. Un pacient poate folosi aparate diferite → device_name în recordings
-- 3. Același aparat poate fi folosit de pacienți diferiți → link-uri diferite
-- 4. Fără expires_at → link-urile NU expiră automat
-- 5. Medicul controlează ce date merg la ce link (selectează link la upload)
```

**🔒 Comparație: Link-uri Temporare vs. Persistente**

| Aspect | Link Temporare ❌ | Link Persistente ✅ (IMPLEMENTAT) |
|--------|-------------------|-----------------------------------|
| Durată validitate | 30-90 zile | NELIMITATĂ (permanent) |
| Câmp `expires_at` | EXISTS | ❌ NU EXISTĂ |
| Pacient revine după 6 luni | ⚠️ "Link expirat" | ✅ "Vezi 12 înregistrări" |
| Link = aparat? | Uneori da | ❌ NU! Link = PACIENT |
| Pacient folosește aparate diferite | ⚠️ Link-uri multiple | ✅ UN link (toate aparatele) |
| Același aparat, pacienți diferiți | OK | ✅ OK (link-uri separate) |
| Medic trimite link | La fiecare upload | ✅ O SINGURĂ DATĂ |
| Partajare cu alți medici | ⚠️ Risc expirare | ✅ Sigur (permanent) |
| Bookmark în browser | ⚠️ Devine invalid | ✅ Funcționează mereu |
| Documentație asigurare | ⚠️ Link mort în documentație | ✅ Link valid în documentație |

#### 2. **Tabel `recordings`** (Major changes)

```sql
CREATE TABLE recordings (
    id SERIAL PRIMARY KEY,
    patient_link_id INTEGER REFERENCES patient_links(id) ON DELETE CASCADE,
    
    -- ✅ ADĂUGAT: Device name la nivel de recording (nu link!)
    device_name VARCHAR(255) NOT NULL,  -- Ex: "Checkme O2 #3539"
    
    recording_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME,
    duration_minutes INTEGER,
    
    -- Statistici calculate (din CSV sau PDF)
    avg_spo2 DECIMAL(5,2),
    min_spo2 INTEGER,
    max_spo2 INTEGER,
    avg_pulse DECIMAL(5,2),
    min_pulse INTEGER,
    max_pulse INTEGER,
    
    -- ✅ ADĂUGAT: Raport parseat din PDF (stocat ca JSON)
    report_data JSONB,  -- PostgreSQL JSONB pentru queries rapide
    /*
    Exemplu report_data:
    {
      "events": {
        "desaturations_count": 23,
        "desaturations_total_duration": 45,
        "longest_desaturation": 195
      },
      "auto_interpretation": "Desaturări moderate...",
      "recommendations": ["Consultație pneumologie"]
    }
    */
    
    -- Fișiere asociate
    csv_file_id INTEGER REFERENCES files(id),
    plot_file_id INTEGER REFERENCES files(id),
    -- ❌ ȘTERS: pdf_file_id (nu mai stocăm PDF, doar parsăm)
    
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    uploaded_by VARCHAR(10) DEFAULT 'admin',
    
    INDEX idx_patient_link (patient_link_id),
    INDEX idx_device_name (device_name),
    INDEX idx_recording_date (recording_date)
);
```

#### 3. **Query Exemple Actualizate**

```sql
-- Găsește toate aparatele folosite de un pacient (via link)
SELECT DISTINCT device_name, COUNT(*) as recordings_count
FROM recordings
WHERE patient_link_id = (
    SELECT id FROM patient_links WHERE token = 'a8f9d2b1'
)
GROUP BY device_name;

-- Rezultat:
-- device_name           | recordings_count
-- Checkme O2 #3539      | 3
-- Checkme O2 #3541      | 2


-- Găsește toate înregistrările pentru un link (inclusiv merged)
WITH RECURSIVE merged_links AS (
    -- Link-ul curent
    SELECT id, token, merged_into
    FROM patient_links
    WHERE token = 'x7y8z9w0'
    
    UNION
    
    -- Dacă e merged, ia target-ul
    SELECT pl.id, pl.token, pl.merged_into
    FROM patient_links pl
    JOIN merged_links ml ON pl.id = ml.merged_into
)
SELECT r.*, f.storage_path as csv_path
FROM recordings r
JOIN files f ON r.csv_file_id = f.id
WHERE r.patient_link_id IN (SELECT id FROM merged_links)
ORDER BY r.recording_date DESC;
```

---

## 📊 FLOW-URI ACTUALIZATE

### Flow 1: Admin Upload Bulk

```
Admin (Cabinet Medical)
         │
         │ 1. Selectează folder cu 14 fișiere
         │    (7 CSV + 7 PDF)
         ▼
┌──────────────────────────────────────┐
│  Frontend: Upload Multiple Files    │
│  ┌────────────────────────────────┐  │
│  │ Processing...                  │  │
│  │ [████████████░░░░] 85%         │  │
│  │ 12/14 files uploaded           │  │
│  └────────────────────────────────┘  │
└──────────────┬───────────────────────┘
               │
               │ 2. POST /api/admin/bulk-upload
               │    FormData: files[] (14 files)
               ▼
┌──────────────────────────────────────────────────────┐
│  Backend: Bulk Processing Pipeline                  │
│                                                      │
│  Step 1: Parse filenames & group                    │
│  ├─ Checkme O2 3539_20251007230437.csv              │
│  ├─ Checkme O2 3539_20251007_Report.pdf             │
│  │  → Group: device=#3539, date=2025-10-07          │
│  │                                                   │
│  ├─ Checkme O2 3539_20251014203224.csv              │
│  ├─ Checkme O2 3539_20251014_Report.pdf             │
│  │  → Group: device=#3539, date=2025-10-14          │
│  │                                                   │
│  ├─ Checkme O2 3541_20251007202217.csv              │
│  ├─ Checkme O2 3541_20251007_Report.pdf             │
│  │  → Group: device=#3541, date=2025-10-07          │
│  │                                                   │
│  └─ ... (4 more groups)                             │
│                                                      │
│  Step 2: Check existing links                       │
│  ├─ Device #3539: No existing link → CREATE NEW     │
│  ├─ Device #3541: No existing link → CREATE NEW     │
│  └─ Device #3540: Existing link found → UPDATE      │
│                                                      │
│  Step 3: Process each group                         │
│  For each (device, date) pair:                      │
│    3.1. Upload CSV to R2                            │
│    3.2. Parse CSV → Generate Plotly graph → PNG     │
│    3.3. Parse PDF → Extract stats → Store JSON in DB│
│    3.4. Create Recording entry in DB                │
│                                                      │
│  Step 4: Generate/Update Links                      │
│  ├─ Link 1 (NEW): token=a8f9d2b1, device=#3539      │
│  ├─ Link 2 (NEW): token=x7y8z9w0, device=#3541      │
│  └─ Link 3 (UPDATE): token=b2c3d4e5, device=#3540   │
│                                                      │
│  ⏱️ Total time: ~20-30 seconds for 14 files         │
└──────────────┬───────────────────────────────────────┘
               │
               │ 3. Response
               ▼
┌──────────────────────────────────────┐
│  Success Summary                     │
│  ┌────────────────────────────────┐  │
│  │ ✅ Upload complet!              │  │
│  │                                │  │
│  │ 📊 Rezultate:                  │  │
│  │ - 7 înregistrări procesate     │  │
│  │ - 3 link-uri (2 noi, 1 update) │  │
│  │ - 7 grafice generate           │  │
│  │ - 7 rapoarte parsate           │  │
│  │                                │  │
│  │ 🔗 Link-uri generate:          │  │
│  │ - a8f9d2b1 (#3539, 3 înreg)    │  │
│  │ - x7y8z9w0 (#3541, 2 înreg)    │  │
│  │ - b2c3d4e5 (#3540, 5 înreg)    │  │
│  │                                │  │
│  │ [Copiază Toate Link-urile]     │  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘
```

### Flow 2: Admin Merge Links

```
Admin Dashboard
         │
         │ 1. Selectează checkbox link 1 + link 2
         │    ☑️ ...a8f9d2b1 (device #3539, 3 recordings)
         │    ☑️ ...x7y8z9w0 (device #3541, 2 recordings)
         ▼
┌──────────────────────────────────────┐
│  Click "Contopește Link-uri"        │
└──────────────┬───────────────────────┘
               │
               │ 2. Confirmation Dialog
               ▼
┌──────────────────────────────────────┐
│  Confirmare Contopire               │
│  ┌────────────────────────────────┐  │
│  │ Sigur vrei să contopești?      │  │
│  │                                │  │
│  │ Link sursă (va fi invalid):    │  │
│  │ ...x7y8z9w0                    │  │
│  │                                │  │
│  │ Link țintă (va primi tot):     │  │
│  │ ...a8f9d2b1                    │  │
│  │                                │  │
│  │ [Confirmare] [Anulează]        │  │
│  └────────────────────────────────┘  │
└──────────────┬───────────────────────┘
               │
               │ 3. POST /api/admin/merge-links
               │    {source: x7y8z9w0, target: a8f9d2b1}
               ▼
┌──────────────────────────────────────────────────────┐
│  Backend: Merge Operation                           │
│                                                      │
│  UPDATE recordings                                   │
│  SET patient_link_id = (SELECT id WHERE token='a8f9')│
│  WHERE patient_link_id = (SELECT id WHERE token='x7y')│
│                                                      │
│  UPDATE patient_links                                │
│  SET is_active = FALSE,                              │
│      merged_into = (SELECT id WHERE token='a8f9'),   │
│      merged_at = NOW()                               │
│  WHERE token = 'x7y8z9w0';                           │
│                                                      │
│  Result: 2 recordings moved                          │
└──────────────┬───────────────────────────────────────┘
               │
               │ 4. Response
               ▼
┌──────────────────────────────────────┐
│  Success Message                     │
│  ┌────────────────────────────────┐  │
│  │ ✅ Link-uri contopite!          │  │
│  │                                │  │
│  │ Link ...a8f9d2b1 conține acum:│  │
│  │ - Aparat #3539: 3 înregistrări │  │
│  │ - Aparat #3541: 2 înregistrări │  │
│  │ TOTAL: 5 înregistrări          │  │
│  │                                │  │
│  │ Link ...x7y8z9w0 a fost        │  │
│  │ dezactivat (redirect automat)  │  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘
```

### Flow 3: Pacient Upload Temporar CSV (Tab "Explorează CSV")

```
Pacient Maria (are deja 5 înregistrări stocate)
         │
         │ 1. Download CSV vechi din Tab 1
         │    → "Checkme O2 3539_20251007.csv" (1.5MB)
         ▼
Local Computer
         │
         │ 2. Switch la Tab 2: "Explorează CSV"
         ▼
┌──────────────────────────────────────┐
│  Tab 2: Explorează CSV              │
│  ┌────────────────────────────────┐  │
│  │ [📁 Drag & drop CSV aici]      │  │
│  └────────────────────────────────┘  │
└──────────────┬───────────────────────┘
               │
               │ 3. Drag & drop CSV vechi
               │    POST /api/patient/temp-plot
               │    {file: <1.5MB CSV>}
               ▼
┌──────────────────────────────────────────────────────┐
│  Backend: Temporary Processing (IN-MEMORY)          │
│                                                      │
│  ❌ NU upload la R2                                 │
│  ❌ NU creare Recording în DB                       │
│  ❌ NU salvare permanentă                           │
│                                                      │
│  ✅ Parse CSV (pandas, in-memory)                   │
│  ✅ Generate Plotly figure (JSON)                   │
│  ✅ Calculate quick stats                           │
│                                                      │
│  Return: {                                          │
│    figure: <plotly_json>,                           │
│    stats: {avg_spo2: 94.2, ...},                    │
│    warning: "Temporar, nu salvat"                   │
│  }                                                   │
│                                                      │
│  ⏱️ Processing: ~1-2 secunde                        │
└──────────────┬───────────────────────────────────────┘
               │
               │ 4. Response (JSON)
               ▼
┌──────────────────────────────────────┐
│  Frontend: Render Plotly Graph      │
│  ┌────────────────────────────────┐  │
│  │  [GRAFIC INTERACTIV]           │  │
│  │                                │  │
│  │  100% ┌─────────────────┐      │  │
│  │   95% │  /\   /\   /\   │      │  │
│  │   90% │ /  \ /  \ /  \  │      │  │
│  │   85% │/    V    V    \ │      │  │
│  │       └─────────────────┘      │  │
│  │                                │  │
│  │  Stats:                        │  │
│  │  • SpO2 mediu: 94.2%          │  │
│  │  • Minim: 87%, Maxim: 99%     │  │
│  │                                │  │
│  │  ⚠️ Grafic temporar            │  │
│  │  (nu salvat în cont)           │  │
│  │                                │  │
│  │  [🔄 Încarcă Alt CSV]          │  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘
         │
         │ 5. Pacient poate:
         │    - Explora graficul (zoom, pan, hover)
         │    - Încărca alt CSV (repeat flow)
         │    - Switch înapoi la Tab 1 (înregistrări stocate)
         │
         │ 6. Când refresh page sau schimbă tab:
         │    → Graficul dispare (nu e salvat!)
         ▼
Tab 1: Înregistrările Mele (date permanente)
```

**Diferența cheie:**
```
Upload MEDIC (Tab Admin):
  └─ Salvare permanentă → DB + R2 → Apare în Tab 1 pacient

Upload PACIENT (Tab 2):
  └─ Procesare temporară → JSON response → Afișare client-side
  └─ Nu salvează NIMIC → Dispare la refresh
```

### Flow 4: Pacient Accesează Link Merged

```
Pacient Maria
         │
         │ 1. Click link vechi (merged):
         │    https://app.com/p/x7y8z9w0
         ▼
┌──────────────────────────────────────┐
│  Backend: Check Link Status         │
│                                      │
│  link = PatientLink.get('x7y8z9w0') │
│  if link.merged_into:                │
│    redirect_to(link.merged_into.token)│
└──────────────┬───────────────────────┘
               │
               │ 2. Redirect 301 (permanent)
               │    → https://app.com/p/a8f9d2b1
               ▼
┌──────────────────────────────────────┐
│  Pagină Pacient (Link Nou)          │
│  ┌────────────────────────────────┐  │
│  │ 📊 Monitorizare Oxigen         │  │
│  │                                │  │
│  │ ℹ️ Link actualizat automat     │  │
│  │                                │  │
│  │ 📁 Înregistrările mele (5):    │  │
│  │                                │  │
│  │ 7 oct | #3539 | 8h23m | 94.2% │  │
│  │ 14 oct | #3539 | 7h12m | 93.8%│  │
│  │ 15 oct | #3539 | 8h01m | 95.2%│  │
│  │ 20 oct | #3541 | 7h45m | 91.5%│  │
│  │ 21 oct | #3541 | 8h30m | 92.1%│  │
│  │        ↑ Aparate diferite! ↑   │  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘
```

---

## 🛠️ IMPLEMENTARE: Cod Actualizat

### 1. **Bulk Upload Handler**

```python
# admin_routes.py

@app.route('/api/admin/bulk-upload', methods=['POST'])
@admin_required
def bulk_upload():
    """
    Upload bulk: acceptă multiple CSV + PDF
    Generează automat link-uri per aparat
    """
    files = request.files.getlist('files[]')
    
    if not files:
        return {"error": "No files uploaded"}, 400
    
    # Grupare fișiere per (device, date)
    groups = {}
    
    for file in files:
        try:
            # Parse filename: "Checkme O2 3539_20251007230437.csv"
            match = re.match(r'(.+?)_(\d{8})', file.filename)
            if not match:
                continue
            
            device_name = match.group(1).strip()  # "Checkme O2 3539"
            date_str = match.group(2)  # "20251007"
            date = datetime.strptime(date_str, '%Y%m%d').date()
            
            key = (device_name, date)
            if key not in groups:
                groups[key] = {'csv': None, 'pdf': None}
            
            if file.filename.endswith('.csv'):
                groups[key]['csv'] = file
            elif file.filename.endswith('.pdf'):
                groups[key]['pdf'] = file
                
        except Exception as e:
            logger.error(f"Failed to parse {file.filename}: {e}")
            continue
    
    # Procesare fiecare grup
    results = {
        'processed': 0,
        'links_created': [],
        'links_updated': [],
        'errors': []
    }
    
    for (device_name, date), files_dict in groups.items():
        try:
            # Check existing link pentru acest aparat
            link = PatientLink.query.filter_by(device_name=device_name).first()
            
            if not link:
                # Create new link
                token = secrets.token_urlsafe(16)
                link = PatientLink(
                    token=token,
                    device_name=device_name,
                    created_by=current_user.id,
                    created_at=datetime.now()
                )
                db.session.add(link)
                db.session.flush()  # Get ID
                results['links_created'].append({
                    'token': token,
                    'device': device_name
                })
            else:
                results['links_updated'].append({
                    'token': link.token,
                    'device': device_name
                })
            
            # Process CSV
            csv_file = files_dict.get('csv')
            if csv_file:
                # 1. Upload original CSV to R2
                csv_path = storage_service.upload(
                    csv_file,
                    bucket='pulsoximetrie-files',
                    key=f"{link.token}/rec_{date.isoformat()}.csv"
                )
                
                csv_file_entry = File(
                    filename=csv_file.filename,
                    file_type='csv',
                    storage_path=csv_path
                )
                db.session.add(csv_file_entry)
                db.session.flush()
                
                # 2. Parse CSV & generate plot
                df = data_parser.parse_csv(csv_file)
                fig = plot_generator.create_interactive_plot(df)
                
                # 3. Export plot as PNG
                plot_png = fig.to_image(format='png', width=1280, height=720)
                plot_path = storage_service.upload_bytes(
                    plot_png,
                    bucket='pulsoximetrie-files',
                    key=f"{link.token}/rec_{date.isoformat()}_plot.png"
                )
                
                plot_file_entry = File(
                    filename=f"plot_{date.isoformat()}.png",
                    file_type='png',
                    storage_path=plot_path
                )
                db.session.add(plot_file_entry)
                db.session.flush()
                
                # 4. Calculate stats from CSV
                stats = {
                    'avg_spo2': df['SpO2'].mean(),
                    'min_spo2': df['SpO2'].min(),
                    'max_spo2': df['SpO2'].max(),
                    'avg_pulse': df['PR'].mean(),
                    'min_pulse': df['PR'].min(),
                    'max_pulse': df['PR'].max(),
                }
            
            # Process PDF report
            report_data = None
            pdf_file = files_dict.get('pdf')
            if pdf_file:
                # Parse PDF și extrage date
                report_data = pdf_parser.parse_report_pdf(pdf_file)
                # report_data = {
                #   "events": {"desaturations_count": 23, ...},
                #   "auto_interpretation": "...",
                #   ...
                # }
            
            # Create Recording entry
            start_time_str = df.iloc[0]['Time'] if csv_file else None
            end_time_str = df.iloc[-1]['Time'] if csv_file else None
            
            recording = Recording(
                patient_link_id=link.id,
                device_name=device_name,
                recording_date=date,
                start_time=datetime.strptime(start_time_str, '%H:%M:%S').time() if start_time_str else None,
                end_time=datetime.strptime(end_time_str, '%H:%M:%S').time() if end_time_str else None,
                duration_minutes=len(df) // 60 if csv_file else None,
                avg_spo2=stats.get('avg_spo2'),
                min_spo2=stats.get('min_spo2'),
                max_spo2=stats.get('max_spo2'),
                avg_pulse=stats.get('avg_pulse'),
                min_pulse=stats.get('min_pulse'),
                max_pulse=stats.get('max_pulse'),
                report_data=report_data,  # JSON field
                csv_file_id=csv_file_entry.id if csv_file else None,
                plot_file_id=plot_file_entry.id if csv_file else None,
                uploaded_by='admin'
            )
            db.session.add(recording)
            
            results['processed'] += 1
            
        except Exception as e:
            logger.error(f"Failed to process {device_name} {date}: {e}")
            results['errors'].append({
                'device': device_name,
                'date': str(date),
                'error': str(e)
            })
            continue
    
    db.session.commit()
    
    return {
        'status': 'success',
        'results': results
    }, 200
```

### 2. **PDF Parser (Nou!)**

```python
# pdf_parser.py
import PyPDF2
import re
import json

def parse_report_pdf(pdf_file):
    """
    Parsează PDF raport generat de aparat
    Returnează dict cu date structurate
    """
    reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    
    # Extract text from all pages
    for page in reader.pages:
        text += page.extract_text()
    
    # Parse structured data using regex
    data = {}
    
    # Extract statistics
    stats_match = re.search(r'SpO2 mediu:\s*([\d.]+)%', text)
    if stats_match:
        data['spo2_avg'] = float(stats_match.group(1))
    
    stats_match = re.search(r'SpO2 minim:\s*(\d+)%', text)
    if stats_match:
        data['spo2_min'] = int(stats_match.group(1))
    
    stats_match = re.search(r'SpO2 maxim:\s*(\d+)%', text)
    if stats_match:
        data['spo2_max'] = int(stats_match.group(1))
    
    # Extract events
    events = {}
    
    events_match = re.search(r'Desaturări[^:]*:\s*(\d+)\s*evenimente', text)
    if events_match:
        events['desaturations_count'] = int(events_match.group(1))
    
    duration_match = re.search(r'Durată totală desaturări:\s*(\d+)\s*minute', text)
    if duration_match:
        events['desaturations_total_duration'] = int(duration_match.group(1))
    
    longest_match = re.search(r'Cea mai lungă[^:]*:\s*(\d+)min\s*(\d+)s', text)
    if longest_match:
        events['longest_desaturation'] = int(longest_match.group(1)) * 60 + int(longest_match.group(2))
    
    if events:
        data['events'] = events
    
    # Extract auto-interpretation
    interp_match = re.search(r'INTERPRETARE AUTOMATĂ[:\s]*(.*?)(?:═{3,}|$)', text, re.DOTALL)
    if interp_match:
        interpretation = interp_match.group(1).strip()
        # Clean up
        interpretation = re.sub(r'[⚠️→]', '', interpretation)
        interpretation = re.sub(r'\s+', ' ', interpretation)
        data['auto_interpretation'] = interpretation
    
    return data

# Exemplu output:
# {
#   "spo2_avg": 94.2,
#   "spo2_min": 87,
#   "spo2_max": 99,
#   "events": {
#     "desaturations_count": 23,
#     "desaturations_total_duration": 45,
#     "longest_desaturation": 195
#   },
#   "auto_interpretation": "Desaturări moderate detectate. Recomandare: Consultație pneumologie."
# }
```

### 3. **Watermark Service (Nou!)**

```python
# watermark_service.py
from PIL import Image, ImageDraw, ImageFont
import io

def apply_watermark(image_bytes, clinic_info):
    """
    Aplică watermark pe imaginea graficului
    
    Args:
        image_bytes: bytes - imaginea PNG originală
        clinic_info: dict - {
            'logo': bytes (PNG logo),
            'name': str,
            'phone': str,
            'address': str
        }
    
    Returns:
        bytes - imaginea cu watermark
    """
    # Deschide imaginea
    img = Image.open(io.BytesIO(image_bytes))
    width, height = img.size
    
    # Creează layer pentru watermark
    watermark = Image.new('RGBA', img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(watermark)
    
    # Font (ajustabil pe măsura imaginii)
    font_size = max(12, int(height * 0.02))  # 2% din înălțimea imaginii
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
        font_bold = ImageFont.truetype("arialbd.ttf", font_size + 2)
    except:
        font = ImageFont.load_default()
        font_bold = font
    
    # Poziție footer (jos, centrat)
    footer_y = height - 80
    
    # Dacă există logo, îl plasăm
    if clinic_info.get('logo'):
        logo_img = Image.open(io.BytesIO(clinic_info['logo']))
        # Resize logo (max 60px înălțime)
        logo_height = 60
        aspect_ratio = logo_img.width / logo_img.height
        logo_width = int(logo_height * aspect_ratio)
        logo_img = logo_img.resize((logo_width, logo_height), Image.Resampling.LANCZOS)
        
        # Plasare logo (stânga jos)
        logo_x = 20
        logo_y = height - logo_height - 10
        
        # Paste logo (cu alpha channel pentru transparență)
        if logo_img.mode == 'RGBA':
            watermark.paste(logo_img, (logo_x, logo_y), logo_img)
        else:
            watermark.paste(logo_img, (logo_x, logo_y))
        
        # Text începe după logo
        text_x = logo_x + logo_width + 20
    else:
        text_x = 20
    
    # Text watermark
    text_y = footer_y
    
    # Clinica (bold)
    if clinic_info.get('name'):
        draw.text((text_x, text_y), clinic_info['name'], 
                 fill=(0, 0, 0, 200), font=font_bold)
        text_y += font_size + 5
    
    # Telefon
    if clinic_info.get('phone'):
        draw.text((text_x, text_y), f"☎ {clinic_info['phone']}", 
                 fill=(0, 0, 0, 180), font=font)
        text_y += font_size + 3
    
    # Adresă
    if clinic_info.get('address'):
        draw.text((text_x, text_y), f"📍 {clinic_info['address']}", 
                 fill=(0, 0, 0, 180), font=font)
    
    # Combină imaginea originală cu watermark
    img_with_watermark = Image.alpha_composite(
        img.convert('RGBA'), 
        watermark
    ).convert('RGB')
    
    # Export ca bytes
    output = io.BytesIO()
    img_with_watermark.save(output, format='PNG', quality=95)
    output.seek(0)
    
    return output.read()


def get_clinic_info(admin_id):
    """
    Preia informații clinică pentru watermark
    """
    admin = Admin.query.get(admin_id)
    
    if not admin:
        return None
    
    info = {
        'name': admin.clinic_name,
        'phone': admin.clinic_phone,
        'address': admin.clinic_address,
        'logo': None
    }
    
    # Descarcă logo dacă există
    if admin.clinic_logo_file_id:
        logo_file = File.query.get(admin.clinic_logo_file_id)
        if logo_file:
            logo_bytes = storage_service.download(logo_file.storage_path)
            info['logo'] = logo_bytes
    
    return info
```

### 4. **Patient Temporary Plot Handler (Actualizat cu Download)**

```python
# patient_routes.py

@app.route('/api/patient/temp-plot', methods=['POST'])
@patient_required
def temporary_plot():
    """
    Upload temporar CSV pentru plotare (fără salvare în DB)
    Folosit de pacienți pentru explorare CSV-uri vechi
    """
    csv_file = request.files.get('csv')
    
    if not csv_file or not csv_file.filename.endswith('.csv'):
        return {"error": "Invalid CSV file"}, 400
    
    try:
        # Parse CSV (in-memory, nu salvăm pe disk!)
        df = data_parser.parse_csv(csv_file)
        
        # Generate plot
        fig = plot_generator.create_interactive_plot(df)
        
        # Calculate quick stats
        stats = {
            'total_readings': len(df),
            'duration_hours': len(df) / 3600,
            'avg_spo2': float(df['SpO2'].mean()),
            'min_spo2': int(df['SpO2'].min()),
            'max_spo2': int(df['SpO2'].max()),
            'avg_pulse': float(df['PR'].mean())
        }
        
        # Return figure as JSON (Plotly native format)
        fig_json = fig.to_json()
        
        return {
            'status': 'success',
            'figure': json.loads(fig_json),
            'stats': stats,
            'warning': 'Graficul este temporar și nu va fi salvat'
        }, 200
        
    except Exception as e:
        logger.error(f"Temp plot failed: {e}")
        return {"error": str(e)}, 500


@app.route('/api/patient/temp-plot/download', methods=['POST'])
@patient_required
def download_temp_plot():
    """
    Download plot temporar cu watermark
    Client trimite figure JSON (din temp-plot response)
    """
    try:
        figure_json = request.json.get('figure')
        
        # Recreate Plotly figure din JSON
        fig = go.Figure(figure_json)
        
        # Export ca PNG (in-memory)
        img_bytes = fig.to_image(format='png', width=1280, height=720)
        
        # Aplică watermark
        current_link = get_current_patient_link()  # Din token
        admin_id = current_link.created_by
        clinic_info = watermark_service.get_clinic_info(admin_id)
        
        if clinic_info:
            img_bytes = watermark_service.apply_watermark(img_bytes, clinic_info)
        
        # Return ca file download
        return send_file(
            io.BytesIO(img_bytes),
            mimetype='image/png',
            as_attachment=True,
            download_name=f'grafic_explorare_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
        )
        
    except Exception as e:
        logger.error(f"Temp plot download failed: {e}")
        return {"error": str(e)}, 500
```

### 5. **Adaptare Funcționalitate Existentă: Generare Ferestre de Timp**

⚠️ **IMPORTANT:** Funcționalitatea de generare grafice pe intervale **EXISTĂ DEJA** în aplicația locală!

**Cod Existent (batch_processor.py):**
```python
# batch_processor.py (ADAPTAT PENTRU CLOUD)

def generate_windowed_plots_cloud(df, window_minutes=30):
    """
    ADAPTARE A FUNCȚIONALITĂȚII EXISTENTE pentru cloud.
    
    În loc să salveze pe disk (ca în batch local), returnează lista de figuri.
    
    Args:
        df: DataFrame cu datele CSV parsate (cu index DatetimeIndex)
        window_minutes: Dimensiune fereastră în minute (15, 30, 60, 120, 180)
    
    Returns:
        List[tuple]: [(start_time, end_time, figure), ...]
    """
    from datetime import timedelta
    from plot_generator import create_plot  # Reutilizăm funcția existentă!
    
    # Logica de "feliere" - IDENTICĂ cu batch_processor.py linia 235-271
    record_start_time = df.index.min()
    record_end_time = df.index.max()
    time_window = timedelta(minutes=window_minutes)
    
    current_slice_start = record_start_time
    windows = []
    
    while current_slice_start < record_end_time:
        current_slice_end = current_slice_start + time_window
        
        # Selectăm datele pentru felia curentă
        df_slice = df[(df.index >= current_slice_start) & (df.index < current_slice_end)]
        
        if df_slice.empty:
            logger.warning(f"Fereastră {current_slice_start.time()} - {current_slice_end.time()} fără date. Se omite.")
            current_slice_start = current_slice_end
            continue
        
        # Generăm graficul folosind funcția existentă create_plot()
        fig = create_plot(df_slice, "cloud_window")
        
        windows.append((current_slice_start, current_slice_end, fig))
        
        current_slice_start = current_slice_end
    
    logger.info(f"Generat {len(windows)} ferestre de {window_minutes} minute")
    return windows


def generate_custom_interval_plot(df, start_time, end_time):
    """
    Generează grafic pentru interval personalizat
    Reutilizează create_plot() existent!
    """
    import pandas as pd
    from plot_generator import create_plot
    
    # Parsare start/end time la datetime (cu aceeași dată ca primul punct)
    base_date = df.index.min().date()
    start_dt = pd.to_datetime(f"{base_date} {start_time}")
    end_dt = pd.to_datetime(f"{base_date} {end_time}")
    
    # Dacă end < start, înseamnă că trece peste miezul nopții
    if end_dt < start_dt:
        end_dt += pd.Timedelta(days=1)
    
    # Filtrare (IDENTIC cu batch_processor.py linia 248)
    filtered_df = df[(df.index >= start_dt) & (df.index < end_dt)]
    
    if filtered_df.empty:
        raise ValueError("No data in selected interval")
    
    # Generare grafic folosind funcția existentă
    fig = create_plot(filtered_df, "custom_interval")
    
    return fig
```

**Ce Se Schimbă față de Batch Local:**

| Aspect | Batch Local (existent) | Cloud Adaptare (nou) |
|--------|------------------------|----------------------|
| Input | Fișier CSV de pe disk | DataFrame în memorie (din R2) |
| Output | Salvare JPG pe disk | Return figuri Plotly (în memorie) |
| Nume fișiere | `generate_intuitive_image_name()` | Generat în endpoint la download |
| Watermark | ❌ Nu există | ✅ Aplicat cu Pillow înainte de download |
| Format | JPG (config: 1280x720) | PNG (pentru transparență watermark) |
| Folder | Creat pe disk cu `os.makedirs()` | ZIP creat în memorie cu `zipfile.ZipFile(io.BytesIO())` |

### 6. **Download Plot cu Selector Interval (Endpoint Adaptat)**

```python
# patient_routes.py

@app.route('/api/patient/recording/<int:recording_id>/download-plot', methods=['POST'])
@patient_required
def download_recording_plot(recording_id):
    """
    Download grafic cu selector interval (ferestre sau personalizat)
    
    REUTILIZEAZĂ FUNCȚIILE EXISTENTE:
    - data_parser.parse_csv_data() (linia 224 din batch_processor.py)
    - generate_windowed_plots_cloud() (adaptat din run_batch_job)
    - generate_intuitive_image_name() (din batch_processor.py linia 131)
    
    POST Body:
    {
        "mode": "complete" | "windows" | "custom",
        "window_minutes": 30,  # dacă mode=windows
        "start_time": "23:04", # dacă mode=custom
        "end_time": "07:27"    # dacă mode=custom
    }
    """
    # Verifică că recording aparține pacientului curent
    current_link = get_current_patient_link()
    recording = Recording.query.filter_by(
        id=recording_id,
        patient_link_id=current_link.id
    ).first()
    
    if not recording:
        return {"error": "Recording not found"}, 404
    
    try:
        # Preia parametri
        data = request.json
        mode = data.get('mode', 'complete')
        
        # Descarcă CSV original din R2
        csv_file = File.query.get(recording.csv_file_id)
        csv_bytes = storage_service.download(csv_file.storage_path)
        
        # REUTILIZARE: parse_csv_data() existent (data_parser.py)
        df = data_parser.parse_csv_data(csv_bytes, csv_file.original_filename)
        
        # Preia info clinică pentru watermark
        admin_id = current_link.created_by
        clinic_info = watermark_service.get_clinic_info(admin_id)
        
        if mode == 'complete':
            # Grafic complet - REUTILIZARE: create_plot() existent
            fig = plot_generator.create_plot(df, csv_file.original_filename)
            img_bytes = fig.to_image(format='png', width=1280, height=720)
            
            if clinic_info:
                img_bytes = watermark_service.apply_watermark(img_bytes, clinic_info)
            
            filename = f"grafic_{recording.recording_date.isoformat()}_complet.png"
            
            return send_file(
                io.BytesIO(img_bytes),
                mimetype='image/png',
                as_attachment=True,
                download_name=filename
            )
        
        elif mode == 'windows':
            # Ferestre de timp - REUTILIZARE: logica din batch_processor.py
            window_minutes = data.get('window_minutes', 30)
            windows = generate_windowed_plots_cloud(df, window_minutes)
            
            # REUTILIZARE: extract_device_number() pentru nume fișiere
            device_number = batch_processor.extract_device_number(csv_file.original_filename)
            
            # Creează ZIP cu toate ferestrele
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for i, (start, end, fig) in enumerate(windows, 1):
                    # Generare PNG
                    img_bytes = fig.to_image(format='png', width=1280, height=720)
                    
                    # Aplică watermark
                    if clinic_info:
                        img_bytes = watermark_service.apply_watermark(img_bytes, clinic_info)
                    
                    # REUTILIZARE: Aceeași logică de nume ca în batch_processor.py
                    # Crează df_slice temporar pentru generate_intuitive_image_name()
                    df_slice = df[(df.index >= start) & (df.index < end)]
                    filename = batch_processor.generate_intuitive_image_name(df_slice, device_number)
                    # Convertim .jpg → .png
                    filename = filename.replace('.jpg', '.png')
                    
                    # Adaugă în ZIP
                    zip_file.writestr(filename, img_bytes)
            
            zip_buffer.seek(0)
            
            # Nume ZIP intuitiv (similar cu folder batch)
            start_time = df.index.min()
            end_time = df.index.max()
            zip_filename = f"{start_time.day:02d}{MONTH_NAMES_RO[start_time.month]}{start_time.year}_ferestre_{window_minutes}min_Aparat{device_number}.zip"
            
            return send_file(
                zip_buffer,
                mimetype='application/zip',
                as_attachment=True,
                download_name=zip_filename
            )
        
        elif mode == 'custom':
            # Interval personalizat
            start_time = data.get('start_time')
            end_time = data.get('end_time')
            
            # REUTILIZARE: Aceeași logică de filtrare ca în batch_processor.py
            fig = generate_custom_interval_plot(df, start_time, end_time)
            img_bytes = fig.to_image(format='png', width=1280, height=720)
            
            if clinic_info:
                img_bytes = watermark_service.apply_watermark(img_bytes, clinic_info)
            
            # Nume fișier cu format similar batch
            device_number = batch_processor.extract_device_number(csv_file.original_filename)
            filename = f"Aparat{device_number}_{start_time.replace(':', 'h')}-{end_time.replace(':', 'h')}.png"
            
            return send_file(
                io.BytesIO(img_bytes),
                mimetype='image/png',
                as_attachment=True,
                download_name=filename
            )
        
        else:
            return {"error": "Invalid mode"}, 400
        
    except Exception as e:
        logger.error(f"Plot download failed: {e}")
        return {"error": str(e)}, 500


# HELPER FUNCȚII ADAPTATE DIN batch_processor.py
MONTH_NAMES_RO = {
    1: 'ian', 2: 'feb', 3: 'mar', 4: 'apr', 5: 'mai', 6: 'iun',
    7: 'iul', 8: 'aug', 9: 'sep', 10: 'oct', 11: 'nov', 12: 'dec'
}
```

**Rezumat Reutilizare Cod Existent:**

| Funcție Existentă | Locație | Reutilizată în Cloud? |
|-------------------|---------|------------------------|
| `parse_csv_data()` | data_parser.py | ✅ DA - identic |
| `create_plot()` | plot_generator.py | ✅ DA - identic |
| `extract_device_number()` | batch_processor.py linia 38 | ✅ DA - pentru nume fișiere |
| `generate_intuitive_image_name()` | batch_processor.py linia 131 | ✅ DA - pentru nume imagini în ZIP |
| `generate_intuitive_folder_name()` | batch_processor.py linia 66 | ✅ DA - pentru nume ZIP |
| Logica de "feliere" | batch_processor.py linia 235-271 | ✅ DA - adaptat în `generate_windowed_plots_cloud()` |

---

## 💡 ECONOMIE DE EFORT PRIN REUTILIZARE COD EXISTENT

### Estimare Timp Economisit:

| Task | Timp Dezvoltare de la Zero | Timp Adaptare Cod Existent | Economie |
|------|----------------------------|----------------------------|----------|
| Logică feliere date pe intervale | 2-3 zile | 2-3 ore | **90%** ⚡ |
| Generare nume intuitive fișiere | 1-2 zile | 1 oră | **90%** ⚡ |
| Parse CSV + validare | 2-3 zile | 30 min | **95%** ⚡ |
| Generare grafice Plotly | 3-5 zile | 1 oră | **95%** ⚡ |
| Detectare test peste miezul nopții | 1 zi | 0 ore (EXISTĂ!) | **100%** ⚡ |
| **TOTAL** | **~10-14 zile** | **~5-6 ore** | **~95%** 🎉 |

### Ce Trebuie Creat de la Zero (Nou pentru Cloud):

| Task | Timp Estimat | Motiv |
|------|--------------|-------|
| `watermark_service.py` | 1-2 zile | Feature NOU (logo + text pe imagini) |
| `pdf_parser.py` | 2-3 zile | Parse PDF raport → JSON pentru DB |
| Endpoints API (5 noi) | 3-4 zile | REST API pentru cloud (bulk upload, download, settings, merge, temp plot) |
| Models DB (Admin clinic_* fields) | 1 zi | Schema DB pentru watermark config |
| UI Frontend (admin + patient) | 5-7 zile | React/Dash componente pentru selector interval + settings |
| **TOTAL NOU** | **~12-17 zile** | Cod care NU există în aplicația locală |

### Concluzie:

- ✅ **~70% din logica backend EXISTĂ DEJA** (`plot_generator.py`, `batch_processor.py`, `data_parser.py`)
- ✅ **Economie totală: ~10 zile de dezvoltare** prin reutilizare
- ✅ **Nume fișiere consistente** între aplicația locală și cloud (UX unificat)
- ✅ **Cod battle-tested** - `batch_processor.py` deja funcțional și testat pe date reale

**📦 Recomandare Arhitectură:**

```
cloud_app/
├─ shared/          # ← Cod reutilizat din aplicația locală
│  ├─ plot_generator.py    (IDENTIC, 0 modificări)
│  ├─ data_parser.py       (IDENTIC, 0 modificări)
│  ├─ config.py            (IDENTIC, 0 modificări)
│  ├─ logger_setup.py      (IDENTIC, 0 modificări)
│  └─ batch_utils.py       (ADAPTAT din batch_processor.py)
│     ├─ extract_device_number()
│     ├─ generate_intuitive_image_name()
│     ├─ generate_intuitive_folder_name()
│     └─ generate_windowed_plots_cloud()  # Adaptat: returnează figuri
│
├─ cloud_specific/  # ← Cod NOU pentru cloud
│  ├─ watermark_service.py
│  ├─ pdf_parser.py
│  ├─ storage_service.py (R2 storage)
│  └─ patient_routes.py
│
└─ migrations/
   └─ add_watermark_fields.py
```

**✅ Avantaje:**
1. **Zero duplicare cod** - folosim aceleași funcții testate
2. **Bug fixes propagate** - repari în `plot_generator.py` → funcționează și în cloud
3. **Consistență UX** - pacientul vede aceleași nume fișiere local/cloud
4. **Timp redus dezvoltare** - focus pe features NOI, nu pe reinventare

---

### 4. **Merge Links Handler**

```python
# admin_routes.py

@app.route('/api/admin/merge-links', methods=['POST'])
@admin_required
def merge_links():
    """
    Contopește 2 link-uri (același pacient, aparate diferite)
    """
    data = request.json
    source_token = data.get('source')
    target_token = data.get('target')
    
    if not source_token or not target_token:
        return {"error": "Missing source or target token"}, 400
    
    source = PatientLink.query.filter_by(token=source_token).first()
    target = PatientLink.query.filter_by(token=target_token).first()
    
    if not source or not target:
        return {"error": "Invalid tokens"}, 404
    
    if not source.is_active:
        return {"error": "Source link already inactive"}, 400
    
    try:
        # Move all recordings from source to target
        moved_count = Recording.query.filter_by(
            patient_link_id=source.id
        ).update({
            'patient_link_id': target.id
        })
        
        # Mark source as merged
        source.is_active = False
        source.merged_into = target.id
        source.merged_at = datetime.now()
        
        db.session.commit()
        
        logger.info(f"Merged link {source_token} → {target_token} ({moved_count} recordings)")
        
        return {
            'status': 'success',
            'moved_recordings': moved_count,
            'target_token': target_token
        }, 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Merge failed: {e}")
        return {"error": str(e)}, 500
```

---

## 📝 REZUMAT MODIFICĂRI NECESARE ÎN DOCUMENTAȚIE

### Documente de Actualizat:

1. **PLAN_IMPLEMENTARE_PLATFORMA_CLOUD.md**
   - [ ] Secțiunea "Workflow Clinic" (pag 3-4)
   - [ ] Secțiunea "User Journey Pacient" (pag 6-8) - ELIMINĂ upload
   - [ ] Secțiunea "User Journey Medic" (pag 9-12) - ADAUGĂ bulk upload
   - [ ] Secțiunea "Schema DB" (pag 30-35) - ACTUALIZEAZĂ tabele
   - [ ] Secțiunea "Flow Upload" (pag 38-42) - ÎNLOCUIEȘTE cu bulk

2. **ARHITECTURA_VIZUALA_DIAGRAME.md**
   - [ ] Diagrama "Flow Upload CSV" (pag 10-15) - ÎNLOCUIEȘTE
   - [ ] UI Wireframe Patient (pag 48) - ELIMINĂ upload component
   - [ ] UI Wireframe Admin (pag 46) - ADAUGĂ bulk upload

3. **REZUMAT_EXECUTIV_DECIZIE.md**
   - [ ] Secțiunea "Features" (pag 2-3) - Actualizează listă
   - [ ] Secțiunea "User Flow" (pag 6) - Simplifică pacient

4. **COMPARATIE_HOSTING_DATABASE_GRATUIT.md**
   - [ ] Secțiunea "Calculator Stocare" (pag 18-22) - Actualizează (nu PDF stocat)

5. **START_AICI_TRANSFORMARE_CLOUD.md**
   - [ ] Secțiunea "Features Cheie" (pag 2) - Actualizează listă

---

## ✅ CHECKLIST IMPLEMENTARE WORKFLOW NOU

```
BACKEND:
□ Creare endpoint /api/admin/bulk-upload (multi-file upload)
□ Implementare pdf_parser.py (parse PDF raport → JSON)
□ Creare endpoint /api/patient/temp-plot (upload temporar, fără DB save)
□ Implementare watermark_service.py (apply_watermark, get_clinic_info) [NOU]
□ ⚡ ADAPTARE funcționalitate existentă:
  □ ✅ EXISTĂ: batch_processor.py → run_batch_job() (linia 178-287)
  □ ✅ EXISTĂ: extract_device_number() (linia 38)
  □ ✅ EXISTĂ: generate_intuitive_image_name() (linia 131)
  □ ✅ EXISTĂ: generate_intuitive_folder_name() (linia 66)
  □ ✅ EXISTĂ: logica de "feliere" date pe ferestre (linia 235-271)
  □ 🔧 ADAPTAT: generate_windowed_plots_cloud() - returnează figuri în loc de salvare disk
  □ 🔧 ADAPTAT: generate_custom_interval_plot() - folosește create_plot() existent
□ Creare endpoint /api/patient/temp-plot/download (cu watermark + selector interval)
□ Creare endpoint /api/patient/recording/<id>/download-plot (POST cu selector interval)
  □ Reutilizează create_plot(), parse_csv_data(), extract_device_number()
  □ Aplică watermark pe fiecare imagine generată
  □ Generează ZIP când ferestre multiple (in-memory cu zipfile.ZipFile(io.BytesIO()))
□ Creare endpoint /api/admin/settings (update clinic info)
□ Creare endpoint /api/admin/logo/upload (upload logo clinică)
□ Actualizare models.py:
  □ Admin: adăugare clinic_name, clinic_phone, clinic_address, clinic_logo_file_id
  □ Recording: adăugare device_name + report_data (JSONB)
  □ PatientLink: adăugare merged_into + merged_at
□ Creare endpoint /api/admin/merge-links
□ Actualizare endpoint /p/<token> (handle merged links redirect)
□ Unit tests pentru bulk upload (14 fișiere test)
□ Unit tests pentru merge links
□ Unit tests pentru temp plot (verifică că nu salvează în DB)
□ Unit tests pentru watermark (verifică aplicare corectă pe PNG)

FRONTEND:
□ Interfață Admin: Bulk upload (folder picker)
□ Interfață Admin: Rezultate upload (listă link-uri generate)
□ Interfață Admin: Merge links (checkbox selection + buton)
□ Interfață Admin: Setări clinică (nume, telefon, adresă, logo)
□ Interfață Admin: Upload logo clinică (PNG, max 1MB)
□ Interfață Admin: Preview watermark (live preview când modifică setări)
□ Interfață Pacient: 2 tabs (Înregistrările Mele + Explorează CSV)
□ Interfață Pacient Tab 1: Vizualizare înregistrări stocate (read-only)
□ Interfață Pacient Tab 1: Buton "Download PNG" → Dialog selector interval
  □ Opțiune: Grafic complet
  □ Opțiune: Ferestre de X minute (15, 30, 60, 120, 180 min)
  □ Opțiune: Interval personalizat (time pickers)
  □ Calcul automat: număr imagini rezultate
  □ Progress bar la generare ferestre multiple
  □ Download ZIP când ferestre multiple
□ Interfață Pacient Tab 1: Buton "Download CSV" (original)
□ Interfață Pacient Tab 1: Buton "Vezi Raport" (parseat din PDF)
□ Interfață Pacient Tab 2: Upload temporar CSV + plotare (fără salvare)
□ Interfață Pacient Tab 2: Buton "Download PNG" → Același selector interval
□ Interfață Pacient: Afișare raport parseat (JSON → HTML)
□ Interfață Pacient: Afișare multiple aparate (grupare)
□ Interfață Pacient: Warning pe toate download-uri: "Imagine include watermark clinică"

DATABASE:
□ Migrație: ALTER TABLE admins ADD clinic_name VARCHAR(255)
□ Migrație: ALTER TABLE admins ADD clinic_phone VARCHAR(50)
□ Migrație: ALTER TABLE admins ADD clinic_address TEXT
□ Migrație: ALTER TABLE admins ADD clinic_logo_file_id INTEGER REFERENCES files(id)
□ Migrație: ALTER TABLE recordings ADD device_name VARCHAR(255)
□ Migrație: ALTER TABLE recordings ADD report_data JSONB
□ Migrație: ALTER TABLE patient_links ADD merged_into INTEGER REFERENCES patient_links(id)
□ Migrație: ALTER TABLE patient_links ADD merged_at TIMESTAMP
□ Migrație: DROP COLUMN patient_links.device_name (dacă există)
□ Index: CREATE INDEX idx_device_name ON recordings(device_name)

DEPENDENCIES:
□ Adăugare în requirements.txt:
  □ Pillow>=10.0.0 (pentru watermark pe imagini)
  □ PyPDF2>=3.0.0 (pentru parsare PDF rapoarte)

DOCUMENTAȚIE:
□ Update PLAN_IMPLEMENTARE_PLATFORMA_CLOUD.md
□ Update ARHITECTURA_VIZUALA_DIAGRAME.md
□ Update REZUMAT_EXECUTIV_DECIZIE.md
□ Update COMPARATIE_HOSTING_DATABASE_GRATUIT.md
□ Update START_AICI_TRANSFORMARE_CLOUD.md
```

---

**Versiune:** 1.0 - Corecții Workflow Real  
**Data:** 11 noiembrie 2025  
**Status:** ⚠️ DOCUMENT DE CORECȚIE - Aplică peste documentația existentă

**IMPORTANT:** Acest document conține workflow-ul REAL confirmat de utilizator.  
Documentele inițiale trebuie actualizate conform acestor specificații! 🔄


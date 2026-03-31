# 📊 Dashboard Medical - Ghid Utilizare

## 🎯 Prezentare Generală

Dashboard-ul medical oferă o interfață profesională pentru gestionarea înregistrărilor de pulsoximetrie, cu funcționalități complete de procesare batch, vizualizare detaliată și interpretare medicală.

## 🏗️ Structura Dashboard-ului

### Tab 1: 📁 Procesare Batch

**Funcționalitate**: Procesare automată în lot a fișierelor CSV cu generare automată de link-uri pentru pacienți.

**Utilizare**:
1. Introduceți calea către folderul cu fișiere CSV
2. (Opțional) Specificați folderul de ieșire pentru imagini
3. Setați durata ferestrei de timp (în minute)
4. Click pe "🚀 Pornește Procesare Batch"

**Rezultat**:
- Imagini JPG generate pentru fiecare interval de timp
- Link-uri unice generate automat pentru fiecare înregistrare
- Organizare automată în foldere intuitive

**Format Foldere Generate**:
```
output/
├── 02mai2025_23h30-03mai_06h37_Aparat3539/
│   ├── Aparat3539_02mai_23h30m-03mai_01h00m.jpg
│   ├── Aparat3539_03mai_01h00m-03mai_01h30m.jpg
│   └── ...
```

### Tab 2: 📊 Vizualizare Date

**Funcționalitate**: Vizualizare detaliată a înregistrărilor cu sistem de expandare/colapsare (accordion).

#### Format Restrâns (Listă Compactă)
Fiecare linie afișează:
- 📅 **Data înregistrării** (format citibil în română)
- 🔧 **Numărul aparatului**
- 👁️ **Număr vizualizări**
- ▶/▼ **Buton expand/collapse**

#### Format Desfășurat (Click pe linie)
La click pe buton ▶, se expandează și afișează:

1. **📈 Grafic Interactiv**
   - Placeholder pentru grafic Plotly (va fi implementat cu CSV stocat)
   - Zoom și navigare interactivă

2. **🖼️ Imagini Generate (Grafice Desfășurate)**
   - Galerie cu toate imaginile JPG generate în procesarea batch
   - Afișare automată din folderul asociat înregistrării
   - Nume fișiere intuitive pentru identificare rapidă
   - Maxim 900px lățime, responsive

3. **📄 Raport PDF**
   - Placeholder pentru upload și vizualizare PDF-uri
   - Va permite încărcarea rapoartelor medicale asociate

4. **📝 Interpretare Medicală**
   - Textarea pentru scriere interpretare medicală detaliată
   - Salvare automată la click pe "💾 Salvează Interpretare"
   - Persistență în baza de date JSON
   - Vizibil doar medicilor (nu apare la pacienți)

5. **🔗 Link Pacient**
   - Link complet pentru partajare cu pacientul
   - Format: `http://127.0.0.1:8050/?token={uuid}`
   - Copy-paste direct din câmp read-only

#### Toggle Behavior
- **Click pe ▶** → Expandare completă cu toate detaliile
- **Click pe ▼** → Colapsare, se închide vizualizarea detaliată
- Doar un rând poate fi expandat simultan pentru claritate

## 🔄 Workflow Medical Complet

### Pas 1: Procesare Batch
```
Medic → Tab "Procesare Batch" → Selectează folder CSV → Procesare
```
**Output**: Link-uri generate automat pentru fiecare înregistrare

### Pas 2: Vizualizare și Interpretare
```
Medic → Tab "Vizualizare Date" → Click pe înregistrare → Expandare
```
**Acțiuni disponibile**:
- Vizualizare imagini grafice
- Scriere interpretare medicală
- (Viitor) Încărcare raport PDF

### Pas 3: Partajare cu Pacientul
```
Medic → Copiază link → Trimite către pacient (email/SMS)
```
**Pacientul vede**:
- Data înregistrării
- Numărul aparatului
- Graficul interactiv (când va fi implementat)
- Notițele medicale (dacă există)

## 📊 Metadata Stocată

Pentru fiecare înregistrare se stochează:
- `token`: UUID persistent
- `device_name`: Nume aparat (ex: "Checkme O2 #3539")
- `recording_date`: Data înregistrării (YYYY-MM-DD)
- `start_time`: Ora de început (HH:MM)
- `end_time`: Ora de sfârșit (HH:MM)
- `output_folder`: Nume folder cu imagini
- `output_folder_path`: Cale absolută către imagini
- `images_count`: Număr imagini generate
- `medical_notes`: Interpretare medicală
- `view_count`: Număr vizualizări de către pacient
- `sent_status`: Marcat ca trimis/netrimis
- `pdf_path`: Cale către PDF asociat (viitor)

## 🎨 Design și UX

### Paleta de Culori
- **Primary**: #3498db (albastru profesional)
- **Success**: #27ae60 (verde pentru acțiuni pozitive)
- **Background**: #f5f7fa (gri deschis)
- **Text**: #2c3e50 (gri închis citibil)
- **Accent**: #2980b9 (albastru închis pentru titluri)

### Principii UX
✅ **Clarity**: Informații esențiale vizibile mereu în format compact
✅ **Efficiency**: Toggle rapid între vizualizare compactă și detaliată
✅ **Consistency**: Iconițe și stiluri uniforme
✅ **Feedback**: Confirmări vizuale la salvare ("✅ Salvat!")
✅ **Accessibility**: Contrast puternic, font lizibil

## 🔒 Securitate și Privacy

### Date GDPR-Compliant
❌ **NU se stochează**:
- Nume pacient
- CNP
- Date de contact
- Adresă

✅ **SE stochează**:
- Token-uri UUID anonime
- Date medicale tehnice (SpO2, puls)
- Metadata aparat
- Interpretări medicale anonime

### Access Control
- **Medici**: Acces complet (procesare + vizualizare + interpretare)
- **Pacienți**: Acces read-only prin link cu token

## 📱 Responsive Design

Dashboard-ul este optimizat pentru:
- **Desktop**: Layout complet cu toate funcționalitățile
- **Tablet**: Imagini scalate, layout adaptat
- **Mobile**: Vizualizare verticală, touch-friendly

## 🚀 Funcționalități Viitoare

### În Dezvoltare
- [ ] Încărcare și vizualizare PDF-uri rapoarte medicale
- [ ] Grafic interactiv din CSV stocat în database
- [ ] Export raport complet PDF (imagini + interpretare)
- [ ] Notificări email/SMS automate la partajare link
- [ ] Comparare multi-înregistrări pentru același pacient
- [ ] Statistici aggregate (trend SpO2 în timp)

## 📝 Exemple de Utilizare

### Exemplu 1: Procesare Rapidă
```
Input: 5 fișiere CSV în C:\DateMedicale\Noi\
Output: 5 link-uri generate, 45 imagini totale
Timp: ~30 secunde
```

### Exemplu 2: Interpretare Medicală
```
1. Click pe înregistrare → Expandare
2. Vizualizare imagini grafice
3. Scriere interpretare: "Episoade frecvente de desaturare sub 90% 
   între 02:00-04:00. Recomand evaluare pentru apnee obstructivă 
   de somn. Programare polisomografie."
4. Click "Salvează" → Confirmare "✅ Salvat!"
```

### Exemplu 3: Partajare cu Pacient
```
Link generat: http://127.0.0.1:8050/?token=a8f9d2b1-3c4e-4d5e-8f9a-1b2c3d4e5f6a
Email către pacient: "Bună ziua, puteți accesa rezultatele 
pulsoximetriei la acest link: [LINK]"
Pacient accesează → Tracking automat (view_count++)
```

## 🛠️ Troubleshooting

### Imaginile nu se încarcă
**Cauză**: Metadata `output_folder_path` lipsă
**Soluție**: Reprocesați CSV-ul prin tab "Procesare Batch"

### Link-ul nu funcționează pentru pacient
**Cauză**: Token invalid sau inactiv
**Soluție**: Verificați în tab "Vizualizare Date" dacă token-ul există

### Salvarea interpretării eșuează
**Cauză**: Eroare la scriere în `patient_links.json`
**Soluție**: Verificați permisiuni fișier și log-uri (`app_activity.log`)

## 📞 Suport

Pentru întrebări sau probleme:
1. Verificați log-urile: `app_activity.log`
2. Consultați `.cursorrules` pentru detalii tehnice
3. Raportați bug-uri cu screenshot-uri și mesaje de eroare

---

**Versiune**: 3.0 - Dashboard Medical cu Accordion
**Data Actualizare**: 11 Noiembrie 2025
**Status**: ✅ Funcțional, în dezvoltare activă


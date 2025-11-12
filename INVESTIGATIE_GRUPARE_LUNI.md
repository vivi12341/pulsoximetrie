# 🔍 INVESTIGAȚIE: Problema Grupare "Pe Luni"

**Data**: 12 Noiembrie 2025  
**Status**: ⚠️ PARȚIAL REZOLVATĂ - Necesită continuare  
**Commit**: c4f86c9 - "WIP: Fix parțial pentru grupare 'Pe Luni'"

---

## 📊 Problema Raportată

Când utilizatorul selectează gruparea **"🗓️ Pe Luni"** în tab-ul "Vizualizare Date", doar **1 din 2 înregistrări** apare, deși header-ul indică corect "**📅 Octombrie 2025 — 2 înregistrări**".

### Date de Test
- **Înregistrare 1**: `cbd8f122` - 7 octombrie 2025 (23:04-06:36) ✅ **APARE**
- **Înregistrare 2**: `56ae5494` - 14 octombrie 2025 (20:32-04:45) ❌ **LIPSEȘTE**

### Comportament Observat
- **Grupare "Pe Zile"**: Funcționează perfect - ambele înregistrări apar
- **Grupare "Pe Săptămâni"**: (netest at în detaliu)
- **Grupare "Pe Luni"**: Doar prima înregistrare apare

---

## 🔬 Investigație Tehnică

### 1. Log-uri Relevante

```
Grup 'Octombrie 2025': are 2 link-uri în group_links
↳ INTRAT în loop pentru link #1 (56ae5494) - is_expanded: False
↳ Începere formatare dată pentru 56ae5494...
↳ Formatare dată completă: Marți 14/10/2025 de la ora 20:32 până în Miercuri...
[❌ NU APARE: "APPEND row_container pentru token 56ae5494"]
↳ INTRAT în loop pentru link #2 (cbd8f122) - is_expanded: False
↳ Începere formatare dată pentru cbd8f122...
↳ Formatare dată completă: Marți 07/10/2025 de la ora 23:04 până în Miercuri...
↳ APPEND row_container pentru token cbd8f122... ✓
🔍 Înainte de verificare: len(group_rows)=1 (AR TREBUI SĂ FIE 2!)
✅ Adăugat container pentru grup 'Octombrie 2025' cu 1 înregistrări
```

### 2. Cauza Identificată

**Problema principală**: După formatarea datei pentru primul link (`56ae5494`), execuția **NU ajunge** la linia `group_rows.append(row_container)` (linia 1343).

**Posibile cauze**:
1. ❓ **Excepție silențioasă** în crearea componentelor UI (`compact_row` sau `row_container`)
2. ❓ **Race condition** în Dash callbacks (callback se re-trigger înainte de finalizare)
3. ❓ **Problemă de indentare** nesidentificată în secțiunile 1000-1330
4. ❓ **Eroare în sortarea** link-urilor din `grouped_links['Octombrie 2025']`

---

## ✅ Fix-uri Aplicate (Commit c4f86c9)

### 1. Dezindentat Verificarea Grupării (Linia 1334-1349)
**Înainte** (GREȘIT):
```python
for idx, link_data in enumerate(group_links):
    # ... procesare link ...
    group_rows.append(row_container)
    
    # ❌ ÎN INTERIORUL LOOP-ULUI (GREȘIT!)
    if group_rows and not is_group_collapsed:
        rows.append(group_container)
```

**După** (CORECT):
```python
for idx, link_data in enumerate(group_links):
    # ... procesare link ...
    group_rows.append(row_container)

# ✅ ÎN AFARA LOOP-ULUI (CORECT!)
if group_rows and not is_group_collapsed:
    rows.append(group_container)
```

### 2. Try-Except pentru Formatare Dată (Linia 983-993)
```python
try:
    if link_data.get('recording_date'):
        date_display = format_recording_date_ro(...)
    logger.info(f"  ↳ Formatare dată completă: {date_display[:50]}...")
except Exception as format_err:
    logger.error(f"  ❌ EROARE la formatare dată pentru {token[:8]}: {format_err}", exc_info=True)
    date_display = f"{link_data.get('recording_date', 'N/A')} ..."
```

### 3. Logging Extensiv Adăugat
- `logger.info(f"  ↳ INTRAT în loop pentru link #{idx+1} din grup '{group_name}' - token: {link_data['token'][:8]}...")`
- `logger.info(f"  ↳ Token {token[:8]}... - is_expanded: {is_expanded}")`
- `logger.info(f"  ↳ Începere formatare dată pentru {token[:8]}...")`
- `logger.info(f"  ↳ Formatare dată completă: {date_display[:50]}...")`
- `logger.info(f"  ↳ Creare compact_row pentru {token[:8]}...")`
- `logger.info(f"  ↳ Compact_row creat pentru {token[:8]}, acum expanded_content...")`
- `logger.info(f"  ↳ Creare row_container pentru {token[:8]}...")`
- `logger.info(f"  ↳ APPEND row_container pentru token {token[:8]}... în group_rows")`

---

## 🎯 Pași Următori (Pentru Noul Context)

### Prioritate 1: Identificare Punct Exact de Blocare
1. **Rulează aplicația** și accesează `http://127.0.0.1:8050/?tab=tab-data-view`
2. **Selectează grupare "Pe Luni"**
3. **Verifică log-urile** (`output\LOGS\app_activity.log`) pentru a vedea EXACT unde se oprește execuția pentru `56ae5494`
4. **Căutare**: `grep "56ae5494" output\LOGS\app_activity.log | tail -50`

### Prioritate 2: Verificare Indentare Completă
Fișier: `callbacks_medical.py`, liniile **974-1343**

**Verificare critică**:
- Toate liniile din loop (974-1343) trebuie să fie corect indentate
- Singura dezindentare ar trebui să fie la linia **1335** (după încheierea loop-ului)

**Comandă verificare**:
```powershell
Get-Content callbacks_medical.py | Select-Object -Skip 973 -First 370 | Select-String "^            " -NotMatch
```

### Prioritate 3: Simplificare Temporară
Dacă problema persistă, **simplifică** crearea `compact_row`:

```python
# VERSIUNE SIMPLIFICATĂ PENTRU DEBUGGING
compact_row = html.Div([
    html.P(f"📅 {date_display}"),
    html.P(f"🔧 {link_data['device_name']} | {view_display}")
], id={'type': 'expand-row-btn', 'index': token})
```

### Prioritate 4: Testare Izolată
Creează un **test minimal** pentru a reproduce problema:

```python
# test_month_grouping_minimal.py
test_links = [
    {'token': '56ae5494', 'recording_date': '2025-10-14', ...},
    {'token': 'cbd8f122', 'recording_date': '2025-10-07', ...}
]
# Procesează manual gruparea și vezi care link se pierde
```

---

## 📝 Note Importante

### Console Warnings (Pot fi ignorate momentan)
```
Warning: defaultProps will be removed from function components
Warning: componentWillReceiveProps has been renamed
```
Acestea sunt warning-uri React deprecate din Dash, **NU** cauzează problema.

### Encoding Log-uri
Log-urile afișează caractere corupte pentru diacritice (Marţi → Mar>i). Acest lucru **NU** afectează funcționalitatea, doar vizualizarea log-urilor.

### Date Test Disponibile
```
bach data\
  - Checkme O2 3539_20251007230437.csv (7 octombrie)
  - Checkme O2 3539_20251014203224.csv (14 octombrie)
  - [+ 6 alte fișiere CSV]
```

---

## 🚀 Comandă Rapidă Start

```powershell
cd "C:\Users\viore\Desktop\programe\pulsoximetrie"
python run_medical.py
# Browser: http://127.0.0.1:8050/?tab=tab-data-view
# Click: "🗓️ Pe Luni"
# Verifică: Se afișează ambele înregistrări?
```

---

## 📊 Statistici Investigație

- **Tokens folosiți**: ~111K / 1M
- **Modificări**: 1 fișier (callbacks_medical.py)
- **Linii modificate**: 1773 insertions, 164 deletions
- **Log-uri adăugate**: 8 puncte de logging
- **Commit hash**: c4f86c9

---

**STATUS FINAL**: Problema identificată parțial. Fix-uri temporare aplicate. Necesită investigație continuă pentru identificarea punctului exact de blocare în crearea componentelor UI pentru primul link din grup.

**PENTRU VIITOR**: Verifică dacă problema apare și la alte grupări (Pe Săptămâni) sau doar la "Pe Luni".


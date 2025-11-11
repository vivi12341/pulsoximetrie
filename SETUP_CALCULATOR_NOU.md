# 🔧 Ghid de Setup pentru Calculator Nou

## ✅ Configurare Completă (FINALIZAT)

Proiectul a fost adaptat cu succes pentru acest calculator!

### Ce s-a schimbat:

1. **✓ Scripturile BAT actualizate**
   - `start_server.bat` - folosește Python din `.venv`
   - `stop_server.bat` - folosește Python portabil
   - `versiuni\1\start_server.bat` - folosește Python portabil

2. **✓ Virtual Environment creat cu UV**
   - Locație: `.venv\` (în directorul proiectului)
   - Tool folosit: `uv` (versiunea 0.9.2)
   - Python: 3.12.10

3. **✓ Dependențe instalate și actualizate**
   - pandas: 2.3.3 (actualizat de la 1.5.3)
   - dash: 3.2.0 (actualizat de la 2.14.2)
   - plotly: 6.4.0 (actualizat de la 5.18.0)
   - kaleido: 1.2.0 (actualizat de la 0.2.1)
   - watchdog: 6.0.0 (actualizat de la 3.0.0)

---

## 🚀 Cum să pornești aplicația

### Metoda 1: Folosind scriptul BAT (recomandat)
```batch
start_server.bat
```
Dublu-click pe fișierul `start_server.bat` sau rulează-l în terminal.

### Metoda 2: Manual din terminal
```powershell
cd "C:\Users\viore\Desktop\programe\pulsoximetrie"
.\.venv\Scripts\activate
python run.py
```

---

## 🔄 Dacă muti proiectul pe ÎNCĂ un calculator nou

### Pași de urmat:

1. **Verifică că ai `uv` instalat:**
   ```powershell
   uv --version
   ```
   Dacă nu este instalat: https://github.com/astral-sh/uv

2. **Creează virtual environment:**
   ```powershell
   cd cale\catre\proiect
   uv venv
   ```

3. **Instalează dependențele:**
   ```powershell
   uv pip install -r requirements.txt
   ```

4. **Pornește aplicația:**
   ```batch
   start_server.bat
   ```

---

## 📝 Note importante

- **Virtual environment** (`.venv`) NU trebuie inclus în git/backup
- **requirements.txt** conține toate dependențele necesare
- Aplicația rulează local la: http://127.0.0.1:8050/
- Pentru oprire: apasă `CTRL+C` în terminal sau rulează `stop_server.bat`

---

## 🛠️ Troubleshooting

### Problema: "Virtual environment nu a fost gasit"
**Soluție:**
```powershell
uv venv
uv pip install -r requirements.txt
```

### Problema: "uv nu este recunoscut"
**Soluție:**
Instalează `uv`: https://github.com/astral-sh/uv
sau folosește `pip`:
```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### Problema: "Portul 8050 este ocupat"
**Soluție:**
Rulează `stop_server.bat` pentru a opri serverul vechi.

---

## 📂 Structura Proiectului

```
pulsoximetrie/
├── .venv/                    # Virtual environment (NU copii în backups!)
├── intrare/                  # Folderul pentru fișiere CSV de intrare
├── output/                   # Folderul pentru rezultate generate
│   └── LOGS/                 # Log-uri aplicație
├── assets/                   # Fișiere CSS și stiluri
├── *.py                      # Modulele aplicației
├── requirements.txt          # Lista de dependențe
├── start_server.bat          # Script pentru pornire
└── stop_server.bat           # Script pentru oprire
```

---

**Data ultimei configurări:** 11 noiembrie 2025
**Calculator:** viore (Python 3.12.10)
**Tool:** uv 0.9.2


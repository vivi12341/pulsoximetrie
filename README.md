# 📊 Analizator Pulsoximetrie Nocturnă

Aplicație web interactivă pentru analizarea datelor de pulsoximetrie din fișiere CSV.

## 🚀 Start Rapid

```bash
# Pornește aplicația
start_server.bat

# Sau manual:
.\.venv\Scripts\activate
python run.py
```

Accesează: **http://127.0.0.1:8050/**

---

## 📋 Funcționalități

### 🔍 **Vizualizare Interactivă**
- Încărcare fișiere CSV
- Grafice interactive cu zoom și pan
- Date SaO2 și Puls afișate simultan
- Scalare dinamică grosime linie la zoom

### 🎨 **Configurare Culori**
- Profile de culori personalizabile (JSON)
- Gradient complex sau culori simple
- Switch rapid între profile

### 📦 **Procesare în Lot (Batch)**
- Procesare multiplă fișiere CSV
- Generare automată grafice JPG
- Ferestre de timp configurabile (implicit 30 min)
- Nume intuitive pentru foldere și imagini

---

## 🛠️ Instalare

### Cerințe
- Python 3.12+ (testat pe 3.12.10)
- UV package manager (recomandat) sau pip

### Setup

#### Folosind UV (recomandat - rapid):
```bash
# Instalează UV: https://github.com/astral-sh/uv

# Creează environment
uv venv

# Instalează dependencies
uv pip install -r requirements.txt
```

#### Folosind pip (alternativă):
```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

---

## 📁 Structura Proiect

```
pulsoximetrie/
├── .venv/                    # Virtual environment (nu include în git!)
├── intrare/                  # 📥 Pune aici fișierele CSV pentru vizualizare
├── output/                   # 📤 Rezultate generate (imagini, logs)
│   └── LOGS/
│       └── app_activity.log  # Log-uri aplicație
├── bach data/                # Date pentru procesare în lot
├── bach output/              # Rezultate batch
├── assets/
│   └── style.css             # Stiluri custom aplicație
├── run.py                    # 🚀 Entry point - pornește aplicația
├── app_instance.py           # Instanță Dash
├── app_layout.py             # Layout UI
├── callbacks.py              # Logică interactivitate
├── config.py                 # Configurări generale
├── data_parser.py            # Parser CSV
├── plot_generator.py         # Generator grafice
├── batch_processor.py        # Procesare în lot
├── logger_setup.py           # Sistem logging
├── colors_config.json        # 🎨 Configurare culori
├── requirements.txt          # Dependencies Python
├── start_server.bat          # Script pornire Windows
└── stop_server.bat           # Script oprire Windows
```

---

## 🎯 Utilizare

### 1. Vizualizare Interactivă

1. Pornește aplicația: `start_server.bat`
2. Deschide browser: http://127.0.0.1:8050/
3. Tab **"Vizualizare Interactivă"**
4. Încarcă fișier CSV
5. Explorează graficul (zoom, pan, hover pentru detalii)

### 2. Procesare în Lot (Batch)

1. Pune fișierele CSV în `bach data/`
2. Tab **"Procesare în Lot"**
3. Configurează:
   - Folder intrare: `bach data`
   - Folder ieșire: `bach output`
   - Durată fereastră: `30` minute
4. Click **"Pornește Procesarea"**
5. Rezultatele apar în `bach output/`

### 3. Personalizare Culori

Editează `colors_config.json`:

```json
{
  "active_profile": "simple",
  "profiles": {
    "simple": {
      "colorscale_min": 75,
      "colorscale_max": 99,
      "colorscale": [
        [0.0, "#D62728"],  // Roșu
        [1.0, "#2CA02C"]   // Verde
      ]
    }
  }
}
```

Repornește aplicația pentru a aplica schimbările.

---

## 📊 Format Date CSV

Aplicația acceptă fișiere CSV cu următoarele coloane:

```csv
CheckmeFlag,Date,Time,SpO2,PR
RECORD,2024-12-05,23:30:00,95,72
RECORD,2024-12-05,23:30:01,96,73
...
```

---

## 🧪 Testare

Verifică că totul funcționează:

```bash
# Test import pachete
.\.venv\Scripts\python.exe -c "import pandas, dash, plotly; print('OK')"

# Test încărcare aplicație
.\.venv\Scripts\python.exe -c "from app_instance import app; print('OK')"
```

---

## 🐛 Troubleshooting

### Aplicația nu pornește
```bash
# Verifică că virtual environment există
dir .venv

# Dacă nu există, recrează:
uv venv
uv pip install -r requirements.txt
```

### Portul 8050 ocupat
```bash
# Oprește serverul vechi
stop_server.bat
```

### Erori la import pachete
```bash
# Reinstalează dependencies
uv pip install --force-reinstall -r requirements.txt
```

---

## 📝 Dependencies

| Pachet | Versiune | Utilizare |
|--------|----------|-----------|
| pandas | ≥2.0.0 | Procesare date CSV |
| dash | ≥2.14.0 | Framework web interactiv |
| plotly | ≥5.18.0 | Grafice interactive |
| kaleido | ≥0.2.1 | Export grafice JPG |
| watchdog | ≥3.0.0 | Monitorizare fișiere |

---

## 🔄 Migrare pe alt calculator

Citește: **[SETUP_CALCULATOR_NOU.md](SETUP_CALCULATOR_NOU.md)**

Pași rapizi:
1. Copiază proiectul (FĂRĂ `.venv/`)
2. `uv venv`
3. `uv pip install -r requirements.txt`
4. `start_server.bat`

---

## 📚 Documentație Extinsă

- **[MIGRARE_COMPLETATA.md](MIGRARE_COMPLETATA.md)** - Istoric migrare și teste
- **[SETUP_CALCULATOR_NOU.md](SETUP_CALCULATOR_NOU.md)** - Ghid setup complet
- **[GHID_CULORI.md](GHID_CULORI.md)** - Configurare avansată culori
- **[ZOOM_FEATURE_GUIDE.md](ZOOM_FEATURE_GUIDE.md)** - Funcționalitate zoom dinamic

---

## 🎨 Features Avansate

### Zoom Dinamic
- Grosimea liniilor se adaptează automat la nivelul de zoom
- Vizibilitate optimă la orice nivel de detaliu
- Configurabil în `config.py` (ZOOM_SCALE_CONFIG)

### Nume Intuitive Batch
- Foldere: `02mai2025_00h25-06h37_Aparat1442`
- Imagini: `Aparat1442_00h25m-00h55m.jpg`
- Detecție automată teste peste miezul nopții

### Logging Complet
- Toate operațiile sunt înregistrate
- Log-uri în `output/LOGS/app_activity.log`
- Nivele: INFO, WARNING, ERROR, CRITICAL

---

## 🤝 Configurare Dezvoltare

```bash
# Activează environment
.\.venv\Scripts\activate

# Pornește în mod debug
python run.py
# Debug mode: ON (hot-reload, dev tools UI)
```

Aplicația va reporni automat la modificări de cod.

---

## ⚙️ Configurări Avansate

Editează `config.py`:

```python
# Rezoluție imagini batch
IMAGE_RESOLUTION = {"width": 1280, "height": 720}

# Durată fereastră implicită (minute)
DEFAULT_WINDOW_MINUTES = 30

# Scalare zoom dinamic
ZOOM_SCALE_CONFIG = {
    "min_scale": 0.50,      # 50% grosime la zoom out maxim
    "max_scale": 1.00,      # 100% grosime la zoom in maxim
    "base_line_width": 3,   # Grosime de bază linie SaO2
    "base_marker_size": 4,  # Dimensiune de bază markeri
}
```

---

## 📄 Licență

Acest proiect este pentru uz intern/personal.

---

## 📧 Contact / Suport

Pentru probleme sau întrebări, consultă fișierele de documentație sau verifică log-urile în `output/LOGS/`.

---

**Versiune:** 4.0 (cu suport culori JSON și zoom dinamic)  
**Ultima actualizare:** 11 noiembrie 2025  
**Python:** 3.12.10  
**Status:** ✅ Funcțional și testat


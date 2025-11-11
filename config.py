# ==============================================================================
# config.py (VERSIUNEA 4.0 - CONFIGURARE CULORI JSON)
# ------------------------------------------------------------------------------
# ROL: Centralizează TOATE constantele, căile și setările de stil.
#
# MODIFICĂRI CHEIE (v4.0):
#  - ADĂUGAT: Suport pentru configurare culori din fișier JSON extern
#  - FLEXIBILITATE: Posibilitatea de a schimba rapid între profile de culori
#    (gradient complex sau doar 2 culori simple)
# ==============================================================================
import os
import json

# --- Setări Generale ale Aplicației ---
OUTPUT_DIR = "output"
LOGS_DIR = os.path.join(OUTPUT_DIR, "LOGS")

# --- Setări pentru Procesarea în Lot (Batch) ---
DEFAULT_WINDOW_MINUTES = 30
IMAGE_RESOLUTION = {"width": 1280, "height": 720}

# --- Culorile de bază pentru gradient (paletă rafinată) ---
SPO2_COLOR_STOPS = {
    85: '#800080',  # Violet pentru valori foarte joase
    90: '#d73027',  # Roșu
    95: '#2CA02C',  # Verde vibrant
    99: '#006400',  # Verde închis pentru valori excelente
}

# --- Funcție pentru Încărcarea Configurației de Culori din JSON ---
def load_color_config():
    """
    Încarcă configurația de culori din fișierul colors_config.json.
    Returnează profilul activ de culori.
    """
    colors_file = "colors_config.json"
    
    # Valori implicite în caz de eroare
    default_config = {
        "colorscale_min": 75,
        "colorscale_max": 99,
        "colorscale": [
            [0.0, "#D62728"],  # Roșu
            [1.0, "#2CA02C"]   # Verde
        ]
    }
    
    try:
        if os.path.exists(colors_file):
            with open(colors_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                active_profile = config_data.get("active_profile", "simple")
                profile = config_data.get("profiles", {}).get(active_profile, default_config)
                return profile
        else:
            print(f"AVERTISMENT: Fișierul '{colors_file}' nu există. Se folosesc culorile implicite.")
            return default_config
    except Exception as e:
        print(f"EROARE la citirea fișierului '{colors_file}': {e}. Se folosesc culorile implicite.")
        return default_config

# Încărcăm configurația de culori
_COLOR_CONFIG = load_color_config()

# --- Configurare Zoom Dinamic (Scalare Grosime Linie) ---
ZOOM_SCALE_CONFIG = {
    "min_scale": 0.50,  # 50% grosime la zoom out maxim (ajustat de la 30%)
    "max_scale": 1.00,  # 100% grosime la zoom in maxim
    "base_line_width": 3,    # Grosimea de bază pentru linia SaO2
    "base_marker_size": 4,   # Dimensiunea de bază pentru markeri
}

# --- Definiția "Standardului de Aur" pentru Stilul Graficelor ---
GOLDEN_STYLE = {
    "layout": {
        "plot_bgcolor": "white",
        "paper_bgcolor": "white",
        "title_font_size": 18,
        "font": {"family": "Arial", "size": 14, "color": "black"}
    },
    "axes": {
        "yaxis_spo2": {
            "title": "SaO2 (%)",
            "range": [70, 100],
            "color": "black",
            "gridcolor": "#EAEAEA",
            "dtick": 5  # ADAUGAT: Specifică o linie de grid la fiecare 5 unități
        },
        "yaxis_pulse": {"title": "Puls (bpm)", "range": None, "color": "#E85F5C"},
        "xaxis": {"title": "Timp", "gridcolor": "#EAEAEA"}
    },
    "traces": {
        "spo2": {
            "name": "SaO2",
            "interpolation_factor": 30, # MODIFICAT: Triplarea punctelor
            "marker_size": 4,           # MODIFICAT: Reducere cu 20% (de la 5)
            "line_width": 3,            # MODIFICAT: Lățime înjumătățită (de la ~6)
            # Culorile sunt încărcate dinamic din colors_config.json
            "colorscale_min": _COLOR_CONFIG["colorscale_min"],
            "colorscale_max": _COLOR_CONFIG["colorscale_max"],
            "colorscale": _COLOR_CONFIG["colorscale"]
        },
        "pulse": {
            "name": "Puls",
            "color": "#E85F5C",
            "width": 2
        }
    },
    "legend": {
        "orientation": "h",
        "yanchor": "bottom", "y": 1.02,
        "xanchor": "right", "x": 1
    }
}
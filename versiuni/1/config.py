# ==============================================================================
# config.py (VERSIUNEA FINALĂ - SINCRONIZATĂ)
# ------------------------------------------------------------------------------
# ROL: Centralizează TOATE constantele, căile și setările de stil.
#
# MODIFICĂRI CHEIE:
#  - Structura 'layout' a fost actualizată pentru a grupa toate setările de
#    font sub o singură cheie 'font', pentru compatibilitate cu plot_generator.
# ==============================================================================

import os

# --- Setări Generale ale Aplicației ---
OUTPUT_DIR = "output"
LOGS_DIR = os.path.join(OUTPUT_DIR, "LOGS")

# --- Setări pentru Procesarea în Lot (Batch) ---
DEFAULT_WINDOW_MINUTES = 30
IMAGE_RESOLUTION = {
    "width": 1280,
    "height": 720
}

# --- Definiția "Standardului de Aur" pentru Stilul Graficelor ---
GOLDEN_STYLE = {
    "layout": {
        "plot_bgcolor": "white",
        "paper_bgcolor": "white",
        "title_font_size": 18,
        # --- STRUCTURA CORECTATĂ AICI ---
        "font": {
            "family": "Arial",
            "size": 14,
            "color": "black"
        }
    },
    "axes": {
        "yaxis_spo2": {
            "title": "SaO2 (%)",
            "range": [70, 100],
            "color": "black",
            "gridcolor": "#EAEAEA"
        },
        "yaxis_pulse": {
            "title": "Puls (bpm)",
            "range": None,
            "color": "#E85F5C",
        },
        "xaxis": {
            "title": "Timp",
            "gridcolor": "#EAEAEA"
        }
    },
    "traces": {
        "pulse": {
            "name": "Puls",
            "color": "#E85F5C",
            "width": 2
        }
    },
    "legend": {
        "orientation": "h",
        "yanchor": "bottom",
        "y": 1.02,
        "xanchor": "right",
        "x": 1
    }
}
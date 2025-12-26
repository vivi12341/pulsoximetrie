# ==============================================================================
# app_layout_new.py (VERSIUNEA 3.1 - REFACTORIZED & MODULAR)
# ------------------------------------------------------------------------------
# ROL: Punctul de asamblare pentru layout-uri.
#      Delegă logica de afișare către `layout_partials/`.
#
# ANALIZĂ ECHIPĂ (V3.0 Fixes):
# - [Architect] Logica separată în module.
# - [Designer] CSS extern (`assets/medical_theme.css`).
# - [Psychologist] Mesaje de eroare empatice.
# ==============================================================================

from dash import html
from flask import request
from flask_login import current_user
from logger_setup import logger
import patient_links

# Import layouts modulare
from layout_partials.medical_layout import get_medical_layout
from layout_partials.patient_layout import get_patient_layout, get_error_layout
from callbacks_medical import create_login_prompt

def get_layout():
    """
    Returnează layout-ul corespunzător bazat pe context (medic sau pacient).
    Router logic centralizat.
    """
    # 1. Verifică dacă există token în URL (PACIENT)
    token = request.args.get('token')
    
    logger.info(f"[LAYOUT ROUTER] Path: {request.path} | Token present: {token is not None}")
    
    if token:
        # Validare token pacient
        if patient_links.validate_token(token):
            logger.info(f"[LAYOUT ROUTER] ✅ Token valid -> Patient Layout")
            return get_patient_layout()
        else:
            logger.warning(f"[LAYOUT ROUTER] ❌ Token invalid -> Error Layout")
            return get_error_layout()
    
    # 2. Fără token -> Verifică autentificare (MEDIC)
    if current_user.is_authenticated:
        logger.info(f"[LAYOUT ROUTER] 👨‍⚕️ Medic autentificat -> Medical Layout")
        return get_medical_layout()
    else:
        logger.info(f"[LAYOUT ROUTER] 🔒 Neautentificat -> Login Prompt")
        return create_login_prompt()

# Backward compatibility
layout = get_layout

# HOTFIX: Nu mai exportăm medical_layout/patient_layout static
# MOTIV: Acestea se execută la import time când current_user este None
# SOLUȚIE: Doar funcția get_layout() se folosește (se execută per-request)
# medical_layout = get_medical_layout()  # ❌ REMOVED - caused AttributeError
# patient_layout = get_patient_layout()  # ❌ REMOVED - not needed



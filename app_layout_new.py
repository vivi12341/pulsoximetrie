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
    logger.info("="*100)
    logger.info("🔀 [ROUTING] get_layout() START")
    logger.info("="*100)
    
    # [LOG 1-5] Request details
    logger.info(f"📍 [LOG 1] Request path: {request.path}")
    logger.info(f"📍 [LOG 2] Request full URL: {request.url}")
    logger.info(f"📍 [LOG 3] Request args: {dict(request.args)}")
    logger.info(f"📍 [LOG 4] Request method: {request.method}")
    user_agent = request.headers.get('User-Agent', 'N/A')
    logger.info(f"📍 [LOG 5] User-Agent: {user_agent[:100]}...")
    
    # 1. Verifică dacă există token în URL (PACIENT)
    token = request.args.get('token')
    logger.info(f"🔑 [LOG 6] Token extracted from URL: {'YES - ' + token[:8] + '...' if token else 'NO (None)'}")
    
    if token:
        logger.info(f"🔍 [LOG 7] TOKEN DETECTED - Starting validation...")
        # Validare token pacient
        is_valid = patient_links.validate_token(token)
        logger.info(f"✅ [LOG 8] Token validation result: {is_valid}")
        
        # Check if user is authenticated (ADMIN viewing patient data)
        is_auth = current_user.is_authenticated
        logger.info(f"👤 [LOG 9] User authenticated status: {is_auth}")
        
        if is_auth:
            logger.info(f"👨‍⚕️ [LOG 10] ADMIN with token → Returning Patient Layout for Verification")
            logger.info(f"👨‍⚕️ [LOG 11] Admin is viewing specific patient data: {token[:8]}...")
            # Pentru "Test in browser", adminul trebuie să vadă ce vede pacientul
            return get_patient_layout()
        else:
            logger.info(f"👤 [LOG 12] PATIENT (unauthenticated) with token")
            if is_valid:
                logger.info(f"✅ [TRACE-DATA] [LOG 13] Valid token → Returning Patient Layout")
                return get_patient_layout()
            else:
                logger.warning(f"❌ [LOG 14] Invalid/Inactive token → Returning Error Layout")
                return get_error_layout()
    
    # 2. Fără token → Verifică autentificare (MEDIC)
    logger.info(f"[LOG 15] NO TOKEN in URL - checking authentication...")
    if current_user.is_authenticated:
        logger.info(f"👨‍⚕️ [LOG 16] Authenticated user (no token) → Medical Layout")
        return get_medical_layout()
    else:
        logger.info(f"🔒 [LOG 17] Unauthenticated user (no token) → Login Prompt")
        return create_login_prompt()

# Backward compatibility
layout = get_layout

# HOTFIX: Nu mai exportăm medical_layout/patient_layout static
# MOTIV: Acestea se execută la import time când current_user este None
# SOLUȚIE: Doar funcția get_layout() se folosește (se execută per-request)
# medical_layout = get_medical_layout()  # ❌ REMOVED - caused AttributeError
# patient_layout = get_patient_layout()  # ❌ REMOVED - not needed



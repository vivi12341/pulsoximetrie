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

from dash import html, dcc  # [HOTFIX v3] Added dcc for dcc.Store and dcc.Location
from flask import request
from flask_login import current_user
from logger_setup import logger
from datetime import datetime  # For diagnostic logging
import patient_links

# Import layouts modulare
from layout_partials.medical_layout import get_medical_layout
from layout_partials.patient_layout import get_patient_layout, get_error_layout
from callbacks.medical_callbacks import create_login_prompt

def get_layout():
    """
    Returnează layout-ul corespunzător bazat pe context (medic sau pacient).
    Router logic centralizat.
    """
    # [CRITICAL DIAGNOSTIC] Track EVERY execution
    logger.critical("🚨"*50)
    logger.critical("🚨 [LAYOUT_DEBUG] get_layout() FUNCTION CALLED!")
    logger.critical(f"🚨 [LAYOUT_DEBUG] Timestamp: {datetime.now().isoformat()}")
    logger.critical("🚨"*50)
    
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
    
    # [CRITICAL FIX] Token extraction from request.args doesn't work for Dash internal requests (/_dash-layout)
    # SOLUTION: Create a global dcc.Store that captures token client-side from window.location
    # The store will be populated via clientside callback
    
    # Return a unified layout with token-store and conditional rendering
    
    return html.Div([
        # Global token store - populated client-side
        dcc.Store(id='global-token-store', storage_type='memory'),
        dcc.Location(id='url-location', refresh=False),
        
        # Conditional content - will be populated by callback based on token presence
        html.Div(id='app-content-router')
    ])

# Backward compatibility
layout = get_layout

# HOTFIX: Nu mai exportăm medical_layout/patient_layout static
# MOTIV: Acestea se execută la import time când current_user este None
# SOLUȚIE: Doar funcția get_layout() se folosește (se execută per-request)
# medical_layout = get_medical_layout()  # ❌ REMOVED - caused AttributeError
# patient_layout = get_patient_layout()  # ❌ REMOVED - not needed



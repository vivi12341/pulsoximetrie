"""
callbacks_routing.py - Application Router Logic

[CRITICAL FIX] Patient token links
Root cause: request.args doesn't work for Dash internal requests (/_dash-layout)
Solution: Client-side token extraction + server-side routing

Pattern: Dash-native, GDPR-compliant, no cookies/session
Voted: 27/30 by multi-disciplinary team
"""

from dash import Input, Output, clientside_callback, callback
from flask_login import current_user
from logger_setup import logger

# Import layouts - [HOTFIX] Corrected import paths
from layout_partials.patient_layout import get_patient_layout, get_error_layout
from layout_partials.medical_layout import get_medical_layout, create_login_prompt

# Import validation
from patient_links import validate_token


# ============================================================================
# CLIENTSIDE CALLBACK - Extract Token from URL
# ============================================================================
# This runs in browser JavaScript - extracts token from window.location
# No server round-trip needed, instant execution

clientside_callback(
    """
    function(href) {
        // Safety check
        if (!href) {
            console.log('[TOKEN_EXTRACT] No href provided');
            return null;
        }
        
        try {
            const url = new URL(href);
            const token = url.searchParams.get('token');
            
            if (token) {
                console.log('[TOKEN_EXTRACT] ✅ Token found:', token.substring(0, 8) + '...');
                console.log('[TOKEN_EXTRACT] Full token length:', token.length);
            } else {
                console.log('[TOKEN_EXTRACT] ℹ️  No token in URL');
            }
            
            return token;
        } catch(e) {
            console.error('[TOKEN_EXTRACT] ❌ ERROR:', e);
            return null;
        }
    }
    """,
    Output('global-token-store', 'data'),
    Input('url-location', 'href'),
    prevent_initial_call=False  # CRITICAL - must run on page load!
)


# ============================================================================
# SERVER CALLBACK - Route Application Based on Token
# ============================================================================

@callback(
    Output('app-content-router', 'children'),
    Input('global-token-store', 'data'),
    prevent_initial_call=False  # CRITICAL - must run on page load!
)
def route_application(token):
    """
    Routes user to appropriate layout based on token and authentication status.
    
    Priority:
    1. Token present → Patient or Error layout (based on validation)
    2. No token + authenticated → Medical dashboard
    3. No token + not authenticated → Login prompt
    
    Args:
        token: Patient UUID from URL (extracted client-side) or None
        
    Returns:
        Dash layout component
    """
    logger.critical("=" * 100)
    logger.critical("🔀 [ROUTER] *** APPLICATION ROUTING START ***")
    logger.critical(f"🔀 [ROUTER] Token from store: {token[:8] + '...' if token else 'None'}")
    logger.critical(f"🔀 [ROUTER] User authenticated: {current_user.is_authenticated}")
    logger.critical("=" * 100)
    
    # ========================================================================
    # PRIORITY 1: Patient Token Link
    # ========================================================================
    if token:
        logger.critical(f"🔑 [ROUTER] PATIENT TOKEN DETECTED")
        logger.critical(f"🔑 [ROUTER] Token value: {token[:8]}...")
        logger.critical(f"🔑 [ROUTER] Starting validation...")
        
        try:
            is_valid = validate_token(token)
            logger.critical(f"🔑 [ROUTER] Validation result: {is_valid}")
            
            if is_valid:
                logger.critical(f"✅ [ROUTER] VALID TOKEN → Rendering PATIENT LAYOUT")
                logger.critical(f"✅ [ROUTER] Patient will see their data")
                logger.critical("=" * 100)
                return get_patient_layout()
            else:
                logger.critical(f"❌ [ROUTER] INVALID TOKEN → Rendering ERROR LAYOUT")
                logger.critical(f"❌ [ROUTER] Token not found or inactive")
                logger.critical("=" * 100)
                return get_error_layout()
                
        except Exception as e:
            logger.critical(f"💥 [ROUTER] EXCEPTION during validation: {e}", exc_info=True)
            logger.critical("=" * 100)
            return get_error_layout()
    
    # ========================================================================
    # PRIORITY 2: Authenticated Medical User (No Token)
    # ========================================================================
    if current_user.is_authenticated:
        logger.critical(f"👨‍⚕️ [ROUTER] AUTHENTICATED MEDICAL USER → Rendering MEDICAL LAYOUT")
        logger.critical(f"👨‍⚕️ [ROUTER] User: {current_user.username if hasattr(current_user, 'username') else 'Unknown'}")
        logger.critical("=" * 100)
        return get_medical_layout()
    
    # ========================================================================
    # PRIORITY 3: Unauthenticated User, No Token
    # ========================================================================
    logger.critical(f"🔒 [ROUTER] UNAUTHENTICATED, NO TOKEN → Rendering LOGIN PROMPT")
    logger.critical(f"🔒 [ROUTER] User needs to log in")
    logger.critical("=" * 100)
    return create_login_prompt()


# ============================================================================
# Module Initialization Log
# ============================================================================
logger.info("✅ callbacks_routing.py initialized - Router callbacks registered")
logger.info("   - Clientside callback: URL token extraction")
logger.info("   - Server callback: Application routing logic")

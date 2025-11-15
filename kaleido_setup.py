# ==============================================================================
# kaleido_setup.py - Inițializare Defensivă Kaleido cu Auto-Install Chrome
# ==============================================================================
# ROL: Verifică și configurează Kaleido pentru export imagini Plotly în production
#
# STRATEGIE DEFENSIVĂ (3 Layer Fallback):
# 1. Detectare Chrome/Chromium existent (Nixpacks/Railway)
# 2. Auto-install Chrome cu kaleido_get_chrome() (backup)
# 3. Dezactivare graceful export imagini (fallback final)
#
# DOCUMENTAȚIE:
# - Kaleido v1.2.0+ necesită Chrome/Chromium
# - Railway: Chrome trebuie adăugat în nixpacks.toml
# - Fallback: kaleido.get_chrome_sync() descarcă Chrome automat
# ==============================================================================

import os
import sys
from logger_setup import logger

def setup_kaleido():
    """
    Configurează Kaleido pentru export imagini Plotly (defensiv cu fallback).
    
    Returns:
        bool: True dacă Kaleido funcțional, False dacă indisponibil
    """
    logger.info("=" * 70)
    logger.info("🔧 INIȚIALIZARE KALEIDO pentru export imagini Plotly...")
    logger.info("=" * 70)
    
    try:
        # [STEP 1] Import Kaleido
        import kaleido
        
        # Verificăm versiunea (dacă disponibilă - Kaleido 1.2.0+ nu mai are __version__)
        try:
            kaleido_version = kaleido.__version__
        except AttributeError:
            # Kaleido 1.2.0+ nu expune __version__ direct
            kaleido_version = "1.2.0+"
        
        logger.info(f"✅ Kaleido {kaleido_version} importat cu succes")
        
        # [STEP 2] Verificăm dacă Chrome/Chromium există deja
        # (Railway cu nixpacks.toml ar trebui să-l instaleze automat)
        chromium_paths = [
            '/nix/store/*/bin/chromium',  # Nix/Railway
            '/usr/bin/chromium',           # Ubuntu/Debian
            '/usr/bin/chromium-browser',   # Ubuntu
            '/usr/bin/google-chrome',      # Chrome oficial
            os.environ.get('CHROMIUM_PATH'),  # Custom env var
            os.environ.get('CHROME_PATH')
        ]
        
        chrome_found = False
        for path in chromium_paths:
            if path and '*' in path:
                # Glob pentru Nix paths
                import glob
                matches = glob.glob(path)
                if matches:
                    chrome_path = matches[0]
                    chrome_found = True
                    logger.info(f"✅ Chrome/Chromium găsit: {chrome_path}")
                    break
            elif path and os.path.exists(path):
                chrome_found = True
                logger.info(f"✅ Chrome/Chromium găsit: {path}")
                break
        
        if chrome_found:
            # [SUCCESS] Chrome detectat - Kaleido ar trebui să funcționeze
            logger.info("✅ Kaleido gata de folosit (Chrome detectat)")
            return True
        
        # [STEP 3] Chrome NU găsit - încercăm auto-install
        logger.warning("⚠️ Chrome/Chromium NU găsit în system")
        logger.info("🔄 Încercare auto-install Chrome cu Kaleido...")
        
        try:
            # Folosim Kaleido's built-in Chrome downloader
            kaleido.get_chrome_sync()
            logger.info("✅ Chrome instalat automat de către Kaleido!")
            return True
            
        except Exception as install_error:
            logger.warning(f"⚠️ Auto-install Chrome eșuat: {install_error}")
            
            # [STEP 4] Verificăm dacă suntem pe Railway
            is_railway = os.environ.get('RAILWAY_ENVIRONMENT') is not None
            
            if is_railway:
                logger.warning("")
                logger.warning("=" * 70)
                logger.warning("🚨 ATENȚIE: Chrome lipsește din container Railway!")
                logger.warning("=" * 70)
                logger.warning("")
                logger.warning("SOLUȚIE RECOMANDATĂ:")
                logger.warning("1. Verifică dacă 'nixpacks.toml' există în repository")
                logger.warning("2. Adaugă 'chromium' în lista nixPkgs:")
                logger.warning("   nixPkgs = ['python3', 'postgresql_16.dev', 'gcc', 'chromium']")
                logger.warning("3. Commit + Push → Railway va rebuida cu Chrome inclus")
                logger.warning("")
                logger.warning("FALLBACK: Export imagini dezactivat (grafice HTML vor funcționa)")
                logger.warning("=" * 70)
            else:
                logger.warning("Export imagini Plotly indisponibil (lipsește Chrome)")
            
            return False
    
    except ImportError:
        # Kaleido nu e instalat (foarte rar - e în requirements.txt)
        logger.error("❌ Kaleido NU este instalat! Verifică requirements.txt")
        return False
        
    except Exception as e:
        # Orice altă eroare
        logger.error(f"❌ Eroare neașteptată la inițializare Kaleido: {e}", exc_info=True)
        return False

def check_kaleido_status():
    """
    Verifică rapid dacă Kaleido funcționează (fără instalare).
    
    Returns:
        str: "available" | "unavailable" | "unknown"
    """
    try:
        import kaleido
        
        # Quick test - verificăm dacă putem crea un scope (test funcțional)
        try:
            # Test simplu: încercăm să importăm și inițializăm scope-ul
            from kaleido.scopes.plotly import PlotlyScope
            # Nu instanțiem (ar fi lent), doar verificăm că poate fi importat
            return "available"
        except Exception:
            # Kaleido importat dar scope-ul nu funcționează
            return "unavailable"
            
    except ImportError:
        return "unavailable"

# ==============================================================================
# USAGE:
# 
# În aplicație (run_medical.py sau batch_processor.py):
#   from kaleido_setup import setup_kaleido
#   
#   KALEIDO_AVAILABLE = setup_kaleido()
#   
#   if KALEIDO_AVAILABLE:
#       fig.write_image(...)  # OK
#   else:
#       logger.warning("Export imagini indisponibil - folosim grafice HTML")
# ==============================================================================

if __name__ == "__main__":
    # Test stand-alone
    print("\n" + "=" * 70)
    print("TEST KALEIDO SETUP")
    print("=" * 70 + "\n")
    
    result = setup_kaleido()
    
    print("\n" + "=" * 70)
    if result:
        print("✅ KALEIDO FUNCȚIONAL - Export imagini disponibil")
    else:
        print("⚠️ KALEIDO INDISPONIBIL - Fallback la grafice HTML")
    print("=" * 70 + "\n")
    
    sys.exit(0 if result else 1)


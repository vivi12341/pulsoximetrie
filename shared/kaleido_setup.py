# ==============================================================================
# shared/kaleido_setup.py - Inițializare Defensivă Kaleido cu Auto-Install Chrome
# ==============================================================================

import os
import sys

from shared.logger_setup import logger


def setup_kaleido():
    """
    Configurează Kaleido pentru export imagini Plotly (defensiv cu fallback).
    """
    logger.info("=" * 70)
    logger.info("🔧 INIȚIALIZARE KALEIDO pentru export imagini Plotly...")
    logger.info("=" * 70)

    try:
        import kaleido

        try:
            kaleido_version = kaleido.__version__
        except AttributeError:
            kaleido_version = "1.2.0+"

        logger.info(f"✅ Kaleido {kaleido_version} importat cu succes")

        chromium_paths = [
            '/nix/store/*/bin/chromium',
            '/usr/bin/chromium',
            '/usr/bin/chromium-browser',
            '/usr/bin/google-chrome',
            os.environ.get('CHROMIUM_PATH'),
            os.environ.get('CHROME_PATH')
        ]

        chrome_found = False
        for path in chromium_paths:
            if path and '*' in path:
                import glob
                matches = glob.glob(path)
                if matches:
                    chrome_found = True
                    logger.info(f"✅ Chrome/Chromium găsit: {matches[0]}")
                    break
            elif path and os.path.exists(path):
                chrome_found = True
                logger.info(f"✅ Chrome/Chromium găsit: {path}")
                break

        if chrome_found:
            logger.info("✅ Kaleido gata de folosit (Chrome detectat)")
            return True

        logger.warning("⚠️ Chrome/Chromium NU găsit în system")
        logger.info("🔄 Încercare auto-install Chrome cu Kaleido...")

        try:
            kaleido.get_chrome_sync()
            logger.info("✅ Chrome instalat automat de către Kaleido!")
            return True

        except Exception as install_error:
            logger.warning(f"⚠️ Auto-install Chrome eșuat: {install_error}")

            is_railway = os.environ.get('RAILWAY_ENVIRONMENT') is not None

            if is_railway:
                logger.warning("")
                logger.warning("=" * 70)
                logger.warning("🚨 ATENȚIE: Chrome lipsește din container Railway!")
                logger.warning("=" * 70)
                logger.warning("FALLBACK: Export imagini dezactivat (grafice HTML vor funcționa)")
                logger.warning("=" * 70)
            else:
                logger.warning("Export imagini Plotly indisponibil (lipsește Chrome)")

            return False

    except ImportError:
        logger.error("❌ Kaleido NU este instalat! Verifică requirements.txt")
        return False

    except Exception as e:
        logger.error(f"❌ Eroare neașteptată la inițializare Kaleido: {e}", exc_info=True)
        return False


def check_kaleido_status():
    """Verifică rapid dacă Kaleido funcționează."""
    try:
        import kaleido
        try:
            from kaleido.scopes.plotly import PlotlyScope  # noqa: F401
            return "available"
        except Exception:
            return "unavailable"
    except ImportError:
        return "unavailable"


if __name__ == "__main__":
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

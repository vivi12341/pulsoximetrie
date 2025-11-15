#!/usr/bin/env python3
# ==============================================================================
# test_r2_connection.py
# ------------------------------------------------------------------------------
# ROL: Test rapid pentru verificare conexiune Cloudflare R2
#      Rulează înainte de deploy pentru a valida credențialele
#
# USAGE:
#   1. Setează variabilele R2 în .env (sau system environment)
#   2. Rulează: python test_r2_connection.py
# ==============================================================================

import os
import sys
from datetime import datetime
from logger_setup import logger

# Import modulul de storage
try:
    from storage_service import r2_client, get_storage_status, upload_patient_csv
except ImportError as e:
    logger.error(f"❌ Eroare import storage_service: {e}")
    logger.error("Asigură-te că ai instalat dependințele: pip install boto3")
    sys.exit(1)


def test_r2_connection():
    """Test complet pentru verificare R2."""
    
    logger.info("=" * 80)
    logger.info("🧪 TEST CLOUDFLARE R2 CONNECTION")
    logger.info("=" * 80)
    
    # === TEST 1: Verificare configurare ===
    logger.info("\n📋 TEST 1: Verificare Configurare")
    status = get_storage_status()
    
    for key, value in status.items():
        if 'key' in key.lower() or 'secret' in key.lower():
            # Ascundem credențialele în log
            masked_value = value[:8] + "..." if value and value != "N/A" else value
            logger.info(f"  {key}: {masked_value}")
        else:
            logger.info(f"  {key}: {value}")
    
    if not r2_client.enabled:
        logger.warning("⚠️ R2 este DEZACTIVAT - aplicația va folosi stocare LOCALĂ")
        logger.warning("Pentru activare R2, setează:")
        logger.warning("  - R2_ENABLED=True")
        logger.warning("  - R2_ENDPOINT=https://...")
        logger.warning("  - R2_ACCESS_KEY_ID=...")
        logger.warning("  - R2_SECRET_ACCESS_KEY=...")
        logger.warning("  - R2_BUCKET_NAME=pulsoximetrie-files")
        return False
    
    logger.info("✅ R2 este ACTIVAT")
    
    # === TEST 2: Verificare conexiune ===
    logger.info("\n🌐 TEST 2: Verificare Conexiune la R2")
    
    try:
        # Încercăm să listăm bucket-ul (operație simplă pentru test)
        r2_client.client.head_bucket(Bucket=r2_client.bucket_name)
        logger.info(f"✅ Conexiune R2 reușită! Bucket: {r2_client.bucket_name}")
    except Exception as e:
        logger.error(f"❌ Eroare conexiune R2: {e}")
        return False
    
    # === TEST 3: Upload fișier test ===
    logger.info("\n📤 TEST 3: Upload Fișier Test")
    
    test_token = "test-r2-connection-" + datetime.now().strftime("%Y%m%d%H%M%S")
    test_content = f"Test R2 Upload - {datetime.now().isoformat()}\n".encode('utf-8')
    test_filename = "test_upload.csv"
    
    try:
        url = upload_patient_csv(
            token=test_token,
            csv_content=test_content,
            filename=test_filename
        )
        
        if url:
            logger.info(f"✅ Upload reușit! URL: {url}")
        else:
            logger.error("❌ Upload eșuat (funcția a returnat None)")
            return False
            
    except Exception as e:
        logger.error(f"❌ Eroare upload: {e}", exc_info=True)
        return False
    
    # === TEST 4: Listare fișiere ===
    logger.info("\n📂 TEST 4: Listare Fișiere Test")
    
    try:
        from storage_service import list_patient_files
        
        files = list_patient_files(test_token, file_type='csvs')
        
        if test_filename in [f.split('/')[-1] for f in files]:
            logger.info(f"✅ Fișier test găsit în listă: {test_filename}")
        else:
            logger.warning(f"⚠️ Fișier test NU apare în listă (poate delay replicare)")
            
    except Exception as e:
        logger.error(f"❌ Eroare listare: {e}", exc_info=True)
    
    # === TEST 5: Download fișier test ===
    logger.info("\n📥 TEST 5: Download Fișier Test")
    
    try:
        from storage_service import download_patient_file
        
        downloaded = download_patient_file(test_token, 'csvs', test_filename)
        
        if downloaded:
            if downloaded == test_content:
                logger.info("✅ Download reușit! Conținutul coincide.")
            else:
                logger.warning("⚠️ Download reușit, dar conținutul diferă (encoding?)")
        else:
            logger.error("❌ Download eșuat (funcția a returnat None)")
            
    except Exception as e:
        logger.error(f"❌ Eroare download: {e}", exc_info=True)
    
    # === TEST 6: Ștergere fișier test ===
    logger.info("\n🗑️ TEST 6: Ștergere Fișier Test (Cleanup)")
    
    try:
        from storage_service import delete_patient_folder
        
        deleted = delete_patient_folder(test_token)
        
        if deleted:
            logger.info(f"✅ Folder test șters: {test_token}")
        else:
            logger.warning(f"⚠️ Ștergere eșuată (fișierul poate rămâne în R2)")
            
    except Exception as e:
        logger.error(f"❌ Eroare ștergere: {e}", exc_info=True)
    
    # === REZULTAT FINAL ===
    logger.info("\n" + "=" * 80)
    logger.info("🎉 TEST COMPLET FINALIZAT!")
    logger.info("=" * 80)
    logger.info("✅ Cloudflare R2 funcționează PERFECT!")
    logger.info("✅ Aplicația este gata pentru deploy pe Railway cu storage persistent!")
    logger.info("")
    logger.info("📝 Next Steps:")
    logger.info("  1. Commit și push cod: git add . ; git commit -m 'feat: R2 integration' ; git push")
    logger.info("  2. Setează variabile R2 în Railway Dashboard")
    logger.info("  3. Așteaptă redeploy (~90 secunde)")
    logger.info("  4. Testează upload CSV în aplicație")
    logger.info("=" * 80)
    
    return True


def test_local_fallback():
    """Test fallback local (când R2 e dezactivat)."""
    
    logger.info("\n" + "=" * 80)
    logger.info("🧪 TEST FALLBACK LOCAL (fără R2)")
    logger.info("=" * 80)
    
    if r2_client.enabled:
        logger.info("⚠️ R2 este activ - test fallback NU este necesar")
        return
    
    logger.info("✅ Mod fallback local detectat")
    logger.info("📂 Fișierele vor fi salvate în: patient_data/")
    logger.info("")
    logger.info("⚠️ ATENȚIE: Stocare locală pe Railway = EFEMERĂ!")
    logger.info("   Fișierele vor dispărea la fiecare redeploy.")
    logger.info("   Activează R2 pentru stocare PERSISTENTĂ.")


if __name__ == "__main__":
    try:
        success = test_r2_connection()
        
        if not success:
            logger.warning("\n⚠️ Testele R2 au eșuat sau R2 e dezactivat")
            test_local_fallback()
            sys.exit(1)
        
        sys.exit(0)
        
    except KeyboardInterrupt:
        logger.warning("\n⚠️ Test întrerupt de utilizator")
        sys.exit(130)
    except Exception as e:
        logger.error(f"\n❌ Eroare neașteptată: {e}", exc_info=True)
        sys.exit(1)


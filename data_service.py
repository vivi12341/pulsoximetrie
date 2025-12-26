# ==============================================================================
# data_service.py
# ------------------------------------------------------------------------------
# ROL: Serviciu centralizat pentru recuperarea și procesarea datelor pacienților.
#      Unifică logica de acces la fișiere (R2/Local) și parsare CSV.
#
# UTILIZAT DE:
# - callbacks_medical.py (atât pentru Pacient cât și pentru Admin Dashboard)
# ==============================================================================

import os
import pandas as pd
from typing import Optional, Tuple, Any

from logger_setup import logger
import patient_links
from data_parser import parse_csv_data

def get_patient_dataframe(token: str) -> Tuple[Optional[pd.DataFrame], str, str]:
    """
    Recuperează și parsează datele CSV pentru un token dat, abstractizând sursa (R2 vs Local).

    Args:
        token (str): Token-ul unic al pacientului.

    Returns:
        tuple: (df, filename, message)
            - df: DataFrame-ul cu datele parsate sau None dacă eșuează.
            - filename: Numele fișierului original (pentru afișare/descărcare).
            - message: Mesaj descriptiv despre sursă sau eroare (pentru logging/display).
    """
    logger.info(f"💾 [DATA SERVICE] Solicitare date pentru token: {token[:8]}...")
    
    csv_content = None
    csv_filename = "Date Pulsoximetrie"
    storage_type = "unknown"
    
    try:
        # 1. Obținem metadata înregistrărilor
        recordings = patient_links.get_patient_recordings(token)
        
        if not recordings:
             logger.warning(f"⚠️ [DATA SERVICE] Nicio înregistrare găsită în metadata pentru {token[:8]}")
             return None, "", "Nu există înregistrări asociate acestui link."

        # Folosim cea mai recentă înregistrare
        recording = recordings[-1]
        csv_filename = recording.get('original_filename', 'Date Pulsoximetrie')
        storage_type = recording.get('storage_type', 'unknown')
        csv_path_info = recording.get('csv_path', '')
        
        logger.info(f"📊 [DATA SERVICE] Metadata găsit. Storage: {storage_type}, File: {csv_filename}")

        # 2. Încercăm recuperarea conținutului (Strategy Pattern: R2 -> Local -> Fallback)
        
        # STRATEGIA A: Cloudflare R2
        if storage_type == 'r2' and recording.get('r2_url'):
            logger.info("☁️ [DATA SERVICE] Încercare descărcare R2...")
            try:
                from storage_service import download_patient_file
                
                # Extragem filename din path
                if 'csvs/' in csv_path_info:
                    r2_filename = csv_path_info.split('csvs/')[-1]
                else:
                    r2_filename = recording.get('original_filename', 'unknown.csv')
                
                csv_content = download_patient_file(token, 'csvs', r2_filename)
                
                if csv_content:
                    logger.info(f"✅ [DATA SERVICE] Download R2 reușit: {len(csv_content)} bytes")
                else:
                    logger.warning("⚠️ [DATA SERVICE] Download R2 a returnat empty content. Trecem la Fallback.")
                    storage_type = 'local' # Force fallback
            except ImportError:
                logger.warning("⚠️ [DATA SERVICE] storage_service module lipsă. Trecem la fallback Local.")
                storage_type = 'local'
            except Exception as e:
                logger.error(f"❌ [DATA SERVICE] Eroare R2: {e}. Trecem la fallback Local.")
                storage_type = 'local'

        # STRATEGIA B: Local Storage (sau Fallback din R2)
        if storage_type == 'local' and not csv_content:
            logger.info("💾 [DATA SERVICE] Încercare citire Locală...")
            
            if csv_path_info and os.path.exists(csv_path_info):
                try:
                    with open(csv_path_info, 'rb') as f:
                        csv_content = f.read()
                    logger.info(f"✅ [DATA SERVICE] Citire Locală reușită: {len(csv_content)} bytes")
                except Exception as e:
                    logger.error(f"❌ [DATA SERVICE] Eroare citire locală: {e}")
            else:
                 logger.warning(f"⚠️ [DATA SERVICE] Fișierul local nu există la calea: {csv_path_info}")

        # STRATEGIA C: Legacy Folder Structure (Ultimul resort)
        if not csv_content:
            logger.info("resh [DATA SERVICE] Încercare Legacy Fallback (structură veche)...")
            patient_folder = patient_links.get_patient_storage_path(token)
            legacy_csv_folder = os.path.join(patient_folder, "csvs")
            
            if os.path.exists(legacy_csv_folder):
                csv_files = [f for f in os.listdir(legacy_csv_folder) if f.endswith('.csv')]
                if csv_files:
                    try:
                        legacy_path = os.path.join(legacy_csv_folder, csv_files[0])
                        with open(legacy_path, 'rb') as f:
                            csv_content = f.read()
                        csv_filename = csv_files[0]
                        logger.info(f"✅ [DATA SERVICE] Legacy Fallback reușit: {len(csv_content)} bytes")
                    except Exception as e:
                        logger.error(f"❌ [DATA SERVICE] Eroare Legacy Fallback: {e}")
                else:
                     logger.warning("⚠️ [DATA SERVICE] Niciun CSV în folderul legacy.")
            else:
                 logger.warning("⚠️ [DATA SERVICE] Folderul legacy nu există.")

        # 3. Parsare și validare
        if csv_content:
            logger.info(f"⚙️ [DATA SERVICE] Parsare conținut CSV ({len(csv_content)} bytes)...")
            try:
                df = parse_csv_data(csv_content, csv_filename)
                if df is not None and not df.empty:
                    logger.info(f"✅ [DATA SERVICE] DataFrame creat cu succes: {len(df)} rânduri.")
                    return df, csv_filename, "Succes"
                else:
                    return None, csv_filename, "Fișierul CSV este gol sau invalid după procesare."
            except Exception as e:
                logger.error(f"❌ [DATA SERVICE] Eroare la parsare: {e}")
                return None, csv_filename, f"Eroare la parsarea datelor: {str(e)}"
        else:
            return None, csv_filename, "Nu s-a putut recupera fișierul de date din nicio sursă."

    except Exception as e:
        logger.critical(f"💥 [DATA SERVICE] CRASH neașteptat: {e}", exc_info=True)
        return None, "", f"Eroare critică internă: {str(e)}"

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
    # [DIAGNOSTIC LOG 1] Start
    logger.warning(f"💾 [DS_TRACE_START] START Request for token: {token[:8]}...")
    logger.warning(f"   - Context: get_patient_dataframe")
    
    csv_content = None
    csv_filename = "Date Pulsoximetrie"
    storage_type = "unknown"
    
    try:
        # [DIAGNOSTIC LOG 2] Verificare module
        logger.debug(f"🔍 [DATA_SERVICE] Verificare importuri și environment...")
        
        # 1. Obținem metadata înregistrărilor
        # [DIAGNOSTIC LOG 3] Apel patient_links
        logger.warning(f"📋 [DS_TRACE_META] Querying patient_links metadata...")
        recordings = patient_links.get_patient_recordings(token)
        logger.warning(f"   - Found {len(recordings)} recordings in metadata")
        
        if not recordings:
             # [DIAGNOSTIC LOG 4] Nu există înregistrări
             logger.warning(f"⚠️ [DATA_SERVICE] Nicio înregistrare găsită în metadata pentru {token[:8]}")
             return None, "", "Nu există înregistrări asociate acestui link."

        # [DIAGNOSTIC LOG 5] Analiză recordings
        logger.info(f"📊 [DATA_SERVICE] S-au găsit {len(recordings)} înregistrări. Analizăm ultima...")

        # Folosim cea mai recentă înregistrare
        recording = recordings[-1]
        
        # Copiem datele relevante pentru logging
        csv_filename = recording.get('original_filename', 'Date Pulsoximetrie')
        storage_type = recording.get('storage_type', 'unknown')
        csv_path_info = recording.get('csv_path', '')
        r2_url = recording.get('r2_url', 'N/A')
        
        # [DIAGNOSTIC LOG 6] Detalii recording
        logger.warning(f"🔎 [DS_TRACE_REC] Selected Recording Details:")
        logger.info(f"   - Filename: {csv_filename}")
        logger.info(f"   - Storage Type: {storage_type}")
        logger.info(f"   - CSV Path/Key: {csv_path_info}")
        logger.info(f"   - R2 URL: {r2_url}")
        
        # 2. Încercăm recuperarea conținutului (Strategy Pattern: Scaleway -> Local -> Fallback)
        
        # STRATEGIA A: Cloudflare R2
        if storage_type == 'r2' and recording.get('r2_url'):
            # [DIAGNOSTIC LOG 7] Tentativă R2
            # [DIAGNOSTIC LOG 7] Tentativă R2
            logger.warning("☁️ [DS_TRACE_STRATEGY] STRATEGY A: Attempting Scaleway Download...")
            try:
                from storage_service import download_patient_file
                
                # Extragem filename din path
                if 'csvs/' in csv_path_info:
                    r2_filename = csv_path_info.split('csvs/')[-1]
                else:
                    r2_filename = recording.get('original_filename', 'unknown.csv')
                
                # [DIAGNOSTIC LOG 8] Parametri download R2
                logger.warning(f"📥 [DS_TRACE_R2] Triggering download_patient_file: bucket='csvs', file='{r2_filename}'")
                
                csv_content = download_patient_file(token, 'csvs', r2_filename)
                
                if csv_content:
                    # [DIAGNOSTIC LOG 9] Scaleway Succes
                    logger.info(f"✅ [DATA_SERVICE] Download Scaleway reușit: {len(csv_content)} bytes")
                else:
                    # [DIAGNOSTIC LOG 10] Scaleway Fail Empty
                    logger.warning("⚠️ [DATA_SERVICE] Download Scaleway a returnat empty content. Trecem la Fallback.")
                    storage_type = 'local' # Force fallback
            except ImportError:
                logger.warning("⚠️ [DATA_SERVICE] storage_service module lipsă. Trecem la fallback Local.")
                storage_type = 'local'
            except Exception as e:
                logger.error(f"❌ [DATA_SERVICE] Eroare R2: {e}. Trecem la fallback Local.")
                storage_type = 'local'

        # STRATEGIA B: Local Storage (sau Fallback din R2)
        if storage_type == 'local' and not csv_content:
            # [DIAGNOSTIC LOG 11] Tentativă Locală
            # [DIAGNOSTIC LOG 11] Tentativă Locală
            logger.warning("💾 [DS_TRACE_STRATEGY] STRATEGY B: Attempting Local Read...")
            logger.warning(f"   - Target Path: '{csv_path_info}'")
            
            if csv_path_info and os.path.exists(csv_path_info):
                try:
                    with open(csv_path_info, 'rb') as f:
                        csv_content = f.read()
                    # [DIAGNOSTIC LOG 12] Local Succes
                    logger.info(f"✅ [DATA_SERVICE] Citire Locală reușită: {len(csv_content)} bytes")
                except Exception as e:
                    # [DIAGNOSTIC LOG 13] Local Error
                    logger.error(f"❌ [DATA_SERVICE] Eroare citire locală: {e}")
            else:
                 # [DIAGNOSTIC LOG 14] Local Missing
                 logger.warning(f"⚠️ [DATA_SERVICE] Fișierul local NU EXISTĂ la calea: {csv_path_info}")
                 # Verifichăm permisiuni sau cwd
                 logger.debug(f"   - CWD curent: {os.getcwd()}")

        # STRATEGIA C: Legacy Folder Structure (Ultimul resort)
        if not csv_content:
            # [DIAGNOSTIC LOG 15] Tentativă Legacy
            # [DIAGNOSTIC LOG 15] Tentativă Legacy
            logger.warning("🕰️ [DS_TRACE_STRATEGY] STRATEGY C: Legacy Fallback...")
            patient_folder = patient_links.get_patient_storage_path(token)
            legacy_csv_folder = os.path.join(patient_folder, "csvs")
            logger.info(f"   - Folder Legacy țintă: {legacy_csv_folder}")
            
            if os.path.exists(legacy_csv_folder):
                csv_files = [f for f in os.listdir(legacy_csv_folder) if f.endswith('.csv')]
                logger.info(f"   - Fișiere găsite în legacy: {csv_files}")
                
                if csv_files:
                    try:
                        legacy_path = os.path.join(legacy_csv_folder, csv_files[0])
                        with open(legacy_path, 'rb') as f:
                            csv_content = f.read()
                        csv_filename = csv_files[0]
                        # [DIAGNOSTIC LOG 16] Legacy Succes
                        logger.info(f"✅ [DATA_SERVICE] Legacy Fallback reușit: {len(csv_content)} bytes")
                    except Exception as e:
                        logger.error(f"❌ [DATA_SERVICE] Eroare Legacy Fallback: {e}")
                else:
                     logger.warning("⚠️ [DATA_SERVICE] Niciun CSV în folderul legacy.")
            else:
                 logger.warning("⚠️ [DATA_SERVICE] Folderul legacy nu există.")

        # 3. Parsare și validare
        if csv_content:
            # [DIAGNOSTIC LOG 17] Start Parsare
            # [DIAGNOSTIC LOG 17] Start Parsare
            logger.warning(f"⚙️ [DS_TRACE_PARSE] Start CSV Parsing | Size: {len(csv_content)} bytes")
            try:
                df = parse_csv_data(csv_content, csv_filename)
                if df is not None and not df.empty:
                    # [DIAGNOSTIC LOG 18] Parsare Succes
                    logger.info(f"✅ [DATA_SERVICE] DataFrame creat cu succes: {len(df)} rânduri.")
                    logger.info(f"   - Columns: {list(df.columns)}")
                    logger.info(f"   - Index Start: {df.index[0] if not df.empty else 'N/A'}")
                    logger.info(f"   - Index End: {df.index[-1] if not df.empty else 'N/A'}")
                    return df, csv_filename, "Succes"
                else:
                    # [DIAGNOSTIC LOG 19] Parsare Empty
                    logger.error("❌ [DATA_SERVICE] Fișierul CSV este gol sau invalid după procesare.")
                    return None, csv_filename, "Fișierul CSV este gol sau invalid după procesare."
            except Exception as e:
                # [DIAGNOSTIC LOG 20] Parsare Excepție
                logger.error(f"❌ [DATA_SERVICE] Eroare CRITICĂ la parsare: {e}", exc_info=True)
                return None, csv_filename, f"Eroare la parsarea datelor: {str(e)}"
        else:
            # [DIAGNOSTIC LOG 21] No Content Final
            logger.error("❌ [DATA_SERVICE] EȘEC TOTAL: Nu s-a putut recupera fișierul de date din nicio sursă.")
            return None, csv_filename, "Nu s-a putut recupera fișierul de date din nicio sursă."

    except Exception as e:
        # [DIAGNOSTIC LOG 22] Crash Handler
        logger.critical(f"💥 [DATA_SERVICE] CRASH neașteptat în get_patient_dataframe: {e}", exc_info=True)
        return None, "", f"Eroare critică internă: {str(e)}"

# ==============================================================================
# patient_links.py
# ------------------------------------------------------------------------------
# ROL: Gestionează link-urile persistente pentru pacienți (stocare locală JSON)
#      Implementează filozofia: 1 PACIENT = 1 LINK PERSISTENT
#
# ARHITECTURĂ:
#   - Fiecare pacient are un UUID unic (token)
#   - Datele sunt stocate în patient_data/{token}/
#   - Metadata pacienți în patient_links.json
#
# RESPECTĂ: .cursorrules - Privacy by Design (zero date personale!)
# ==============================================================================

import os
import json
import uuid
import shutil
from datetime import datetime
from typing import Dict, List, Optional
from logger_setup import logger

# --- Configurare Căi ---
PATIENT_DATA_DIR = "patient_data"
PATIENT_LINKS_FILE = "patient_links.json"  # Local cache (ephemeral)
LINKS_METADATA_S3_KEY = "patient_links.json"  # Scaleway persistent storage

# Creăm directorul de bază la import
os.makedirs(PATIENT_DATA_DIR, exist_ok=True)


# ==============================================================================
# FUNCȚII CORE - GESTIONARE LINK-URI
# ==============================================================================

def load_patient_links() -> Dict:
    """
    [CRITICAL FIX] Încarcă link-urile din SCALEWAY (persistent) cu fallback local.
    
    Priority:
    1. Scaleway S3 (PERSISTENT - survives Railway redeploys)
    2. Local file (EPHEMERAL - lost on redeploy, used as cache)
    
    Returns:
        Dict: Dicționar cu token-uri ca chei și metadata ca valori
    """
    _migrate = None
    try:
        from repositories.patient_repository import load_all_from_postgres, migrate_legacy_if_empty
        _migrate = migrate_legacy_if_empty
        _pg = load_all_from_postgres()
        if _pg is not None:
            logger.warning(f"📗 [LINKS_PG] Încărcate {len(_pg)} link-uri din PostgreSQL")
            return _pg
    except Exception as pg_err:
        logger.debug(f"[LINKS_PG] ocolit: {pg_err}")

    # PRIORITY 1: Try loading from Scaleway (PERSISTENT)
    try:
        from storage_service import r2_client
        if r2_client.enabled:
            logger.debug(f"☁️ [LINKS_SCALEWAY] === ATTEMPTING SCALEWAY LOAD ===")
            logger.debug(f"☁️ [LINKS_SCALEWAY] Object key: {LINKS_METADATA_S3_KEY}")
            logger.debug(f"☁️ [LINKS_SCALEWAY] R2 Client enabled: {r2_client.enabled}")
            logger.debug(f"☁️ [LINKS_SCALEWAY] Bucket: {getattr(r2_client, 'bucket_name', 'N/A')}")
            
            import time
            start_time = time.time()
            content = r2_client.download_file(LINKS_METADATA_S3_KEY)
            elapsed = time.time() - start_time
            
            if content:
                links = json.loads(content.decode('utf-8'))
                logger.debug(f"✅ [LINKS_SCALEWAY] SUCCESS!")
                logger.debug(f"   - Links Count: {len(links)}")
                logger.debug(f"   - Download Time: {elapsed:.3f}s")
                logger.debug(f"   - Size: {len(content)} bytes ({len(content)/1024:.2f} KB)")
                
                # Show sample of loaded tokens
                if links:
                    sample_tokens = list(links.keys())[:5]
                    logger.debug(f"   - Sample Tokens: {[t[:8] + '...' for t in sample_tokens]}")
                
                # Save local cache for faster subsequent reads
                try:
                    with open(PATIENT_LINKS_FILE, 'w', encoding='utf-8') as f:
                        json.dump(links, f, indent=2, ensure_ascii=False)
                    logger.debug(f"💾 [LINKS_CACHE] Cached {len(links)} links locally")
                except Exception as cache_err:
                    logger.warning(f"⚠️ [LINKS_CACHE] Cache write failed: {cache_err}")

                if _migrate:
                    _migrate(links)
                return links
            else:
                logger.debug(f"⚠️ [LINKS_SCALEWAY] Returned EMPTY content (file may not exist)")
                logger.debug(f"   - Download Time: {elapsed:.3f}s")
    except ImportError as imp_err:
        logger.debug(f"⚠️ [LINKS_SCALEWAY] ImportError: {imp_err}")
        logger.debug(f"⚠️ [LINKS_SCALEWAY] storage_service not available")
    except Exception as e:
        logger.debug(f"❌ [LINKS_SCALEWAY] Exception: {e}", exc_info=True)
    
    # FALLBACK: Try local file (ephemeral cache)
    if os.path.exists(PATIENT_LINKS_FILE):
        try:
            with open(PATIENT_LINKS_FILE, 'r', encoding='utf-8') as f:
                links = json.load(f)
                logger.warning(f"💾 [LINKS_LOAD] Loaded {len(links)} links from LOCAL (ephemeral cache)")
                if _migrate:
                    _migrate(links)
                return links
        except Exception as e:
            logger.error(f"❌ [LINKS_LOAD] Local load failed: {e}", exc_info=True)
    
    logger.warning(f"📭 [LINKS_LOAD] No links found (neither Scaleway nor local)")
    return {}


def save_patient_links(links: Dict) -> bool:
    """
    [CRITICAL FIX] Salvează link-urile în SCALEWAY (persistent) + local cache.
    
    Strategy:
    1. Save to Scaleway S3 (PERSISTENT - critical!)
    2. Save to local file (CACHE - optional)
    
    Args:
        links: dicționar cu link-uri
        
    Returns:
        bool: True dacă salvarea Scaleway a reușit
    """
    import time
    scaleway_success = False
    local_success = False

    try:
        from repositories.patient_repository import replace_all_in_postgres
        replace_all_in_postgres(links)
    except Exception as pg_save_err:
        logger.debug(f"[LINKS_PG] save ocolit: {pg_save_err}")

    # PRIORITY 1: Save to Scaleway (PERSISTENT)
    try:
        from storage_service import r2_client
        if r2_client.enabled:
            logger.warning(f"☁️ [LINKS_SAVE] Attempting Scaleway save for {len(links)} links...")
            
            content = json.dumps(links, indent=2, ensure_ascii=False).encode('utf-8')
            
            # Upload as JSON file
            success = r2_client.upload_file(
                content,
                LINKS_METADATA_S3_KEY,
                content_type='application/json'
            )
            
            if success:
                logger.warning(f"✅ [LINKS_SAVE] Saved {len(links)} links to SCALEWAY (persistent)")
                scaleway_success = True
            else:
                logger.error(f"❌ [LINKS_SAVE] Scaleway upload returned False")
    except ImportError:
        logger.warning(f"⚠️ [LINKS_SAVE] storage_service not available - using LOCAL only")
    except Exception as e:
        logger.error(f"❌ [LINKS_SAVE] Scaleway save failed: {e}", exc_info=True)
    
    # CACHE: Save to local file (with retry for file locking)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with open(PATIENT_LINKS_FILE, 'w', encoding='utf-8') as f:
                json.dump(links, f, indent=2, ensure_ascii=False)
            logger.warning(f"💾 [LINKS_SAVE] Cached {len(links)} links locally")
            local_success = True
            break
            
        except PermissionError as pe:
            wait_time = (2 ** attempt) * 0.1
            logger.warning(f"🔒 [FILE_LOCK] patient_links.json LOCKED (attempt {attempt+1}/{max_retries})")
            
            if attempt < max_retries - 1:
                time.sleep(wait_time)
            else:
                logger.error(f"❌ [FILE_LOCK] FAILED after {max_retries} attempts")
                
        except Exception as e:
            logger.error(f"❌ [LINKS_SAVE] Local save failed: {e}", exc_info=True)
    
    # Return True if at least Scaleway succeeded (critical path)
    # Local is just a cache, so it's OK if it fails
    return scaleway_success or local_success


def generate_patient_link(device_name: str, notes: str = "", recording_date: str = None, 
                         start_time: str = None, end_time: str = None, pdf_path: str = None) -> str:
    """
    Generează un nou link persistent pentru un pacient SAU updatează unul existent.
    
    ⚠️ IMPORTANT: Link-ul NU conține date personale (GDPR compliant)
    
    [UPDATED v5.0] Duplicate Detection:
    - Verifică dacă există deja un link pentru device_name + recording_date + start_time
    - Dacă DA: returnează token-ul existent (evitare duplicare)
    - Dacă NU: creează link nou
    
    Args:
        device_name: Numele aparatului (ex: "Checkme O2 #1442")
        notes: Notițe medicale opționale
        recording_date: Data înregistrării (YYYY-MM-DD)
        start_time: Ora de început (HH:MM sau HH:MM:SS)
        end_time: Ora de sfârșit (HH:MM sau HH:MM:SS)
        pdf_path: Calea către PDF asociat (opțional)
        
    Returns:
        str: Token-ul UUID (existent sau nou) sau None dacă eroare
    """
    # [DIAGNOSTIC LOG 1] Function entry
    logger.debug(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.debug(f"🔗 [LINK_CREATE] START: generate_patient_link()")
    logger.debug(f"   - Device: {device_name}")
    logger.debug(f"   - Recording date: {recording_date}")
    logger.debug(f"   - Time range: {start_time} → {end_time}")
    logger.debug(f"   - PDF path: {pdf_path if pdf_path else 'None'}")
    logger.debug(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    try:
        # [STEP 1] Verificare duplicate (evitare link-uri duplicate pentru același device + dată)
        logger.debug(f"🔍 [LINK_CREATE] STEP 1: Checking for existing link (duplicate detection)...")
        links = load_patient_links()
        
        existing_token = None
        if device_name and recording_date and start_time:
            for token, metadata in links.items():
                if (metadata.get('device_name') == device_name and 
                    metadata.get('recording_date') == recording_date and
                    metadata.get('start_time') == start_time):
                    existing_token = token
                    logger.debug(f"✅ [LINK_CREATE] STEP 1 RESULT: Existing link found (duplicate)")
                    logger.debug(f"   - Existing token: {existing_token}")
                    logger.debug(f"   - Device: {device_name}")
                    logger.debug(f"   - Date: {recording_date} {start_time}")
                    logger.debug(f"   - Action: Returning existing token (no new link created)")
                    logger.debug(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                    return existing_token
        
        if not existing_token:
            logger.debug(f"✅ [LINK_CREATE] STEP 1 RESULT: No existing link found")
            logger.debug(f"   - Action: Creating new link")
        
        # [STEP 2] Generare token nou
        # [DIAGNOSTIC LOG 2] Token generation
        token = str(uuid.uuid4())
        logger.debug(f"🆕 [LINK_CREATE] STEP 2: New token generated")
        logger.debug(f"   - Token: {token}")
        logger.debug(f"   - Short token: {token[:8]}...")
        
        # [STEP 3] Creare metadata link
        logger.debug(f"📋 [LINK_CREATE] STEP 3: Creating link metadata...")
        
        # Creăm folderul pentru acest pacient
        patient_folder = os.path.join(PATIENT_DATA_DIR, token)
        os.makedirs(patient_folder, exist_ok=True)
        
        # Salvăm metadata EXTINSĂ pentru workflow medical
        current_time = datetime.now().isoformat()
        links[token] = {
            "device_name": device_name,
            "notes": notes,
            "created_at": current_time,  # Prima procesare
            "last_processed_at": current_time,  # [NEW] Ultima reprocessare
            "last_accessed": None,
            "is_active": True,
            "recordings_count": 0,
            # [NEW] Metadata medicală extinsă
            "recording_date": recording_date,  # Data înregistrării
            "start_time": start_time,          # Ora de început
            "end_time": end_time,              # Ora de sfârșit
            "medical_notes": "",               # Notițe medicale detaliate (textarea)
            "sent_status": False,              # Marcat ca trimis către pacient
            "sent_at": None,                   # Când a fost marcat ca trimis
            "view_count": 0,                   # Număr total vizualizări
            "first_viewed_at": None,           # Prima vizualizare
            "last_viewed_at": None,            # Ultima vizualizare
            "pdf_path": pdf_path               # Cale către PDF asociat (opțional)
        }
        
        # [STEP 4] Salvare în Scaleway (persistent)
        logger.debug(f"💾 [LINK_CREATE] STEP 4: Saving to Scaleway (persistent storage)...")
        logger.debug(f"   - Links count: {len(links)}")
        logger.debug(f"   - New token added: {token[:8]}...")
        
        save_success = save_patient_links(links)
        
        # [DIAGNOSTIC LOG 3] Save result
        if save_success:
            logger.debug(f"✅ [LINK_CREATE] STEP 4 COMPLETE: Link saved to Scaleway successfully")
            logger.debug(f"   - Token: {token}")
            logger.debug(f"   - Device: {device_name}")
            logger.debug(f"   - Scaleway persistence: CONFIRMED")
        else:
            logger.debug(f"❌ [LINK_CREATE] STEP 4 FAILED: Scaleway save returned False")
            logger.debug(f"   - Token: {token}")
            logger.warning(f"   - WARNING: Link may not persist across Railway restarts!")
        
        logger.debug(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info(f"✅ [TRACE-DATA] [LOG 08] Link nou generat pentru aparat '{device_name}': {token}")
        logger.info(f"   [TRACE-DATA] PDF Path: {pdf_path}")
        logger.info(f"   [TRACE-DATA] Recording Date: {recording_date}")
        logger.info(f"   [TRACE-DATA] created_at: {current_time}")
        logger.info(f"   [TRACE-DATA] last_processed_at: {current_time}")
        return token
            
    except Exception as e:
        logger.error(f"Eroare la generarea link-ului: {e}", exc_info=True)
        return None


def get_patient_link(token: str, track_view: bool = True) -> Optional[Dict]:
    """
    Preia metadata pentru un link de pacient.
    
    Args:
        token: UUID-ul pacientului
        track_view: Dacă True, contorizează vizualizarea (default True)
        
    Returns:
        Dict: Metadata pacient sau None dacă nu există
    """
    logger.debug(f"📥 [GET_PATIENT_LINK] *** START for token {token[:8]}... ***")
    logger.debug(f"📥 [GET_PATIENT_LINK] track_view={track_view}")
    
    logger.debug(f"📥 [GET_PATIENT_LINK] Step 1: Loading all patient links from Scaleway...")
    links = load_patient_links()
    logger.debug(f"📥 [GET_PATIENT_LINK] Step 2: Loaded {len(links)} total links")
    logger.debug(f"📥 [GET_PATIENT_LINK] Step 3: Searching for token {token[:8]}... in {len(links)} links")
    
    patient_data = links.get(token)
    
    if patient_data:
        logger.debug(f"✅ [GET_PATIENT_LINK] Step 4: Token FOUND!")
        logger.debug(f"📊 [GET_PATIENT_LINK] Device: {patient_data.get('device_name', 'N/A')}")
        logger.debug(f"📊 [GET_PATIENT_LINK] is_active: {patient_data.get('is_active', 'N/A')}")
        logger.debug(f"📊 [GET_PATIENT_LINK] created_at: {patient_data.get('created_at', 'N/A')}")
        
        # Actualizăm last_accessed (backward compatibility)
        patient_data['last_accessed'] = datetime.now().isoformat()
        links[token] = patient_data
        save_patient_links(links)
        logger.debug(f"Link accesat: {token[:8]}...")
        
        # [NEW] Tracking automat vizualizări
        if track_view:
            track_link_view(token)
    else:
        logger.debug(f"❌ [GET_PATIENT_LINK] Step 4: Token {token[:8]}... NOT FOUND!")
        logger.debug(f"❌ [GET_PATIENT_LINK] Available tokens in DB: {[t[:8] + '...' for t in list(links.keys())[:10]]}")
    
    return patient_data


def get_all_patient_links() -> List[Dict]:
    """
    Preia toate link-urile active de pacienți (pentru dashboard admin).
    
    Returns:
        List[Dict]: Listă cu toate link-urile și metadata lor
    """
    links = load_patient_links()
    result = []
    
    for token, data in links.items():
        if data.get('is_active', True):
            result.append({
                "token": token,
                "device_name": data.get("device_name", "Unknown"),
                "notes": data.get("notes", ""),
                "created_at": data.get("created_at"),
                "recordings_count": data.get("recordings_count", 0)
            })
    
    logger.debug(f"Returnate {len(result)} link-uri active.")
    return result


def deactivate_patient_link(token: str) -> bool:
    """
    Dezactivează un link de pacient (nu șterge datele!).
    
    Args:
        token: UUID-ul pacientului
        
    Returns:
        bool: True dacă operațiunea a reușit
    """
    links = load_patient_links()
    
    if token in links:
        links[token]['is_active'] = False
        links[token]['deactivated_at'] = datetime.now().isoformat()
        
        if save_patient_links(links):
            logger.info(f"⚠️ Link dezactivat: {token[:8]}...")
            return True
    
    logger.error(f"Nu s-a putut dezactiva link-ul: {token}")
    return False


def delete_patient_link(token: str) -> bool:
    """
    ⚠️ ȘTERGE COMPLET un link de pacient și TOATE datele asociate.
    IRREVERSIBIL! Folosit pentru GDPR "dreptul de a fi uitat".
    
    Args:
        token: UUID-ul pacientului
        
    Returns:
        bool: True dacă ștergerea a reușit
    """
    try:
        # Ștergem folderul cu toate datele
        patient_folder = os.path.join(PATIENT_DATA_DIR, token)
        if os.path.exists(patient_folder):
            shutil.rmtree(patient_folder)
            logger.info(f"🗑️ Folder șters: {patient_folder}")
        
        # Ștergem din metadata
        links = load_patient_links()
        if token in links:
            del links[token]
            save_patient_links(links)
        
        logger.info(f"🗑️ Link șters complet (GDPR): {token[:8]}...")
        return True
        
    except Exception as e:
        logger.error(f"Eroare la ștergerea link-ului {token}: {e}", exc_info=True)
        return False


# ==============================================================================
# FUNCȚII RECORDINGS - GESTIONARE ÎNREGISTRĂRI
# ==============================================================================

def get_patient_recordings(token: str) -> List[Dict]:
    """
    Preia toate înregistrările pentru un pacient din PostgreSQL.
    
    CRITICAL FIX v2: Read from PostgreSQL (PatientRecording model) instead of:
    - Local recordings.json (ephemeral on Railway) ❌
    - patient_links.json metadata (too large with recordings) ❌
    
    PostgreSQL ensures recordings PERSIST across Railway restarts ✅
    
    AUTO-MIGRATION: If PostgreSQL has 0 recordings but patient_links.json has data,
    automatically migrates old recordings from JSON to PostgreSQL.
    
    Args:
        token: UUID-ul pacientului
        
    Returns:
        List[Dict]: Listă cu metadata fiecărei înregistrări
    """
    logger.warning(f"📥 [GET_RECORDINGS_PG] START for token {token[:8]}...")
    
    try:
        # Import PostgreSQL model
        from auth.models import PatientRecording
        
        # Query PostgreSQL - sortate descrescător după dată
        recordings = PatientRecording.query.filter_by(token=token).order_by(
            PatientRecording.recording_date.desc()
        ).all()
        
        logger.warning(f"✅ [GET_RECORDINGS_PG] Found {len(recordings)} recordings in PostgreSQL for {token[:8]}")
        
        # === AUTO-MIGRATION: Check if we need to import from old JSON ===
        if len(recordings) == 0:
            logger.warning(f"🔍 [GET_RECORDINGS_PG] PostgreSQL empty - checking for old JSON recordings...")
            
            # Load patient_links to see if there are old recordings
            links = load_patient_links()
            
            if token in links and 'recordings' in links[token]:
                old_recordings = links[token]['recordings']
                
                if len(old_recordings) > 0:
                    logger.warning(f"📦 [MIGRATION] Found {len(old_recordings)} OLD recordings in patient_links.json")
                    logger.warning(f"📦 [MIGRATION] Auto-migrating to PostgreSQL...")
                    
                    # Migrate each recording to PostgreSQL
                    migrated_count = 0
                    for rec_dict in old_recordings:
                        try:
                            PatientRecording.create_from_dict(token, rec_dict)
                            migrated_count += 1
                        except Exception as e:
                            logger.error(f"❌ [MIGRATION] Failed to migrate recording {rec_dict.get('id', 'unknown')}: {e}")
                    
                    logger.warning(f"✅ [MIGRATION] Successfully migrated {migrated_count}/{len(old_recordings)} recordings to PostgreSQL")
                    
                    # Re-query to get migrated recordings
                    recordings = PatientRecording.query.filter_by(token=token).order_by(
                        PatientRecording.recording_date.desc()
                    ).all()
                    
                    logger.warning(f"✅ [MIGRATION] After migration: {len(recordings)} recordings now in PostgreSQL")
        
        # Convert to dict format (backward compatible)
        recordings_list = [rec.to_dict() for rec in recordings]
        
        # Log sample for debugging
        if recordings_list:
            logger.warning(f"📊 [GET_RECORDINGS_PG] Sample IDs: {[r['id'] for r in recordings_list[:3]]}")
        
        return recordings_list
        
    except Exception as e:
        logger.error(f"❌ [GET_RECORDINGS_PG] Error reading from PostgreSQL: {e}", exc_info=True)
        # Fallback: return empty list (don't crash)
        return []


def save_patient_recordings(token: str, recordings: List[Dict]) -> bool:
    """
    DEPRECATED: Use add_recording() instead for new recordings.
    
    This function is kept for backward compatibility during migration.
    It now saves to PostgreSQL instead of local files.
    
    Args:
        token: UUID-ul pacientului
        recordings: Listă cu metadata înregistrărilor
        
    Returns:
        bool: True dacă salvarea a reușit
    """
    logger.warning(f"⚠️ [SAVE_RECORDINGS_DEPRECATED] Called with {len(recordings)} recordings for {token[:8]}")
    logger.warning("⚠️ [SAVE_RECORDINGS_DEPRECATED] This function is deprecated - use add_recording() for new data")
    
    try:
        from auth.models import PatientRecording, db
        
        # For each recording in the list, ensure it exists in PostgreSQL
        for rec_dict in recordings:
            # Check if already exists
            rec_id = rec_dict.get('id', str(uuid.uuid4())[:8])
            existing = PatientRecording.query.filter_by(
                token=token, 
                recording_id=rec_id
            ).first()
            
            if not existing:
                # Create new entry
                PatientRecording.create_from_dict(token, rec_dict)
                logger.info(f"✅ Migrated recording {rec_id} to PostgreSQL")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ [SAVE_RECORDINGS_DEPRECATED] Error: {e}", exc_info=True)
        return False


def add_recording(token: str, csv_filename: str, csv_content: bytes, 
                 recording_date: str, start_time: str, end_time: str,
                 avg_spo2: float = None, min_spo2: int = None, max_spo2: int = None) -> bool:
    """
    Adaugă o nouă înregistrare pentru un pacient.
    
    Args:
        token: UUID-ul pacientului
        csv_filename: Numele fișierului CSV original
        csv_content: Conținutul brut al fișierului CSV
        recording_date: Data înregistrării (ISO format)
        start_time: Ora de început (HH:MM:SS)
        end_time: Ora de sfârșit (HH:MM:SS)
        avg_spo2, min_spo2, max_spo2: Statistici opționale
        
    Returns:
        bool: True dacă adăugarea a reușit
    """
    try:
        # Import Scaleway storage service
        try:
            from storage_service import upload_patient_csv, r2_client
            r2_available = r2_client.enabled
        except ImportError:
            logger.warning("⚠️ storage_service nu e disponibil - folosim stocare LOCALĂ (EPHEMERAL pe Railway!)")
            r2_available = False
        
        patient_folder = os.path.join(PATIENT_DATA_DIR, token)
        
        # Generăm un ID unic pentru înregistrare
        recording_id = str(uuid.uuid4())[:8]
        
        # PRIORITATE 1: Încercăm să salvăm în Scaleway (PERSISTENT)
        csv_path = None
        r2_url = None
        
        if r2_available:
            logger.warning(f"☁️ [LINK_TRACE_SAVE] Attempting Scaleway Storage for {token[:8]}...")
            try:
                # Salvăm în R2 cu nume structurat
                r2_filename = f"recording_{recording_id}_{csv_filename}"
                r2_url = upload_patient_csv(token, csv_content, r2_filename)
                
                if r2_url:
                    logger.info(f"✅ CSV salvat în R2: {r2_url}")
                    csv_path = f"r2://{token}/csvs/{r2_filename}"  # Path virtual pentru referință
                else:
                    logger.warning(f"⚠️ Upload Scaleway eșuat, folosim fallback LOCAL")
                    r2_available = False  # Fallback la local
            except Exception as e:
                logger.error(f"❌ Eroare upload R2: {e} - folosim fallback LOCAL", exc_info=True)
                r2_available = False
        
        # FALLBACK: Salvăm LOCAL (EPHEMERAL pe Railway!)
        if not r2_available or not r2_url:
            logger.warning(f"💾 [LINK_TRACE_SAVE] Fallback to LOCAL STORAGE (Ephemeral Mode)")
            os.makedirs(patient_folder, exist_ok=True)
            csv_path = os.path.join(patient_folder, f"recording_{recording_id}.csv")
            with open(csv_path, 'wb') as f:
                f.write(csv_content)
            logger.info(f"⚠️ CSV salvat LOCAL: {csv_path} (TEMPORARY!)")
        
        # CRITICAL FIX v2: Save to PostgreSQL (PERSISTENT) instead of JSON
        logger.warning(f"💾 [ADD_RECORDING_PG] Saving to PostgreSQL for {token[:8]}...")
        
        try:
            from auth.models import PatientRecording, db
            from dateutil.parser import parse as parse_date
            
            # Parse dates if strings
            if isinstance(recording_date, str):
                recording_date = parse_date(recording_date).date()
            if isinstance(start_time, str):
                start_time = parse_date(start_time).time()
            if isinstance(end_time, str):
                end_time = parse_date(end_time).time()
            
            # Create PostgreSQL record
            recording = PatientRecording(
                token=token,
                recording_id=recording_id,
                original_filename=csv_filename,
                csv_path=csv_path,
                r2_url=r2_url,
                storage_type='r2' if (r2_available and r2_url) else 'local',
                recording_date=recording_date,
                start_time=start_time,
                end_time=end_time,
                avg_spo2=avg_spo2,
                min_spo2=min_spo2,
                max_spo2=max_spo2
            )
            
            db.session.add(recording)
            db.session.commit()
            
            storage_info = "☁️ R2 (PERSISTENT)" if (r2_available and r2_url) else "💾 LOCAL (EPHEMERAL!)"
            logger.warning(f"✅ [ADD_RECORDING_PG] Saved to PostgreSQL | Token: {token[:8]} | Storage: {storage_info} | ID: {recording_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ [ADD_RECORDING_PG] PostgreSQL save failed: {e}", exc_info=True)
            try:
                db.session.rollback()
            except:
                pass
            return False
            
    except Exception as e:
        logger.error(f"Eroare la adăugarea înregistrării pentru {token}: {e}", exc_info=True)
        return False


def delete_recording(token: str, recording_id: str) -> bool:
    """
    Șterge o înregistrare specifică pentru un pacient.
    
    ⚠️ IMPORTANT: Șterge fișierul CSV (din R2 sau local) și actualizează metadata!
    
    Args:
        token: UUID-ul pacientului
        recording_id: ID-ul unic al înregistrării de șters
        
    Returns:
        bool: True dacă ștergerea a reușit
    """
    try:
        # Încărcăm înregistrările existente
        recordings = get_patient_recordings(token)
        
        if not recordings:
            logger.warning(f"Nu există înregistrări pentru pacientul {token[:8]}...")
            return False
        
        # Găsim înregistrarea de șters
        recording_to_delete = None
        for rec in recordings:
            if rec['id'] == recording_id:
                recording_to_delete = rec
                break
        
        if not recording_to_delete:
            logger.warning(f"Înregistrarea {recording_id} nu există pentru pacientul {token[:8]}...")
            return False
        
        # Încercăm să ștergem fișierul fizic (R2 sau local)
        csv_path = recording_to_delete.get('csv_path')
        storage_type = recording_to_delete.get('storage_type', 'local')
        
        if storage_type == 'r2':
            # Ștergem din R2
            try:
                from storage_service import r2_client
                # Extragem key-ul din csv_path (format: r2://{token}/csvs/{filename})
                if csv_path and csv_path.startswith('r2://'):
                    r2_key = csv_path.replace('r2://', '')
                    r2_client.delete_file(r2_key)
                    logger.info(f"☁️ CSV șters din R2: {r2_key}")
                else:
                    logger.warning(f"⚠️ Path Scaleway invalid: {csv_path}")
            except Exception as e:
                logger.error(f"❌ Eroare ștergere R2: {e}", exc_info=True)
                # Continuăm oricum cu ștergerea din metadata
        else:
            # Ștergem local
            try:
                if csv_path and os.path.exists(csv_path):
                    os.remove(csv_path)
                    logger.info(f"💾 CSV șters local: {csv_path}")
                else:
                    logger.warning(f"⚠️ Fișier local inexistent: {csv_path}")
            except Exception as e:
                logger.error(f"❌ Eroare ștergere locală: {e}", exc_info=True)
        
        # Ștergem și imaginile asociate (dacă există)
        patient_folder = os.path.join(PATIENT_DATA_DIR, token)
        images_folder = os.path.join(patient_folder, "images")
        
        if os.path.exists(images_folder):
            # Căutăm imagini care conțin recording_id în nume
            try:
                for img_file in os.listdir(images_folder):
                    if recording_id in img_file:
                        img_path = os.path.join(images_folder, img_file)
                        os.remove(img_path)
                        logger.info(f"🖼️ Imagine ștearsă: {img_file}")
            except Exception as e:
                logger.warning(f"⚠️ Eroare la ștergerea imaginilor: {e}")
        
        # Eliminăm înregistrarea din lista de recordings
        recordings.remove(recording_to_delete)
        
        # Salvăm lista actualizată
        if save_patient_recordings(token, recordings):
            logger.info(f"✅ Înregistrare ștearsă cu succes: {recording_id} pentru pacient {token[:8]}...")
            logger.info(f"   📁 Fișier: {recording_to_delete.get('original_filename')}")
            logger.info(f"   📅 Data: {recording_to_delete.get('recording_date')} {recording_to_delete.get('start_time')}")
            return True
        else:
            logger.error(f"❌ Eroare la salvarea listei de înregistrări după ștergere")
            return False
            
    except Exception as e:
        logger.error(f"Eroare la ștergerea înregistrării {recording_id} pentru {token}: {e}", exc_info=True)
        return False


# ==============================================================================
# FUNCȚII UTILITARE
# ==============================================================================

def get_patient_storage_path(token: str) -> str:
    """
    Returnează calea către folderul de stocare al pacientului.
    
    Args:
        token: UUID-ul pacientului
        
    Returns:
        str: Cale absolută către folder
    """
    return os.path.abspath(os.path.join(PATIENT_DATA_DIR, token))


def validate_token(token: str) -> bool:
    """
    Verifică dacă un token este valid și activ.
    
    Args:
        token: UUID-ul de verificat
        
    Returns:
        bool: True dacă token-ul este valid
    """
    logger.debug("=" * 100)
    logger.debug(f"🔐 [TOKEN_VALIDATION] *** START VALIDATION ***")
    logger.debug(f"🔐 [TOKEN_VALIDATION] Token to validate: {token[:8] if token else 'None'}...")
    logger.debug("=" * 100)
    
    if not token:
        logger.debug(f"❌ [TOKEN_VALIDATION] Token is None or empty - INVALID")
        return False
    
    logger.debug(f"🔐 [TOKEN_VALIDATION] Step 1: Calling get_patient_link()...")
    patient_data = get_patient_link(token, track_view=False)
    logger.debug(f"🔐 [TOKEN_VALIDATION] Step 2: get_patient_link() returned: {type(patient_data)}")
    
    if not patient_data:
        logger.debug(f"❌ [TOKEN_VALIDATION] Token {token[:8]}... NOT FOUND in database - INVALID")
        logger.debug(f"❌ [TOKEN_VALIDATION] get_patient_link() returned: {patient_data}")
        return False
    
    logger.debug(f"✅ [TOKEN_VALIDATION] Step 3: Token FOUND in database!")
    logger.debug(f"📊 [TOKEN_VALIDATION] Data keys: {list(patient_data.keys())}")
    
    device_name = patient_data.get('device_name', 'N/A')
    logger.debug(f"📊 [TOKEN_VALIDATION] Device: {device_name[:30]}...")
    logger.debug(f"📊 [TOKEN_VALIDATION] Recording date: {patient_data.get('recording_date', 'N/A')}")
    logger.debug(f"📊 [TOKEN_VALIDATION] Created at: {patient_data.get('created_at', 'N/A')}")
    
    is_active = patient_data.get('is_active', True)
    logger.debug(f"🔍 [TOKEN_VALIDATION] Step 4: Checking is_active status...")
    logger.debug(f"🔍 [TOKEN_VALIDATION] is_active value: {is_active} (type: {type(is_active)})")
    
    if not is_active:
        logger.debug(f"⚠️ [TOKEN_VALIDATION] Token is INACTIVE (deactivated) - INVALID")
        return False
    
    logger.debug(f"✅ [TOKEN_VALIDATION] *** VALIDATION SUCCESS ***")
    logger.debug(f"✅ [TOKEN_VALIDATION] Token {token[:8]}... is VALID and ACTIVE")
    logger.debug("=" * 100)
    return True


# ==============================================================================
# FUNCȚII WORKFLOW MEDICAL - TRACKING & MANAGEMENT
# ==============================================================================

def track_link_view(token: str) -> bool:
    """
    Înregistrează o vizualizare a link-ului de către pacient.
    Actualizează contoarele și timestamp-urile.
    
    Args:
        token: UUID-ul pacientului
        
    Returns:
        bool: True dacă tracking-ul a reușit
    """
    try:
        links = load_patient_links()
        
        if token not in links:
            logger.warning(f"Token inexistent pentru tracking: {token}")
            return False
        
        now = datetime.now().isoformat()
        
        # Incrementăm view_count
        links[token]['view_count'] = links[token].get('view_count', 0) + 1
        
        # Setăm first_viewed_at dacă e prima vizualizare
        if links[token].get('first_viewed_at') is None:
            links[token]['first_viewed_at'] = now
            logger.info(f"🔵 Prima vizualizare pentru link {token[:8]}...")
        
        # Actualizăm last_viewed_at
        links[token]['last_viewed_at'] = now
        
        if save_patient_links(links):
            logger.debug(f"📊 Tracking view: {token[:8]}... (Total: {links[token]['view_count']})")
            return True
        else:
            return False
            
    except Exception as e:
        logger.error(f"Eroare la tracking vizualizare pentru {token}: {e}", exc_info=True)
        return False


def update_link_medical_notes(token: str, medical_notes: str) -> bool:
    """
    Actualizează notițele medicale pentru un link de pacient.
    
    Args:
        token: UUID-ul pacientului
        medical_notes: Notițele medicale (text liber)
        
    Returns:
        bool: True dacă actualizarea a reușit
    """
    try:
        links = load_patient_links()
        
        if token not in links:
            logger.warning(f"Token inexistent pentru actualizare notițe: {token}")
            return False
        
        links[token]['medical_notes'] = medical_notes
        links[token]['notes_updated_at'] = datetime.now().isoformat()
        
        if save_patient_links(links):
            logger.info(f"📝 Notițe medicale actualizate pentru {token[:8]}...")
            return True
        else:
            return False
            
    except Exception as e:
        logger.error(f"Eroare la actualizarea notițelor pentru {token}: {e}", exc_info=True)
        return False


def mark_link_as_sent(token: str, sent: bool = True) -> bool:
    """
    Marchează un link ca trimis (sau netrimis) către pacient.
    
    Args:
        token: UUID-ul pacientului
        sent: True = marcat ca trimis, False = anulare status trimis
        
    Returns:
        bool: True dacă actualizarea a reușit
    """
    try:
        links = load_patient_links()
        
        if token not in links:
            logger.warning(f"Token inexistent pentru marcare trimis: {token}")
            return False
        
        links[token]['sent_status'] = sent
        
        if sent:
            links[token]['sent_at'] = datetime.now().isoformat()
            logger.info(f"📨 Link marcat ca TRIMIS: {token[:8]}...")
        else:
            links[token]['sent_at'] = None
            logger.info(f"🔄 Link marcat ca NETRIMIS: {token[:8]}...")
        
        if save_patient_links(links):
            return True
        else:
            return False
            
    except Exception as e:
        logger.error(f"Eroare la marcarea status trimis pentru {token}: {e}", exc_info=True)
        return False


def get_all_links_for_admin() -> List[Dict]:
    """
    Preia TOATE link-urile cu metadata completă pentru dashboard-ul medical.
    Include: date, notițe, status trimis, vizualizări.
    
    Returns:
        List[Dict]: Listă cu toate link-urile și metadata detaliată
    """
    links = load_patient_links()
    result = []
    
    for token, data in links.items():
        if data.get('is_active', True):
            result.append({
                "token": token,
                "device_name": data.get("device_name", "Unknown"),
                "notes": data.get("notes", ""),
                "created_at": data.get("created_at"),
                "recordings_count": data.get("recordings_count", 0),
                # Metadata medicală extinsă
                "recording_date": data.get("recording_date"),
                "start_time": data.get("start_time"),
                "end_time": data.get("end_time"),
                "medical_notes": data.get("medical_notes", ""),
                "sent_status": data.get("sent_status", False),
                "sent_at": data.get("sent_at"),
                "view_count": data.get("view_count", 0),
                "first_viewed_at": data.get("first_viewed_at"),
                "last_viewed_at": data.get("last_viewed_at"),
                "pdf_paths": data.get("pdf_paths", [])
            })
    
    # Sortăm după created_at (cele mai noi primele)
    result.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    
    logger.debug(f"Dashboard admin: {len(result)} link-uri active returnate.")
    return result


# ==============================================================================
# FUNCȚII PDF - GESTIONARE RAPOARTE PDF
# ==============================================================================

def save_pdf_for_link(token: str, pdf_content: bytes, pdf_filename: str) -> Optional[str]:
    """
    Salvează un raport PDF pentru un link de pacient.
    
    Args:
        token: UUID-ul pacientului
        pdf_content: Conținutul binar al fișierului PDF
        pdf_filename: Numele original al fișierului PDF
        
    Returns:
        str: Calea relativă către PDF-ul salvat sau None dacă eroare
    """
    try:
        # Creăm folderul pdfs/ pentru acest pacient
        patient_folder = os.path.join(PATIENT_DATA_DIR, token)
        pdfs_folder = os.path.join(patient_folder, "pdfs")
        os.makedirs(pdfs_folder, exist_ok=True)
        
        # Sanitizăm numele fișierului
        import re
        safe_filename = re.sub(r'[^\w\s\-\.]', '_', pdf_filename)
        
        # Adăugăm timestamp pentru unicitate
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name_parts = os.path.splitext(safe_filename)
        unique_filename = f"{name_parts[0]}_{timestamp}{name_parts[1]}"
        
        # Calea completă
        pdf_path = os.path.join(pdfs_folder, unique_filename)
        
        # Salvăm fișierul
        with open(pdf_path, 'wb') as f:
            f.write(pdf_content)
        
        # Returnăm calea relativă (pentru portabilitate)
        relative_path = os.path.join("pdfs", unique_filename)
        
        logger.info(f"📄 PDF salvat pentru {token[:8]}...: {unique_filename} ({len(pdf_content)} bytes)")
        return relative_path
        
    except Exception as e:
        logger.error(f"Eroare la salvarea PDF pentru {token}: {e}", exc_info=True)
        return None


def save_pdf_parsed_data(token: str, pdf_path: str, parsed_data: Dict) -> bool:
    """
    Salvează datele parsate din PDF în fișierul de metadata al pacientului.
    
    Args:
        token: UUID-ul pacientului
        pdf_path: Calea relativă către PDF
        parsed_data: Dicționar cu date parsate din PDF (de la pdf_parser)
        
    Returns:
        bool: True dacă salvarea a reușit
    """
    try:
        patient_folder = os.path.join(PATIENT_DATA_DIR, token)
        pdfs_metadata_file = os.path.join(patient_folder, "pdfs_metadata.json")
        
        # Încărcăm metadata existentă sau creăm una nouă
        pdfs_metadata = {}
        if os.path.exists(pdfs_metadata_file):
            with open(pdfs_metadata_file, 'r', encoding='utf-8') as f:
                pdfs_metadata = json.load(f)
        
        # Adăugăm/actualizăm datele pentru acest PDF
        pdfs_metadata[pdf_path] = {
            "pdf_path": pdf_path,
            "parsed_at": datetime.now().isoformat(),
            "data": parsed_data
        }
        
        # Salvăm metadata
        with open(pdfs_metadata_file, 'w', encoding='utf-8') as f:
            json.dump(pdfs_metadata, f, indent=2, ensure_ascii=False)
        
        # Actualizăm și link-ul principal cu calea PDF
        links = load_patient_links()
        if token in links:
            if 'pdf_paths' not in links[token]:
                links[token]['pdf_paths'] = []
            if pdf_path not in links[token]['pdf_paths']:
                links[token]['pdf_paths'].append(pdf_path)
            save_patient_links(links)
        
        logger.info(f"✅ Metadata PDF salvată pentru {token[:8]}...: {pdf_path}")
        return True
        
    except Exception as e:
        logger.error(f"Eroare la salvarea metadata PDF pentru {token}: {e}", exc_info=True)
        return False


def get_pdf_data_for_link(token: str, pdf_path: str = None) -> Optional[Dict]:
    """
    Preia datele parsate din PDF pentru un link de pacient.
    
    Args:
        token: UUID-ul pacientului
        pdf_path: Calea relativă către PDF (opțional - dacă None, returnează toate PDF-urile)
        
    Returns:
        Dict: Date parsate din PDF sau None dacă nu există
    """
    try:
        patient_folder = os.path.join(PATIENT_DATA_DIR, token)
        pdfs_metadata_file = os.path.join(patient_folder, "pdfs_metadata.json")
        
        if not os.path.exists(pdfs_metadata_file):
            logger.debug(f"Nu există PDF-uri pentru {token[:8]}...")
            return None
        
        with open(pdfs_metadata_file, 'r', encoding='utf-8') as f:
            pdfs_metadata = json.load(f)
        
        if pdf_path:
            # Returnăm doar PDF-ul specificat
            return pdfs_metadata.get(pdf_path)
        else:
            # Returnăm toate PDF-urile
            return pdfs_metadata
        
    except Exception as e:
        logger.error(f"Eroare la citirea metadata PDF pentru {token}: {e}", exc_info=True)
        return None


def get_all_pdfs_for_link(token: str) -> List[Dict]:
    """
    Preia toate PDF-urile asociate unui link de pacient.
    
    Args:
        token: UUID-ul pacientului
        
    Returns:
        List[Dict]: Listă cu toate PDF-urile și metadata lor
    """
    try:
        all_pdfs = get_pdf_data_for_link(token)
        
        if not all_pdfs:
            return []
        
        # Convertim dict în list pentru UI
        result = []
        for pdf_path, metadata in all_pdfs.items():
            result.append({
                "pdf_path": pdf_path,
                "parsed_at": metadata.get("parsed_at"),
                "data": metadata.get("data", {})
            })
        
        # Sortăm după data parsing (cele mai recente primele)
        result.sort(key=lambda x: x.get('parsed_at', ''), reverse=True)
        
        logger.debug(f"Găsite {len(result)} PDF-uri pentru {token[:8]}...")
        return result
        
    except Exception as e:
        logger.error(f"Eroare la listarea PDF-urilor pentru {token}: {e}", exc_info=True)
        return []


def delete_pdf_from_link(token: str, pdf_path: str) -> bool:
    """
    Șterge un PDF și metadata asociată dintr-un link de pacient.
    
    Args:
        token: UUID-ul pacientului
        pdf_path: Calea relativă către PDF
        
    Returns:
        bool: True dacă ștergerea a reușit
    """
    try:
        patient_folder = os.path.join(PATIENT_DATA_DIR, token)
        
        # Ștergem fișierul fizic
        full_pdf_path = os.path.join(patient_folder, pdf_path)
        if os.path.exists(full_pdf_path):
            os.remove(full_pdf_path)
            logger.info(f"🗑️ PDF șters: {full_pdf_path}")
        
        # Ștergem din metadata
        pdfs_metadata_file = os.path.join(patient_folder, "pdfs_metadata.json")
        if os.path.exists(pdfs_metadata_file):
            with open(pdfs_metadata_file, 'r', encoding='utf-8') as f:
                pdfs_metadata = json.load(f)
            
            if pdf_path in pdfs_metadata:
                del pdfs_metadata[pdf_path]
                
                with open(pdfs_metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(pdfs_metadata, f, indent=2, ensure_ascii=False)
        
        # Actualizăm link-ul principal
        links = load_patient_links()
        if token in links and 'pdf_paths' in links[token]:
            if pdf_path in links[token]['pdf_paths']:
                links[token]['pdf_paths'].remove(pdf_path)
                save_patient_links(links)
        
        logger.info(f"✅ PDF șters complet pentru {token[:8]}...: {pdf_path}")
        return True
        
    except Exception as e:
        logger.error(f"Eroare la ștergerea PDF pentru {token}: {e}", exc_info=True)
        return False


# ==============================================================================
# INIȚIALIZARE
# ==============================================================================

# Creăm fișierul de link-uri dacă nu există
if not os.path.exists(PATIENT_LINKS_FILE):
    save_patient_links({})
    logger.info(f"Fișier {PATIENT_LINKS_FILE} creat.")

logger.info("✅ Modulul patient_links.py inițializat cu succes.")


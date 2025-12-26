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
PATIENT_LINKS_FILE = "patient_links.json"

# Creăm directorul de bază la import
os.makedirs(PATIENT_DATA_DIR, exist_ok=True)


# ==============================================================================
# FUNCȚII CORE - GESTIONARE LINK-URI
# ==============================================================================

def load_patient_links() -> Dict:
    """
    Încarcă toate link-urile de pacienți din fișierul JSON.
    
    Returns:
        Dict: Dicționar cu token-uri ca chei și metadata ca valori
    """
    if not os.path.exists(PATIENT_LINKS_FILE):
        logger.debug(f"Fișierul {PATIENT_LINKS_FILE} nu există. Se creează unul nou.")
        return {}
    
    try:
        with open(PATIENT_LINKS_FILE, 'r', encoding='utf-8') as f:
            links = json.load(f)
            logger.debug(f"S-au încărcat {len(links)} link-uri de pacienți.")
            return links
    except Exception as e:
        logger.error(f"Eroare la încărcarea link-urilor: {e}", exc_info=True)
        return {}


def save_patient_links(links: Dict) -> bool:
    """
    Salvează toate link-urile de pacienți în fișierul JSON.
    
    Args:
        links: Dicționar cu link-uri
        
    Returns:
        bool: True dacă salvarea a reușit
    """
    try:
        with open(PATIENT_LINKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(links, f, indent=2, ensure_ascii=False)
        logger.debug(f"S-au salvat {len(links)} link-uri de pacienți.")
        return True
    except Exception as e:
        logger.error(f"Eroare la salvarea link-urilor: {e}", exc_info=True)
        return False


def generate_patient_link(device_name: str, notes: str = "", recording_date: str = None, 
                         start_time: str = None, end_time: str = None, pdf_path: str = None) -> Optional[str]:
    """
    Generează un nou link persistent pentru un pacient.
    
    ⚠️ IMPORTANT: Link-ul NU conține date personale (GDPR compliant)
    
    Args:
        device_name: Numele aparatului (ex: "Checkme O2 #3539")
        notes: Notițe medicale opționale (ex: "Apnee severă")
        recording_date: Data înregistrării (ex: "2025-05-02")
        start_time: Ora de început (ex: "23:30")
        end_time: Ora de sfârșit (ex: "06:37")
        pdf_path: Calea către fișierul PDF asociat (opțional)
        
    Returns:
        str: Token-ul UUID generat sau None dacă eroare
    """
    try:
        # Generăm UUID v4 (random, criptografic sigur)
        token = str(uuid.uuid4())
        
        # Creăm folderul pentru acest pacient
        patient_folder = os.path.join(PATIENT_DATA_DIR, token)
        os.makedirs(patient_folder, exist_ok=True)
        
        # Salvăm metadata EXTINSĂ pentru workflow medical
        links = load_patient_links()
        links[token] = {
            "device_name": device_name,
            "notes": notes,
            "created_at": datetime.now().isoformat(),
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
        
        if save_patient_links(links):
            logger.info(f"✅ Link nou generat pentru aparat '{device_name}': {token}")
            return token
        else:
            logger.error("Eroare la salvarea link-ului nou.")
            return None
            
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
    links = load_patient_links()
    patient_data = links.get(token)
    
    if patient_data:
        # Actualizăm last_accessed (backward compatibility)
        patient_data['last_accessed'] = datetime.now().isoformat()
        links[token] = patient_data
        save_patient_links(links)
        logger.debug(f"Link accesat: {token[:8]}...")
        
        # [NEW] Tracking automat vizualizări
        if track_view:
            track_link_view(token)
    else:
        logger.warning(f"Link inexistent: {token}")
    
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
    Preia toate înregistrările pentru un pacient.
    
    Args:
        token: UUID-ul pacientului
        
    Returns:
        List[Dict]: Listă cu metadata fiecărei înregistrări
    """
    patient_folder = os.path.join(PATIENT_DATA_DIR, token)
    recordings_file = os.path.join(patient_folder, "recordings.json")
    
    if not os.path.exists(recordings_file):
        logger.debug(f"Pacientul {token[:8]}... nu are încă înregistrări.")
        return []
    
    try:
        with open(recordings_file, 'r', encoding='utf-8') as f:
            recordings = json.load(f)
            logger.debug(f"Pacientul {token[:8]}... are {len(recordings)} înregistrări.")
            return recordings
    except Exception as e:
        logger.error(f"Eroare la citirea înregistrărilor pentru {token}: {e}", exc_info=True)
        return []


def save_patient_recordings(token: str, recordings: List[Dict]) -> bool:
    """
    Salvează lista de înregistrări pentru un pacient.
    
    Args:
        token: UUID-ul pacientului
        recordings: Listă cu metadata înregistrărilor
        
    Returns:
        bool: True dacă salvarea a reușit
    """
    patient_folder = os.path.join(PATIENT_DATA_DIR, token)
    recordings_file = os.path.join(patient_folder, "recordings.json")
    
    try:
        with open(recordings_file, 'w', encoding='utf-8') as f:
            json.dump(recordings, f, indent=2, ensure_ascii=False)
        
        # Actualizăm contorul în link
        links = load_patient_links()
        if token in links:
            links[token]['recordings_count'] = len(recordings)
            save_patient_links(links)
        
        logger.debug(f"Salvate {len(recordings)} înregistrări pentru pacientul {token[:8]}...")
        return True
        
    except Exception as e:
        logger.error(f"Eroare la salvarea înregistrărilor pentru {token}: {e}", exc_info=True)
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
        # Import R2 storage service
        try:
            from storage_service import upload_patient_csv, r2_client
            r2_available = r2_client.enabled
        except ImportError:
            logger.warning("⚠️ storage_service nu e disponibil - folosim stocare LOCALĂ (EPHEMERAL pe Railway!)")
            r2_available = False
        
        patient_folder = os.path.join(PATIENT_DATA_DIR, token)
        
        # Generăm un ID unic pentru înregistrare
        recording_id = str(uuid.uuid4())[:8]
        
        # PRIORITATE 1: Încercăm să salvăm în R2 (PERSISTENT)
        csv_path = None
        r2_url = None
        
        if r2_available:
            logger.info(f"☁️ Salvare CSV în Cloudflare R2 pentru {token[:8]}...")
            try:
                # Salvăm în R2 cu nume structurat
                r2_filename = f"recording_{recording_id}_{csv_filename}"
                r2_url = upload_patient_csv(token, csv_content, r2_filename)
                
                if r2_url:
                    logger.info(f"✅ CSV salvat în R2: {r2_url}")
                    csv_path = f"r2://{token}/csvs/{r2_filename}"  # Path virtual pentru referință
                else:
                    logger.warning(f"⚠️ Upload R2 eșuat, folosim fallback LOCAL")
                    r2_available = False  # Fallback la local
            except Exception as e:
                logger.error(f"❌ Eroare upload R2: {e} - folosim fallback LOCAL", exc_info=True)
                r2_available = False
        
        # FALLBACK: Salvăm LOCAL (EPHEMERAL pe Railway!)
        if not r2_available or not r2_url:
            logger.warning(f"💾 Salvare CSV LOCAL (EPHEMERAL - va dispărea la redeploy Railway!)")
            os.makedirs(patient_folder, exist_ok=True)
            csv_path = os.path.join(patient_folder, f"recording_{recording_id}.csv")
            with open(csv_path, 'wb') as f:
                f.write(csv_content)
            logger.info(f"⚠️ CSV salvat LOCAL: {csv_path} (TEMPORARY!)")
        
        # Creăm metadata înregistrării
        recording_metadata = {
            "id": recording_id,
            "original_filename": csv_filename,
            "csv_path": csv_path,
            "r2_url": r2_url,  # URL R2 dacă disponibil
            "storage_type": "r2" if r2_available and r2_url else "local",
            "recording_date": recording_date,
            "start_time": start_time,
            "end_time": end_time,
            "uploaded_at": datetime.now().isoformat(),
            "stats": {
                "avg_spo2": avg_spo2,
                "min_spo2": min_spo2,
                "max_spo2": max_spo2
            }
        }
        
        # Adăugăm la lista de înregistrări
        recordings = get_patient_recordings(token)
        recordings.append(recording_metadata)
        
        if save_patient_recordings(token, recordings):
            storage_info = "☁️ R2 (PERSISTENT)" if r2_available and r2_url else "💾 LOCAL (EPHEMERAL!)"
            logger.info(f"✅ Înregistrare adăugată pentru {token[:8]}... → {storage_info}: {csv_filename}")
            return True
        else:
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
                    logger.warning(f"⚠️ Path R2 invalid: {csv_path}")
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
    patient_data = get_patient_link(token)
    
    if not patient_data:
        return False
    
    if not patient_data.get('is_active', True):
        logger.warning(f"Token inactiv: {token[:8]}...")
        return False
    
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


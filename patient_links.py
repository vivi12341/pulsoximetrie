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
        patient_folder = os.path.join(PATIENT_DATA_DIR, token)
        
        # Generăm un ID unic pentru înregistrare
        recording_id = str(uuid.uuid4())[:8]
        
        # Salvăm CSV-ul original
        csv_path = os.path.join(patient_folder, f"recording_{recording_id}.csv")
        with open(csv_path, 'wb') as f:
            f.write(csv_content)
        
        # Creăm metadata înregistrării
        recording_metadata = {
            "id": recording_id,
            "original_filename": csv_filename,
            "csv_path": csv_path,
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
            logger.info(f"✅ Înregistrare adăugată pentru pacientul {token[:8]}...: {csv_filename}")
            return True
        else:
            return False
            
    except Exception as e:
        logger.error(f"Eroare la adăugarea înregistrării pentru {token}: {e}", exc_info=True)
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
                "last_viewed_at": data.get("last_viewed_at")
            })
    
    # Sortăm după created_at (cele mai noi primele)
    result.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    
    logger.debug(f"Dashboard admin: {len(result)} link-uri active returnate.")
    return result


# ==============================================================================
# INIȚIALIZARE
# ==============================================================================

# Creăm fișierul de link-uri dacă nu există
if not os.path.exists(PATIENT_LINKS_FILE):
    save_patient_links({})
    logger.info(f"Fișier {PATIENT_LINKS_FILE} creat.")

logger.info("✅ Modulul patient_links.py inițializat cu succes.")


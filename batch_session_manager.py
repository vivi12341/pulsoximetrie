"""
📊 BATCH SESSION MANAGER - Gestionare Sesiuni Upload & Progres
================================================================

FUNCȚIONALITĂȚI:
- Tracking sesiuni batch cu UUID unic
- Salvare stare procesare (fișiere procesate/eroare)
- Reluare automată din ultimul checkpoint
- Istoric sesiuni cu statistici
- Backup incremental pentru reziliență

STORAGE:
- batch_sessions/{session_id}/
  - session_metadata.json (status, timestamp, total_files)
  - files_progress.json (listă fișiere cu status)
  - processed_files/ (copii CSV procesate)

MODEL DATE:
{
  "session_id": "uuid",
  "created_at": "2025-11-11T20:30:00",
  "updated_at": "2025-11-11T20:35:00",
  "status": "in_progress|completed|failed|paused",
  "total_files": 10,
  "processed_files": 7,
  "failed_files": 1,
  "files": [
    {
      "filename": "Checkme O2 3539_20251007230437.csv",
      "status": "completed|pending|processing|failed",
      "token": "uuid-pacient",
      "processed_at": "2025-11-11T20:32:15",
      "error": null
    }
  ]
}

PRIVACY: Zero date personale, doar metadata tehnică.
"""

import os
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from logger_setup import logger

# Directoare pentru sesiuni batch
BATCH_SESSIONS_DIR = Path("batch_sessions")
BATCH_SESSIONS_DIR.mkdir(exist_ok=True)

# Fișier index global cu toate sesiunile
SESSIONS_INDEX_FILE = BATCH_SESSIONS_DIR / "sessions_index.json"


def create_batch_session(total_files: int, file_list: List[str]) -> str:
    """
    Creează o nouă sesiune de procesare batch.
    
    Args:
        total_files: Numărul total de fișiere pentru procesare
        file_list: Lista cu numele fișierelor
    
    Returns:
        session_id: UUID unic pentru sesiune
    """
    session_id = str(uuid.uuid4())
    session_dir = BATCH_SESSIONS_DIR / session_id
    session_dir.mkdir(exist_ok=True)
    
    # Creare subdirectoare
    (session_dir / "processed_files").mkdir(exist_ok=True)
    
    # Metadata sesiune
    session_metadata = {
        "session_id": session_id,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "status": "pending",
        "total_files": total_files,
        "processed_files": 0,
        "failed_files": 0,
        "paused_files": 0
    }
    
    # Lista fișiere cu status inițial
    files_progress = {
        "files": [
            {
                "filename": filename,
                "status": "pending",
                "token": None,
                "processed_at": None,
                "error": None,
                "pdf_associated": None
            }
            for filename in file_list
        ]
    }
    
    # Salvare metadata
    with open(session_dir / "session_metadata.json", "w", encoding="utf-8") as f:
        json.dump(session_metadata, f, indent=2, ensure_ascii=False)
    
    with open(session_dir / "files_progress.json", "w", encoding="utf-8") as f:
        json.dump(files_progress, f, indent=2, ensure_ascii=False)
    
    # Actualizare index global
    _update_sessions_index(session_id, session_metadata)
    
    logger.info(f"✅ Sesiune batch creată: {session_id} ({total_files} fișiere)")
    return session_id


def update_file_status(
    session_id: str,
    filename: str,
    status: str,
    token: Optional[str] = None,
    error: Optional[str] = None,
    pdf_associated: Optional[str] = None
) -> bool:
    """
    Actualizează statusul unui fișier în sesiunea batch.
    
    Args:
        session_id: UUID sesiune
        filename: Numele fișierului
        status: completed|processing|failed|pending
        token: Token pacient (dacă succesat)
        error: Mesaj eroare (dacă eșuat)
        pdf_associated: Numele PDF-ului asociat (dacă există)
    
    Returns:
        True dacă actualizare reușită
    """
    session_dir = BATCH_SESSIONS_DIR / session_id
    
    if not session_dir.exists():
        logger.error(f"❌ Sesiune {session_id} nu există")
        return False
    
    # Citire progress actual
    progress_file = session_dir / "files_progress.json"
    with open(progress_file, "r", encoding="utf-8") as f:
        files_progress = json.load(f)
    
    # Găsire și actualizare fișier
    file_found = False
    for file_entry in files_progress["files"]:
        if file_entry["filename"] == filename:
            file_entry["status"] = status
            file_entry["processed_at"] = datetime.now().isoformat()
            if token:
                file_entry["token"] = token
            if error:
                file_entry["error"] = error
            if pdf_associated:
                file_entry["pdf_associated"] = pdf_associated
            file_found = True
            break
    
    if not file_found:
        logger.warning(f"⚠️ Fișier {filename} nu găsit în sesiune {session_id}")
        return False
    
    # Salvare progress actualizat
    with open(progress_file, "w", encoding="utf-8") as f:
        json.dump(files_progress, f, indent=2, ensure_ascii=False)
    
    # Actualizare metadata sesiune (contoare)
    _update_session_counters(session_id)
    
    logger.info(f"📝 Actualizat: {filename} → {status} (sesiune {session_id[:8]}...)")
    return True


def get_session_progress(session_id: str) -> Optional[Dict]:
    """
    Obține progresul curent al sesiunii.
    
    Returns:
        Dict cu metadata și progress sau None
    """
    session_dir = BATCH_SESSIONS_DIR / session_id
    
    if not session_dir.exists():
        return None
    
    # Citire metadata
    with open(session_dir / "session_metadata.json", "r", encoding="utf-8") as f:
        metadata = json.load(f)
    
    # Citire progress fișiere
    with open(session_dir / "files_progress.json", "r", encoding="utf-8") as f:
        files_progress = json.load(f)
    
    return {
        "metadata": metadata,
        "files": files_progress["files"]
    }


def get_pending_files(session_id: str) -> List[Dict]:
    """
    Obține lista fișierelor neprocesate (pending) din sesiune.
    Folosit pentru reluare automată.
    
    Returns:
        Lista cu fișiere pending
    """
    progress = get_session_progress(session_id)
    
    if not progress:
        return []
    
    pending_files = [
        file_entry for file_entry in progress["files"]
        if file_entry["status"] == "pending"
    ]
    
    logger.info(f"📋 Găsite {len(pending_files)} fișiere pending în sesiune {session_id[:8]}...")
    return pending_files


def get_all_sessions(limit: int = 20) -> List[Dict]:
    """
    Obține istoricul sesiunilor batch (cele mai recente).
    
    Args:
        limit: Număr maxim de sesiuni de returnat
    
    Returns:
        Lista cu metadata sesiuni, sortate descrescător după dată
    """
    if not SESSIONS_INDEX_FILE.exists():
        return []
    
    with open(SESSIONS_INDEX_FILE, "r", encoding="utf-8") as f:
        sessions_index = json.load(f)
    
    # Sortare după created_at (descrescător)
    sessions_list = list(sessions_index.get("sessions", {}).values())
    sessions_list.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return sessions_list[:limit]


def mark_session_completed(session_id: str) -> bool:
    """
    Marchează sesiunea ca fiind completată.
    """
    session_dir = BATCH_SESSIONS_DIR / session_id
    
    if not session_dir.exists():
        return False
    
    # Citire metadata
    metadata_file = session_dir / "session_metadata.json"
    with open(metadata_file, "r", encoding="utf-8") as f:
        metadata = json.load(f)
    
    metadata["status"] = "completed"
    metadata["updated_at"] = datetime.now().isoformat()
    
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    # Actualizare index
    _update_sessions_index(session_id, metadata)
    
    logger.info(f"✅ Sesiune {session_id[:8]}... marcată ca COMPLETĂ")
    return True


def _update_session_counters(session_id: str):
    """
    Actualizează contoarele (processed_files, failed_files) din metadata.
    """
    session_dir = BATCH_SESSIONS_DIR / session_id
    
    # Citire progress
    with open(session_dir / "files_progress.json", "r", encoding="utf-8") as f:
        files_progress = json.load(f)
    
    # Calcul contoare
    completed = sum(1 for f in files_progress["files"] if f["status"] == "completed")
    failed = sum(1 for f in files_progress["files"] if f["status"] == "failed")
    processing = sum(1 for f in files_progress["files"] if f["status"] == "processing")
    
    # Citire și actualizare metadata
    metadata_file = session_dir / "session_metadata.json"
    with open(metadata_file, "r", encoding="utf-8") as f:
        metadata = json.load(f)
    
    metadata["processed_files"] = completed
    metadata["failed_files"] = failed
    metadata["updated_at"] = datetime.now().isoformat()
    
    # Actualizare status sesiune
    if completed + failed == metadata["total_files"]:
        metadata["status"] = "completed"
    elif processing > 0:
        metadata["status"] = "in_progress"
    
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    # Actualizare index global
    _update_sessions_index(session_id, metadata)


def _update_sessions_index(session_id: str, metadata: Dict):
    """
    Actualizează index-ul global cu toate sesiunile.
    """
    # Citire index existent
    if SESSIONS_INDEX_FILE.exists():
        with open(SESSIONS_INDEX_FILE, "r", encoding="utf-8") as f:
            sessions_index = json.load(f)
    else:
        sessions_index = {"sessions": {}}
    
    # Actualizare sesiune
    sessions_index["sessions"][session_id] = {
        "session_id": session_id,
        "created_at": metadata.get("created_at"),
        "updated_at": metadata.get("updated_at"),
        "status": metadata.get("status"),
        "total_files": metadata.get("total_files"),
        "processed_files": metadata.get("processed_files", 0),
        "failed_files": metadata.get("failed_files", 0)
    }
    
    # Salvare index
    with open(SESSIONS_INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(sessions_index, f, indent=2, ensure_ascii=False)


logger.info("✅ Modulul batch_session_manager.py inițializat cu succes.")


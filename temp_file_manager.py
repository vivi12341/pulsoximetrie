# ==============================================================================
# temp_file_manager.py - WORKAROUND pentru problema dcc.Store
# ------------------------------------------------------------------------------
# PROBLEMA: dcc.Store nu propagă datele corect între callback-uri în Railway
# SOLUȚIE: Salvăm fișierele uploadate direct pe disk într-un folder temporar
#          și folosim session ID pentru tracking
# ==============================================================================

import os
import tempfile
import base64
import json
import uuid
from pathlib import Path
from typing import List, Dict, Optional
from logger_setup import logger

# Folder global pentru fișiere temporare uploadate
TEMP_UPLOAD_FOLDER = Path(tempfile.gettempdir()) / "pulsoximetrie_uploads"
TEMP_UPLOAD_FOLDER.mkdir(exist_ok=True)

# Cleanup la pornire (șterge sesiuni vechi > 24h)
def cleanup_old_sessions():
    """Șterge sesiuni vechi > 24h la pornirea aplicației."""
    import time
    cutoff_time = time.time() - (24 * 3600)  # 24 ore
    
    try:
        for session_folder in TEMP_UPLOAD_FOLDER.iterdir():
            if session_folder.is_dir():
                folder_mtime = session_folder.stat().st_mtime
                if folder_mtime < cutoff_time:
                    import shutil
                    shutil.rmtree(session_folder)
                    logger.warning(f"🗑️ Cleanup: Șters sesiune veche: {session_folder.name}")
    except Exception as e:
        logger.error(f"Eroare cleanup sesiuni vechi: {e}")

# Executăm cleanup la import
cleanup_old_sessions()


class TempFileManager:
    """
    Manager pentru fișiere temporare uploadate.
    Înlocuiește dcc.Store cu salvare pe disk.
    """
    
    def __init__(self, session_id: Optional[str] = None):
        """
        Inițializează manager cu session ID.
        
        Args:
            session_id: ID unic sesiune (generat automat dacă None)
        """
        self.session_id = session_id or str(uuid.uuid4())
        self.session_folder = TEMP_UPLOAD_FOLDER / self.session_id
        self.session_folder.mkdir(exist_ok=True)
        self.metadata_file = self.session_folder / "metadata.json"
        
        logger.warning(f"📁 TempFileManager init: session_id={self.session_id}")
        logger.warning(f"📁 Session folder: {self.session_folder}")
    
    def save_uploaded_files(self, list_of_contents: List[str], list_of_names: List[str]) -> int:
        """
        Salvează fișierele uploadate pe disk.
        
        Args:
            list_of_contents: Listă cu conținutul fișierelor (base64)
            list_of_names: Listă cu numele fișierelor
            
        Returns:
            Numărul de fișiere salvate
        """
        if not list_of_contents or not list_of_names:
            logger.error("❌ save_uploaded_files: liste goale!")
            return 0
        
        metadata = self._load_metadata()
        saved_count = 0
        
        for content, filename in zip(list_of_contents, list_of_names):
            # Skip duplicate
            if any(f['filename'] == filename for f in metadata):
                logger.warning(f"⚠️ Fișier duplicat (skip): {filename}")
                continue
            
            try:
                # Decode base64 content
                content_type, content_string = content.split(',')
                decoded_content = base64.b64decode(content_string)
                
                # Salvează fișierul pe disk
                file_path = self.session_folder / filename
                with open(file_path, 'wb') as f:
                    f.write(decoded_content)
                
                # Adaugă metadata
                file_type = 'CSV' if filename.lower().endswith('.csv') else 'PDF'
                metadata.append({
                    'filename': filename,
                    'size': len(decoded_content),
                    'type': file_type,
                    'path': str(file_path)
                })
                
                saved_count += 1
                logger.warning(f"✅ Salvat fișier: {filename} ({file_type}) - {len(decoded_content)} bytes")
                
            except Exception as e:
                logger.error(f"❌ Eroare salvare {filename}: {e}")
        
        # Salvează metadata
        self._save_metadata(metadata)
        logger.warning(f"📊 Total fișiere salvate: {saved_count}")
        
        return saved_count
    
    def get_uploaded_files(self) -> List[Dict]:
        """
        Citește lista de fișiere uploadate din metadata.
        
        Returns:
            Listă cu metadata fișiere (fără content, doar info)
        """
        metadata = self._load_metadata()
        logger.warning(f"📦 get_uploaded_files: {len(metadata)} fișiere găsite")
        return metadata
    
    def get_files_for_processing(self) -> List[str]:
        """
        Returnează căile complete către fișierele uploadate pentru procesare.
        
        Returns:
            Listă cu path-uri absolute către fișiere CSV și PDF
        """
        metadata = self._load_metadata()
        paths = [f['path'] for f in metadata if os.path.exists(f['path'])]
        logger.warning(f"📤 get_files_for_processing: {len(paths)} fișiere pentru procesare")
        return paths
    
    def clear_session(self):
        """Șterge toate fișierele și metadata sesiunii."""
        import shutil
        try:
            if self.session_folder.exists():
                shutil.rmtree(self.session_folder)
                logger.warning(f"🗑️ Sesiune ștearsă: {self.session_id}")
                # Recreează folder gol
                self.session_folder.mkdir(exist_ok=True)
        except Exception as e:
            logger.error(f"Eroare ștergere sesiune: {e}")
    
    def _load_metadata(self) -> List[Dict]:
        """Încarcă metadata din fișier JSON."""
        if not self.metadata_file.exists():
            return []
        
        try:
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Eroare citire metadata: {e}")
            return []
    
    def _save_metadata(self, metadata: List[Dict]):
        """Salvează metadata în fișier JSON."""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            logger.warning(f"💾 Metadata salvată: {len(metadata)} fișiere")
        except Exception as e:
            logger.error(f"Eroare salvare metadata: {e}")


def get_manager(session_id: str) -> TempFileManager:
    """
    Factory function pentru TempFileManager.
    
    Args:
        session_id: ID sesiune (din dcc.Store)
        
    Returns:
        Instanță TempFileManager
    """
    return TempFileManager(session_id)


# ==============================================================================
# storage_service.py
# ------------------------------------------------------------------------------
# ROL: Gestionează stocare fișiere în Cloudflare R2 (S3-compatible)
#      Implementează upload/download/delete pentru CSV, PDF, PNG
#
# ARHITECTURĂ:
#   - Cloudflare R2: Storage persistent cloud (alternativă S3)
#   - boto3: Client Python pentru operații S3-compatible
#   - Fallback local: Dacă R2 nu e disponibil, salvează local
#
# RESPECTĂ: .cursorrules - Privacy by Design (zero date personale!)
# ==============================================================================

import os
import io
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError, BotoCoreError
from typing import Optional, BinaryIO, Union
from logger_setup import logger

# --- Configurare R2 din Environment Variables ---
R2_ENABLED = os.getenv('R2_ENABLED', 'False').lower() == 'true'
R2_ENDPOINT = os.getenv('R2_ENDPOINT', '')
R2_ACCESS_KEY_ID = os.getenv('R2_ACCESS_KEY_ID', '')
R2_SECRET_ACCESS_KEY = os.getenv('R2_SECRET_ACCESS_KEY', '')
R2_BUCKET_NAME = os.getenv('R2_BUCKET_NAME', 'pulsoximetrie-files')
R2_REGION = os.getenv('R2_REGION', 'auto')

# Fallback pentru stocare locală
LOCAL_STORAGE_DIR = "patient_data"


# ==============================================================================
# CLOUDFLARE R2 CLIENT - S3-COMPATIBLE
# ==============================================================================

class CloudflareR2Client:
    """
    Client pentru interacțiune cu Cloudflare R2 (S3-compatible storage).
    
    Features:
    - Upload fișiere (CSV, PDF, PNG)
    - Download fișiere (stream sau bytes)
    - Delete fișiere
    - List fișiere din folder
    - Generate signed URLs (opțional)
    """
    
    def __init__(self):
        """Inițializează client-ul R2 cu credențiale din environment."""
        self.enabled = R2_ENABLED
        self.bucket_name = R2_BUCKET_NAME
        self.client = None
        
        if not self.enabled:
            logger.warning("⚠️ Cloudflare R2 DEZACTIVAT - folosim stocare LOCALĂ")
            return
        
        if not all([R2_ENDPOINT, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY]):
            logger.error("❌ Credențiale R2 incomplete! Setează R2_ENDPOINT, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY")
            self.enabled = False
            return
        
        try:
            # Inițializare client boto3 pentru R2
            self.client = boto3.client(
                's3',
                endpoint_url=R2_ENDPOINT,
                aws_access_key_id=R2_ACCESS_KEY_ID,
                aws_secret_access_key=R2_SECRET_ACCESS_KEY,
                region_name=R2_REGION,
                config=Config(signature_version='s3v4')
            )
            
            # Test conexiune (verifică dacă bucket-ul există)
            self.client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"✅ [R2_TRACE_INIT] Cloudflare R2 conectat cu succes!")
            logger.info(f"   - Endpoint: {R2_ENDPOINT}")
            logger.info(f"   - Bucket: {self.bucket_name}")
            logger.info(f"   - Region: {R2_REGION}")
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == '404':
                logger.error(f"❌ Bucket R2 '{self.bucket_name}' nu există! Creează-l în Cloudflare Dashboard.")
            elif error_code == '403':
                logger.error(f"❌ Acces refuzat la bucket '{self.bucket_name}'. Verifică permisiunile token-ului R2.")
            else:
                logger.error(f"❌ Eroare R2: {e}", exc_info=True)
            self.enabled = False
            
        except BotoCoreError as e:
            logger.error(f"❌ Eroare boto3: {e}", exc_info=True)
            self.enabled = False
    
    
    def upload_file(self, file_content: Union[bytes, BinaryIO], key: str, 
                   content_type: str = 'application/octet-stream') -> Optional[str]:
        """
        Uploadează un fișier în R2.
        
        Args:
            file_content: Conținutul fișierului (bytes sau file-like object)
            key: Calea în bucket (ex: "abc123/csvs/file.csv")
            content_type: MIME type (ex: "text/csv", "application/pdf", "image/png")
            
        Returns:
            str: URL-ul fișierului uploadat sau None dacă eroare
        """
        if not self.enabled:
            logger.warning(f"⚠️ R2 dezactivat - fișierul {key} NU va fi uploadat în cloud")
            return self._save_local_fallback(file_content, key)
        
        try:
            # Convertim la bytes dacă e file-like object
            if hasattr(file_content, 'read'):
                file_content = file_content.read()
            
            file_size_bytes = len(file_content)
            file_size_mb = file_size_bytes / (1024 * 1024)
            logger.info(f"🚀 [R2_TRACE_UPLOAD] START Upload: {key} | Size: {file_size_mb:.2f} MB ({file_size_bytes} bytes)")
            
            # Upload către R2
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=file_content,
                ContentType=content_type
            )
            
            logger.info(f"✅ [R2_TRACE_UPLOAD] SUCCESS Upload: {key} | Size: {file_size_mb:.2f} MB")
            
            # Returnăm URL-ul (format: https://bucket.endpoint/key)
            url = f"{R2_ENDPOINT}/{self.bucket_name}/{key}"
            return url
            
        except ClientError as e:
            logger.error(f"❌ [R2_TRACE_UPLOAD] FAIL Upload R2 pentru {key}: {e}", exc_info=True)
            # Fallback: salvăm local
            return self._save_local_fallback(file_content, key)
    
    
    def download_file(self, key: str) -> Optional[bytes]:
        """
        Descarcă un fișier din R2.
        
        Args:
            key: Calea în bucket (ex: "abc123/csvs/file.csv")
            
        Returns:
            bytes: Conținutul fișierului sau None dacă eroare
        """
        if not self.enabled:
            logger.warning(f"⚠️ R2 dezactivat - încercare download local pentru {key}")
            return self._read_local_fallback(key)
        
        try:
            logger.info(f"🔽 [R2_TRACE_DOWNLOAD] START Download: {key}")
            response = self.client.get_object(
                Bucket=self.bucket_name,
                Key=key
            )
            
            file_content = response['Body'].read()
            file_size_mb = len(file_content) / (1024 * 1024)
            logger.info(f"✅ [R2_TRACE_DOWNLOAD] SUCCESS Download: {key} | Size: {file_size_mb:.2f} MB")
            
            return file_content
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == 'NoSuchKey':
                logger.warning(f"⚠️ [R2_TRACE_DOWNLOAD] NoSuchKey - Fișierul nu există în R2: {key}")
            else:
                logger.error(f"❌ [R2_TRACE_DOWNLOAD] FAIL Download R2 pentru {key}: {e}", exc_info=True)
            
            # Fallback: citim local
            return self._read_local_fallback(key)
    
    
    def delete_file(self, key: str) -> bool:
        """
        Șterge un fișier din R2.
        
        Args:
            key: Calea în bucket (ex: "abc123/csvs/file.csv")
            
        Returns:
            bool: True dacă șters cu succes, False altfel
        """
        if not self.enabled:
            logger.warning(f"⚠️ R2 dezactivat - ștergere locală pentru {key}")
            return self._delete_local_fallback(key)
        
        try:
            logger.info(f"🗑️ [R2_TRACE_DELETE] Attempt delete: {key}")
            self.client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )
            logger.info(f"✅ [R2_TRACE_DELETE] SUCCESS Delete: {key}")
            return True
            
        except ClientError as e:
            logger.error(f"❌ Eroare ștergere R2 pentru {key}: {e}", exc_info=True)
            return False
    
    
    def list_files(self, prefix: str = "") -> list[str]:
        """
        Listează fișierele dintr-un folder R2.
        
        Args:
            prefix: Prefixul căii (ex: "abc123/csvs/")
            
        Returns:
            list: Lista de chei (căi) ale fișierelor
        """
        if not self.enabled:
            logger.warning(f"⚠️ R2 dezactivat - listare locală pentru {prefix}")
            return self._list_local_fallback(prefix)
        
        try:
            response = self.client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            files = [obj['Key'] for obj in response.get('Contents', [])]
            logger.info(f"📂 Găsite {len(files)} fișiere în R2 cu prefix '{prefix}'")
            return files
            
        except ClientError as e:
            logger.error(f"❌ Eroare listare R2 pentru {prefix}: {e}", exc_info=True)
            return []
    
    
    def generate_presigned_url(self, key: str, expiration: int = 3600) -> Optional[str]:
        """
        Generează un URL cu semnătură temporară pentru acces direct (opțional).
        
        Args:
            key: Calea în bucket
            expiration: Timp de expirare în secunde (default: 1 oră)
            
        Returns:
            str: URL signed sau None
        """
        if not self.enabled:
            logger.warning(f"⚠️ R2 dezactivat - nu se poate genera URL signed pentru {key}")
            return None
        
        try:
            url = self.client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': key},
                ExpiresIn=expiration
            )
            logger.info(f"🔗 URL signed generat pentru {key} (expiră în {expiration}s)")
            return url
            
        except ClientError as e:
            logger.error(f"❌ Eroare generare URL signed pentru {key}: {e}", exc_info=True)
            return None
    
    
    # ==============================================================================
    # FALLBACK - STOCARE LOCALĂ (dacă R2 nu e disponibil)
    # ==============================================================================
    
    def _save_local_fallback(self, content: bytes, key: str) -> Optional[str]:
        """Salvează fișierul local ca fallback."""
        try:
            local_path = os.path.join(LOCAL_STORAGE_DIR, key)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            with open(local_path, 'wb') as f:
                f.write(content)
            
            logger.info(f"💾 Fișier salvat LOCAL (fallback): {local_path}")
            return local_path
            
        except Exception as e:
            logger.error(f"❌ Eroare salvare locală pentru {key}: {e}", exc_info=True)
            return None
    
    
    def _read_local_fallback(self, key: str) -> Optional[bytes]:
        """Citește fișierul local ca fallback."""
        try:
            local_path = os.path.join(LOCAL_STORAGE_DIR, key)
            
            if not os.path.exists(local_path):
                logger.warning(f"⚠️ Fișier inexistent local: {local_path}")
                return None
            
            with open(local_path, 'rb') as f:
                content = f.read()
            
            logger.info(f"📂 Fișier citit LOCAL (fallback): {local_path}")
            return content
            
        except Exception as e:
            logger.error(f"❌ Eroare citire locală pentru {key}: {e}", exc_info=True)
            return None
    
    
    def _delete_local_fallback(self, key: str) -> bool:
        """Șterge fișierul local ca fallback."""
        try:
            local_path = os.path.join(LOCAL_STORAGE_DIR, key)
            
            if os.path.exists(local_path):
                os.remove(local_path)
                logger.info(f"🗑️ Fișier șters LOCAL (fallback): {local_path}")
                return True
            else:
                logger.warning(f"⚠️ Fișier inexistent local pentru ștergere: {local_path}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Eroare ștergere locală pentru {key}: {e}", exc_info=True)
            return False
    
    
    def _list_local_fallback(self, prefix: str) -> list[str]:
        """Listează fișierele locale ca fallback."""
        try:
            local_path = os.path.join(LOCAL_STORAGE_DIR, prefix)
            
            if not os.path.exists(local_path):
                return []
            
            files = []
            for root, _, filenames in os.walk(local_path):
                for filename in filenames:
                    full_path = os.path.join(root, filename)
                    # Convertim calea în format key (relativ la LOCAL_STORAGE_DIR)
                    key = os.path.relpath(full_path, LOCAL_STORAGE_DIR).replace('\\', '/')
                    files.append(key)
            
            logger.info(f"📂 Găsite {len(files)} fișiere LOCAL (fallback) cu prefix '{prefix}'")
            return files
            
        except Exception as e:
            logger.error(f"❌ Eroare listare locală pentru {prefix}: {e}", exc_info=True)
            return []


# ==============================================================================
# INSTANȚĂ GLOBALĂ - SINGLETON
# ==============================================================================

# Creăm o instanță globală pentru a fi folosită în toată aplicația
r2_client = CloudflareR2Client()


# ==============================================================================
# FUNCȚII HELPER - INTERFAȚĂ SIMPLIFICATĂ
# ==============================================================================

def upload_patient_csv(token: str, csv_content: bytes, filename: str) -> Optional[str]:
    """
    Uploadează CSV pacient în R2.
    
    Args:
        token: UUID pacient
        csv_content: Conținutul CSV (bytes)
        filename: Numele fișierului original
        
    Returns:
        str: URL sau calea fișierului
    """
    key = f"{token}/csvs/{filename}"
    return r2_client.upload_file(csv_content, key, content_type='text/csv')


def upload_patient_pdf(token: str, pdf_content: bytes, filename: str) -> Optional[str]:
    """
    Uploadează PDF raport pacient în R2.
    
    Args:
        token: UUID pacient
        pdf_content: Conținutul PDF (bytes)
        filename: Numele fișierului original
        
    Returns:
        str: URL sau calea fișierului
    """
    key = f"{token}/pdfs/{filename}"
    return r2_client.upload_file(pdf_content, key, content_type='application/pdf')


def upload_patient_plot(token: str, plot_content: bytes, filename: str) -> Optional[str]:
    """
    Uploadează grafic PNG pacient în R2.
    
    Args:
        token: UUID pacient
        plot_content: Conținutul PNG (bytes)
        filename: Numele fișierului original
        
    Returns:
        str: URL sau calea fișierului
    """
    key = f"{token}/plots/{filename}"
    return r2_client.upload_file(plot_content, key, content_type='image/png')


def download_patient_file(token: str, file_type: str, filename: str) -> Optional[bytes]:
    """
    Descarcă un fișier pacient din R2.
    
    Args:
        token: UUID pacient
        file_type: Tipul fișierului ('csvs', 'pdfs', 'plots')
        filename: Numele fișierului
        
    Returns:
        bytes: Conținutul fișierului sau None
    """
    key = f"{token}/{file_type}/{filename}"
    return r2_client.download_file(key)


def list_patient_files(token: str, file_type: str = "") -> list[str]:
    """
    Listează fișierele unui pacient.
    
    Args:
        token: UUID pacient
        file_type: Tipul fișierelor ('csvs', 'pdfs', 'plots') sau '' pentru toate
        
    Returns:
        list: Lista de fișiere
    """
    prefix = f"{token}/{file_type}" if file_type else f"{token}/"
    return r2_client.list_files(prefix)


def delete_patient_folder(token: str) -> bool:
    """
    Șterge TOATE fișierele unui pacient (DANGER ZONE!).
    
    Args:
        token: UUID pacient
        
    Returns:
        bool: True dacă șters cu succes
    """
    try:
        files = list_patient_files(token)
        
        for file_key in files:
            r2_client.delete_file(file_key)
        
        logger.info(f"🗑️ Folder pacient {token[:8]}... șters complet ({len(files)} fișiere)")
        return True
        
    except Exception as e:
        logger.error(f"❌ Eroare ștergere folder pacient {token[:8]}...: {e}", exc_info=True)
        return False


# ==============================================================================
# STATUS CHECK - DEBUGGING
# ==============================================================================

def get_storage_status() -> dict:
    """
    Returnează statusul storage-ului (R2 sau local).
    
    Returns:
        dict: Informații despre storage
    """
    return {
        "r2_enabled": r2_client.enabled,
        "r2_endpoint": R2_ENDPOINT if r2_client.enabled else "N/A",
        "r2_bucket": R2_BUCKET_NAME if r2_client.enabled else "N/A",
        "fallback_storage": LOCAL_STORAGE_DIR,
        "mode": "Cloudflare R2" if r2_client.enabled else "Local Storage (Fallback)"
    }


if __name__ == "__main__":
    # Test rapid pentru verificare configurare
    logger.info("=== TEST CLOUDFLARE R2 STORAGE ===")
    status = get_storage_status()
    
    for key, value in status.items():
        logger.info(f"  {key}: {value}")
    
    if r2_client.enabled:
        logger.info("✅ Cloudflare R2 este ACTIV și funcțional!")
    else:
        logger.warning("⚠️ Cloudflare R2 este DEZACTIVAT - folosim stocare locală")


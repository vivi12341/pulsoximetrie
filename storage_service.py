# ==============================================================================
# storage_service.py
# ------------------------------------------------------------------------------
# ROL: Gestionează stocare fișiere în S3-Compatible Storage (ex: Scaleway, R2, AWS)
#      Implementează upload/download/delete pentru CSV, PDF, PNG
#
# ARHITECTURĂ:
#   - S3 Storage: Storage persistent cloud
#   - boto3: Client Python pentru operații S3-compatible
#   - Fallback local: Dacă S3 nu e disponibil, salvează local
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

# --- Configurare S3 din Environment Variables ---
# NOTĂ: Suportă 3 naming conventions:
#   1. S3_* (generic, prioritate 1)
#   2. R2_* (Cloudflare R2 legacy, prioritate 2)
#   3. SCW_* (Scaleway Object Storage, prioritate 3)

# Helper: Detectăm dacă folosim Scaleway
SCW_ACCESS_KEY = os.getenv('SCW_ACCESS_KEY', '')
SCW_SECRET_KEY = os.getenv('SCW_SECRET_KEY', '')
SCW_REGION = os.getenv('SCW_DEFAULT_REGION', os.getenv('SCW_REGION', 'fr-par'))  # Default: Paris
SCW_BUCKET = os.getenv('SCW_BUCKET_NAME', 'pulsoximetrie')

# Dacă avem variabile SCW, construim endpoint-ul Scaleway automat
if SCW_ACCESS_KEY and SCW_SECRET_KEY:
    SCW_ENDPOINT = f"https://s3.{SCW_REGION}.scw.cloud"
    logger.warning(f"🔍 [SCALEWAY_DETECTED] Auto-constructing endpoint: {SCW_ENDPOINT}")
else:
    SCW_ENDPOINT = ''

# Fallback chain: S3_* → R2_* → SCW_*
S3_ENABLED = os.getenv('S3_ENABLED', os.getenv('R2_ENABLED', 'True' if SCW_ACCESS_KEY else 'False')).lower() == 'true'
S3_ENDPOINT = os.getenv('S3_ENDPOINT', os.getenv('R2_ENDPOINT', SCW_ENDPOINT))
S3_ACCESS_KEY_ID = os.getenv('S3_ACCESS_KEY_ID', os.getenv('R2_ACCESS_KEY_ID', SCW_ACCESS_KEY))
S3_SECRET_ACCESS_KEY = os.getenv('S3_SECRET_ACCESS_KEY', os.getenv('R2_SECRET_ACCESS_KEY', SCW_SECRET_KEY))
S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME', os.getenv('R2_BUCKET_NAME', SCW_BUCKET))
S3_REGION = os.getenv('S3_REGION', os.getenv('R2_REGION', SCW_REGION))

# Fallback pentru stocare locală
LOCAL_STORAGE_DIR = "patient_data"


# ==============================================================================
# S3 GENERIC CLIENT - S3-COMPATIBLE
# ==============================================================================

class S3StorageClient:
    """
    Client generic pentru interacțiune cu orice S3-compatible storage (Scaleway, R2, AWS).
    
    Features:
    - Upload fișiere (CSV, PDF, PNG)
    - Download fișiere (stream sau bytes)
    - Delete fișiere
    - List fișiere din folder
    - Generate signed URLs (opțional)
    """
    
    def __init__(self):
        """Inițializează client-ul S3 cu credențiale din environment."""
        self.enabled = S3_ENABLED
        self.bucket_name = S3_BUCKET_NAME
        self.client = None
        self.init_error = None # [DIAGNOSTIC] Capture exact error
        
        if not self.enabled:
            self.init_error = "S3_ENABLED env var is False/Missing"
            logger.warning("⚠️ S3 Storage DEZACTIVAT - folosim stocare LOCALĂ")
            return
        
        if not all([S3_ENDPOINT, S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY]):
            self.init_error = "Missing Credentials (ENDPOINT/KEY/SECRET)"
            logger.error("❌ Credențiale S3 incomplete! Setează S3_ENDPOINT, S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY")
            self.enabled = False
            return
        
        try:
            # Inițializare client boto3 pentru S3
            self.client = boto3.client(
                's3',
                endpoint_url=S3_ENDPOINT,
                aws_access_key_id=S3_ACCESS_KEY_ID,
                aws_secret_access_key=S3_SECRET_ACCESS_KEY,
                region_name=S3_REGION,
                config=Config(signature_version='s3v4')
            )
            
            # [ITERATION 5] Test conexiune - try HEAD, but don't fail if 403
            try:
                self.client.head_bucket(Bucket=self.bucket_name)
                logger.warning(f"✅ [S3_TRACE_INIT] S3 Storage conectat cu succes! (Read Access OK)")
            except ClientError as head_err:
                error_code = head_err.response.get('Error', {}).get('Code', 'Unknown')
                logger.warning(f"⚠️ [S3_TRACE_INIT] head_bucket FAILED: {error_code}")
                if error_code == '403':
                    logger.warning(f"⚠️ [S3_READ_PERM] Token lacks READ permission (head_bucket denied)")
                    logger.warning(f"⚠️ [S3_READ_PERM] Will still attempt WRITE test...")
                elif error_code == '404':
                    logger.critical(f"❌ [S3_BUCKET] Bucket '{self.bucket_name}' NOT FOUND!")
                    self.init_error = f"Bucket '{self.bucket_name}' not found"
                    self.enabled = False
                    return
                # Don't disable S3 yet - maybe write works even if read doesn't
            
            logger.warning(f"   - Endpoint: {S3_ENDPOINT}")
            logger.warning(f"   - Bucket: {self.bucket_name}")
            logger.warning(f"   - Region: {S3_REGION}")
            
            # [ITERATION 5] Check Write Permissions ALWAYS (even if head failed)
            self._check_write_permission()
            
            # [ITERATION 2] Log boto3 client configuration details
            logger.warning(f"🔍 [S3_CONFIG] Signature Version: s3v4")
            logger.warning(f"🔍 [S3_CONFIG] Using boto3 client with endpoint: {S3_ENDPOINT}")
            
            # If we got here without errors, consider S3 enabled
            if self.init_error is None:
                self.init_error = None  # Explicitly clear
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == '404':
                msg = f"Bucket '{self.bucket_name}' NOT FOUND (404)"
            elif error_code == '403':
                msg = f"Access DENIED to bucket '{self.bucket_name}' (403) - Check Permissions"
            else:
                msg = f"S3 ClientError: {e}"
            
            logger.error(f"❌ {msg}")
            self.init_error = msg
            self.enabled = False
            
        except BotoCoreError as e:
            msg = f"BotoCoreError: {e}"
            logger.error(f"❌ {msg}", exc_info=True)
            self.init_error = msg
            self.enabled = False
        except Exception as e:
            msg = f"Unexpected Init Error: {e}"
            logger.error(f"❌ {msg}", exc_info=True)
            self.init_error = msg
            self.enabled = False
    
    
    def upload_file(self, file_content: Union[bytes, BinaryIO], key: str, 
                   content_type: str = 'application/octet-stream') -> Optional[str]:
        """
        Uploadează un fișier în S3.
        
        Args:
            file_content: Conținutul fișierului (bytes sau file-like object)
            key: Calea în bucket (ex: "abc123/csvs/file.csv")
            content_type: MIME type (ex: "text/csv", "application/pdf", "image/png")
            
        Returns:
            str: URL-ul fișierului uploadat sau None dacă eroare
        """
        if not self.enabled:
            reason = self.init_error if self.init_error else "Unknown Reason"
            logger.warning(f"⚠️ S3 disabled (Reason: {reason}) - file {key} NOT uploaded to cloud")
            return self._save_local_fallback(file_content, key)
        
        try:
            # Convertim la bytes dacă e file-like object
            if hasattr(file_content, 'read'):
                file_content = file_content.read()
            
            file_size_bytes = len(file_content)
            file_size_mb = file_size_bytes / (1024 * 1024)
            
            # [ITERATION 2] Add timestamp for upload tracking
            import time
            upload_start = time.time()
            logger.warning(f"🚀 [S3_TRACE_UPLOAD] START Upload: {key} | Size: {file_size_mb:.2f} MB ({file_size_bytes} bytes) | Time: {upload_start}")
            
            # Upload către S3
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=file_content,
                ContentType=content_type
            )
            
            # [ITERATION 2] Log upload duration
            upload_duration = time.time() - upload_start
            logger.warning(f"✅ [S3_TRACE_UPLOAD] SUCCESS Upload: {key} | Size: {file_size_mb:.2f} MB | Duration: {upload_duration:.2f}s")
            
            # Returnăm URL-ul (format: https://bucket.endpoint/key sau endpoint/bucket/key)
            # Adaptare pentru endpoint-uri care nu au bucket-ul în subdomain
            if self.bucket_name in S3_ENDPOINT:
                 url = f"{S3_ENDPOINT}/{key}"
            else:
                 url = f"{S3_ENDPOINT}/{self.bucket_name}/{key}"

            return url
            
        except ClientError as e:
            # [DIAGNOSTIC] Granular Error Logging
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            request_id = e.response.get('ResponseMetadata', {}).get('RequestId', 'Unknown')
            http_status = e.response.get('ResponseMetadata', {}).get('HTTPStatusCode', 'Unknown')
            
            logger.error(f"❌ [S3_TRACE_UPLOAD] FAIL Upload S3 pentru {key}")
            logger.error(f"   - Error Code: {error_code}")
            logger.error(f"   - HTTP Status: {http_status}")
            logger.error(f"   - Request ID: {request_id}")
            logger.error(f"   - Full Exception: {e}")
            
            # [ITERATION 2] Log the exact moment of fallback
            logger.warning(f"🔄 [S3_FALLBACK] Switching to LOCAL storage for {key} due to S3 error")
            logger.warning(f"🔄 [S3_FALLBACK] Reason: {error_code} (HTTP {http_status})")
            
            # [ITERATION 4] Detect specific error scenarios
            if error_code == 'QuotaExceeded' or 'quota' in str(e).lower():
                logger.critical(f"💾 [S3_QUOTA] BUCKET QUOTA EXCEEDED! Check Scaleway Object Storage limits.")
            elif error_code == 'AccessDenied' or error_code == '403':
                logger.critical(f"🔒 [S3_PERMISSION] Token lacks WRITE permission. Check API Token scopes.")
            elif 'cors' in str(e).lower():
                logger.warning(f"🌐 [S3_CORS] Possible CORS policy issue.")
            
            # Fallback: salvăm local
            return self._save_local_fallback(file_content, key)
    
    
    def download_file(self, key: str) -> Optional[bytes]:
        """
        Descarcă un fișier din S3.
        
        Args:
            key: Calea în bucket (ex: "abc123/csvs/file.csv")
            
        Returns:
            bytes: Conținutul fișierului sau None dacă eroare
        """
        if not self.enabled:
            logger.warning(f"⚠️ S3 dezactivat - încercare download local pentru {key}")
            return self._read_local_fallback(key)
        
        try:
            logger.warning(f"🔽 [S3_TRACE_DOWNLOAD] START Download: {key}")
            response = self.client.get_object(
                Bucket=self.bucket_name,
                Key=key
            )
            
            file_content = response['Body'].read()
            file_size_mb = len(file_content) / (1024 * 1024)
            logger.warning(f"✅ [S3_TRACE_DOWNLOAD] SUCCESS Download: {key} | Size: {file_size_mb:.2f} MB")
            
            return file_content
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == 'NoSuchKey':
                logger.warning(f"⚠️ [S3_TRACE_DOWNLOAD] NoSuchKey - Fișierul nu există în S3: {key}")
            else:
                logger.error(f"❌ [S3_TRACE_DOWNLOAD] FAIL Download S3 pentru {key}: {e}", exc_info=True)
            
            # Fallback: citim local
            return self._read_local_fallback(key)
    
    
    def delete_file(self, key: str) -> bool:
        """
        Șterge un fișier din S3.
        
        Args:
            key: Calea în bucket (ex: "abc123/csvs/file.csv")
            
        Returns:
            bool: True dacă șters cu succes, False altfel
        """
        if not self.enabled:
            logger.warning(f"⚠️ S3 dezactivat - ștergere locală pentru {key}")
            return self._delete_local_fallback(key)
        
        try:
            logger.warning(f"🗑️ [S3_TRACE_DELETE] Attempt delete: {key}")
            self.client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )
            logger.warning(f"✅ [S3_TRACE_DELETE] SUCCESS Delete: {key}")
            return True
            
        except ClientError as e:
            logger.error(f"❌ Eroare ștergere S3 pentru {key}: {e}", exc_info=True)
            return False
    
    
    def list_files(self, prefix: str = "") -> list[str]:
        """
        Listează fișierele dintr-un folder S3.
        
        Args:
            prefix: Prefixul căii (ex: "abc123/csvs/")
            
        Returns:
            list: Lista de chei (căi) ale fișierelor
        """
        if not self.enabled:
            logger.warning(f"⚠️ S3 dezactivat - listare locală pentru {prefix}")
            return self._list_local_fallback(prefix)
        
        try:
            response = self.client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            files = [obj['Key'] for obj in response.get('Contents', [])]
            logger.info(f"📂 Găsite {len(files)} fișiere în S3 cu prefix '{prefix}'")
            return files
            
        except ClientError as e:
            logger.error(f"❌ Eroare listare S3 pentru {prefix}: {e}", exc_info=True)
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
            logger.warning(f"⚠️ S3 dezactivat - nu se poate genera URL signed pentru {key}")
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
    # FALLBACK - STOCARE LOCALĂ (dacă S3 nu e disponibil)
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

    def _check_write_permission(self):
        """
        [DIAGNOSTIC] Testează explicit permisiunea de scriere (PUT).
        Unele token-uri Scaleway au doar 'Object Read' dar nu 'Object Write'.
        """
        try:
            test_key = "diagnostic_write_check.txt"
            logger.warning(f"🕵️ [S3_PERM_CHECK] Testing WRITE permission on {test_key}...")
            
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=test_key,
                Body=b"write_test",
                ContentType="text/plain"
            )
            logger.warning(f"✅ [S3_PERM_CHECK] WRITE Permission CONFIRMED!")
            
            # Cleanup
            self.client.delete_object(Bucket=self.bucket_name, Key=test_key)
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            logger.critical(f"❌ [S3_PERM_CHECK] WRITE Permission FAILED! Code: {error_code}")
            logger.critical(f"   - Sfat: Verifică Token Permissions în Scaleway Console")
            logger.critical(f"   - Token trebuie să aibă: ObjectStorageReadOnly=false + ObjectStorageReadWrite=true")
            logger.critical(f"   - Location: Scaleway Console → Identity and Access Management (IAM) → API Keys")
        except Exception as e:
            logger.critical(f"❌ [S3_PERM_CHECK] Write Check Failed Unexpectedly: {e}")


# ==============================================================================
# INSTANȚĂ GLOBALĂ - SINGLETON
# ==============================================================================

# Creăm o instanță globală pentru a fi folosită în toată aplicația
# Variabila păstrată ca r2_client pentru backward compatibility (opțional putem schimba în s3_client)
# Vom alinia totul la s3_client intern
s3_client = S3StorageClient()
r2_client = s3_client # Alias pentru cod vechi


# ==============================================================================
# FUNCȚII HELPER - INTERFAȚĂ SIMPLIFICATĂ
# ==============================================================================

def upload_patient_csv(token: str, csv_content: bytes, filename: str) -> Optional[str]:
    """
    Uploadează CSV pacient în S3.
    
    Args:
        token: UUID pacient
        csv_content: Conținutul CSV (bytes)
        filename: Numele fișierului original
        
    Returns:
        str: URL sau calea fișierului
    """
    key = f"{token}/csvs/{filename}"
    return s3_client.upload_file(csv_content, key, content_type='text/csv')


def upload_patient_pdf(token: str, pdf_content: bytes, filename: str) -> Optional[str]:
    """
    Uploadează PDF raport pacient în S3.
    
    Args:
        token: UUID pacient
        pdf_content: Conținutul PDF (bytes)
        filename: Numele fișierului original
        
    Returns:
        str: URL sau calea fișierului
    """
    key = f"{token}/pdfs/{filename}"
    return s3_client.upload_file(pdf_content, key, content_type='application/pdf')


def upload_patient_plot(token: str, plot_content: bytes, filename: str) -> Optional[str]:
    """
    Uploadează grafic PNG pacient în S3.
    
    Args:
        token: UUID pacient
        plot_content: Conținutul PNG (bytes)
        filename: Numele fișierului original
        
    Returns:
        str: URL sau calea fișierului
    """
    key = f"{token}/plots/{filename}"
    return s3_client.upload_file(plot_content, key, content_type='image/png')


def download_patient_file(token: str, file_type: str, filename: str) -> Optional[bytes]:
    """
    Descarcă un fișier pacient din S3.
    
    Args:
        token: UUID pacient
        file_type: Tipul fișierului ('csvs', 'pdfs', 'plots')
        filename: Numele fișierului
        
    Returns:
        bytes: Conținutul fișierului sau None
    """
    key = f"{token}/{file_type}/{filename}"
    return s3_client.download_file(key)


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
    return s3_client.list_files(prefix)


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
            s3_client.delete_file(file_key)
        
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
    Returnează statusul storage-ului (S3 sau local).
    
    Returns:
        dict: Informații despre storage
    """
    return {
        "s3_enabled": s3_client.enabled,
        "s3_endpoint": S3_ENDPOINT if s3_client.enabled else "N/A",
        "s3_bucket": S3_BUCKET_NAME if s3_client.enabled else "N/A",
        "fallback_storage": LOCAL_STORAGE_DIR,
        "mode": "S3 Storage Cloud" if s3_client.enabled else "Local Storage (Fallback)"
    }


if __name__ == "__main__":
    # Test rapid pentru verificare configurare
    logger.info("=== TEST S3 STORAGE (Generic) ===")
    status = get_storage_status()
    
    for key, value in status.items():
        logger.info(f"  {key}: {value}")
    
    if s3_client.enabled:
        logger.info("✅ S3 Storage este ACTIV și funcțional!")
    else:
        logger.warning("⚠️ S3 Storage este DEZACTIVAT - folosim stocare locală")

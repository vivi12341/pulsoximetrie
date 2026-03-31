# ==============================================================================
# repositories/storage_repository.py — fațadă peste storage_service (R2/S3)
# ==============================================================================

from storage_service import (  # noqa: F401
    S3StorageClient,
    r2_client,
    upload_patient_csv,
    upload_patient_pdf,
    upload_patient_plot,
    download_patient_file,
    list_patient_files,
    delete_patient_folder,
    get_storage_status,
)

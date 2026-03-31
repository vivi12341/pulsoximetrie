# ==============================================================================
# repositories/session_repository.py — fațadă peste batch_session_manager (JSON local)
# ==============================================================================

from batch_session_manager import (  # noqa: F401
    create_batch_session,
    update_file_status,
    get_session_progress,
    get_pending_files,
    get_all_sessions,
    mark_session_completed,
)

# ==============================================================================
# repositories/patient_repository.py
# ------------------------------------------------------------------------------
# ROL: Persistență metadata link-uri pacient în PostgreSQL (JSON per token).
#      Migrare automată din fluxul legacy (R2 / patient_links.json) la primul load.
# ==============================================================================

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from logger_setup import logger


def _postgres_links_enabled() -> bool:
    """Dezactivare explicită: USE_POSTGRES_PATIENT_LINKS=0."""
    return os.getenv("USE_POSTGRES_PATIENT_LINKS", "1").strip().lower() not in (
        "0", "false", "no", "off",
    )


def load_all_from_postgres() -> Optional[Dict[str, Any]]:
    """
    Returnează dict token -> metadata dacă există rânduri în DB și context Flask activ.
    Altfel None (apelantul folosește R2/JSON).
    """
    if not _postgres_links_enabled():
        return None
    try:
        from flask import has_app_context
        if not has_app_context():
            return None
        from auth.models import PatientLinkRow
        rows = PatientLinkRow.query.all()
        if not rows:
            return None
        return {row.token: row.payload for row in rows}
    except Exception as exc:
        logger.warning(f"[patient_repository] load PG skipped: {exc}")
        return None


def replace_all_in_postgres(links: Dict[str, Any]) -> bool:
    """
    Înlocuiește conținutul tabelului cu dicționarul dat (upsert per token).
    """
    if not _postgres_links_enabled():
        return False
    if not links:
        return True
    try:
        from flask import has_app_context
        if not has_app_context():
            return False
        from auth.models import db, PatientLinkRow
        existing_tokens = {r.token for r in PatientLinkRow.query.all()}
        new_tokens = {t for t in links if t}
        for obsolete in existing_tokens - new_tokens:
            row = PatientLinkRow.query.get(obsolete)
            if row is not None:
                db.session.delete(row)
        for token, payload in links.items():
            if not token:
                continue
            row = PatientLinkRow.query.get(token)
            if row is None:
                row = PatientLinkRow(token=token, payload=payload)
                db.session.add(row)
            else:
                row.payload = payload
        db.session.commit()
        logger.info(f"[patient_repository] PostgreSQL: salvate {len(links)} link-uri")
        return True
    except Exception as exc:
        logger.error(f"[patient_repository] save PG failed: {exc}", exc_info=True)
        try:
            from auth.models import db
            db.session.rollback()
        except Exception:
            pass
        return False


def migrate_legacy_if_empty(legacy: Dict[str, Any]) -> None:
    """Dacă PG e gol și legacy are date, inserează o singură dată."""
    if not legacy or not _postgres_links_enabled():
        return
    try:
        from flask import has_app_context
        if not has_app_context():
            return
        from auth.models import db, PatientLinkRow
        if PatientLinkRow.query.count() > 0:
            return
        for token, payload in legacy.items():
            if not token:
                continue
            db.session.add(PatientLinkRow(token=token, payload=payload))
        db.session.commit()
        logger.warning(f"[patient_repository] Migrare automată: {len(legacy)} link-uri → PostgreSQL")
    except Exception as exc:
        logger.warning(f"[patient_repository] Migrare PG anulată: {exc}")
        try:
            from auth.models import db
            db.session.rollback()
        except Exception:
            pass

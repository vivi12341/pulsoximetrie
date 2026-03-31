# ==============================================================================
# services/patient_service.py — operații link pacient (fără UI)
# ==============================================================================

from __future__ import annotations

from typing import Any, Dict, List, Optional

import patient_links as _pl


def validate_token(token: str) -> bool:
    return _pl.validate_token(token)


def get_patient_link(token: str) -> Optional[Dict[str, Any]]:
    return _pl.get_patient_link(token)


def get_patient_recordings(token: str) -> List[Dict[str, Any]]:
    return _pl.get_patient_recordings(token)


def load_patient_links() -> Dict[str, Any]:
    return _pl.load_patient_links()


def generate_patient_link(*args: Any, **kwargs: Any) -> Optional[str]:
    return _pl.generate_patient_link(*args, **kwargs)

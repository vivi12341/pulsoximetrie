# ==============================================================================
# services/doctor_service.py — setări medic (footer, logo)
# ==============================================================================

from __future__ import annotations

from typing import Any, List

import doctor_settings as _ds


def load_doctor_settings(*args: Any, **kwargs: Any):
    return _ds.load_doctor_settings(*args, **kwargs)


def save_doctor_settings(*args: Any, **kwargs: Any) -> bool:
    return _ds.save_doctor_settings(*args, **kwargs)


def get_footer_info(*args: Any, **kwargs: Any) -> str:
    return _ds.get_footer_info(*args, **kwargs)


def get_doctor_logo_base64(*args: Any, **kwargs: Any):
    return _ds.get_doctor_logo_base64(*args, **kwargs)


def should_apply_logo_to_site(*args: Any, **kwargs: Any) -> bool:
    return _ds.should_apply_logo_to_site(*args, **kwargs)


def process_footer_links(text: str) -> List[Any]:
    return _ds.process_footer_links(text)

# ==============================================================================
# services/batch_service.py — procesare lot (delegare către batch_processor)
# ==============================================================================

from __future__ import annotations

from typing import Any, Dict, List

from batch_processor import run_batch_job as _run_batch_job
from batch_processor import extract_device_number as _extract_device_number
from batch_processor import generate_intuitive_folder_name as _generate_intuitive_folder_name


def run_batch_job(*args: Any, **kwargs: Any):
    """Rulează job batch CSV/PDF (aceeași semnătură ca batch_processor.run_batch_job)."""
    return _run_batch_job(*args, **kwargs)


def extract_device_number(filename: str) -> str:
    return _extract_device_number(filename)


def generate_intuitive_folder_name(*args: Any, **kwargs: Any) -> str:
    return _generate_intuitive_folder_name(*args, **kwargs)

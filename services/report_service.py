# ==============================================================================
# services/report_service.py — grafice + PDF rapoarte
# ==============================================================================

from __future__ import annotations

from typing import Any, Optional

from plot_generator import create_plot as _create_plot, apply_logo_to_figure as _apply_logo_to_figure
from pdf_parser import (
    parse_checkme_o2_report as _parse_checkme_o2_report,
    format_report_for_display as _format_report_for_display,
    extract_pdf_text as _extract_pdf_text,
)


def create_plot(*args: Any, **kwargs: Any):
    return _create_plot(*args, **kwargs)


def apply_logo_to_figure(fig, *args: Any, **kwargs: Any):
    return _apply_logo_to_figure(fig, *args, **kwargs)


def parse_checkme_o2_report(*args: Any, **kwargs: Any):
    return _parse_checkme_o2_report(*args, **kwargs)


def format_report_for_display(*args: Any, **kwargs: Any):
    return _format_report_for_display(*args, **kwargs)


def extract_pdf_text(*args: Any, **kwargs: Any):
    return _extract_pdf_text(*args, **kwargs)

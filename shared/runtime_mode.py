# ==============================================================================
# shared/runtime_mode.py — detectare mediu local vs. cloud (PaaS)
# ==============================================================================
from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse


def is_cloud_runtime() -> bool:
    """
    True dacă aplicația rulează pe o platformă tipică de hosting (variabile setate de provider).
    Nu se bazează doar pe PORT (uneori setat și local).
    Pentru VPS fără aceste variabile: setează FORCE_CLOUD_RUNTIME=1 în mediu.
    """
    if os.getenv("FORCE_CLOUD_RUNTIME", "").strip().lower() in ("1", "true", "yes"):
        return True
    if os.getenv("RAILWAY_ENVIRONMENT"):
        return True
    if os.getenv("RENDER", "").lower() in ("true", "1", "yes"):
        return True
    if os.getenv("HEROKU_APP_NAME") or os.getenv("DYNO"):
        return True
    if os.getenv("FLY_APP_NAME"):
        return True
    if os.getenv("K_SERVICE"):  # Google Cloud Run
        return True
    if os.getenv("WEBSITE_SITE_NAME"):  # Azure App Service
        return True
    return False


def default_local_sqlite_url() -> str:
    """Fișier SQLite în directorul curent al proiectului (dev fără PostgreSQL)."""
    db_path = (Path.cwd() / "pulsox_local_dev.db").resolve()
    return "sqlite:///" + str(db_path).replace("\\", "/")


def normalize_postgres_url_for_cloud(database_url: str) -> str:
    """
    Ajustări pentru PostgreSQL gestionat (Railway, Render, etc.).
    """
    if not database_url:
        return database_url
    url = database_url
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    scheme = (urlparse(url).scheme or "").lower()
    if scheme in ("postgresql", "postgresql+psycopg2") and "sslmode" not in url:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}sslmode=require"
    return url


def resolve_database_url() -> str:
    """
    Cloud: DATABASE_URL obligatoriu din mediu (normalizat).
    Local: DATABASE_URL din .env dacă există; altfel SQLite implicit.
    """
    raw = os.getenv("DATABASE_URL", "").strip()
    if is_cloud_runtime():
        return normalize_postgres_url_for_cloud(raw)
    if raw:
        return raw
    return default_local_sqlite_url()


def apply_default_patient_links_storage_mode() -> None:
    """
    Local: metadata link-uri din JSON/R2 (fără nevoie de Postgres pentru patient_link_rows).
    Cloud: implicit PostgreSQL dacă nu e setat altfel.
    """
    if is_cloud_runtime():
        os.environ.setdefault("USE_POSTGRES_PATIENT_LINKS", "1")
    else:
        os.environ.setdefault("USE_POSTGRES_PATIENT_LINKS", "0")


def sqlalchemy_engine_options(database_url: str) -> dict:
    """Opțiuni SQLAlchemy compatibile cu SQLite vs PostgreSQL."""
    scheme = (urlparse(database_url).scheme or "").lower()
    if scheme.startswith("sqlite"):
        return {
            "pool_pre_ping": True,
            "connect_args": {"check_same_thread": False},
        }
    return {
        "pool_size": 10,
        "max_overflow": 20,
        "pool_timeout": 30,
        "pool_recycle": 1800,
        "pool_pre_ping": True,
        "connect_args": {
            "connect_timeout": 10,
            "options": "-c statement_timeout=60000",
        },
    }

"""Carga y normalización de variables de configuración basadas en ``.env``."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

# ---------------------------------------------------------------------------
# Carga automática de archivos ``.env``
# ---------------------------------------------------------------------------
env_loaded_from: str | None = None
try:
    from dotenv import find_dotenv, load_dotenv  # type: ignore

    env_path = find_dotenv(usecwd=True)
    if not env_path:
        repo_root = Path(__file__).resolve().parents[2]
        candidate = repo_root / ".env"
        if candidate.exists():
            env_path = str(candidate)

    if env_path:
        load_dotenv(env_path, override=False)
        env_loaded_from = env_path
    else:  # Último intento: carga “silenciosa” del CWD
        load_dotenv()
except Exception:  # pragma: no cover - robustez en import opcional
    pass


def _get_any(keys: Iterable[str] | str, default: str) -> str:
    """Devuelve el primer valor no vacío encontrado en ``keys``."""

    if isinstance(keys, (list, tuple, set)):
        for key in keys:
            value = os.getenv(key)
            if value is not None and str(value).strip():
                return value
        return default
    return os.getenv(keys, default)


APP_ENV: str = _get_any(["APP_ENV", "ENVIRONMENT"], "production").strip().lower()


def getenv(key: str, default: str = "") -> str:
    return _get_any([key], default)


def getint(key: str, default: int) -> int:
    return int(getenv(key, str(default)))


def getbool(key: str, default: bool = False) -> bool:
    val = getenv(key, str(default))
    return str(val).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class BrowserConfig:
    """Configuración específica del navegador/control via CDP."""

    cdp_endpoint: str
    base_url: str


CDP_ENDPOINT: str = _get_any(["CDP_ENDPOINT"], "http://127.0.0.1:9222")
BASE: str = _get_any(["BASE"], "https://web.whatsapp.com/").strip().rstrip("/")

BROWSER = BrowserConfig(cdp_endpoint=CDP_ENDPOINT, base_url=BASE)
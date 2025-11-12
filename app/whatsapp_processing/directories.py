"""Operaciones sobre el sistema de archivos para la captura de comprobantes."""

from __future__ import annotations

from .constants import IMG_DIR, OUT_DIR


def ensure_directories() -> None:
    """Crea las carpetas de salida necesarias si aún no existen."""

    OUT_DIR.mkdir(exist_ok=True)
    IMG_DIR.mkdir(parents=True, exist_ok=True)


__all__ = ["ensure_directories"]

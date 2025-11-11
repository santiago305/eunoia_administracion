"""Punto de entrada de línea de comandos para la automatización."""

from __future__ import annotations

import asyncio
import logging

from .bootstrap import run


logger = logging.getLogger(__name__)


def main() -> None:
    """Ejecuta la aplicación principal en un loop de asyncio."""

    logger.debug("Iniciando la aplicación de automatización...")
    # Ejecutamos la rutina principal asegurando que el loop se cierre adecuadamente.
    asyncio.run(run())


__all__ = ["main"]
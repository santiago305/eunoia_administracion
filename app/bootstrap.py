"""Secuencia de arranque simplificada de la aplicación CLI."""

from __future__ import annotations

import asyncio
import logging
from typing import Iterable

from playwright.async_api import BrowserContext, Page, async_playwright


logger = logging.getLogger(__name__)


async def _close_extra_pages(context: BrowserContext, keep: Page) -> None:
    """Close every page in *context* except for *keep*."""

    async def _close_page(page: Page) -> None:
        try:
            await page.close()
        except Exception:  # pragma: no cover - logging side effect
            logger.exception("No se pudo cerrar una ventana adicional")

    to_close: Iterable[Page] = (
        page for page in context.pages if page != keep and not page.is_closed()
    )
    tasks = [asyncio.create_task(_close_page(page)) for page in to_close]
    if tasks:
        logger.info("Cerrando %d ventana(s) adicionales detectadas", len(tasks))
        await asyncio.gather(*tasks)


async def run(settings=None) -> None:  # noqa: D401 - firma heredada
    """Abre un navegador Chromium y muestra un saludo."""

    logging.basicConfig(level=logging.INFO)
    logger.info("Iniciando navegador...")

    page = await BrowserContext.new_page()
    await page.wait_for_timeout(10000)


__all__ = ["run"]
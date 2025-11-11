"""Utilidades para normalizar contextos y páginas de Playwright."""

from __future__ import annotations

import asyncio
import logging
from typing import Iterable

from playwright.async_api import Browser, BrowserContext, Page


logger = logging.getLogger(__name__)


async def close_extra_pages(context: BrowserContext, keep: Page) -> None:
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


async def prepare_context(browser: Browser) -> BrowserContext:
    """Return the primary context from *browser*, creating one if needed."""

    if browser.contexts:
        return browser.contexts[0]

    return await browser.new_context()


async def prepare_primary_page(context: BrowserContext) -> Page:
    """Return a ready-to-use page, creating one when necessary."""

    page: Page
    if context.pages:
        page = context.pages[0]
        await close_extra_pages(context, page)
    else:
        page = await context.new_page()

    await page.bring_to_front()
    return page


__all__ = ["close_extra_pages", "prepare_context", "prepare_primary_page"]
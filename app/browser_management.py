"""Utilidades para normalizar contextos y páginas de Playwright."""

from __future__ import annotations

import asyncio
import logging
from typing import Iterable

from playwright.async_api import Browser, BrowserContext, Page
from playwright._impl._errors import TargetClosedError


logger = logging.getLogger(__name__)


class BrowserSessionClosedError(RuntimeError):
    """Señala que la sesión CDP se perdió y es necesario reconectar."""

    pass


async def close_extra_pages(context: BrowserContext, keep: Page) -> None:
    """Cierra todas las páginas del contexto excepto la que necesitamos conservar."""

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


def _context_is_active(context: BrowserContext) -> bool:
    """True si el contexto sigue operativo según los indicadores internos."""

    impl = getattr(context, "_impl_obj", None)
    if impl is None:
        return True

    closing_or_closed = getattr(impl, "_closing_or_closed", None)
    if closing_or_closed is None:
        return True

    return not closing_or_closed


async def prepare_context(browser: Browser) -> BrowserContext:
    """Devuelve un contexto activo o crea uno nuevo si los existentes están cerrados."""

    if hasattr(browser, "is_connected") and not browser.is_connected():
        raise BrowserSessionClosedError("El navegador CDP se desconectó.")

    for context in browser.contexts:
        if _context_is_active(context):
            return context

    return await browser.new_context()


async def prepare_primary_page(context: BrowserContext) -> tuple[BrowserContext, Page]:
    """Obtiene la página principal lista para trabajar o crea una nueva.

    Puede devolver un nuevo contexto cuando el original quedó inutilizable
    (por ejemplo, cuando Chrome cerró la sesión de depuración anterior).
    """

    page: Page
    open_pages = [page for page in context.pages if not page.is_closed()]
    if open_pages:
        page = open_pages[0]
        # Limpiamos ventanas sobrantes para evitar interferencias con la automatización.
        await close_extra_pages(context, page)
    else:
        try:
            page = await context.new_page()
        except TargetClosedError as error:
            logger.warning(
                "Contexto cerrado detectado. Creando un nuevo contexto en Chrome."
            )
            browser = getattr(context, "browser", None)
            if browser is None or not browser.is_connected():
                raise BrowserSessionClosedError(
                    "El navegador CDP se desconectó y no se puede abrir un nuevo contexto."
                ) from error
            context = await browser.new_context()
            page = await context.new_page()

    # Traemos la pestaña al frente para que el usuario vea el proceso en curso.
    await page.bring_to_front()
    return context, page


__all__ = [
    "BrowserSessionClosedError",
    "close_extra_pages",
    "prepare_context",
    "prepare_primary_page",
]
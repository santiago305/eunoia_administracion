"""Secuencia de arranque simplificada de la aplicación CLI."""

from __future__ import annotations

import asyncio
import logging
from enum import Enum
from typing import Iterable

from playwright.async_api import (
    Browser,
    BrowserContext,
    Error as PlaywrightError,
    Locator,
    Page,
)

from browser import connect_browser_over_cdp
from settings.settings import BASE


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


class LoginState(Enum):
    """Posibles estados de autenticación en WhatsApp Web."""

    UNKNOWN = "unknown"
    LOGGED_OUT = "logged_out"
    LOGGED_IN = "logged_in"


LOGIN_PROMPT_TEXTS = (
    "Pasos para iniciar sesión",
    "Vincular con el número de teléfono",
    "Iniciar sesión con número de teléfono",
)

LOGGED_IN_XPATHS = (
    "//*[@id='app']/div[1]/div/div[3]",
    "//*[@id='app']/div[1]/div/div[3]/div/div[4]",
    "//*[@id='app']/div[1]/div/div[3]/div/div[5]",
)


async def _locator_is_visible(locator: Locator) -> bool:
    """Return ``True`` when the ``locator`` is visible, ``False`` otherwise."""

    try:
        return await locator.is_visible()
    except PlaywrightError:
        return False


async def _detect_login_state(page: Page) -> LoginState:
    """Intenta determinar si la sesión de WhatsApp Web está activa."""

    for xpath in LOGGED_IN_XPATHS:
        locator = page.locator(f"xpath={xpath}")
        if await _locator_is_visible(locator):
            return LoginState.LOGGED_IN

    for text in LOGIN_PROMPT_TEXTS:
        locator = page.get_by_text(text, exact=True)
        if await _locator_is_visible(locator):
            return LoginState.LOGGED_OUT

    return LoginState.UNKNOWN


async def _monitor_login_state(page: Page, interval: float = 15.0) -> None:
    """Supervisa el estado de sesión e informa cuando cambia."""

    last_state: LoginState | None = None
    while True:
        state = await _detect_login_state(page)
        if state != last_state:
            if state == LoginState.LOGGED_IN:
                logger.info("Gracias por la espera. ¡La sesión de WhatsApp Web está iniciada!")
            elif state == LoginState.LOGGED_OUT:
                logger.info(
                    "No se ha iniciado sesión en WhatsApp Web. Por favor, escanea el código QR para continuar."
                )
            else:
                logger.info(
                    "Aún no se puede determinar el estado de la sesión. Continuaremos verificando..."
                )
            last_state = state

        await asyncio.sleep(interval)


async def _prepare_context(browser: Browser) -> BrowserContext:
    """Obtiene un contexto utilizable, creando uno nuevo si es necesario."""

    if browser.contexts:
        return browser.contexts[0]

    return await browser.new_context()


async def run(settings=None) -> None:  # noqa: D401 - firma heredada
    """Conecta con Chrome vía CDP y monitorea el estado de WhatsApp Web."""

    del settings  # parámetro reservado para compatibilidad

    logging.basicConfig(level=logging.INFO)
    logger.info("Conectando con Chrome existente mediante CDP...")

    browser = await connect_browser_over_cdp()
    if browser is None:
        logger.error(
            "No se pudo conectar con el navegador Chrome en modo depuración remota. "
            "Asegúrate de ejecutar scripts/open_chrome_debug.ps1 antes de iniciar la app."
        )
        return

    context = await _prepare_context(browser)

    page: Page
    if context.pages:
        page = context.pages[0]
        await _close_extra_pages(context, page)
    else:
        page = await context.new_page()

    await page.bring_to_front()
    await page.goto(f"{BASE}/", wait_until="domcontentloaded")
    logger.info("WhatsApp Web abierto. Supervisando el estado de inicio de sesión...")

    try:
        await _monitor_login_state(page)
    finally:
        logger.info("Monitor de sesión detenido. Chrome permanecerá abierto.")


__all__ = ["run"]

"""Secuencia de arranque simplificada de la aplicación CLI."""

from __future__ import annotations

import logging

from browser import connect_browser_over_cdp
from settings.settings import BASE

from .browser_management import (
    BrowserSessionClosedError,
    prepare_context,
    prepare_primary_page,
)
from .login_state import LoginState, monitor_login_state

logger = logging.getLogger(__name__)


async def run(settings=None) -> None:  # noqa: D401 - firma heredada
    """Conecta con Chrome vía CDP y monitorea el estado de WhatsApp Web."""

    del settings  # parámetro reservado para compatibilidad

    logging.basicConfig(level=logging.INFO)
    logger.info("Conectando con Chrome existente mediante CDP...")

    # Intentamos conectar con una instancia existente de Chrome mediante CDP.
    browser_connection = await connect_browser_over_cdp()
    if browser_connection is None:
        logger.error(
            "No se pudo conectar con el navegador Chrome en modo depuración remota. "
            "Asegúrate de ejecutar scripts/open_chrome_debug.ps1 antes de iniciar la app."
        )
        return

    logger.info("Conexión establecida con Chrome mediante CDP.")

    # Normalizamos el contexto y la página principal para garantizar un entorno limpio.
    attempt = 0
    max_attempts = 2
    while True:
        attempt += 1
        browser = browser_connection.browser
        try:
            context = await prepare_context(browser)
            context, page = await prepare_primary_page(context)
            break
        except BrowserSessionClosedError:
            logger.warning(
                "Se perdió la conexión con Chrome. Intentando reconectar (%d/%d)...",
                attempt,
                max_attempts,
            )
            await browser_connection.close()
            browser_connection = None
            if attempt >= max_attempts:
                logger.error(
                    "No fue posible restablecer la sesión con Chrome en modo depuración."
                )
                return

            new_connection = await connect_browser_over_cdp()
            if new_connection is None:
                logger.error(
                    "No se pudo reconectar con el navegador Chrome en modo depuración remota."
                )
                return
            browser_connection = new_connection
            logger.info("Reconexión con Chrome exitosa.")
            continue

    await page.goto(f"{BASE}/", wait_until="domcontentloaded")
    logger.info("WhatsApp Web abierto. Supervisando el estado de inicio de sesión...")

    try:
        state = await monitor_login_state(page, logger_instance=logger)
        if state == LoginState.LOGGED_IN:
            logger.info("Sesión autenticada en WhatsApp Web.")
    finally:
        logger.info("Monitor de sesión detenido. Chrome permanecerá abierto.")
        if browser_connection is not None:
            await browser_connection.close()
        logger.info("Trabajo terminado.")

__all__ = ["run"]

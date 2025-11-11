"""Secuencia de arranque simplificada de la aplicación CLI."""

from __future__ import annotations

import logging

from browser import connect_browser_over_cdp
from settings.settings import BASE

from .browser_management import prepare_context, prepare_primary_page
from .login_state import monitor_login_state


logger = logging.getLogger(__name__)


async def run(settings=None) -> None:  # noqa: D401 - firma heredada
    """Conecta con Chrome vía CDP y monitorea el estado de WhatsApp Web."""

    del settings  # parámetro reservado para compatibilidad

    logging.basicConfig(level=logging.INFO)
    logger.debug("Conectando con Chrome existente mediante CDP...")

    browser = await connect_browser_over_cdp()
    if browser is None:
        logger.error(
            "No se pudo conectar con el navegador Chrome en modo depuración remota. "
            "Asegúrate de ejecutar scripts/open_chrome_debug.ps1 antes de iniciar la app."
        )
        return

    logger.debug("Conexión establecida con Chrome mediante CDP.")

    context = await prepare_context(browser)
    page = await prepare_primary_page(context)

    await page.goto(f"{BASE}/", wait_until="domcontentloaded")
    logger.debug("WhatsApp Web abierto. Supervisando el estado de inicio de sesión...")

    try:
        await monitor_login_state(page, logger_instance=logger)
    finally:
        logger.debug("Monitor de sesión detenido. Chrome permanecerá abierto.")


__all__ = ["run"]
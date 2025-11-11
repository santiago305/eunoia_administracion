+15
-156

"""Secuencia de arranque simplificada de la aplicación CLI."""

from __future__ import annotations

import logging

from playwright.async_api import async_playwright


logger = logging.getLogger(__name__)


async def run(settings=None) -> None:  # noqa: D401 - firma heredada
    """Abre un navegador Chromium y muestra un saludo."""

    logging.basicConfig(level=logging.INFO)
    logger.info("Iniciando navegador...")

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        logger.info("Navegador abierto.")
        print("Hola mundo")

        # Mantén la ventana viva brevemente para evitar que se cierre de inmediato.
        await page.wait_for_timeout(10000)


__all__ = ["run"]
from typing import Optional

from playwright.async_api import Browser, async_playwright

from ..settings import settings


async def connect_browser_over_cdp() -> Optional[Browser]:
    """
    Conecta a Chrome ya abierto con --remote-debugging-port.
    Lanza primero scripts/open_chrome_debug.ps1 y loguéate manualmente.
    """
    try:
        pw = await async_playwright().start()
        browser = await pw.chromium.connect_over_cdp(settings.CDP_ENDPOINT)

        try:
            contexts = list(browser.contexts)

            if not contexts:
                primary_context = await browser.new_context()
                contexts = [primary_context]
            else:
                primary_context = contexts[0]

            # Cierra por completo los contextos adicionales.
            for extra_context in contexts[1:]:
                for page in extra_context.pages:
                    await page.close()
                await extra_context.close()

            # Asegura que solo quede una pestaña en el contexto principal.
            # Cierra todas las pestañas existentes en el contexto principal y crea una nueva.
            for page in list(primary_context.pages):
                try:
                    await page.close()
                except Exception as page_error:
                    print(f"[CDP] Advertencia al cerrar pestaña: {page_error}")

            await primary_context.new_page()

        except Exception as cleanup_error:
            print(f"[CDP] Advertencia al normalizar pestañas: {cleanup_error}")

        return browser
    except Exception as e:
        print(f"[CDP] Error al conectar: {e}")
        return None

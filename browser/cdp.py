from typing import Optional

from playwright.async_api import Browser, async_playwright

from fuvexbn.config import settings

async def connect_browser_over_cdp() -> Optional[Browser]:
    """
    Conecta a Chrome ya abierto con --remote-debugging-port.
    Lanza primero scripts/open_chrome_debug.ps1 y loguéate manualmente.
    """
    try:
        pw = await async_playwright().start()
        browser = await pw.chromium.connect_over_cdp(settings.CDP_ENDPOINT)
        return browser
    except Exception as e:
        print(f"[CDP] Error al conectar: {e}")
        return None
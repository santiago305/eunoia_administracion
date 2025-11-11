from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, urlunparse

from playwright.async_api import Browser, Playwright, async_playwright

from settings import CDP_ENDPOINT

_PORT_METADATA_FILE = Path(__file__).resolve().parent.parent / "scripts" / "chrome_cdp_port.txt"


@dataclass
class BrowserConnection:
    """Agrupa el navegador conectado y el objeto de Playwright para su limpieza."""

    browser: Browser
    playwright: Playwright

    async def close(self) -> None:
        """Cierra la conexión con Chrome y detiene Playwright de forma segura."""

        try:
            # Cerramos la sesión de CDP mantenida por Playwright sin finalizar Chrome.
            await self.browser.close()
        except Exception as close_error:
            print(f"[CDP] Advertencia al cerrar el navegador conectado: {close_error}")
        finally:
            try:
                # Garantizamos la liberación del proceso auxiliar de Playwright.
                await self.playwright.stop()
            except Exception as stop_error:
                print(f"[CDP] Advertencia al detener Playwright: {stop_error}")
                
def _port_from_metadata() -> Optional[int]:
    """Lee el puerto usado por ``open_chrome_debug.ps1`` si está disponible."""

    try:
        text = _PORT_METADATA_FILE.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    except OSError as exc:
        print(f"[CDP] Advertencia al leer el puerto registrado: {exc}")
        return None

    if not text:
        return None

    try:
        port = int(text)
    except ValueError:
        print(f"[CDP] Valor de puerto inválido en {_PORT_METADATA_FILE}: '{text}'")
        return None

    if port <= 0 or port > 65535:
        print(f"[CDP] Puerto fuera de rango en {_PORT_METADATA_FILE}: {port}")
        return None

    return port


def _resolve_cdp_endpoint() -> str:
    """Combina ``settings.CDP_ENDPOINT`` con el puerto registrado, si existe."""

    endpoint = (CDP_ENDPOINT or "").strip() or "http://127.0.0.1:9222"
    override_port = _port_from_metadata()

    if override_port is None:
        return endpoint

    parsed = urlparse(endpoint if "://" in endpoint else f"http://{endpoint}")

    scheme = parsed.scheme or "http"
    path = parsed.path or ""
    params = parsed.params or ""
    query = parsed.query or ""
    fragment = parsed.fragment or ""

    hostname = parsed.hostname or "127.0.0.1"
    userinfo = ""
    if parsed.username:
        userinfo = parsed.username
        if parsed.password:
            userinfo = f"{userinfo}:{parsed.password}"

    netloc = hostname
    if userinfo:
        netloc = f"{userinfo}@{netloc}"
    netloc = f"{netloc}:{override_port}"

    resolved = urlunparse((scheme, netloc, path, params, query, fragment))
    print(
        "[CDP] Puerto detectado en scripts/open_chrome_debug.ps1: "
        f"{override_port}. Endpoint resuelto: {resolved}"
    )
    return resolved


async def connect_browser_over_cdp() -> Optional[BrowserConnection]:
    """Establece una sesión CDP contra un Chrome ya abierto."""


    pw = None
    try:
        pw = await async_playwright().start()
        endpoint = _resolve_cdp_endpoint()
        browser = await pw.chromium.connect_over_cdp(endpoint)

        try:
            # Obtenemos los contextos existentes para reutilizarlos en caso de ser posible.
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

        # Devolvemos una estructura que facilita el cierre correcto al finalizar.
        return BrowserConnection(browser=browser, playwright=pw)
    except Exception as e:
        print(f"[CDP] Error al conectar: {e}")
        if pw is not None:
            try:
                await pw.stop()
            except Exception as stop_error:
                print(f"[CDP] Advertencia al detener Playwright tras un error: {stop_error}")
        return None


__all__ = ["BrowserConnection", "connect_browser_over_cdp"]
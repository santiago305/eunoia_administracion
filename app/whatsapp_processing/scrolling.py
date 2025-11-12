"""Utilidades para posicionar la vista dentro de la conversación."""

from __future__ import annotations

from playwright.async_api import Page

from .constants import SLOW_AFTER_SCROLL_MS, TOP_SCROLL_MAX_ROUNDS, TOP_SCROLL_PGUP_BURST
from .containers import get_messages_container
from .iteration import first_message_id


async def _pageup_burst(page: Page) -> None:
    """Realiza un pequeño lote de desplazamientos hacia arriba."""

    for _ in range(TOP_SCROLL_PGUP_BURST):
        await page.keyboard.press("PageUp")
        await page.wait_for_timeout(SLOW_AFTER_SCROLL_MS)


async def scroll_to_very_top(page: Page) -> None:
    """Intenta llegar al inicio completo de la conversación."""

    messages = get_messages_container(page)
    try:
        await messages.focus()
    except Exception:  # pragma: no cover - depende del estado del DOM
        pass

    previous_top = ""
    rounds_without_change = 0

    for _ in range(TOP_SCROLL_MAX_ROUNDS):
        await _pageup_burst(page)
        try:
            await page.evaluate("(el)=>{el.scrollTop=0}", messages)
        except Exception:  # pragma: no cover - puede fallar según el renderizado
            pass
        await page.wait_for_timeout(SLOW_AFTER_SCROLL_MS + 200)

        top_id = await first_message_id(page)
        if not top_id:
            continue
        if top_id == previous_top:
            rounds_without_change += 1
        else:
            rounds_without_change = 0
        previous_top = top_id
        if rounds_without_change >= 3:
            break


async def scroll_to_last_processed(page: Page, last_id: str) -> None:
    """Posiciona la vista cerca del último mensaje procesado."""

    if not last_id:
        return

    locator = page.locator(f'div[role="row"] div[data-id="{last_id}"]')
    try:
        await locator.first.scroll_into_view_if_needed(timeout=3_000)
        await page.wait_for_timeout(SLOW_AFTER_SCROLL_MS)
        await page.keyboard.press("PageDown")
        await page.wait_for_timeout(SLOW_AFTER_SCROLL_MS)
    except Exception:  # pragma: no cover - depende del estado de carga de la UI
        for _ in range(10):
            await page.keyboard.press("End")
            await page.wait_for_timeout(SLOW_AFTER_SCROLL_MS)
            if await locator.count() > 0:
                try:
                    await locator.first.scroll_into_view_if_needed(timeout=2_000)
                    await page.keyboard.press("PageDown")
                    await page.wait_for_timeout(SLOW_AFTER_SCROLL_MS)
                except Exception:  # pragma: no cover - interacción con la UI
                    pass
                break


__all__ = ["scroll_to_last_processed", "scroll_to_very_top"]
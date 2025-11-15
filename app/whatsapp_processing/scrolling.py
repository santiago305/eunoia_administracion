"""Utilidades para posicionar la vista dentro de la conversación."""

from __future__ import annotations

from playwright.async_api import Page

from .constants import (
    SLOW_AFTER_SCROLL_MS,
    TOP_SCROLL_MAX_ROUNDS,
    TOP_SCROLL_PGUP_BURST,
    TOP_SCROLL_STABLE_ROUNDS,
)
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
    attempts = 0

    while True:
        if TOP_SCROLL_MAX_ROUNDS and attempts >= TOP_SCROLL_MAX_ROUNDS:
            break
        attempts += 1
        await _pageup_burst(page)
        try:
            await page.evaluate("(el)=>{el.scrollTop=0}", messages)
        except Exception:  # pragma: no cover - puede fallar según el renderizado
            pass
        await page.wait_for_timeout(SLOW_AFTER_SCROLL_MS + 200)

        top_id = await first_message_id(page)
        if not top_id:
            rounds_without_change += 1
            if rounds_without_change >= TOP_SCROLL_STABLE_ROUNDS:
                break
            continue
        if top_id == previous_top:
            rounds_without_change += 1
        else:
            rounds_without_change = 0
        previous_top = top_id
        if rounds_without_change >= TOP_SCROLL_STABLE_ROUNDS:
            break


async def scroll_to_last_processed(page: Page, last_id: str) -> None:
    """Posiciona la vista cerca del último mensaje procesado.

    - Si el identificador existe en la vista actual se centra y avanza una página
      para reanudar la lectura desde el siguiente mensaje.
    - Si el identificador no está visible, se realiza un desplazamiento gradual
      hacia el final hasta encontrarlo. Si finalmente no aparece, la captura
      continúa desde la posición alcanzada, que corresponderá al segmento más
      reciente de la conversación.
    """

    if not last_id:
        return

    locator = page.locator(f'div[role="row"] div[data-id="{last_id}"]')
    messages = get_messages_container(page)

    try:
        await messages.focus()
    except Exception:  # pragma: no cover - depende del estado del DOM
        pass

    async def _scroll_metrics() -> dict:
        try:
            return await messages.evaluate(
                "(el) => ({"
                "scrollTop: el.scrollTop,"
                "scrollHeight: el.scrollHeight,"
                "clientHeight: el.clientHeight"
                "})"
            )
        except Exception:  # pragma: no cover - puede fallar según el renderizado
            return {"scrollTop": 0, "scrollHeight": 0, "clientHeight": 0}

    while True:
        if await locator.count() > 0:
            try:
                await locator.first.scroll_into_view_if_needed(timeout=3_000)
            except Exception:  # pragma: no cover - interacción con la UI
                pass
            else:
                await page.wait_for_timeout(SLOW_AFTER_SCROLL_MS)
                await page.keyboard.press("PageDown")
                await page.wait_for_timeout(SLOW_AFTER_SCROLL_MS)
            break

        metrics_before = await _scroll_metrics()
        await page.keyboard.press("End")
        await page.wait_for_timeout(SLOW_AFTER_SCROLL_MS)
        metrics_after = await _scroll_metrics()

        # Si no hay avance en el desplazamiento damos por terminado el intento.
        if metrics_after.get("scrollTop", 0) <= metrics_before.get("scrollTop", 0):
            break


__all__ = ["scroll_to_last_processed", "scroll_to_very_top"]


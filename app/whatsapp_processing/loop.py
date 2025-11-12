"""Bucle principal que replica la lógica del script de ejemplo ``whatsapp.py``."""

from __future__ import annotations

import asyncio

from playwright.async_api import Locator, Page

from .cache import ProcessedIds, save_cache
from .constants import POLL_SECONDS, SLOW_AFTER_SCROLL_MS
from .containers import get_messages_container
from .processing import process_visible_top_to_bottom
from .scrolling import scroll_to_last_processed, scroll_to_very_top


async def _prepare_messages_container(page: Page) -> Locator:
    """Garantiza que el contenedor de mensajes esté listo para interactuar."""

    container = get_messages_container(page)
    await container.wait_for(state="attached")
    try:
        await container.focus()
    except Exception:  # pragma: no cover - depende del estado de la UI
        pass
    return container


async def monitor_conversation(
    page: Page,
    processed_ids: ProcessedIds,
    last_id: str,
    *,
    verbose_print: bool = True,
) -> str:
    """Mantiene la captura de mensajes nuevos siguiendo la simulación original."""

    await _prepare_messages_container(page)

    if not processed_ids:
        await scroll_to_very_top(page)
    else:
        await scroll_to_last_processed(page, last_id)

    _, last_id = await process_visible_top_to_bottom(
        page,
        processed_ids,
        last_id,
        verbose_print=verbose_print,
    )
    save_cache(processed_ids, last_id)

    print("🔄 Conectado. Escuchando nuevos mensajes... (Ctrl+C para salir)")

    try:
        while True:
            await _prepare_messages_container(page)
            await page.keyboard.press("End")
            await page.wait_for_timeout(SLOW_AFTER_SCROLL_MS)

            new_count, last_id = await process_visible_top_to_bottom(
                page,
                processed_ids,
                last_id,
                verbose_print=verbose_print,
            )
            if new_count:
                save_cache(processed_ids, last_id)

            await asyncio.sleep(POLL_SECONDS)
    finally:
        save_cache(processed_ids, last_id)

    return last_id


__all__ = ["monitor_conversation"]
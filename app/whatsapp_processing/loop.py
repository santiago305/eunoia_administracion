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


async def _needs_scroll_to_bottom(page: Page, last_id: str) -> bool:
    """Determina si es necesario desplazarse al final de la conversación."""

    if not last_id:
        return True

    messages = get_messages_container(page)
    try:
        metrics = await messages.evaluate(
            "(el) => ({"
            "scrollTop: el.scrollTop,"
            "scrollHeight: el.scrollHeight,"
            "clientHeight: el.clientHeight"
            "})"
        )
    except Exception:  # pragma: no cover - depende del estado del DOM
        return True

    remaining = metrics["scrollHeight"] - (
        metrics["scrollTop"] + metrics["clientHeight"]
    )
    if remaining > 48:
        return True

    locator = page.locator(f'div[role="row"] div[data-id="{last_id}"]')
    return await locator.count() == 0

async def _announce_last_id_context(
    page: Page, last_id: str, previous_cached_id: str = ""
) -> None:
    """Informa el estado del último mensaje registrado antes de iniciar el bucle."""

    if not last_id:
        print("🗂️ Caché vacía. Se iniciará la captura desde el inicio de la conversación.")
        if previous_cached_id:
            print(f"↪️ Último ID registrado anteriormente: {previous_cached_id}")
        return

    print(f"🧭 Último ID registrado en caché: {last_id}")

    locator = page.locator(f'div[role="row"] div[data-id="{last_id}"]')
    try:
        count = await locator.count()
    except Exception:  # pragma: no cover - depende del estado del DOM
        count = 0

    if count:
        try:
            context = await locator.evaluate(
                "(el) => {"
                "  const row = el.closest('[role=\"row\"]');"
                "  const previousRow = row?.previousElementSibling;"
                "  const previousMessage = previousRow?.querySelector('div[data-id]');"
                "  const previousId = previousMessage ? previousMessage.getAttribute('data-id') || '' : '';"
                "  return { previousId };"
                "}"
            )
        except Exception:  # pragma: no cover - depende del estado del DOM
            context = {"previousId": ""}

        print("✅ ID encontrado en la conversación. Se continuará buscando hacia abajo.")
        previous_id = context.get("previousId", "") if isinstance(context, dict) else ""
        if previous_id:
            print(f"↪️ Mensaje anterior visible: {previous_id}")
        else:
            if previous_cached_id:
                print(f"↪️ Penúltimo mensaje en caché: {previous_cached_id}")
            else:
                print(
                    "↪️ No se detectó un mensaje anterior visible; se continuará desde este punto hacia abajo."
                )
    else:
        print(
            f"⚠️ No se encontró el ID {last_id} en la vista actual; "
            "se desplazará para reubicar el punto de partida."
        )
        if previous_cached_id:
            print(f"↪️ Referencia previa en caché: {previous_cached_id}")

async def monitor_conversation(
    page: Page,
    processed_ids: ProcessedIds,
    last_id: str,
    last_signature: str,
    *,
    previous_cached_id: str = "",
    verbose_print: bool = True,
) -> str:
    """Mantiene la captura de mensajes nuevos siguiendo la simulación original."""

    await _prepare_messages_container(page)
    
    await _announce_last_id_context(page, last_id, previous_cached_id)

    if last_id and last_id not in processed_ids:
        processed_ids.add(last_id)

    if not processed_ids:
        await scroll_to_very_top(page)
    else:
        await scroll_to_last_processed(page, last_id)

    _, last_id, last_signature = await process_visible_top_to_bottom(
        page,
        processed_ids,
        last_id,
        last_signature,
        verbose_print=verbose_print,
    )
    save_cache(processed_ids, last_id, last_signature)

    print("🔄 Conectado. Escuchando nuevos mensajes... (Ctrl+C para salir)")

    try:
        while True:
            while True:
                await _prepare_messages_container(page)

                if last_id and await _needs_scroll_to_bottom(page, last_id):
                    await page.keyboard.press("End")
                    await page.wait_for_timeout(SLOW_AFTER_SCROLL_MS)
                    await _prepare_messages_container(page)

                print("🔍 Buscando mensajes nuevos...")
                new_count, last_id, last_signature = await process_visible_top_to_bottom(
                    page,
                    processed_ids,
                    last_id,
                    last_signature,
                    verbose_print=verbose_print,
                )
                if not new_count:
                    break

                save_cache(processed_ids, last_id, last_signature)

            await asyncio.sleep(POLL_SECONDS)
    finally:
        save_cache(processed_ids, last_id, last_signature)

    return last_id


__all__ = ["monitor_conversation"]
"""Bucle principal que replica la lógica del script de ejemplo ``whatsapp.py``."""

from __future__ import annotations

import asyncio
import logging

from playwright.async_api import Locator, Page

from .cache import ProcessedIds, save_cache
from .constants import POLL_SECONDS, SLOW_AFTER_SCROLL_MS
from .containers import get_messages_container
from .processing import process_visible_top_to_bottom
from .scrolling import scroll_to_last_processed, scroll_to_very_top

logger = logging.getLogger(__name__)

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
        await page.wait_for_timeout(2_000)
        count = 0
        for _ in range(2):
            count = await locator.count()
            if count:
                break
            try:
                await page.locator("div[role='row'] div[data-id]").first.wait_for(
                    state="attached", timeout=2_000
                )
            except Exception:  # pragma: no cover - depende del estado del DOM
                await page.wait_for_timeout(500)
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

    if not last_id:
        # eliminar comentario a futuro
        print("⚠️ No tenemos un ID de búsqueda en caché (svc). Se partirá desde el inicio.")
        await scroll_to_very_top(page)
    else:
        # 1) Reubicación en el último mensaje procesado.
        #    Mantiene el punto de partida cuando hay datos en caché para
        #    evitar re-procesar la conversación completa tras una desconexión.
        print(f"🔎 Intentando reubicar el ID de búsqueda: {last_id}")
        await scroll_to_last_processed(page, last_id)

    # 2) Barrido inicial y guardado de mensajes visibles.
    #    Se recorre la ventana actual de mensajes desde el inicio hacia abajo para
    #    procesar y registrar cualquier mensaje que aún no esté en caché. La
    #    función devuelve el conteo de mensajes nuevos (ignoramos el valor), el
    #    último ID procesado y su firma, que se almacenan para mantener la
    #    continuidad del seguimiento.
    _, last_id, last_signature = await process_visible_top_to_bottom(
        page,
        processed_ids,
        last_id,
        last_signature,
        verbose_print=verbose_print,
    )

    #    Tras el barrido se persisten los identificadores procesados y el último
    #    punto de control para que, si la sesión se interrumpe, el sistema pueda
    #    reanudar desde el mismo lugar sin re-trabajar mensajes ya vistos

    print("🔄 Conectado. Escuchando nuevos mensajes... (Ctrl+C para salir)")

    try:
        while True:
            await _prepare_messages_container(page)

            if await _needs_scroll_to_bottom(page, last_id):
                await scroll_to_last_processed(page, last_id)
                try:
                    await page.keyboard.press("End")
                except Exception:  # pragma: no cover - depende del estado del DOM
                    pass
                await page.wait_for_timeout(SLOW_AFTER_SCROLL_MS)

            new_count, last_id, last_signature = await process_visible_top_to_bottom(
                page,
                processed_ids,
                last_id,
                last_signature,
                verbose_print=verbose_print,
            )

            if new_count or last_id:
                save_cache(processed_ids, last_id, last_signature)

            await asyncio.sleep(POLL_SECONDS)
    finally:
        save_cache(processed_ids, last_id, last_signature)

    return last_id


__all__ = ["monitor_conversation"]
"""Rutinas de análisis de mensajes visibles en la conversación."""

from __future__ import annotations

from typing import Dict, Tuple
from uuid import uuid4

from playwright.async_api import Locator, Page

from .cache import ProcessedIds
from .constants import SLOW_PER_MESSAGE_MS
from .csv_export import append_csv
from .jsonl_export import append_jsonl
from .media import download_from_blob, strict_has_blob_img_inside_copyable
from .parsing import get_text_fields
from .text_blocks import extract_timestamp_and_sender, get_text_block
from .iteration import iter_message_elements


async def process_message_strict(page: Page, message: Locator) -> Dict[str, str] | None:
    """Evalúa si un mensaje cumple con la estructura requerida y extrae sus datos."""

    data_id = await message.get_attribute("data-id") or ""
    blob_element, blob_src, data_src = await strict_has_blob_img_inside_copyable(message)
    if blob_element is None or not blob_src:
        return None

    full_text = await get_text_block(message)
    if not full_text:
        return None

    fields = get_text_fields(full_text)
    if not fields:
        return None

    timestamp, sender = await extract_timestamp_and_sender(message)
    file_stem = data_id or uuid4().hex
    image_path = await download_from_blob(page, blob_src, file_stem)

    result: Dict[str, str] = {
        "data_id": data_id,
        "timestamp": timestamp,
        "sender": sender,
        "raw_text": full_text,
        "img_src_blob": blob_src,
        "img_src_data": data_src,
        "img_file": image_path,
    }
    result.update(fields)
    return result


async def process_visible_top_to_bottom(
    page: Page,
    processed_ids: ProcessedIds,
    last_id: str,
    *,
    verbose_print: bool = True,
) -> Tuple[int, str]:
    """Recorre los mensajes visibles y procesa los que aún no fueron atendidos."""

    new_count = 0
    elements = await iter_message_elements(page)
    for element in elements:
        data_id = await element.get_attribute("data-id") or ""
        if not data_id or data_id in processed_ids:
            continue

        try:
            await element.scroll_into_view_if_needed(timeout=1_500)
        except Exception:  # pragma: no cover - depende de la UI
            pass
        await page.wait_for_timeout(SLOW_PER_MESSAGE_MS)

        parsed = await process_message_strict(page, element)
        if not parsed:
            continue

        append_csv(parsed)
        append_jsonl(parsed)

        processed_ids.add(parsed["data_id"])
        last_id = parsed["data_id"]
        if verbose_print:
            print("════════════════════════════════════════")
            print(f"✅ Capturado: {parsed['data_id']}")
            print(f"  Fecha/Hora : {parsed.get('timestamp', '')}")
            print(f"  Remitente  : {parsed.get('sender', '')}")
            print(f"  Nombre     : {parsed.get('Nombre de cliente', '')}")
            print(f"  N° Cel     : {parsed.get('N° de cel', '')}")
            print(f"  Producto   : {parsed.get('Producto y cantidad', '')}")
            print(f"  Serv./Desc.: {parsed.get('servicio_o_descripcion', '')}")
            print(f"  Método pago: {parsed.get('Método de pago', '')}")
            print(f"  Cuenta     : {parsed.get('Cuenta', '')}")
            print(f"  Detalle    : {parsed.get('Detalle', '')}")
            print(f"  Img SRC    : {parsed.get('img_src_blob', '')}")
            print(f"  Img File   : {parsed.get('img_file', '')}")
        new_count += 1

        await page.wait_for_timeout(SLOW_PER_MESSAGE_MS)

    return new_count, last_id


__all__ = ["process_message_strict", "process_visible_top_to_bottom"]
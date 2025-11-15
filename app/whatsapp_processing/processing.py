"""Rutinas de análisis de mensajes visibles en la conversación."""

from __future__ import annotations

import hashlib
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

    try:
        data_id = await message.get_attribute("data-id") or ""
    except Exception:
        return None
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


def _build_signature(payload: Dict[str, str]) -> str:
    """Genera una huella determinística de un mensaje exportado."""

    pieces = (
        payload.get("timestamp", ""),
        payload.get("sender", ""),
        payload.get("raw_text", ""),
        payload.get("img_src_blob", ""),
        payload.get("img_src_data", ""),
    )
    joined = "\u241e".join(pieces)
    return hashlib.sha1(joined.encode("utf-8", "ignore")).hexdigest()


async def process_visible_top_to_bottom(
    page: Page,
    processed_ids: ProcessedIds,
    last_id: str,
    last_signature: str,
    *,
    verbose_print: bool = True,
) -> Tuple[int, str, str]:
    """Recorre los mensajes visibles y procesa los que aún no fueron atendidos."""

    new_count = 0
    skip_until_last = False
    has_seen_last = False

    if last_id:
        try:
            locator = page.locator(f'div[role="row"] div[data-id="{last_id}"]')
            skip_until_last = await locator.count() > 0
        except Exception:  # pragma: no cover - depende del estado del DOM
            skip_until_last = False

    if not skip_until_last:
        has_seen_last = True

    elements = await iter_message_elements(page)
    for element in elements:
        try:
            data_id = await element.get_attribute("data-id") or ""
        except Exception:
            continue
        if not data_id:
            continue

        if skip_until_last and not has_seen_last and data_id != last_id:
            if data_id not in processed_ids:
                processed_ids.add(data_id)
            continue

        if data_id in processed_ids:
            continue

        try:
            await element.scroll_into_view_if_needed(timeout=1_500)
        except Exception:  # pragma: no cover - depende de la UI
            pass
        await page.wait_for_timeout(SLOW_PER_MESSAGE_MS)

        try:
            parsed = await process_message_strict(page, element)
        except Exception:
            continue
        if not parsed:
            continue

        signature = _build_signature(parsed)
        if last_signature and signature == last_signature and (
            not last_id or data_id == last_id
        ):
            processed_ids.add(parsed["data_id"])
            last_id = parsed["data_id"]
            last_signature = signature
            has_seen_last = True
            continue

        if data_id == last_id:
            if data_id not in processed_ids:
                processed_ids.add(data_id)
            last_signature = signature
            has_seen_last = True
            continue

        append_csv(parsed)
        append_jsonl(parsed)

        processed_ids.add(parsed["data_id"])
        last_id = parsed["data_id"]
        last_signature = signature
        has_seen_last = True
        if verbose_print:
            print("════════════════════════════════════════")
            print(f"✅ Capturado: {parsed['data_id']}")
            print(f"  Fecha/Hora : {parsed.get('timestamp', '')}")
            print(f"  Remitente  : {parsed.get('sender', '')}")
            print(f"  Nombre     : {parsed.get('Nombre de cliente', '')}")
            print(f"  N° Cel     : {parsed.get('N° de cel', '')}")
            print(f"  Producto   : {parsed.get('Producto y cantidad', '')}")
            print(f"  Serv./Desc.: {parsed.get('servicio_o_descripcion', '')}")
            print(f"  Balance    : {parsed.get('Balance', '')}")
            print(f"  Método pago: {parsed.get('Método de pago', '')}")
            print(f"  Cuenta     : {parsed.get('Cuenta', '')}")
            print(f"  Detalle    : {parsed.get('Detalle', '')}")
            print(f"  Img SRC    : {parsed.get('img_src_blob', '')}")
            print(f"  Img File   : {parsed.get('img_file', '')}")
        new_count += 1

        await page.wait_for_timeout(SLOW_PER_MESSAGE_MS)

    return new_count, last_id, last_signature


__all__ = ["process_message_strict", "process_visible_top_to_bottom"]

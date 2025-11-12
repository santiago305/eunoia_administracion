"""Gestión de imágenes asociadas a los comprobantes compartidos."""

from __future__ import annotations

import asyncio
import base64
from typing import Tuple

from playwright.async_api import Locator, Page

from .constants import BLOB_POLL_STEP_MS, BLOB_WAIT_MS_TOTAL, IMG_DIR
from .text_blocks import find_copyable_block_in


async def fetch_blob_to_base64(page: Page, blob_url: str) -> dict[str, str]:
    """Descarga un recurso ``blob:`` y lo convierte en base64."""

    return await page.evaluate(
        """async (blobUrl) => {
            const res = await fetch(blobUrl);
            const buf = await res.arrayBuffer();
            const ct = res.headers.get('content-type') || 'image/jpeg';
            const b64 = btoa(String.fromCharCode(...new Uint8Array(buf)));
            return { b64, contentType: ct };
        }""",
        blob_url,
    )


def ext_from_content_type(content_type: str | None) -> str:
    """Calcula la extensión de archivo más apropiada para un tipo MIME."""

    content_type = (content_type or "").lower()
    if "png" in content_type:
        return "png"
    if "webp" in content_type:
        return "webp"
    if "gif" in content_type:
        return "gif"
    return "jpg"


async def _wake_up_blob_image(message: Locator) -> None:
    """Intenta forzar la carga diferida de una imagen tipo blob."""

    try:
        await message.scroll_into_view_if_needed(timeout=1_500)
    except Exception:  # pragma: no cover - depende del estado de renderizado
        pass

    elapsed = 0
    while elapsed < BLOB_WAIT_MS_TOTAL:
        try:
            await message.hover(timeout=500)
        except Exception:  # pragma: no cover - depende del estado de la UI
            pass
        await asyncio.sleep(BLOB_POLL_STEP_MS / 1000.0)
        elapsed += BLOB_POLL_STEP_MS
        blob_count = await message.locator('img[src^="blob:"]').count()
        if blob_count > 0:
            return


async def strict_has_blob_img_inside_copyable(message: Locator) -> Tuple[Locator | None, str, str]:
    """Localiza las imágenes ``blob:`` dentro del bloque copyable-text."""

    block = await find_copyable_block_in(message)
    if block is None:
        return None, "", ""

    blob_images = block.locator('img[src^="blob:"]')
    data_images = block.locator('img[src^="data:image"]')

    if await blob_images.count() == 0:
        await _wake_up_blob_image(message)

    if await blob_images.count() == 0:
        return None, "", ""

    blob_element = blob_images.first
    blob_src = await blob_element.get_attribute("src") or ""
    data_src = ""
    if await data_images.count() > 0:
        data_src = await data_images.first.get_attribute("src") or ""
    return blob_element, blob_src, data_src


async def download_from_blob(page: Page, blob_src: str, file_stem: str) -> str:
    """Descarga y persiste una imagen ``blob:`` retornando la ruta creada."""

    if not blob_src:
        return ""

    response = await fetch_blob_to_base64(page, blob_src)
    extension = ext_from_content_type(response.get("contentType"))
    path = IMG_DIR / f"{file_stem}.{extension}"
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(base64.b64decode(response.get("b64", "")))
    return str(path)


__all__ = [
    "download_from_blob",
    "ext_from_content_type",
    "fetch_blob_to_base64",
    "strict_has_blob_img_inside_copyable",
]
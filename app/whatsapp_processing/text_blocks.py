"""Extracción de fragmentos de texto y metadatos desde cada mensaje."""

from __future__ import annotations

import re
from typing import Tuple

from playwright.async_api import Locator


async def find_copyable_block_in(message: Locator) -> Locator | None:
    """Localiza el bloque copyable-text asociado a un mensaje."""

    block = message.locator("div.copyable-text[data-pre-plain-text]").first
    if await block.count() == 0:
        return None
    return block


async def get_text_block(message: Locator) -> str:
    """Recupera el texto del mensaje combinando los spans seleccionables."""

    block = await find_copyable_block_in(message)
    if block is None:
        return ""

    spans = block.locator("span.selectable-text")
    total = min(await spans.count(), 120)
    texts: list[str] = []
    for index in range(total):
        try:
            content = await spans.nth(index).inner_text()
        except Exception:  # pragma: no cover - depende del renderizado
            continue
        value = content.strip()
        if value:
            texts.append(value)
    return "\n".join(texts)


async def extract_timestamp_and_sender(message: Locator) -> Tuple[str, str]:
    """Obtiene la marca temporal y el remitente de un mensaje."""

    block = await find_copyable_block_in(message)
    if block is None:
        return "", ""
    raw = await block.get_attribute("data-pre-plain-text") or ""
    match = re.search(r"\[(.*?)\]\s*(.*?):\s*$", raw)
    if not match:
        return "", ""
    return match.group(1).strip(), match.group(2).strip()


__all__ = ["extract_timestamp_and_sender", "find_copyable_block_in", "get_text_block"]
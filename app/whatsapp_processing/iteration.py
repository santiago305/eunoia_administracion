"""Recorridos ordenados sobre los mensajes visibles del chat."""

from __future__ import annotations

from typing import List

from playwright.async_api import Locator, Page

from .containers import message_rows


_PINNED_NOTICE_KEYWORDS = (
    "fijó un mensaje",
    "mensaje fijado",
    "pinned a message",
    "pinned message",
)


def _looks_like_pinned_notice(text: str) -> bool:
    """Detecta si el contenido corresponde al aviso de mensaje fijado."""

    simplified = text.strip().lower()
    if not simplified:
        return False
    return any(keyword in simplified for keyword in _PINNED_NOTICE_KEYWORDS)


async def first_message_id(page: Page) -> str:
    """Devuelve el identificador del primer mensaje visible."""

    rows = message_rows(page)
    count = await rows.count()
    if count == 0:
        return ""

    for index in range(count):
        row = rows.nth(index)
        data_id = await row.get_attribute("data-id")
        if not data_id:
            continue
        try:
            text = await row.inner_text()
        except Exception:  # pragma: no cover - depende del renderizado
            text = ""
        if _looks_like_pinned_notice(text):
            continue
        return data_id

    return ""


async def iter_message_elements(page: Page) -> List[Locator]:
    """Recorre los mensajes visibles de arriba hacia abajo."""

    rows = message_rows(page)
    count = await rows.count()
    if count == 0:
        return []

    items: List[tuple[float, Locator]] = []
    for index in range(count):
        el = rows.nth(index)
        try:
            box = await el.bounding_box()
        except Exception:  # pragma: no cover - depende del renderizado en tiempo real
            box = None
        y = box["y"] if box else 0.0
        items.append((y, el))

    items.sort(key=lambda item: item[0])
    return [element for _, element in items]


__all__ = ["first_message_id", "iter_message_elements"]
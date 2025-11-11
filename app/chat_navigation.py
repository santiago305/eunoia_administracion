"""Acciones de navegación específicas para WhatsApp Web."""

from __future__ import annotations

import logging

from playwright.async_api import Page, TimeoutError

logger = logging.getLogger(__name__)

_SEARCH_ENTRY_XPATH = "//*[@id='side']/div[1]/div/div[2]"
_CHAT_INPUT_SELECTOR = "div[role='textbox']"
_FIRST_RESULT_XPATH = (
    "//*[@id='pane-side']/div[1]/div/div/div[2]/div/div/div/div[2]/div[1]/div[1]/span/span"
)


class ChatNavigationError(RuntimeError):
    """Indica que no se pudo abrir el chat solicitado."""


async def open_chat(page: Page, chat_name: str) -> None:
    """Localiza y abre un chat por nombre dentro de WhatsApp Web."""

    logger.info("Buscando el chat '%s' en WhatsApp Web...", chat_name)

    try:
        await page.wait_for_selector(f"xpath={_SEARCH_ENTRY_XPATH}", timeout=10_000)
        await page.click(f"xpath={_SEARCH_ENTRY_XPATH}")
        await page.wait_for_selector(_CHAT_INPUT_SELECTOR, timeout=10_000)
        await page.fill(_CHAT_INPUT_SELECTOR, chat_name)
        await page.wait_for_selector(f"xpath={_FIRST_RESULT_XPATH}", timeout=10_000)
        await page.click(f"xpath={_FIRST_RESULT_XPATH}")
    except TimeoutError as exc:  # pragma: no cover - interacción con la UI
        raise ChatNavigationError(
            f"No se pudo abrir el chat '{chat_name}'. Verifica que exista."
        ) from exc

    logger.info("Chat '%s' abierto correctamente.", chat_name)


__all__ = ["ChatNavigationError", "open_chat"]
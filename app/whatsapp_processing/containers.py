"""Localizadores de WhatsApp Web empleados durante la captura."""

from __future__ import annotations

from playwright.async_api import Locator, Page


_MESSAGES_CONTAINER_SELECTOR = "div[data-scrolltracepolicy='wa.web.conversation.messages']"
_MESSAGE_ROWS_SELECTOR = "div[role='row'] div[data-id]"


def get_messages_container(page: Page) -> Locator:
    """Devuelve el contenedor que aloja el historial de mensajes."""

    container = page.locator(_MESSAGES_CONTAINER_SELECTOR).first
    return container


def message_rows(page: Page) -> Locator:
    """Construye un ``Locator`` con todos los mensajes visibles actuales."""

    return page.locator(_MESSAGE_ROWS_SELECTOR)


__all__ = ["get_messages_container", "message_rows"]
"""Utilidades para navegar a conversaciones específicas en WhatsApp Web."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from playwright.async_api import Locator, Page, TimeoutError as PlaywrightTimeoutError


logger = logging.getLogger(__name__)


class ConversationNotFoundError(RuntimeError):
    """Señala que no se pudo localizar la conversación solicitada."""

    pass


@dataclass(frozen=True)
class _ConversationSelectors:
    """Selectores relevantes para interactuar con la lista de chats."""

    chat_list: str = "[data-testid='chat-list']"
    search_container: str = "[data-testid='chat-list-search']"
    search_input: str = "[contenteditable='true']"


async def _ensure_chat_list_ready(page: Page, selectors: _ConversationSelectors, *, timeout: float) -> None:
    """Espera a que la columna de chats esté disponible."""

    try:
        await page.locator(selectors.chat_list).first.wait_for(
            state="visible", timeout=int(timeout * 1000)
        )
    except PlaywrightTimeoutError as exc:  # pragma: no cover - robustez
        raise ConversationNotFoundError(
            "No se pudo detectar la lista de conversaciones en el panel principal."
        ) from exc


async def _type_in_search(
    page: Page,
    selectors: _ConversationSelectors,
    conversation_title: str,
    *,
    timeout: float,
) -> None:
    """Escribe el nombre de la conversación en la búsqueda lateral."""

    container = page.locator(selectors.search_container).first
    try:
        await container.wait_for(state="visible", timeout=int(timeout * 1000))
    except PlaywrightTimeoutError:
        # La barra de búsqueda podría no existir (por ejemplo, interfaz reducida).
        logger.debug("No se encontró la barra de búsqueda lateral. Se intentará sin filtrado.")
        return

    input_box: Locator = container.locator(selectors.search_input).first
    try:
        await input_box.wait_for(state="visible", timeout=int(timeout * 1000))
    except PlaywrightTimeoutError:
        logger.debug("No se encontró un cuadro de texto para la búsqueda. Se continua sin filtrar.")
        return

    await input_box.click()
    await input_box.fill("")
    await input_box.type(conversation_title, delay=50)


async def _click_conversation(
    page: Page,
    conversation_title: str,
    *,
    timeout: float,
) -> None:
    """Busca y selecciona la conversación por su atributo ``title``."""

    conversation_locator = page.locator(f"span[title='{conversation_title}']").first
    try:
        await conversation_locator.wait_for(state="visible", timeout=int(timeout * 1000))
    except PlaywrightTimeoutError as exc:
        raise ConversationNotFoundError(
            f"No se encontró la conversación con el título '{conversation_title}'."
        ) from exc

    await conversation_locator.click()


async def _ensure_conversation_open(
    page: Page,
    conversation_title: str,
    *,
    timeout: float,
) -> None:
    """Verifica que el encabezado del chat activo coincida con el solicitado."""

    header_locator = page.locator(f"header span[title='{conversation_title}']").first
    try:
        await header_locator.wait_for(state="visible", timeout=int(timeout * 1000))
    except PlaywrightTimeoutError as exc:
        raise ConversationNotFoundError(
            "Se hizo clic en la conversación, pero el encabezado no coincide con el título esperado."
        ) from exc


async def open_conversation(
    page: Page,
    conversation_title: str,
    *,
    timeout: float = 30.0,
    logger_instance: logging.Logger | None = None,
) -> None:
    """Abre una conversación específica después de iniciar sesión en WhatsApp Web."""

    title = conversation_title.strip()
    if not title:
        raise ValueError("Se requiere un título de conversación no vacío para navegar.")

    logger_to_use = logger_instance or logger
    selectors = _ConversationSelectors()

    logger_to_use.info("Buscando la conversación '%s'...", title)

    await _ensure_chat_list_ready(page, selectors, timeout=timeout)
    await _type_in_search(page, selectors, title, timeout=timeout)
    await _click_conversation(page, title, timeout=timeout)
    await _ensure_conversation_open(page, title, timeout=timeout)

    logger_to_use.info("Conversación '%s' abierta correctamente.", title)


__all__ = ["ConversationNotFoundError", "open_conversation"]
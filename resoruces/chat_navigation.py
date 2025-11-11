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

    chat_list: tuple[str, ...] = (
        "[data-testid='chat-list']",
        "div[aria-label='Lista de chats']",
        "div[role='grid']",
    )
    search_container: tuple[str, ...] = (
        "[data-testid='chat-list-search']",
        "div._ai04",
    )
    search_input: tuple[str, ...] = (
        "[data-testid='chat-list-search'] [contenteditable='true']",
        "div[aria-label='Cuadro de texto para ingresar la búsqueda'][contenteditable='true']",
        "div[aria-placeholder='Buscar un chat o iniciar uno nuevo'][contenteditable='true']",
        "div[contenteditable='true'][role='textbox']",
    )
    search_button: tuple[str, ...] = (
        "button[data-icon='search']",
        "button[data-icon='search-alt']",
        "button[data-icon='search-refreshed-thin']",
        "div._ai04 button",
    )


async def _ensure_chat_list_ready(page: Page, selectors: _ConversationSelectors, *, timeout: float) -> None:
    """Espera a que la columna de chats esté disponible."""

    last_exc: PlaywrightTimeoutError | None = None
    for selector in selectors.chat_list:
        locator = page.locator(selector).first
        try:
            await locator.wait_for(state="visible", timeout=int(timeout * 1000))
            return
        except PlaywrightTimeoutError as exc:  # pragma: no cover - robustez
            last_exc = exc

    raise ConversationNotFoundError(
        "No se pudo detectar la lista de conversaciones en el panel principal."
    ) from last_exc


async def _type_in_search(
    page: Page,
    selectors: _ConversationSelectors,
    conversation_title: str,
    *,
    timeout: float,
) -> None:
    """Escribe el nombre de la conversación en la búsqueda lateral."""

    input_box: Locator | None = None

    # Intentamos localizar el contenedor y el cuadro de búsqueda con distintos selectores.
    for container_selector in selectors.search_container:
        container = page.locator(container_selector).first
        try:
            await container.wait_for(state="visible", timeout=int(timeout * 1000))
        except PlaywrightTimeoutError:
            continue

        for input_selector in selectors.search_input:
            candidate = container.locator(input_selector).first
            try:
                await candidate.wait_for(state="visible", timeout=int(timeout * 1000))
            except PlaywrightTimeoutError:
                continue

            input_box = candidate
            break

        if input_box:
            break

    if input_box is None:
        # Intentamos localizar el cuadro de búsqueda de manera global como último recurso.
        for input_selector in selectors.search_input:
            candidate = page.locator(input_selector).first
            try:
                await candidate.wait_for(state="visible", timeout=int(timeout * 1000))
            except PlaywrightTimeoutError:
                continue
            input_box = candidate
            break

    if input_box is None:
        logger.debug(
            "No se encontró un cuadro de texto para la búsqueda. Se continua sin filtrar."
        )
        return

    # Algunas interfaces requieren activar el cuadro de búsqueda mediante un botón previo.
    if not await input_box.is_enabled():
        for button_selector in selectors.search_button:
            button = page.locator(button_selector).first
            try:
                await button.click()
            except Exception:  # pragma: no cover - intento de robustez
                continue
            if await input_box.is_enabled():
                break

    await input_box.click()
    try:
        await input_box.fill("")
    except Exception:
        # Algunos cuadros basados en contenteditable no soportan ``fill``.
        await input_box.press("Control+A")
        await input_box.press("Backspace")

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
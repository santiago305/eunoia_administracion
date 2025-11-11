"""Herramientas para detectar y monitorear el estado de login en WhatsApp Web."""

from __future__ import annotations

import asyncio
import logging
from enum import Enum
from typing import Sequence

from playwright.async_api import Error as PlaywrightError, Locator, Page


logger = logging.getLogger(__name__)


class LoginState(Enum):
    """Posibles estados de autenticación en WhatsApp Web."""

    UNKNOWN = "unknown"
    LOGGED_OUT = "logged_out"
    LOGGED_IN = "logged_in"


DEFAULT_LOGIN_PROMPT_TEXTS: Sequence[str] = (
    "Pasos para iniciar sesión",
    "Vincular con el número de teléfono",
    "Iniciar sesión con número de teléfono",
)

DEFAULT_LOGGED_IN_XPATHS: Sequence[str] = (
    "//*[@id='app']/div[1]/div/div[3]",
    "//*[@id='app']/div[1]/div/div[3]/div/div[4]",
    "//*[@id='app']/div[1]/div/div[3]/div/div[5]",
)


async def _locator_is_visible(locator: Locator) -> bool:
    """Devuelve ``True`` cuando el elemento es visible y ``False`` en caso contrario."""

    try:
        return await locator.is_visible()
    except PlaywrightError:
        return False


async def detect_login_state(
    page: Page,
    *,
    prompt_texts: Sequence[str] = DEFAULT_LOGIN_PROMPT_TEXTS,
    logged_in_xpaths: Sequence[str] = DEFAULT_LOGGED_IN_XPATHS,
) -> LoginState:
    """Intenta determinar si la sesión de WhatsApp Web está activa."""

    # Revisamos los posibles selectores que indican una sesión activa.
    for xpath in logged_in_xpaths:
        locator = page.locator(f"xpath={xpath}")
        if await _locator_is_visible(locator):
            return LoginState.LOGGED_IN

    # Si no hay sesión activa, buscamos textos del asistente de inicio de sesión.
    for text in prompt_texts:
        locator = page.get_by_text(text, exact=True)
        if await _locator_is_visible(locator):
            return LoginState.LOGGED_OUT

    return LoginState.UNKNOWN


async def monitor_login_state(
    page: Page,
    *,
    check_interval: float = 15.0,
    prompt_interval: float = 10.0,
    prompt_message: str = "Escanea el QR para loguearte.",
    logger_instance: logging.Logger | None = None,
) -> LoginState:
    """Supervisa el estado de sesión e informa cuando cambia."""

    last_state: LoginState | None = None
    prompt_task: asyncio.Task[None] | None = None
    logger_to_use = logger_instance or logger

    async def _prompt_loop() -> None:
        # Mientras la sesión siga pendiente, recordamos al usuario escanear el QR.
        while True:
            logger_to_use.info(prompt_message)
            await asyncio.sleep(prompt_interval)

    async def _ensure_prompt_running() -> None:
        nonlocal prompt_task
        if prompt_task is None or prompt_task.done():
            prompt_task = asyncio.create_task(_prompt_loop())

    async def _stop_prompt() -> None:
        nonlocal prompt_task
        if prompt_task is not None:
            prompt_task.cancel()
            try:
                await prompt_task
            except asyncio.CancelledError:  # pragma: no cover - side effect
                pass
            prompt_task = None

    while True:
        state = await detect_login_state(page)
        if state != last_state:
            if state == LoginState.LOGGED_IN:
                logger_to_use.info("Te has logueado correctamente.")
            elif state == LoginState.LOGGED_OUT:
                logger_to_use.info("No se ha iniciado sesión en WhatsApp Web.")
            else:
                logger_to_use.info(
                    "Aún no se puede determinar el estado de la sesión. Continuaremos verificando..."
                )
            last_state = state

        if state == LoginState.LOGGED_IN:
            await _stop_prompt()
            return state
        if state == LoginState.LOGGED_OUT:
            await _ensure_prompt_running()
        else:
            await _stop_prompt()

        # Esperamos el intervalo configurado antes de volver a comprobar el estado.
        await asyncio.sleep(check_interval)


__all__ = [
    "DEFAULT_LOGGED_IN_XPATHS",
    "DEFAULT_LOGIN_PROMPT_TEXTS",
    "LoginState",
    "detect_login_state",
    "monitor_login_state",
]
"""Secuencia de arranque de la aplicación CLI."""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from fuvexbn.app.config import AppSettings, load_app_settings
# from fuvexbn.app.menu import prompt_filter_combo
from fuvexbn.app.orchestrator import (
    build_filter_combos,
    build_filter_runner_factories,
    run_selected_filters,
)
from fuvexbn.infra.browser.cdp import connect_browser_over_cdp
from fuvexbn.infra.browser.login import ensure_login
from fuvexbn.infra.excel.io import collect_dnis_sorted_by_abono
from fuvexbn.infra.excel.tree import ensure_excel_tree
from fuvexbn.infra.fs.resolve import resolve_dir
from fuvexbn.utils.excel.cleanup import cleanup_excel_temporaries
from fuvexbn.utils.logging_setup import setup_logging


logger = logging.getLogger(__name__)


def _collect_dnis_from_dir(base_dir: Path) -> list[str]:
    """Lee todos los Excel de ``base_dir`` y devuelve DNIs ordenados por abono."""

    return collect_dnis_sorted_by_abono(base_dir, global_sort=True, dedupe=True)


async def run(settings: AppSettings | None = None) -> None:
    """Ejecuta el flujo principal de la aplicación."""

    setup_logging()

    settings = settings or load_app_settings()
    logged_in = asyncio.Event()

    excel_base = settings.excels_base_path.strip()
    excel_user = settings.user_name.strip()
    derived_user_name = False

    if excel_base:
        if not excel_user:
            excel_user = (
                os.getenv("USERNAME")
                or os.getenv("USER")
                or Path.home().name
            )
            derived_user_name = True

        try:
            ensure_excel_tree(
                excel_base,
                user_name=excel_user,
                derived_user_name=derived_user_name,
            )
        except ValueError as exc:  # pragma: no cover - validación defensiva
            logger.error("No se pudo preparar la estructura de Excels: %s", exc)
            return

    browser = await connect_browser_over_cdp()
    if browser is None:
        logger.error(
            "No se pudo conectar a Chrome (CDP). Abre scripts/open_chrome_debug.ps1 y loguéate primero.",
        )
        return

    context = browser.contexts[0] if browser.contexts else await browser.new_context()

    try:
        await ensure_login(context)
    except Exception as exc:  # pragma: no cover - dependiente de Playwright
        logger.exception("No se pudo iniciar sesión automáticamente: %s", exc)
        await browser.close()
        return

    logged_in.set()

    base_buscar = resolve_dir(settings.excel_path_buscar, "buscar_lista/excels")
    base_filtrar = resolve_dir(settings.excel_path_filtrar, "filtrar_registrar/filtrar")

    cleanup_roots = [base_buscar, base_filtrar]

    register_wait_base: Path | None = None
    base_register: Path | None = None
    registros_root = settings.excel_path_registros.strip()

    if registros_root:
        register_wait_base = Path(registros_root).expanduser()
        try:
            base_register = resolve_dir(registros_root, "filtrar_registrar/registrar")
        except Exception as exc:  # pragma: no cover - lectura de disco
            logger.warning("[REGISTRO] No se pudo leer DNIs de carpeta Registro: %s", exc)
        else:
            cleanup_roots.append(base_register)
        cleanup_roots.append(register_wait_base)

    if excel_base:
        cleanup_roots.append(Path(excel_base).expanduser())

    cleanup_excel_temporaries(cleanup_roots)

    dnis_buscar = _collect_dnis_from_dir(base_buscar)
    dnis_filtrar = _collect_dnis_from_dir(base_filtrar)

    dnis_registrar: list[str] = []
    if base_register is not None:
        dnis_registrar = _collect_dnis_from_dir(base_register)


    logger.info(
        "[SETUP] Totales -> Busqueda: %d, Filtrar: %d, Registrar: %d",
        len(dnis_buscar),
        len(dnis_filtrar),
        len(dnis_registrar),
    )

    factories = build_filter_runner_factories(
        context=context,
        logged_in=logged_in,
        dnis_ing=dnis_buscar,
        base_pos=base_filtrar,
        register_wait_base=register_wait_base,
    )

    combos = build_filter_combos(
        factories,
        dnis_ing=dnis_buscar,
        base_pos=base_filtrar,
        register_wait_base=register_wait_base,
    )

    preferred_combo_order = (
        "Filtrar y registrar",
        "Filtrar",
        "Registrar",
    )

    selected_combo_label = None
    selected_keys: tuple[str, ...] = tuple()

    for combo_name in preferred_combo_order:
        combo = combos.get(combo_name)
        if combo is not None:
            selected_combo_label = combo_name
            selected_keys = combo.keys
            break
    else:
        selected_keys = tuple(factories.keys())
        if selected_keys:
            selected_combo_label = "Todos los filtros disponibles"
        else:
            selected_combo_label = "Sin filtros disponibles"

    logger.info(
        "[AUTOCOMBO] Seleccionado: %s -> %s",
        selected_combo_label,
        ", ".join(selected_keys) if selected_keys else "(ninguno)",
    )

    try:
        await run_selected_filters(factories, selected_keys)
    finally:
        await browser.close()


__all__ = ["run"]
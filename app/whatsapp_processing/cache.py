"""Persistencia mínima del estado de mensajes ya procesados."""

from __future__ import annotations

import json
from typing import Iterable, Set, Tuple

from .constants import CACHE_FILE


ProcessedIds = Set[str]


def load_cache(cache_path: str | None = None) -> Tuple[ProcessedIds, str, str]:
    """Recupera el estado previamente almacenado desde disco."""

    path = CACHE_FILE if cache_path is None else cache_path
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        return set(), "", ""

    processed = set(data.get("processed_ids", []))
    last_id = data.get("last_id", "")
    last_signature = data.get("last_signature", "")
    if last_id and last_id not in processed:
        processed.add(last_id)
    return processed, last_id, last_signature


def save_cache(
    processed_ids: Iterable[str],
    last_id: str,
    last_signature: str = "",
    cache_path: str | None = None,
) -> None:
    """Guarda el estado actual de captura para continuar en futuras ejecuciones."""

    path = CACHE_FILE if cache_path is None else cache_path
    payload = {
        "processed_ids": sorted(set(processed_ids)),
        "last_id": last_id,
        "last_signature": last_signature,
    }
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


__all__ = ["ProcessedIds", "load_cache", "save_cache"]

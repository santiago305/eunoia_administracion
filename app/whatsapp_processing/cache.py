"""Persistencia mínima del estado de mensajes ya procesados."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable, Set, Tuple

from .constants import CACHE_FILE, CSV_FILE


ProcessedIds = Set[str]


def _load_ids_from_csv(csv_path: str | None = None) -> tuple[ProcessedIds, str]:
    """Recupera los identificadores previamente exportados al CSV."""

    path = Path(CSV_FILE if csv_path is None else csv_path)
    if not path.exists():
        return set(), ""

    collected: ProcessedIds = set()
    last_seen = ""

    try:
        with path.open("r", newline="", encoding="utf-8") as handle:
            reader = csv.reader(handle)
            next(reader, None)  # omitimos el encabezado si existe
            for row in reader:
                if not row:
                    continue
                data_id = (row[0] or "").strip()
                if not data_id:
                    continue
                collected.add(data_id)
                last_seen = data_id
    except Exception:
        return collected, last_seen

    return collected, last_seen


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

    csv_ids, csv_last_id = _load_ids_from_csv()
    if csv_ids:
        processed.update(csv_ids)

    if csv_last_id:
        if last_id != csv_last_id:
            last_id = csv_last_id
            last_signature = ""

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
    ids = set(processed_ids)
    if last_id:
        ids.add(last_id)

    ordered_ids = sorted(ids)
    if last_id:
        try:
            ordered_ids.remove(last_id)
        except ValueError:
            pass
        ordered_ids.append(last_id)

    payload = {
        "processed_ids": ordered_ids,
        "last_id": last_id,
        "last_signature": last_signature,
    }
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


__all__ = ["ProcessedIds", "load_cache", "save_cache"]
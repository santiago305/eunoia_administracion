"""Persistencia mínima del estado de mensajes ya procesados."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator, List, Set, Tuple

from .constants import CACHE_FILE, CSV_FILE


ProcessedIds = Set[str]


@dataclass
class CacheState:
    """Estado completo recuperado del caché en disco."""

    processed_ids: ProcessedIds
    last_id: str
    last_signature: str
    previous_id: str = ""
    ordered_ids: Tuple[str, ...] = field(default_factory=tuple)

    def __iter__(self) -> Iterator[object]:
        """Permite desempaquetar ``CacheState`` como una tupla clásica."""

        yield self.processed_ids
        yield self.last_id
        yield self.last_signature


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


def load_cache(
    cache_path: str | None = None,
    csv_path: str | None = None,
) -> CacheState:
    """Recupera el estado previamente almacenado desde disco."""

    path = CACHE_FILE if cache_path is None else cache_path
    raw_ids: List[str] = []
    data: dict[str, object] = {}

    try:
        with open(path, "r", encoding="utf-8") as handle:
            loaded = json.load(handle)
    except FileNotFoundError:
        loaded = {}

    if isinstance(loaded, dict):
        data = loaded
        raw_ids = [
            value
            for value in data.get("processed_ids", [])
            if isinstance(value, str)
        ]
    else:
        raw_ids = []
        data = {}

    processed: ProcessedIds = set(raw_ids)

    last_id = str(data.get("last_id", "") or "")
    last_signature = str(data.get("last_signature", "") or "")

    if not last_id and raw_ids:
        # Compatibilidad con ejecuciones antiguas donde ``last_id`` no se guardaba.
        for candidate in reversed(raw_ids):
            if candidate:
                last_id = candidate
                last_signature = ""
                break

    csv_ids, csv_last_id = _load_ids_from_csv(csv_path)
    if csv_ids:
        processed.update(csv_ids)

    if csv_last_id:
        if last_id != csv_last_id:
            last_id = csv_last_id
            last_signature = ""

    if last_id and last_id not in processed:
        processed.add(last_id)

    previous_id = ""
    ordered_ids: Tuple[str, ...] = tuple(raw_ids)
    if last_id and raw_ids:
        try:
            idx = raw_ids.index(last_id)
        except ValueError:
            if len(raw_ids) >= 2:
                previous_id = raw_ids[-2]
        else:
            if idx > 0:
                previous_id = raw_ids[idx - 1]

    return CacheState(
        processed_ids=processed,
        last_id=last_id,
        last_signature=last_signature,
        previous_id=previous_id,
        ordered_ids=ordered_ids,
    )

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


__all__ = ["CacheState", "ProcessedIds", "load_cache", "save_cache"]

"""Persistencia mínima del estado de mensajes ya procesados."""

from __future__ import annotations

import csv
import json
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator, List, Mapping, Sequence, Set, Tuple

from .constants import CACHE_FILE, CSV_FILE, JSONL_FILE


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


def _load_ids_from_csv(
    csv_path: str | None = None,
) -> tuple[ProcessedIds, str, Tuple[str, ...]]:
    """Recupera los identificadores previamente exportados al CSV."""

    path = Path(CSV_FILE if csv_path is None else csv_path)
    if not path.exists():
        return set(), "", tuple()

    collected: ProcessedIds = set()
    ordered: list[str] = []
    last_seen = ""

    try:
        with path.open("r", newline="", encoding="utf-8") as handle:
            reader = csv.reader(handle)
            header = next(reader, None) or []
            header_lower = [value.lower() for value in header]
            data_idx = header_lower.index("data_id") if "data_id" in header_lower else 0
            for row in reader:
                if not row:
                    continue
                try:
                    data_id = (row[data_idx] or "").strip()
                except Exception:
                    continue
                if not data_id:
                    continue
                collected.add(data_id)
                ordered.append(data_id)
                last_seen = data_id
    except Exception:
        return collected, last_seen, tuple(ordered)

    return collected, last_seen, tuple(ordered)


def _build_signature(payload: Mapping[str, str]) -> str:
    """Replica la huella utilizada al exportar mensajes."""

    pieces: Sequence[str] = (
        payload.get("timestamp", ""),
        payload.get("sender", ""),
        payload.get("raw_text", ""),
        payload.get("img_src_blob", ""),
        payload.get("img_src_data", ""),
    )
    joined = "\u241e".join(pieces)
    return hashlib.sha1(joined.encode("utf-8", "ignore")).hexdigest()


def _load_last_signature_from_jsonl(
    jsonl_path: str | None = None,
) -> tuple[str, str]:
    """Obtiene la firma del último registro exportado en JSONL."""

    path = Path(JSONL_FILE if jsonl_path is None else jsonl_path)
    if not path.exists():
        return "", ""

    try:
        with path.open("r", encoding="utf-8") as handle:
            lines = [line.strip() for line in handle if line.strip()]
    except Exception:
        return "", ""

    for raw in reversed(lines):
        try:
            record = json.loads(raw)
        except Exception:
            continue
        if not isinstance(record, dict):
            continue
        data_id = str(record.get("data_id", "") or "")
        if not data_id:
            continue
        return data_id, _build_signature(record)

    return "", ""


def load_cache(
    cache_path: str | None = None,
    csv_path: str | None = None,
    jsonl_path: str | None = None,
    *,
    use_cache_file: bool = False,
) -> CacheState:
    """Recupera el estado previamente almacenado desde disco."""

    raw_ids: List[str] = []
    data: dict[str, object] = {}

    if use_cache_file:
        path = CACHE_FILE if cache_path is None else cache_path
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

    csv_ids, csv_last_id, ordered_csv_ids = _load_ids_from_csv(csv_path)
    if csv_ids:
        processed.update(csv_ids)

    if csv_last_id:
        if last_id != csv_last_id:
            last_id = csv_last_id
            last_signature = ""

    jsonl_last_id, jsonl_signature = _load_last_signature_from_jsonl(jsonl_path)
    if jsonl_last_id:
        processed.add(jsonl_last_id)
        if not last_id:
            last_id = jsonl_last_id
        if jsonl_last_id == last_id:
            last_signature = jsonl_signature or last_signature

    if last_id and last_id not in processed:
        processed.add(last_id)

    previous_id = ""
    ordered_ids: Tuple[str, ...] = ordered_csv_ids or tuple(raw_ids)
    if last_id and ordered_ids:
        try:
            idx = ordered_ids.index(last_id)
        except ValueError:
            if len(ordered_ids) >= 2:
                previous_id = ordered_ids[-2]
        else:
            if idx > 0:
                previous_id = ordered_ids[idx - 1]

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

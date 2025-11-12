"""Serialización de registros en formato JSONL."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

from .constants import JSONL_FILE


def append_jsonl(row: Mapping[str, str], jsonl_path: str | None = None) -> None:
    """Agrega un registro en formato JSON Lines al archivo configurado."""

    path = Path(JSONL_FILE if jsonl_path is None else jsonl_path)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


__all__ = ["append_jsonl"]
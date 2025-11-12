"""Constantes y patrones utilizados durante la captura de mensajes."""

from __future__ import annotations

import re
from pathlib import Path

CHAT_NAME = "Comprobantes Eunoia"

OUT_DIR = Path("outputs")
IMG_DIR = OUT_DIR / "images"
CSV_FILE = OUT_DIR / "comprobantes.csv"
JSONL_FILE = OUT_DIR / "comprobantes.jsonl"
CACHE_FILE = OUT_DIR / f"wa_cache_{CHAT_NAME}.json"

TOP_SCROLL_MAX_ROUNDS = 30
TOP_SCROLL_PGUP_BURST = 6
SLOW_PER_MESSAGE_MS = 350
SLOW_AFTER_SCROLL_MS = 400
BLOB_WAIT_MS_TOTAL = 2_500
BLOB_POLL_STEP_MS = 200
POLL_SECONDS = 2.0

FIELD_PATTERNS = {
    "Nombre de cliente": re.compile(r"(?i)Nombre\s*de\s*cliente:\s*(.+)"),
    "N° de cel": re.compile(r"(?i)(?:N[°º]\s*de\s*cel|N[°º]\s*cel|Cel(?:ular)?):\s*(\+?\d[\d\s]+)"),
    "Producto y cantidad": re.compile(r"(?i)Producto\s*y\s*cantidad:\s*(.+)"),
    "Servicio": re.compile(r"(?i)\bServicio:\s*(.+)"),
    "Descripción": re.compile(r"(?i)\bDescripci[oó]n:\s*(.+)"),
    "Método de pago": re.compile(r"(?i)M[eé]todo\s*de\s*pago:\s*(.+)"),
    "Cuenta": re.compile(r"(?i)\bCuenta:\s*(.+)"),
    "Detalle": re.compile(r"(?i)\bDetalle:\s*(.+)"),
}

__all__ = [
    "BLOB_POLL_STEP_MS",
    "BLOB_WAIT_MS_TOTAL",
    "CACHE_FILE",
    "CHAT_NAME",
    "CSV_FILE",
    "FIELD_PATTERNS",
    "IMG_DIR",
    "JSONL_FILE",
    "OUT_DIR",
    "POLL_SECONDS",
    "SLOW_AFTER_SCROLL_MS",
    "SLOW_PER_MESSAGE_MS",
    "TOP_SCROLL_MAX_ROUNDS",
    "TOP_SCROLL_PGUP_BURST",
]
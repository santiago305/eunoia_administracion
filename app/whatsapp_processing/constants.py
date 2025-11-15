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

TOP_SCROLL_MAX_ROUNDS = 60
TOP_SCROLL_PGUP_BURST = 10
SLOW_PER_MESSAGE_MS = 350
SLOW_AFTER_SCROLL_MS = 400
BLOB_WAIT_MS_TOTAL = 2_500
BLOB_POLL_STEP_MS = 200
POLL_SECONDS = 1.0

_FIELD_BOUNDARY = (
    r"(?="
    r"(?:\s{2,}(?:"
    r"Nombre\s*de\s*cliente"
    r"|N[°º]\s*de\s*cel"
    r"|Producto\s*y\s*cantidad"
    r"|Servicio"
    r"|Descripci[oó]n"
    r"|Balance"
    r"|M[eé]todo\s*(?:de\s*)?pago"
    r"|Cuenta"
    r"|Detalle"
    r"|Nombre"
    r"|Remitente"
    r"|Img\s*(?:SRC|File)?"
    r"|Fecha\s*/?\s*Hora"
    r"|Capturado"
    r")\s*:"
    r")"
    r"|[\r\n]"
    r"|$)"
)

FIELD_PATTERNS = {
    "Nombre de cliente": re.compile(r"Nombre\s*de\s*cliente:\s*(.+?)" + _FIELD_BOUNDARY, re.IGNORECASE),
    "N° de cel": re.compile(
        r"(?:N[°º]\s*de\s*cel|N[°º]\s*cel|Cel(?:ular)?):\s*(\+?\d[\d\s]+?)" + _FIELD_BOUNDARY,
        re.IGNORECASE,
    ),
    "Producto y cantidad": re.compile(r"Producto\s*y\s*cantidad:\s*(.+?)" + _FIELD_BOUNDARY, re.IGNORECASE),
    "Servicio": re.compile(r"\bServicio:\s*(.+?)" + _FIELD_BOUNDARY, re.IGNORECASE),
    "Descripción": re.compile(r"\bDescripci[oó]n:\s*(.+?)" + _FIELD_BOUNDARY, re.IGNORECASE),
    "Balance": re.compile(r"\bBalance:\s*(.+?)" + _FIELD_BOUNDARY, re.IGNORECASE),
    "Método de pago": re.compile(r"M[eé]todo\s*(?:de\s*)?pago:\s*(.+?)" + _FIELD_BOUNDARY, re.IGNORECASE),
    "Cuenta": re.compile(r"\bCuenta:\s*(.+?)" + _FIELD_BOUNDARY, re.IGNORECASE),
    "Detalle": re.compile(r"\bDetalle:\s*(.+?)" + _FIELD_BOUNDARY, re.IGNORECASE),
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
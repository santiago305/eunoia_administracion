"""Normalización y envío de comprobantes a Google Sheets."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Mapping

from sheets.googlesheets import (
    MONTH_WORKSHEET_TITLES,
    get_worksheet_by_month,
    registrar_movimiento,
)


DATE_PATTERN = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{2,4})")
MONTH_ABBREVIATIONS = (
    "ENE",
    "FEB",
    "MAR",
    "ABR",
    "MAY",
    "JUN",
    "JUL",
    "AGO",
    "SEP",
    "OCT",
    "NOV",
    "DIC",
)
PAYMENT_METHOD_ALIASES = {
    "BCP": {"yape", "bcp"},
    "LIGO": {"plin", "ligo"},
    "EFECTIVO": {"efectivo", "cash"},
}
DEFAULT_STATE = "REALIZADO"


def _normalize_year(raw_year: str) -> int | None:
    try:
        numeric = int(raw_year)
    except ValueError:
        return None

    if numeric < 100:
        return 2000 + numeric
    return numeric


def _extract_date(*candidates: str) -> datetime | None:
    for value in candidates:
        if not value:
            continue
        match = DATE_PATTERN.search(value)
        if not match:
            continue

        day, month, year = match.groups()
        normalized_year = _normalize_year(year)
        if normalized_year is None:
            continue

        try:
            return datetime(normalized_year, int(month), int(day))
        except ValueError:
            continue
    return None


def _normalize_payment_method(raw: str) -> str:
    if not raw:
        return ""

    lowered = raw.lower()
    for canonical, tokens in PAYMENT_METHOD_ALIASES.items():
        if any(token in lowered for token in tokens):
            return canonical

    return raw.strip().upper()


def _build_sheet_payload(parsed: Mapping[str, str]) -> dict[str, Any] | None:
    timestamp = parsed.get("timestamp", "")
    raw_text = parsed.get("raw_text", "")
    parsed_date = _extract_date(timestamp, raw_text)
    if parsed_date is None:
        return None

    month_abbr = MONTH_ABBREVIATIONS[parsed_date.month - 1]
    if month_abbr not in MONTH_WORKSHEET_TITLES:
        return None

    descripcion = parsed.get("servicio_o_descripcion", "").strip()
    detalle = parsed.get("Detalle", "").strip()
    metodo_pago = _normalize_payment_method(parsed.get("Método de pago", ""))
    numero_operacion = parsed.get("Cuenta", "").strip()

    return {
        "mes": month_abbr,
        "fecha": parsed_date.strftime("%d/%m/%Y"),
        "numero_operacion": numero_operacion,
        "descripcion": descripcion,
        "detalle": detalle,
        "metodo_pago": metodo_pago,
        "estado": DEFAULT_STATE,
        "ingresos": None,
        "egresos": None,
    }


def export_to_sheets(parsed: Mapping[str, str]) -> bool:
    """Envía el mensaje procesado a la pestaña mensual correspondiente."""

    payload = _build_sheet_payload(parsed)
    if payload is None:
        return False

    worksheet = get_worksheet_by_month(payload["mes"])
    if worksheet is None:
        return False

    return registrar_movimiento(
        worksheet,
        payload["mes"],
        payload["fecha"],
        payload["numero_operacion"],
        payload["descripcion"],
        payload["detalle"],
        payload["metodo_pago"],
        payload["estado"],
        ingresos=payload["ingresos"],
        egresos=payload["egresos"],
    )


__all__ = ["export_to_sheets"]
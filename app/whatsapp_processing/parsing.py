"""Normalización de campos de texto obtenidos desde los mensajes."""

from __future__ import annotations

import re
from typing import Dict

from .constants import FIELD_PATTERNS


def looks_like_form_alt(alt_text: str | None) -> bool:
    """Verifica si un texto alternativo contiene claves relevantes del formulario."""

    if not alt_text:
        return False
    lowered = alt_text.lower()
    tokens = [
        "nombre de cliente",
        "producto y cantidad",
        "método de pago",
        "metodo de pago",
        "servicio",
        "descripción",
        "descripcion",
        "cuenta",
        "detalle",
        "anticipo",
        "completo",
    ]
    return any(token in lowered for token in tokens)


def get_text_fields(text: str) -> Dict[str, str] | None:
    """Extrae los campos estructurados presentes en el cuerpo del mensaje."""

    data: Dict[str, str] = {}
    for field, pattern in FIELD_PATTERNS.items():
        match = pattern.search(text)
        if match:
            data[field] = match.group(1).strip()

    if "Detalle" not in data and re.search(r"(?im)^\s*ANTICIPO\s*$", text):
        data["Detalle"] = "ANTICIPO"

    service = data.get("Servicio")
    description = data.get("Descripción")
    if service and description:
        data["servicio_o_descripcion"] = description
    elif service:
        data["servicio_o_descripcion"] = service
    elif description:
        data["servicio_o_descripcion"] = description

    keys = [
        "Nombre de cliente",
        "N° de cel",
        "Producto y cantidad",
        "servicio_o_descripcion",
        "Método de pago",
        "Cuenta",
        "Detalle",
    ]
    if not any(key in data for key in keys):
        return None
    return data


__all__ = ["get_text_fields", "looks_like_form_alt"]
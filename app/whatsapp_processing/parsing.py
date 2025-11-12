"""Normalización de campos de texto obtenidos desde los mensajes."""

from __future__ import annotations

import re
import unicodedata
from typing import Dict, List

from .constants import FIELD_PATTERNS


ANTICIPO_PATTERN = re.compile(r"(?i)ANTICIPO")
KNOWN_FIELD_PREFIXES = {
    "nombre de cliente",
    "n de cel",
    "n de celular",
    "producto y cantidad",
    "producto",
    "servicio",
    "serv desc",
    "servicio descripcion",
    "descripcion",
    "metodo de pago",
    "metodo pago",
    "metodo",
    "cuenta",
    "img src",
    "img file",
    "imagen",
    "capturado",
    "fecha hora",
    "remitente",
    "nombre",
}


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

    if "Detalle" not in data:
        detail_candidate = _extract_implied_detail(text)
        if detail_candidate:
            data["Detalle"] = detail_candidate

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


def _extract_implied_detail(text: str) -> str | None:
    """Deriva un detalle a partir del contenido libre del mensaje."""

    segments = _segment_message(text)
    if not segments:
        return None

    # Prioriza aquellos fragmentos que mencionan ANTICIPO.
    for segment in reversed(segments):
        if not ANTICIPO_PATTERN.search(segment):
            continue
        extracted = _detail_from_anticipo_segment(segment)
        if extracted:
            return extracted

    # Como alternativa, usa el último fragmento que no sea un campo conocido.
    for segment in reversed(segments):
        if _segment_is_known_field(segment):
            continue
        cleaned = _clean_detail_segment(segment)
        if cleaned:
            return cleaned

    return None


def _segment_message(text: str) -> List[str]:
    """Divide el mensaje en segmentos relevantes, separando por saltos y viñetas."""

    segments: List[str] = []
    for raw_line in re.split(r"[\r\n]+", text):
        if not raw_line:
            continue
        parts = raw_line.split("✅") if "✅" in raw_line else [raw_line]
        for part in parts:
            cleaned = part.strip()
            if cleaned:
                segments.append(cleaned)
    return segments


def _detail_from_anticipo_segment(segment: str) -> str | None:
    """Obtiene la porción posterior a la palabra ANTICIPO dentro de un segmento."""

    match = re.search(r"(?i)ANTICIPO\b[\s:\-]*([^\r\n]*)", segment)
    if match:
        remainder = match.group(1).strip()
        if remainder:
            return remainder

    trailing = re.split(r"(?i)ANTICIPO", segment)[-1].strip(" :.-")
    return trailing or None


def _segment_is_known_field(segment: str) -> bool:
    prefix = _normalize_prefix(segment)
    if not prefix:
        return False
    return any(prefix.startswith(item) for item in KNOWN_FIELD_PREFIXES)


def _normalize_prefix(segment: str) -> str:
    normalized = unicodedata.normalize("NFD", segment)
    normalized = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    normalized = normalized.replace("º", "").replace("°", "")
    normalized = normalized.lower()
    prefix = normalized.split(":", 1)[0]
    prefix = re.sub(r"[^a-z0-9]+", " ", prefix)
    prefix = re.sub(r"\s+", " ", prefix)
    return prefix.strip()


def _clean_detail_segment(segment: str) -> str:
    cleaned = segment.strip()
    cleaned = cleaned.lstrip("-•:·")
    return cleaned.strip()


__all__ = ["get_text_fields", "looks_like_form_alt"]
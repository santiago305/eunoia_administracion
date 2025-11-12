"""Funciones auxiliares para escribir el CSV de comprobantes."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Mapping

from .constants import CSV_FILE


HEADER = [
    "data_id",
    "timestamp",
    "sender",
    "Nombre de cliente",
    "N° de cel",
    "Producto y cantidad",
    "servicio_o_descripcion",
    "Método de pago",
    "Cuenta",
    "Detalle",
    "img_src_blob",
    "img_src_data",
    "img_file",
]


def init_csv(csv_path: str | None = None) -> None:
    """Crea el archivo CSV con el encabezado apropiado si no existe."""

    path = Path(CSV_FILE if csv_path is None else csv_path)
    if not path.exists():
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(HEADER)


def append_csv(row: Mapping[str, str], csv_path: str | None = None) -> None:
    """Agrega una fila con los datos extraídos al archivo CSV."""

    path = Path(CSV_FILE if csv_path is None else csv_path)
    with open(path, "a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow([row.get(column, "") for column in HEADER])


__all__ = ["append_csv", "init_csv"]
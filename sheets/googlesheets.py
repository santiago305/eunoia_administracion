from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional

import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import WorksheetNotFound


# -------- CONFIGURACIÓN GLOBAL --------
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SERVICE_ACCOUNT_FILE = Path("eunoia.json")
SHEET_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1aWa99epeIy7pZn3MaVxOy-CMsc9RQLVP3MGk1kwQeqA/edit?gid=472731081#gid=472731081"
)

MONTH_WORKSHEET_TITLES: Dict[str, str] = {
    "ENE": "ENERO",
    "FEB": "FEBRERO",
    "MAR": "MARZO",
    "ABR": "ABRIL",
    "MAY": "MAYO",
    "JUN": "JUNIO",
    "JUL": "JULIO",
    "AGO": "AGOSTO",
    "SEP": "SEPTIEMBRE",
    "OCT": "OCTUBRE",
    "NOV": "NOVIEMBRE",
    "DIC": "DICIEMBRE",
}


@lru_cache(maxsize=1)
def _get_sheet() -> Optional[gspread.Spreadsheet]:
    """Obtiene la hoja de cálculo si las credenciales están disponibles."""
    if not SERVICE_ACCOUNT_FILE.exists():
        return None

    try:
        creds = Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        client = gspread.authorize(creds)
        return client.open_by_url(SHEET_URL)
    except Exception:
        return None


_WORKSHEET_CACHE: Dict[str, gspread.Worksheet] = {}


def get_worksheet_by_month(month_abbr: str) -> Optional[gspread.Worksheet]:
    """Recupera la pestaña asociada al mes abreviado (ENE, FEB, ...)."""
    title = MONTH_WORKSHEET_TITLES.get(month_abbr.upper())
    if not title:
        return None

    if title in _WORKSHEET_CACHE:
        return _WORKSHEET_CACHE[title]

    sheet = _get_sheet()
    if sheet is None:
        return None

    try:
        # 👉 aquí usamos el título correcto según el mes
        worksheet = sheet.worksheet(title)
    except WorksheetNotFound:
        return None
    except Exception:
        return None

    _WORKSHEET_CACHE[title] = worksheet
    return worksheet


# -------- FUNCIÓN PRINCIPAL --------
RANGO_ENCABEZADOS = "B2:J2"
CAMPOS_NUMERICOS = {"INGRESOS", "EGRESOS"}


def registrar_movimiento(
    worksheet: gspread.Worksheet | None,
    mes: str,
    fecha: str,
    numero_operacion: str,
    descripcion: str,
    detalle: str,
    metodo_pago: str,
    estado: str,
    ingresos: float | int | None = None,
    egresos: float | int | None = None,
) -> bool:
    """
    Inserta un movimiento en la hoja indicada,
    respetando los encabezados B2:J2 y sin tocar la columna K (SALDO).
    """
    if worksheet is None:
        return False

    try:
        # Leer encabezados
        encabezados = worksheet.get(RANGO_ENCABEZADOS)[0]

        # Calcular siguiente fila libre usando la columna B (MES)
        col_mes = worksheet.col_values(2)
        siguiente_fila = 3 if len(col_mes) <= 1 else len(col_mes) + 1

        # Crear diccionario con datos
        nuevo_registro = {
            "MES": mes,
            "FECHA": fecha,
            "N° DE OPERACIÓN": numero_operacion,
            "DESCRIPCIÓN": descripcion,
            "DETALLE": detalle,
            "MÉTODO DE PAGO": metodo_pago,
            "ESTADO": estado,
            "INGRESOS": ingresos if ingresos is not None else 0,
            "EGRESOS": egresos if egresos is not None else 0,
        }

        # Construir fila respetando orden de encabezados
        fila_nueva = []
        for h in encabezados:
            valor = nuevo_registro.get(h, "")
            if h in CAMPOS_NUMERICOS and valor not in ("", None):
                try:
                    valor = float(valor)
                except ValueError:
                    pass
            else:
                if valor is None:
                    valor = ""
            fila_nueva.append(valor)

        # Escribir en B:J en la fila disponible
        rango = f"B{siguiente_fila}:J{siguiente_fila}"
        worksheet.update(range_name=rango, values=[fila_nueva])
        return True

    except Exception:
        return False

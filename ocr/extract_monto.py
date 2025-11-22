"""
extract_monto.py
-----------------
Funciones para detectar el monto principal.
"""

from typing import List, Tuple, Dict
import re

from text_utils import normalizar

# Lista de meses para detección de fechas y descartar años
MESES = [
    "ene", "feb", "mar", "abr", "may", "jun",
    "jul", "ago", "set", "oct", "nov", "dic"
]


def extraer_numeros_monto(linea: str):
    """
    Devuelve una lista de posibles montos encontrados en la línea.
    Normaliza comas y puntos a formato decimal estándar.
    """
    patron = r"[0-9][0-9\.,]*[0-9]"
    matches = re.findall(patron, linea)
    candidatos = []
    for m in matches:
        limpio = m.replace(" ", "")
        if "," in limpio and "." in limpio:
            limpio = limpio.replace(".", "").replace(",", ".")
        elif "," in limpio and "." not in limpio:
            limpio = limpio.replace(",", ".")
        if len(limpio) >= 2:
            candidatos.append(limpio)
    return candidatos


def _es_posible_anio(valor: float) -> bool:
    """Devuelve True si el número parece un año (1900–2100)."""
    return 1900 <= valor <= 2100


def extraer_monto_desde_texto(texto: str):
    """
    Encuentra el monto principal dentro de un bloque OCR.

    Mejoras:
    - Prioriza número después de "S/" como monto.
    - Ignora números que parecen año (1900–2100).
    - Si aparece un mes (ene, feb... dic), descarta el número de 4 dígitos como año.
    """
    lineas = [l.strip() for l in texto.splitlines() if l.strip()]
    candidatas = []

    # 1: Líneas con S/
    for linea in lineas:
        norm = normalizar(linea)
        if "s/" in norm or "s/." in norm:
            candidatas.append(linea)

    # 2: Palabras clave si falta
    if not candidatas:
        for linea in lineas:
            norm = normalizar(linea)
            if any(p in norm for p in ["monto", "importe", "total"]):
                if any(bad in norm for bad in ["saldo", "comision", "igv"]):
                    continue
                candidatas.append(linea)

    if not candidatas:
        return None

    # --- Intento 1: reconocer monto inmediatamente después de S/ ---
    for linea in candidatas:
        m = re.search(
            r"[sS]\s*/\.?\s*([0-9]{1,5}(?:[.,][0-9]{2})?)",
            linea
        )
        if m:
            monto_raw = m.group(1)

            # Normalizar
            monto_norm = monto_raw.replace(" ", "")
            if "," in monto_norm and "." in monto_norm:
                monto_norm = monto_norm.replace(".", "").replace(",", ".")
            elif "," in monto_norm and "." not in monto_norm:
                monto_norm = monto_norm.replace(",", ".")

            try:
                valor = float(monto_norm)
                if not _es_posible_anio(valor):
                    return monto_norm
            except ValueError:
                pass

    # --- Intento 2: enfoque general ---
    mejor_monto = None
    mejor_valor = -1.0

    for linea in candidatas:
        norm = normalizar(linea)
        contiene_mes = any(m in norm for m in MESES)

        nums = extraer_numeros_monto(linea)
        for n in nums:
            try:
                valor = float(n)
            except ValueError:
                continue

            # Si parece año, descartamos
            if contiene_mes and _es_posible_anio(valor):
                continue
            if _es_posible_anio(valor):
                continue

            if valor > mejor_valor:
                mejor_valor = valor
                mejor_monto = n

    return mejor_monto


def elegir_mejor_monto(textos_ocr: "List[Tuple[str, str]]"):
    """
    Dado el OCR de varios motores, elige el monto más consistente y probable.
    Cuenta repeticiones y elige el mayor valor.
    """
    conteo: Dict[str, int] = {}
    valores: Dict[str, float] = {}

    for source, texto in textos_ocr:
        monto = extraer_monto_desde_texto(texto)
        if not monto:
            continue
        clave = monto
        conteo[clave] = conteo.get(clave, 0) + 1
        try:
            valor = float(monto)
        except ValueError:
            valor = -1.0
        valores[clave] = valor

    if not conteo:
        return None

    mejor = sorted(
        conteo.keys(),
        key=lambda m: (conteo[m], valores.get(m, -1.0)),
        reverse=True
    )[0]
    return mejor

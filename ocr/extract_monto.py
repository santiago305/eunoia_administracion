"""
extract_monto.py
-----------------
Funciones para detectar el monto principal.
"""

from typing import List, Tuple, Dict
import re

from text_utils import normalizar

def extraer_numeros_monto(linea: str):
    patron = r"[0-9][0-9\.,]*[0-9]"
    matches = re.findall(patron, linea)
    candidatos = []
    for m in matches:
        limpio = m.replace(" ", "")
        if "," in limpio and "." in limpio:
            limpio = limpio.replace(".", "").replace(",", ".")
        elif "," in limpio and "." not in limpio:
            limpio = limpio.replace(",", ".")
        if len(limpio) >= 3:
            candidatos.append(limpio)
    return candidatos

def extraer_monto_desde_texto(texto: str):
    lineas = [l.strip() for l in texto.splitlines() if l.strip()]
    candidatas = []

    for linea in lineas:
        norm = normalizar(linea)
        if "s/" in norm or "s/." in norm:
            candidatas.append(linea)

    if not candidatas:
        for linea in lineas:
            norm = normalizar(linea)
            if any(p in norm for p in ["monto", "importe", "total"]):
                if any(bad in norm for bad in ["saldo", "comision", "igv"]):
                    continue
                candidatas.append(linea)

    if not candidatas:
        return None

    mejor_monto = None
    mejor_valor = -1.0

    for linea in candidatas:
        nums = extraer_numeros_monto(linea)
        for n in nums:
            try:
                valor = float(n)
            except ValueError:
                continue
            if valor > mejor_valor:
                mejor_valor = valor
                mejor_monto = n

    return mejor_monto

def elegir_mejor_monto(textos_ocr: "List[Tuple[str, str]]"):
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

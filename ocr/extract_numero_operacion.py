"""
extract_numero_operacion.py
----------------------------
Funciones para detectar el número de operación.
"""

from typing import List, Tuple, Dict
import re

from text_utils import normalizar

CLAVES_NUM_OPERACION = [
    "nro de operacion",
    "nro. de operacion",
    "numero de operacion",
    "número de operacion",
    "numero operacion",
    "nro operacion",
    "nro. operacion",
    "nro operacion:",
    "codigo de operacion",
    "codigo operacion",
    "codigo de operaci",
    "cod de operacion",
    "n operacion",
    "no. operacion",
    "no operacion",
    "codigo de operacion",
    "código de operación",
]

def extraer_numero_operacion_desde_texto(texto: str):
    lineas = [l.strip() for l in texto.splitlines() if l.strip()]

    mejor_candidato = None
    mejor_longitud = 0

    for linea in lineas:
        norm = normalizar(linea)
        if any(cl in norm for cl in CLAVES_NUM_OPERACION):
            numeros = re.findall(r"\d{6,}", linea)
            for num in numeros:
                if len(num) > mejor_longitud:
                    mejor_longitud = len(num)
                    mejor_candidato = num

    if not mejor_candidato:
        ultimas = lineas[-5:]
        for linea in ultimas:
            numeros = re.findall(r"\d{6,}", linea)
            for num in numeros:
                if len(num) > mejor_longitud:
                    mejor_longitud = len(num)
                    mejor_candidato = num

    return mejor_candidato

def elegir_mejor_numero_operacion(textos_ocr: "List[Tuple[str, str]]"):
    conteo: Dict[str, int] = {}
    longitudes: Dict[str, int] = {}

    for source, texto in textos_ocr:
        num = extraer_numero_operacion_desde_texto(texto)
        if not num:
            continue
        clave = num
        conteo[clave] = conteo.get(clave, 0) + 1
        longitudes[clave] = len(num)

    if not conteo:
        return None

    mejor = sorted(
        conteo.keys(),
        key=lambda n: (conteo[n], longitudes.get(n, 0)),
        reverse=True
    )[0]
    return mejor

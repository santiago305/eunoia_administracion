"""
procesar_comprobantes.py
-------------------------
Script principal que orquesta todo el flujo OCR para comprobantes.
"""

import os
from typing import List, Dict, Any

from ocr_settings import CARPETA_COMPROBANTES
from ocr_engines import ocr_multi, HAS_EASYOCR, HAS_TROCR
from extract_monto import elegir_mejor_monto
from extract_numero_operacion import elegir_mejor_numero_operacion

def procesar_comprobante_premium(ruta_imagen: str) -> Dict[str, Any]:
    print(f"Procesando (premium): {ruta_imagen}")
    textos_ocr = ocr_multi(ruta_imagen)
    if not textos_ocr:
        print("   [ERROR] No se obtuvo texto del OCR.")
        return {
            "ruta": ruta_imagen,
            "textos_ocr": [],
            "monto": None,
            "numero_operacion": None,
        }

    monto = elegir_mejor_monto(textos_ocr)
    numero_operacion = elegir_mejor_numero_operacion(textos_ocr)

    data: Dict[str, Any] = {
        "ruta": ruta_imagen,
        "textos_ocr": textos_ocr,
        "monto": monto,
        "numero_operacion": numero_operacion,
    }

    print(f"   Motores usados    : {[s for s, _ in textos_ocr]}")
    print(f"   Monto elegido     : {monto}")
    print(f"   Número operación  : {numero_operacion}")
    return data

def procesar_carpeta_premium(ruta_carpeta) -> "List[Dict[str, Any]]":
    resultados: List[Dict[str, Any]] = []

    if not ruta_carpeta.exists() or not ruta_carpeta.is_dir():
        print(f"[ERROR] La carpeta {ruta_carpeta} no existe o no es una carpeta.")
        return resultados

    extensiones = (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff")

    for nombre in sorted(os.listdir(ruta_carpeta)):
        if not nombre.lower().endswith(extensiones):
            continue

        ruta = ruta_carpeta / nombre
        info = procesar_comprobante_premium(str(ruta))
        resultados.append(info)

    return resultados

if __name__ == "__main__":
    print("=== OCR PREMIUM de comprobantes (monto + número de operación) ===")
    print(f"Carpeta configurada: {CARPETA_COMPROBANTES}")
    print(f"EasyOCR disponible : {HAS_EASYOCR}")
    print(f"TrOCR disponible   : {HAS_TROCR}")

    resultados = procesar_carpeta_premium(CARPETA_COMPROBANTES)

    print("\n=== Resumen final ===")
    for r in resultados:
        print("------------------------------")
        print(f"Archivo          : {r['ruta']}")
        print(f"Monto            : {r['monto']}")
        print(f"Número operación : {r['numero_operacion']}")
        print(f" Motores usados  : {[s for s, _ in r['textos_ocr']]}")

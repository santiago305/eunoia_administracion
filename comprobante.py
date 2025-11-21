import os
import re
import cv2
import pytesseract
from PIL import Image

# ========== CONFIGURACIÓN GENERAL ==========

# SOLO en Windows: si tesseract no está en el PATH, descomenta esta línea
# y coloca la ruta donde se instaló tesseract.exe
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Carpeta por defecto donde se guardan las imágenes de comprobantes
CARPETA_COMPROBANTES = r"C:\proyectos-finales\eunoia_administracion\outputs\images"

# Config por defecto de Tesseract
OCR_CONFIG = "--oem 3 --psm 6"  # motor LSTM + bloque de texto "normal"


# ========== 1. OCR + PREPROCESAMIENTO ==========

def _mejorar_imagen(img):
    """Aplica una serie de mejoras a la imagen para ayudar al OCR."""
    # Escala de grises
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Aumentar tamaño (Tesseract lee mejor texto grande)
    h, w = gray.shape
    scale = 2.0
    gray = cv2.resize(gray, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)

    # Suavizar un poco para reducir ruido
    gray = cv2.medianBlur(gray, 3)

    # Umbralización adaptativa (mejor que un umbral fijo)
    thresh = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        10,
    )

    return thresh


def _ocr_pil(pil_img):
    """
    Ejecuta Tesseract con config mejorada.
    Intenta primero con español ('spa'); si no está instalado, cae a config sin idioma.
    """
    try:
        texto = pytesseract.image_to_string(pil_img, lang="spa", config=OCR_CONFIG)
    except pytesseract.TesseractError:
        texto = pytesseract.image_to_string(pil_img, config=OCR_CONFIG)
    return texto


def ocr_preprocesar_ruta(ruta_imagen: str) -> str:
    """
    Lee una imagen de comprobante, aplica preprocesamiento agresivo
    y devuelve el texto OCR resultante.
    """
    img = cv2.imread(ruta_imagen)

    if img is None:
        print(f"[ADVERTENCIA] No se pudo leer la imagen: {ruta_imagen}")
        return ""

    procesada = _mejorar_imagen(img)

    # Convertir a PIL para pytesseract
    pil_img = Image.fromarray(procesada)

    # Extraer texto
    texto = _ocr_pil(pil_img)
    return texto


# ========== 2. HELPERS GENERALES ==========

def normalizar(texto: str) -> str:
    """Pasa a minúsculas y quita tildes para comparar más fácil."""
    texto = texto.lower()
    reemplazos = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ñ": "n",
    }
    for a, b in reemplazos.items():
        texto = texto.replace(a, b)
    return texto


def _extraer_numeros_monto(linea: str):
    """
    Devuelve una lista de posibles montos (como string) encontrados en la línea.
    Soporta formatos como:
    - 123.45
    - 1,234.56
    - 1234,56
    """
    # Reemplazar comas por puntos si parecen ser decimales
    # Primero capturamos patrones con coma o punto
    patron = r"[0-9][0-9\.,]*[0-9]"
    matches = re.findall(patron, linea)
    candidatos = []
    for m in matches:
        # Limpieza básica
        limpio = m.replace(" ", "")
        # Normalizar separador decimal a punto:
        # si tiene tanto "." como "," -> asumimos que "," es decimal
        if "," in limpio and "." in limpio:
            limpio = limpio.replace(".", "").replace(",", ".")
        elif "," in limpio and "." not in limpio:
            limpio = limpio.replace(",", ".")
        # descartar cosas muy raras
        if len(limpio) >= 3:
            candidatos.append(limpio)
    return candidatos


# ========== 3. EXTRAER MONTO ==========

def extraer_monto(texto: str):
    """
    Busca el monto principal:
    1) Prioriza líneas con 'S/' (moneda Soles).
    2) Si no, busca líneas con 'monto', 'importe', 'total' (y evita 'saldo', 'comision', etc.).
    3) Dentro de esas líneas busca el número más "grande" con decimales.
    """
    lineas = [l.strip() for l in texto.splitlines() if l.strip()]
    candidatas = []

    # 1) Líneas con S/
    for linea in lineas:
        norm = normalizar(linea)
        if "s/" in norm or "s/." in norm:
            candidatas.append(linea)

    # 2) Si no hay candidatas, buscar por palabras clave
    if not candidatas:
        for linea in lineas:
            norm = normalizar(linea)
            if any(p in norm for p in ["monto", "importe", "total"]):
                # Excluir posibles distracciones
                if any(bad in norm for bad in ["saldo", "comision", "igv"]):
                    continue
                candidatas.append(linea)

    if not candidatas:
        return None

    mejor_monto = None
    mejor_valor = -1.0

    for linea in candidatas:
        nums = _extraer_numeros_monto(linea)
        for n in nums:
            try:
                valor = float(n)
            except ValueError:
                continue
            # nos quedamos con el mayor valor encontrado,
            # asumiendo que el total suele ser el mayor
            if valor > mejor_valor:
                mejor_valor = valor
                mejor_monto = n

    return mejor_monto


# ========== 4. EXTRAER NÚMERO DE OPERACIÓN ==========

def extraer_numero_operacion(texto: str):
    """
    Busca el número de operación:
    - Lineas con 'nro. de operación', 'numero de operacion',
      'codigo de operacion', etc.
    - Dentro de esas líneas toma el número más largo (>= 6 dígitos).
    """
    lineas = [l.strip() for l in texto.splitlines() if l.strip()]
    claves = [
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
        "código de operación",
    ]

    mejor_candidato = None
    mejor_longitud = 0

    for linea in lineas:
        norm = normalizar(linea)
        if any(cl in norm for cl in claves):
            # buscar secuencias de 6+ dígitos
            numeros = re.findall(r"\d{6,}", linea)
            for num in numeros:
                if len(num) > mejor_longitud:
                    mejor_longitud = len(num)
                    mejor_candidato = num

    # fallback: si no encontró en líneas con clave, buscar en últimas líneas del texto
    if not mejor_candidato:
        ultimas = lineas[-5:]  # miramos las 5 últimas
        for linea in ultimas:
            numeros = re.findall(r"\d{6,}", linea)
            for num in numeros:
                if len(num) > mejor_longitud:
                    mejor_longitud = len(num)
                    mejor_candidato = num

    return mejor_candidato


# ========== 5. PROCESAR UN SOLO COMPROBANTE ==========

def procesar_comprobante(ruta_imagen: str):
    """
    Procesa una sola imagen de comprobante:
    - Aplica OCR
    - Extrae monto
    - Extrae número de operación
    """
    print(f"Procesando: {ruta_imagen}")
    texto = ocr_preprocesar_ruta(ruta_imagen)
    if not texto:
        print("   [ERROR] No se obtuvo texto del OCR.")
        return {
            "ruta": ruta_imagen,
            "texto": "",
            "monto": None,
            "numero_operacion": None,
        }

    monto = extraer_monto(texto)
    numero_operacion = extraer_numero_operacion(texto)

    data = {
        "ruta": ruta_imagen,
        "texto": texto,
        "monto": monto,
        "numero_operacion": numero_operacion,
    }

    print(f"   Monto            : {monto}")
    print(f"   Número operación : {numero_operacion}")
    return data


# ========== 6. PROCESAR UNA CARPETA COMPLETA ==========

def procesar_carpeta(ruta_carpeta: str):
    """
    Procesa todas las imágenes .png/.jpg/.jpeg de una carpeta.
    Devuelve una lista de diccionarios con:
    - ruta
    - texto
    - monto
    - numero_operacion
    """
    resultados = []

    if not os.path.isdir(ruta_carpeta):
        print(f"[ERROR] La carpeta {ruta_carpeta} no existe.")
        return resultados

    extensiones = (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff")

    for nombre in sorted(os.listdir(ruta_carpeta)):
        if not nombre.lower().endswith(extensiones):
            continue

        ruta = os.path.join(ruta_carpeta, nombre)
        info = procesar_comprobante(ruta)
        resultados.append(info)

    return resultados


# ========== 7. PUNTO DE ENTRADA ==========

if __name__ == "__main__":
    print("=== OCR de comprobantes (monto + número de operación) ===")
    print(f"Carpeta configurada: {CARPETA_COMPROBANTES}")

    resultados = procesar_carpeta(CARPETA_COMPROBANTES)

    print("\n=== Resumen final ===")
    for r in resultados:
        print("------------------------------")
        print(f"Archivo          : {r['ruta']}")
        print(f"Monto            : {r['monto']}")
        print(f"Número operación : {r['numero_operacion']}")

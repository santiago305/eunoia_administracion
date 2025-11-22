"""
OCR premium para comprobantes bancarios borrosos.
pip install opencv-python pillow pytesseract easyocr numpy torch torchvision transformers

Incluye:
- Preprocesamiento fuerte (deskew, upscale, filtrado).
- Múltiples motores OCR: Tesseract, EasyOCR y opcionalmente TrOCR (Transformers).
- Fusión de resultados para extraer Monto y Número de Operación lo mejor posible.

Requisitos recomendados (requirements.txt):

opencv-python
pillow
pytesseract
easyocr
numpy
torch
torchvision
transformers

NOTA:
- EasyOCR y TrOCR se usan solo si están instalados. Si no, el script sigue trabajando con Tesseract.
- Para TrOCR se descargará el modelo "microsoft/trocr-base-printed" la primera vez (requiere internet).
"""

import os
import re
import cv2
import pytesseract
import numpy as np
from PIL import Image

# ======== CONFIGURACIÓN GENERAL ========

# SOLO en Windows: si tesseract no está en el PATH, descomenta esta línea
# y coloca la ruta donde se instaló tesseract.exe
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Carpeta por defecto donde se guardan las imágenes de comprobantes
CARPETA_COMPROBANTES = r"C:\proyectos-finales\eunoia_administracion\outputs\images"

# Configs avanzadas de Tesseract
OCR_CONFIG_TEXTO = "--oem 3 --psm 6 -c preserve_interword_spaces=1"
OCR_CONFIG_NUMEROS = "--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789.,:/-"

# Flags para motores opcionales
HAS_EASYOCR = False
HAS_TROCR = False
easyocr_reader = None
trocr_processor = None
trocr_model = None

# ======== INTENTAR CARGAR EASYOCR ========

try:
    import easyocr  # type: ignore
    HAS_EASYOCR = True
    # Inicializamos una sola vez (es pesado)
    easyocr_reader = easyocr.Reader(['es', 'en'])
except Exception:
    HAS_EASYOCR = False

# ======== INTENTAR CARGAR TrOCR (Transformers) ========

try:
    from transformers import TrOCRProcessor, VisionEncoderDecoderModel  # type: ignore
    HAS_TROCR = True
except Exception:
    HAS_TROCR = False
    TrOCRProcessor = None
    VisionEncoderDecoderModel = None


# ======== PREPROCESAMIENTO AVANZADO ========

def deskew_image(gray: np.ndarray) -> np.ndarray:
    """
    Intenta corregir la inclinación del texto en una imagen en escala de grises.
    Si algo sale mal, devuelve la original.
    """
    try:
        # Binarizar para encontrar pixeles de texto
        _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        # Invertir: texto blanco sobre fondo negro
        bw_inv = cv2.bitwise_not(bw)
        coords = np.column_stack(np.where(bw_inv > 0))
        if coords.size == 0:
            return gray
        angle = cv2.minAreaRect(coords)[-1]
        # Ajustar ángulo
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        (h, w) = gray.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        return rotated
    except Exception:
        return gray


def mejorar_imagen(img: np.ndarray) -> np.ndarray:
    """
    Preprocesamiento fuerte:
    - Escala de grises
    - Deskew
    - Upscale x2.5
    - Filtro bilateral (reduce ruido sin perder bordes)
    - Sharpen ligero
    - Umbralización adaptativa
    """
    # Escala de grises
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Corregir inclinación
    gray = deskew_image(gray)

    # Upscale
    h, w = gray.shape
    scale = 2.5
    gray = cv2.resize(gray, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_LANCZOS4)

    # Filtro bilateral (suaviza ruido, preserva bordes)
    gray = cv2.bilateralFilter(gray, d=9, sigmaColor=75, sigmaSpace=75)

    # Sharpen (enfocar ligeramente)
    kernel_sharp = np.array([[0, -1, 0],
                             [-1, 5, -1],
                             [0, -1, 0]])
    gray = cv2.filter2D(gray, -1, kernel_sharp)

    # Umbralización adaptativa
    thresh = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        10,
    )

    return thresh


# ======== OCR CON DIFERENTES MOTORES ========

def ocr_tesseract_texto(pil_img: Image.Image) -> str:
    """OCR general usando Tesseract (texto completo)."""
    try:
        texto = pytesseract.image_to_string(pil_img, lang="spa", config=OCR_CONFIG_TEXTO)
    except pytesseract.TesseractError:
        texto = pytesseract.image_to_string(pil_img, config=OCR_CONFIG_TEXTO)
    return texto


def ocr_tesseract_numeros(pil_img: Image.Image) -> str:
    """OCR especializado en números (monto y códigos)."""
    try:
        texto = pytesseract.image_to_string(pil_img, lang="spa", config=OCR_CONFIG_NUMEROS)
    except pytesseract.TesseractError:
        texto = pytesseract.image_to_string(pil_img, config=OCR_CONFIG_NUMEROS)
    return texto


def ocr_easyocr_img(img_bgr: np.ndarray) -> str:
    """OCR con EasyOCR (si está disponible)."""
    if not HAS_EASYOCR or easyocr_reader is None:
        return ""
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    try:
        resultados = easyocr_reader.readtext(img_rgb, detail=0, paragraph=True)
        return "\n".join(resultados)
    except Exception:
        return ""


def cargar_trocr():
    """Carga perezosa de TrOCR para no demorar si no se usa."""
    global trocr_processor, trocr_model
    from transformers import TrOCRProcessor, VisionEncoderDecoderModel  # type: ignore
    trocr_processor = TrOCRProcessor.from_pretrained(
        "microsoft/trocr-base-printed", use_fast=True
    )
    trocr_model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-printed")


def ocr_trocr_pil(pil_img: Image.Image) -> str:
    """
    OCR con TrOCR (modelo Transformer de Microsoft).
    Está pensado para líneas / bloques de texto,
    pero igual puede ayudar como fuente extra.
    """
    if not HAS_TROCR:
        return ""
    try:
        import torch  # type: ignore
        global trocr_processor, trocr_model
        if trocr_processor is None or trocr_model is None:
            cargar_trocr()

        pixel_values = trocr_processor(images=pil_img, return_tensors="pt").pixel_values
        with torch.no_grad():
            generated_ids = trocr_model.generate(pixel_values, max_length=256)
        texto = trocr_processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        return texto
    except Exception:
        return ""


def ocr_multi(ruta_imagen: str):
    """
    Aplica múltiples OCR sobre la misma imagen:
    - Tesseract (texto general)
    - Tesseract (numérico)
    - EasyOCR (si está)
    - TrOCR (si está)
    Devuelve una lista de textos.
    """
    img = cv2.imread(ruta_imagen)
    if img is None:
        print(f"[ADVERTENCIA] No se pudo leer la imagen: {ruta_imagen}")
        return []

    procesada = mejorar_imagen(img)
    pil_procesada = Image.fromarray(procesada)

    textos = []

    # Tesseract texto general
    t_texto = ocr_tesseract_texto(pil_procesada)
    if t_texto.strip():
        textos.append(("tesseract_texto", t_texto))

    # Tesseract numérico
    t_num = ocr_tesseract_numeros(pil_procesada)
    if t_num.strip():
        textos.append(("tesseract_numeros", t_num))

    # EasyOCR
    if HAS_EASYOCR:
        e_texto = ocr_easyocr_img(img)
        if e_texto.strip():
            textos.append(("easyocr", e_texto))

    # TrOCR sobre una versión reducida
    if HAS_TROCR:
        pil_small = pil_procesada.copy()
        max_side = 1024
        w, h = pil_small.size
        scale = min(max_side / max(w, h), 1.0)
        if scale < 1.0:
            pil_small = pil_small.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        tr_texto = ocr_trocr_pil(pil_small)
        if tr_texto.strip():
            textos.append(("trocr", tr_texto))

    return textos


# ======== HELPERS DE NORMALIZACIÓN Y PARSEO ========

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


def extraer_numeros_monto(linea: str):
    """
    Devuelve una lista de posibles montos (como string) encontrados en la línea.
    Soporta formatos como:
    - 123.45
    - 1,234.56
    - 1234,56
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
        if len(limpio) >= 3:
            candidatos.append(limpio)
    return candidatos


def extraer_monto_desde_texto(texto: str):
    """
    Busca el monto principal en un solo texto.
    """
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


def extraer_numero_operacion_desde_texto(texto: str):
    """
    Busca el número de operación en un solo texto.
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


# ======== FUSIÓN DE RESULTADOS ========

def elegir_mejor_monto(textos_ocr):
    """
    Recibe una lista de (motor, texto) y decide el mejor monto:
    - Cuenta cuántas veces se repite cada monto.
    - Si empatan, se queda con el de mayor valor numérico.
    """
    conteo = {}
    valores = {}

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

    mejor = sorted(conteo.keys(), key=lambda m: (conteo[m], valores.get(m, -1.0)), reverse=True)[0]
    return mejor


def elegir_mejor_numero_operacion(textos_ocr):
    """
    Igual que para el monto, pero con número de operación.
    """
    conteo = {}
    longitudes = {}

    for source, texto in textos_ocr:
        num = extraer_numero_operacion_desde_texto(texto)
        if not num:
            continue
        clave = num
        conteo[clave] = conteo.get(clave, 0) + 1
        longitudes[clave] = len(num)

    if not conteo:
        return None

    mejor = sorted(conteo.keys(), key=lambda n: (conteo[n], longitudes.get(n, 0)), reverse=True)[0]
    return mejor


# ======== PROCESAR UN SOLO COMPROBANTE ========

def procesar_comprobante_premium(ruta_imagen: str):
    """
    Procesa una sola imagen de comprobante con OCR premium.
    """
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

    data = {
        "ruta": ruta_imagen,
        "textos_ocr": textos_ocr,
        "monto": monto,
        "numero_operacion": numero_operacion,
    }

    print(f"   Motores usados    : {[s for s, _ in textos_ocr]}")
    print(f"   Monto elegido     : {monto}")
    print(f"   Número operación  : {numero_operacion}")
    return data


# ======== PROCESAR CARPETA COMPLETA ========

def procesar_carpeta_premium(ruta_carpeta: str):
    """
    Procesa todas las imágenes de una carpeta con el pipeline premium.
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
        info = procesar_comprobante_premium(ruta)
        resultados.append(info)

    return resultados


# ======== MAIN ========

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

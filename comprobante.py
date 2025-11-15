import os
import re
import cv2
import pytesseract
from PIL import Image

# ========== CONFIGURACIÓN ==========
# SOLO en Windows: si tesseract no está en el PATH, descomenta esta línea
# y coloca la ruta donde se instaló tesseract.exe
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

CARPETA_COMPROBANTES = r"D:\whatsapp\outputs\images"  # carpeta donde pondrás las imágenes


# ========== 1. OCR + PREPROCESAMIENTO ==========

def ocr_preprocesar_ruta(ruta_imagen: str) -> str:
    """Lee una imagen de comprobante, la mejora un poco y devuelve el texto OCR."""
    img = cv2.imread(ruta_imagen)

    if img is None:
        print(f"[ADVERTENCIA] No se pudo leer la imagen: {ruta_imagen}")
        return ""

    # Escala de grises
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Binarizar (puedes jugar con el valor 150)
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)

    # Convertir a PIL para pytesseract
    pil_img = Image.fromarray(thresh)

    # Extraer texto (puedes probar lang='spa' si tienes el idioma instalado)
    texto = pytesseract.image_to_string(pil_img)  # , lang='spa'
    return texto


# ========== 2. HELPERS ==========

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


# ========== 3. FUNCIONES PARA EXTRAER CAMPOS ==========

def extraer_monto(texto: str):
    """
    Busca el monto principal:
    1) Prioriza líneas con 'S/' (moneda Soles).
    2) Si no, busca líneas con 'monto', 'importe', 'total'.
    3) Dentro de esas líneas busca el número con decimales.
    """
    lineas = [l.strip() for l in texto.splitlines() if l.strip()]
    candidatas = []

    # 1) Líneas con S/
    for linea in lineas:
        if "s/" in normalizar(linea):
            candidatas.append(linea)

    # 2) Si no hay candidatas, buscar por palabras clave
    if not candidatas:
        for linea in lineas:
            norm = normalizar(linea)
            if any(p in norm for p in ["monto", "importe", "total"]):
                candidatas.append(linea)

    # 3) Buscar número en las candidatas
    for linea in candidatas:
        # Ej: "S/ 112.40", "S/20.00", "S/ 10"
        m = re.search(r"S/?\s*([\d.,]+)", linea)
        if m:
            monto = m.group(1)
            # normalizar coma a punto
            monto = monto.replace(",", ".")
            return monto

        # Plan B: cualquier número con decimales
        m2 = re.search(r"(\d+[.,]\d{2})", linea)
        if m2:
            monto = m2.group(1).replace(",", ".")
            return monto

    # Último intento: último número con decimales en todo el texto
    montos = re.findall(r"(\d+[.,]\d{2})", texto)
    if montos:
        return montos[-1].replace(",", ".")

    return None


def extraer_numero_operacion(texto: str):
    """
    Busca el número de operación:
    - Lineas con 'nro. de operación', 'numero de operacion',
      'codigo de operacion', 'nro operacion', etc.
    - Luego toma el número más largo de esa línea (>= 5 dígitos para evitar códigos de 3 dígitos).
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
        "nro operacion",
        "n operacion",
        "no. operacion",
        "nro. de operación",
        "código de operación",
    ]

    candidatas = []

    for linea in lineas:
        norm = normalizar(linea)
        if any(clave in norm for clave in claves):
            candidatas.append(linea)

    # Revisar desde el final (suele estar al final del comprobante)
    for linea in reversed(candidatas):
        # Buscar números largos (>=5 dígitos, para evitar códigos tipo "017")
        numeros = re.findall(r"\d+", linea)
        numeros_largos = [n for n in numeros if len(n) >= 5]
        if numeros_largos:
            return numeros_largos[-1]  # el último de la línea

    # Si no encontramos por etiqueta, como último recurso:
    # tomamos el último número MUY largo del texto (>=7 dígitos)
    numeros = re.findall(r"\d+", texto)
    numeros_muy_largos = [n for n in numeros if len(n) >= 7]
    if numeros_muy_largos:
        return numeros_muy_largos[-1]

    return None


# ========== 4. PROCESAR UN COMPROBANTE ==========

def procesar_comprobante(ruta_imagen: str) -> dict:
    """Devuelve un diccionario con los datos básicos de un comprobante."""
    print(f"\n📄 Procesando: {ruta_imagen}")
    texto = ocr_preprocesar_ruta(ruta_imagen)

    if not texto.strip():
        print("   [ERROR] No se obtuvo texto del OCR.")
        return {
            "ruta": ruta_imagen,
            "texto_completo": "",
            "monto": None,
            "numero_operacion": None,
        }

    monto = extraer_monto(texto)
    numero_operacion = extraer_numero_operacion(texto)

    data = {
        "ruta": ruta_imagen,
        "texto_completo": texto,
        "monto": monto,
        "numero_operacion": numero_operacion,
    }

    print(f"   Monto            : {monto}")
    print(f"   Número operación : {numero_operacion}")

    return data


# ========== 5. PROCESAR UNA CARPETA COMPLETA ==========

def procesar_carpeta(ruta_carpeta: str):
    """Procesa todas las imágenes .png/.jpg/.jpeg de una carpeta."""
    resultados = []
    if not os.path.isdir(ruta_carpeta):
        print(f"[ERROR] La carpeta {ruta_carpeta} no existe.")
        return resultados

    for nombre in os.listdir(ruta_carpeta):
        if nombre.lower().endswith((".png", ".jpg", ".jpeg", ".jpg")):
            ruta = os.path.join(ruta_carpeta, nombre)
            info = procesar_comprobante(ruta)
            resultados.append(info)

    return resultados


# ========== 6. PUNTO DE ENTRADA ==========

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

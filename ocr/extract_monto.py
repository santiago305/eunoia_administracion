from typing import List, Optional, Tuple, Dict
import re
import cv2
from ocr.utils.ocr_image import ocr_image
from ocr.utils.parse_mount_text import parse_amount_text
from text_utils import normalizar

MESES = [
    "ene", "feb", "mar", "abr", "may", "jun",
    "jul", "ago", "set", "oct", "nov", "dic",
]


def _normalizar_numero(num_str: str) -> str:
    """Normaliza una cadena numérica a formato estándar con punto decimal."""
    limpio = num_str.replace(" ", "")
    if "," in limpio and "." in limpio:
        limpio = limpio.replace(".", "").replace(",", ".")
    elif "," in limpio and "." not in limpio:
        limpio = limpio.replace(",", ".")
    return limpio


def extraer_numeros_monto(linea: str) -> List[str]:
    """Devuelve una lista de posibles montos encontrados en la línea."""
    patron = r"[0-9][0-9\.,]*[0-9]"
    matches = re.findall(patron, linea)
    candidatos = []
    for m in matches:
        limpio = _normalizar_numero(m)
        if len(limpio) >= 1:
            candidatos.append(limpio)
    return candidatos


def _es_posible_anio(valor: float) -> bool:
    return 1900 <= valor <= 2100


def _es_monto_valido(valor: float) -> bool:
    if valor <= 0:
        return False
    if _es_posible_anio(valor):
        return False
    if valor > 10_000_000:
        return False
    return True


def extraer_monto_roi(img_path: str) -> Optional[str]:
    """Función para realizar la extracción del monto usando ROIs."""
    img = cv2.imread(img_path)
    if img is None:
        return None

    h, w = img.shape[:2]
    rois = [
        (0.17, 0.37, 0.02, 0.60),  # ROI 1
        (0.22, 0.42, 0.08, 0.55),  # ROI 2
        (0.14, 0.34, 0.00, 0.55),  # ROI 3
        (0.24, 0.44, 0.00, 0.70),  # ROI 4
    ]

    for (ry1, ry2, rx1, rx2) in rois:
        y1 = int(ry1 * h)
        y2 = int(ry2 * h)
        x1 = int(rx1 * w)
        x2 = int(rx2 * w)

        roi = img[y1:y2, x1:x2]
        if roi.size == 0:
            continue

        roi = cv2.resize(roi, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        cfg = r"--oem 3 --psm 7 -l spa+eng"
        roi_text = ocr_image(gray, cfg)
        
        amount = parse_amount_text(roi_text, prefer_multidigit=True)
        if amount:
            return amount

    return None


def extraer_monto_desde_texto(texto: str) -> Optional[str]:
    """Encuentra el monto principal dentro de un bloque OCR."""
    lineas = [l.strip() for l in texto.splitlines() if l.strip()]
    if not lineas:
        return None

    texto_unido = " ".join(lineas)
    texto_unido_norm = normalizar(texto_unido)
    patron_s_global = r"[sS]\s*/\.?\s*([0-9][0-9\.,]*[0-9])"
    m_global = re.search(patron_s_global, texto_unido_norm)
    if m_global:
        bruto = m_global.group(1)
        monto_norm = _normalizar_numero(bruto)
        try:
            valor = float(monto_norm)
            if _es_monto_valido(valor):
                return monto_norm
        except ValueError:
            pass

    candidatas_idx: set[int] = set()
    palabras_monto = ["monto", "importe", "total"]

    for i, linea in enumerate(lineas):
        norm = normalizar(linea)
        tiene_slash = "s/" in norm or "s /" in norm or "s/." in norm
        tiene_palabra = any(p in norm for p in palabras_monto)

        if tiene_slash or tiene_palabra:
            candidatas_idx.add(i)
            if tiene_slash and i + 1 < len(lineas):
                candidatas_idx.add(i + 1)

    candidatas = [lineas[i] for i in sorted(candidatas_idx)]

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
            if contiene_mes and _es_posible_anio(valor):
                continue
            if not _es_monto_valido(valor):
                continue
            if valor > mejor_valor:
                mejor_valor = valor
                mejor_monto = n

    return mejor_monto


def elegir_mejor_monto(textos_ocr: List[Tuple[str, str]]) -> Optional[str]:
    """Dado el OCR de varios motores, elige el monto más consistente y probable."""
    conteo: Dict[str, int] = {}
    valores: Dict[str, float] = {}

    for source, texto in textos_ocr:
        monto = extraer_monto_desde_texto(texto)
        if not monto:
            continue

        conteo[monto] = conteo.get(monto, 0) + 1
        try:
            valores[monto] = float(monto)
        except ValueError:
            valores[monto] = -1.0

    if not conteo:
        return None

    mejor = sorted(
        conteo.keys(),
        key=lambda m: (conteo[m], valores.get(m, -1.0)),
        reverse=True,
    )[0]
    return mejor


def extraer_monto_final(texto: str, img_path: str) -> Optional[str]:
    """Función principal para obtener el monto de un texto OCR con múltiples ROIs."""
    monto_texto = extraer_monto_desde_texto(texto)
    monto_roi = extraer_monto_roi(img_path)
    
    if monto_roi:
        return monto_roi
    return monto_texto

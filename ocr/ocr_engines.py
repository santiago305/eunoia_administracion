"""
ocr_engines.py
---------------
Motores de OCR: Tesseract, EasyOCR y TrOCR (incluye modelo entrenado para montos).
"""

from typing import List, Tuple
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
import pytesseract

from ocr_settings import OCR_CONFIG_TEXTO, OCR_CONFIG_NUMEROS
from ocr_preprocess import mejorar_imagen

# Ruta del modelo TrOCR entrenado para montos
TROCR_MONTOS_MODEL = Path(
    r"C:\proyectos-finales\eunoia_administracion\entrenamiento\modelos\trocr_montos_v1"
)

HAS_EASYOCR = False
HAS_TROCR = False
easyocr_reader = None
trocr_processor = None
trocr_model = None

# --- Intentar cargar EasyOCR ---
try:
    import easyocr  # type: ignore

    HAS_EASYOCR = True
    easyocr_reader = easyocr.Reader(["es", "en"])
except Exception:
    HAS_EASYOCR = False

# --- Intentar cargar TrOCR (Transformers) ---
try:
    from transformers import TrOCRProcessor, VisionEncoderDecoderModel  # type: ignore

    HAS_TROCR = True
except Exception:
    HAS_TROCR = False
    TrOCRProcessor = None  # type: ignore
    VisionEncoderDecoderModel = None  # type: ignore


def ocr_tesseract_texto(pil_img: Image.Image) -> str:
    """
    Ejecuta OCR usando Tesseract para texto general.
    """
    try:
        texto = pytesseract.image_to_string(
            pil_img, lang="spa", config=OCR_CONFIG_TEXTO
        )
    except pytesseract.TesseractError:
        texto = pytesseract.image_to_string(pil_img, config=OCR_CONFIG_TEXTO)
    return texto


def ocr_tesseract_numeros(pil_img: Image.Image) -> str:
    """
    Ejecuta OCR usando Tesseract, pero especializado en números (montos, códigos, etc.).
    """
    try:
        texto = pytesseract.image_to_string(
            pil_img, lang="spa", config=OCR_CONFIG_NUMEROS
        )
    except pytesseract.TesseractError:
        texto = pytesseract.image_to_string(pil_img, config=OCR_CONFIG_NUMEROS)
    return texto


def ocr_easyocr_img(img_bgr: "np.ndarray") -> str:
    """
    Ejecuta OCR con EasyOCR sobre una imagen en BGR (OpenCV).
    """
    if not HAS_EASYOCR or easyocr_reader is None:
        return ""
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    try:
        resultados = easyocr_reader.readtext(
            img_rgb,
            detail=0,  # solo texto
            paragraph=True,  # agrupar por párrafos
        )
        return "\n".join(resultados)
    except Exception:
        return ""


def _cargar_trocr():
    """
    Carga perezosamente el modelo TrOCR.

    Primero intenta cargar el modelo ENTRENADO que guardaste en:
    entrenamiento/modelos/trocr_montos_v1

    Si algo falla, hace fallback al modelo base "microsoft/trocr-base-printed".
    """
    global trocr_processor, trocr_model, TrOCRProcessor, VisionEncoderDecoderModel, HAS_TROCR

    if not HAS_TROCR or TrOCRProcessor is None or VisionEncoderDecoderModel is None:
        return

    if trocr_processor is not None and trocr_model is not None:
        return

    try:
        from transformers import TrOCRProcessor, VisionEncoderDecoderModel  # type: ignore
        import torch  # type: ignore

        # Intentar cargar el modelo entrenado
        if TROCR_MONTOS_MODEL.exists():
            trocr_processor = TrOCRProcessor.from_pretrained(
                TROCR_MONTOS_MODEL, use_fast=True
            )
            device = "cuda" if torch.cuda.is_available() else "cpu"
            trocr_model = VisionEncoderDecoderModel.from_pretrained(
                TROCR_MONTOS_MODEL
            ).to(device)
            return
        else:
            print(
                f"[ADVERTENCIA] Carpeta del modelo entrenado no encontrada: {TROCR_MONTOS_MODEL}. "
                "Usando modelo base microsoft/trocr-base-printed."
            )
            trocr_processor = TrOCRProcessor.from_pretrained(
                "microsoft/trocr-base-printed", use_fast=True
            )
            device = "cuda" if torch.cuda.is_available() else "cpu"
            trocr_model = VisionEncoderDecoderModel.from_pretrained(
                "microsoft/trocr-base-printed"
            ).to(device)
    except Exception as e:
        print(f"[ERROR] No se pudo cargar TrOCR (entrenado ni base): {e}")
        HAS_TROCR = False
        trocr_processor = None
        trocr_model = None


def ocr_trocr_pil(pil_img: Image.Image) -> str:
    """
    Ejecuta OCR usando TrOCR (modelo Transformer).

    Usa el modelo entrenado si está disponible. Si no, usa el modelo base.
    """
    if not HAS_TROCR:
        return ""
    try:
        import torch  # type: ignore

        global trocr_processor, trocr_model
        _cargar_trocr()
        if trocr_processor is None or trocr_model is None:
            return ""

        pixel_values = trocr_processor(images=pil_img, return_tensors="pt").pixel_values
        pixel_values = pixel_values.to(trocr_model.device)  # asegurar mismo dispositivo

        with torch.no_grad():
            generated_ids = trocr_model.generate(pixel_values, max_length=32)

        texto = trocr_processor.batch_decode(
            generated_ids, skip_special_tokens=True
        )[0]
        return texto
    except Exception as e:
        print(f"[ERROR] TrOCR falló en ocr_trocr_pil: {e}")
        return ""


def ocr_multi(ruta_imagen: str) -> "List[Tuple[str, str]]":
    """
    Ejecuta TODOS los motores OCR disponibles sobre una misma imagen.

    Devuelve una lista de tuplas:
        [
            ("tesseract_texto", "texto ..."),
            ("tesseract_numeros", "123.45 ..."),
            ("easyocr", "texto ..."),
            ("trocr", "texto ..."),
        ]
    """
    img = cv2.imread(ruta_imagen)
    if img is None:
        print(f"[ADVERTENCIA] No se pudo leer la imagen: {ruta_imagen}")
        return []

    procesada = mejorar_imagen(img)
    pil_procesada = Image.fromarray(procesada)

    textos: List[Tuple[str, str]] = []

    # --- Tesseract texto general ---
    t_texto = ocr_tesseract_texto(pil_procesada)
    if t_texto.strip():
        textos.append(("tesseract_texto", t_texto))

    # --- Tesseract numérico ---
    t_num = ocr_tesseract_numeros(pil_procesada)
    if t_num.strip():
        textos.append(("tesseract_numeros", t_num))

    # --- EasyOCR sobre la imagen original ---
    if HAS_EASYOCR:
        e_texto = ocr_easyocr_img(img)
        if e_texto.strip():
            textos.append(("easyocr", e_texto))

    # --- TrOCR (modelo entrenado/base) ---
    if HAS_TROCR:
        pil_small = pil_procesada.copy()
        max_side = 1024
        w, h = pil_small.size
        scale = min(max_side / max(w, h), 1.0)
        if scale < 1.0:
            pil_small = pil_small.resize(
                (int(w * scale), int(h * scale)), Image.LANCZOS
            )
        tr_texto = ocr_trocr_pil(pil_small)
        if tr_texto.strip():
            textos.append(("trocr", tr_texto))

    return textos

"""
ocr_engines.py
---------------
Motores de OCR: Tesseract, EasyOCR y TrOCR.
"""

from typing import List, Tuple
import cv2
import numpy as np
from PIL import Image
import pytesseract

from ocr_settings import OCR_CONFIG_TEXTO, OCR_CONFIG_NUMEROS
from ocr_preprocess import mejorar_imagen

HAS_EASYOCR = False
HAS_TROCR = False
easyocr_reader = None
trocr_processor = None
trocr_model = None

try:
    import easyocr  # type: ignore
    HAS_EASYOCR = True
    easyocr_reader = easyocr.Reader(['es', 'en'])
except Exception:
    HAS_EASYOCR = False

try:
    from transformers import TrOCRProcessor, VisionEncoderDecoderModel  # type: ignore
    HAS_TROCR = True
except Exception:
    HAS_TROCR = False
    TrOCRProcessor = None
    VisionEncoderDecoderModel = None

def ocr_tesseract_texto(pil_img: Image.Image) -> str:
    try:
        texto = pytesseract.image_to_string(
            pil_img,
            lang="spa",
            config=OCR_CONFIG_TEXTO
        )
    except pytesseract.TesseractError:
        texto = pytesseract.image_to_string(
            pil_img,
            config=OCR_CONFIG_TEXTO
        )
    return texto

def ocr_tesseract_numeros(pil_img: Image.Image) -> str:
    try:
        texto = pytesseract.image_to_string(
            pil_img,
            lang="spa",
            config=OCR_CONFIG_NUMEROS
        )
    except pytesseract.TesseractError:
        texto = pytesseract.image_to_string(
            pil_img,
            config=OCR_CONFIG_NUMEROS
        )
    return texto

def ocr_easyocr_img(img_bgr: "np.ndarray") -> str:
    if not HAS_EASYOCR or easyocr_reader is None:
        return ""
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    try:
        resultados = easyocr_reader.readtext(
            img_rgb,
            detail=0,
            paragraph=True,
        )
        return "\n".join(resultados)
    except Exception:
        return ""

def _cargar_trocr():
    global trocr_processor, trocr_model, TrOCRProcessor, VisionEncoderDecoderModel
    if TrOCRProcessor is None or VisionEncoderDecoderModel is None:
        return
    if trocr_processor is None or trocr_model is None:
        trocr_processor = TrOCRProcessor.from_pretrained(
            "microsoft/trocr-base-printed", use_fast=True
        )
        trocr_model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-printed")

def ocr_trocr_pil(pil_img: Image.Image) -> str:
    if not HAS_TROCR:
        return ""
    try:
        import torch  # type: ignore
        global trocr_processor, trocr_model
        _cargar_trocr()
        if trocr_processor is None or trocr_model is None:
            return ""
        pixel_values = trocr_processor(images=pil_img, return_tensors="pt").pixel_values
        with torch.no_grad():
            generated_ids = trocr_model.generate(pixel_values, max_length=256)
        texto = trocr_processor.batch_decode(
            generated_ids,
            skip_special_tokens=True
        )[0]
        return texto
    except Exception:
        return ""

def ocr_multi(ruta_imagen: str) -> "List[Tuple[str, str]]":
    img = cv2.imread(ruta_imagen)
    if img is None:
        print(f"[ADVERTENCIA] No se pudo leer la imagen: {ruta_imagen}")
        return []

    procesada = mejorar_imagen(img)
    pil_procesada = Image.fromarray(procesada)

    textos = []

    t_texto = ocr_tesseract_texto(pil_procesada)
    if t_texto.strip():
        textos.append(("tesseract_texto", t_texto))

    t_num = ocr_tesseract_numeros(pil_procesada)
    if t_num.strip():
        textos.append(("tesseract_numeros", t_num))

    if HAS_EASYOCR:
        e_texto = ocr_easyocr_img(img)
        if e_texto.strip():
            textos.append(("easyocr", e_texto))

    if HAS_TROCR:
        pil_small = pil_procesada.copy()
        max_side = 1024
        w, h = pil_small.size
        scale = min(max_side / max(w, h), 1.0)
        if scale < 1.0:
            pil_small = pil_small.resize(
                (int(w * scale), int(h * scale)),
                Image.LANCZOS
            )
        tr_texto = ocr_trocr_pil(pil_small)
        if tr_texto.strip():
            textos.append(("trocr", tr_texto))

    return textos

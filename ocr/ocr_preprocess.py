"""
ocr_preprocess.py
------------------
Funciones de preprocesamiento de imágenes para mejorar la lectura del OCR.
"""

from typing import Tuple
import cv2
import numpy as np

def deskew_image(gray: "np.ndarray") -> "np.ndarray":
    """
    Intenta corregir la inclinación (rotación) del texto en una imagen en escala de grises.
    Si algo falla, retorna la imagen original.
    """
    try:
        _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        bw_inv = cv2.bitwise_not(bw)
        coords = np.column_stack(np.where(bw_inv > 0))
        if coords.size == 0:
            return gray
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        (h, w) = gray.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(
            gray, M, (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE
        )
        return rotated
    except Exception:
        return gray

def mejorar_imagen(img: "np.ndarray") -> "np.ndarray":
    """
    Aplica una cadena de mejoras sobre la imagen original en color (BGR)
    para que el texto se lea mejor con OCR.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = deskew_image(gray)
    h, w = gray.shape
    scale = 2.5
    gray = cv2.resize(
        gray,
        (int(w * scale), int(h * scale)),
        interpolation=cv2.INTER_LANCZOS4
    )
    gray = cv2.bilateralFilter(gray, d=9, sigmaColor=75, sigmaSpace=75)
    kernel_sharp = np.array([[0, -1, 0],
                             [-1, 5, -1],
                             [0, -1, 0]])
    gray = cv2.filter2D(gray, -1, kernel_sharp)
    thresh = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        10,
    )
    return thresh

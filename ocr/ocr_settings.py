"""
ocr_settings.py
----------------
Configuración centralizada para el OCR de comprobantes.

Aquí defines:
- La carpeta donde están las imágenes de los comprobantes.
- La ruta de Tesseract en Windows (si no está en el PATH).
- Configuraciones por defecto para Tesseract.
"""

import pytesseract
from pathlib import Path

# Carpeta por defecto donde se guardan las imágenes de comprobantes.
# Ajusta esta ruta según tu proyecto.
CARPETA_COMPROBANTES = Path(r"C:\proyectos-finales\eunoia_administracion\outputs\images")

# --- Configuración de Tesseract en Windows ---
# Si Tesseract ya está en el PATH, puedes dejar esto comentado.
# Si no, descomenta y coloca la ruta exacta a tesseract.exe.
#
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# --- Configs avanzadas de Tesseract ---
# OCR_CONFIG_TEXTO:
#   - --oem 3  -> Usa el mejor motor disponible (LSTM + legacy).
#   - --psm 6  -> Asume un bloque de texto normal (varias líneas).
#   - preserve_interword_spaces=1 -> Conserva mejor los espacios.
OCR_CONFIG_TEXTO = "--oem 3 --psm 6 -c preserve_interword_spaces=1"

# OCR_CONFIG_NUMEROS:
#   - --psm 7  -> Asume una sola línea de texto (ideal para montos/códigos).
#   - tessedit_char_whitelist -> Indica qué caracteres son válidos.
OCR_CONFIG_NUMEROS = "--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789.,:/-"

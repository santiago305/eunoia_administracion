# ocr.py
import cv2
import easyocr
import os

from .amount_extractor import find_amount_from_texts
from .op_extractor import find_operation_number_from_texts

# ─────────────────────────────────────────────
#   OCR GLOBAL (se crea una sola vez)
# ─────────────────────────────────────────────
reader = easyocr.Reader(['en', 'es'])  # Idiomas a reconocer


# ─────────────────────────────────────────────
#   FUNCIÓN PRINCIPAL REUTILIZABLE
#   Le pasas una foto y te devuelve:
#   (monto, numero_operacion)
# ─────────────────────────────────────────────
def extract_voucher_data(image_path: str, debug: bool = False) -> tuple[str | None, str | None]:
    """
    Analiza una imagen de voucher y devuelve:
      - monto (str o None)
      - número de operación (str o None)

    No imprime nada a menos que debug=True.
    """

    # 1) Correr EasyOCR SOLO UNA VEZ
    result = reader.readtext(image_path)
    texts = [detection[1] for detection in result]

    # Debug de textos OCR (para pruebas)
    if debug:
        print("\nTexto extraído con EasyOCR:")
        for t in texts:
            print(t)

    # 2) Sacar monto usando tu extractor actual
    amount = find_amount_from_texts(texts)

    # 3) Sacar número de operación usando las nuevas reglas
    op_number = find_operation_number_from_texts(texts)

    # 👇 Esta función SOLO devuelve, no imprime
    return amount, op_number


# ─────────────────────────────────────────────
#   Procesar carpeta de imágenes (solo para pruebas)
# ─────────────────────────────────────────────
def process_images_in_folder(folder_path: str, debug: bool = False):
    """
    Función de utilidad para pruebas manuales.
    Recorre una carpeta, llama a extract_voucher_data
    y AHÍ recién imprime los resultados.
    """
    for filename in os.listdir(folder_path):
        if filename.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
            image_path = os.path.join(folder_path, filename)
            print("\n───────────────────────────────")
            print(f"Procesando: {filename}")

            amount, op_number = extract_voucher_data(image_path, debug=debug)

            # 4) Imprimir resultados SOLO en modo prueba
            if amount is not None:
                print(f"👉 Monto detectado: S/ {amount}")
            else:
                print("⚠ No se detectó monto en esta imagen")

            if op_number is not None:
                print(f"🔢 Número de operación detectado: {op_number}")
            else:
                print("⚠ No se detectó número de operación en esta imagen")


# ─────────────────────────────────────────────
#   Main (solo cuando corres este archivo directo)
# ─────────────────────────────────────────────
if __name__ == "__main__":
    folder_path = r"C:\proyectos-finales\ocr\OCR\imagenes"
    # Activa debug=True solo cuando quieras ver el texto crudo del OCR
    process_images_in_folder(folder_path, debug=True)

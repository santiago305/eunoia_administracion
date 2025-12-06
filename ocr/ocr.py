# ocr.py
import cv2
import easyocr
import os

from amount_extractor import find_amount_from_texts
from op_extractor import find_operation_number_from_texts

# ─────────────────────────────────────────────
#   OCR GLOBAL (se crea una sola vez)
# ─────────────────────────────────────────────
reader = easyocr.Reader(['en', 'es'])  # Idiomas a reconocer

# ─────────────────────────────────────────────
#   Procesar carpeta de imágenes con UN SOLO OCR
# ─────────────────────────────────────────────
def process_images_in_folder(folder_path: str):
    for filename in os.listdir(folder_path):
        if filename.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
            image_path = os.path.join(folder_path, filename)
            print("\n───────────────────────────────")
            print(f"Procesando: {filename}")

            # 🔹 1) Correr EasyOCR SOLO UNA VEZ
            result = reader.readtext(image_path)
            texts = [detection[1] for detection in result]

            # Debug de textos OCR (UNA sola vez)
            print("\nTexto extraído con EasyOCR:")
            for t in texts:
                print(t)

            # 🔹 2) Sacar monto usando tu extractor actual (NO lo tocamos)
            amount = find_amount_from_texts(texts)

            # 🔹 3) Sacar número de operación usando las nuevas reglas
            op_number = find_operation_number_from_texts(texts)

            # 🔹 4) Imprimir resultados
            if amount is not None:
                print(f"👉 Monto detectado: S/ {amount}")
            else:
                print("⚠ No se detectó monto en esta imagen")

            if op_number is not None:
                print(f"🔢 Número de operación detectado: {op_number}")
            else:
                print("⚠ No se detectó número de operación en esta imagen")


# ─────────────────────────────────────────────
#   Main
# ─────────────────────────────────────────────
if __name__ == "__main__":
    folder_path = r"C:\proyectos-finales\ocr\OCR\imagenes"
    process_images_in_folder(folder_path)

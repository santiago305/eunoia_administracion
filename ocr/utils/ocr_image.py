import pytesseract


def ocr_image(img, config: str) -> str:
    """Aplica OCR con pytesseract y retorna texto limpio."""
    text = pytesseract.image_to_string(img, config=config)
    clean = "\n".join(
        line.strip() for line in text.splitlines() if line.strip()
    )
    return clean
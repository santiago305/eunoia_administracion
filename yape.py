import cv2
import pytesseract
import re
from pathlib import Path
from dataclasses import dataclass, asdict

# 👉 SOLO EN WINDOWS: descomenta y pon la ruta correcta a tu tesseract.exe
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


@dataclass
class YapeTicket:
    file: str
    amount: str | None = None
    name: str | None = None
    date: str | None = None
    time: str | None = None
    op_number: str | None = None
    raw_text: str | None = None          # OCR general
    raw_amount_text: str | None = None   # texto crudo solo del ROI del monto


# ---------------------------------------------------------------------
# Helpers de OCR general
# ---------------------------------------------------------------------
def preprocess_image(img_path: str) -> "cv2.Mat":
    """Lee y mejora la imagen para el OCR general (todo el voucher)."""
    img = cv2.imread(img_path)

    if img is None:
        raise ValueError(f"No se pudo leer la imagen: {img_path}")

    # Redimensionar (un poco más grande suele ayudar)
    h, w = img.shape[:2]
    scale = 1000 / max(h, w)
    if scale < 1.5:
        img = cv2.resize(
            img,
            None,
            fx=scale * 1.5,
            fy=scale * 1.5,
            interpolation=cv2.INTER_CUBIC,
        )

    # Escala de grises + suavizado + binarización
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.medianBlur(gray, 3)
    _, thresh = cv2.threshold(
        gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    return thresh


def ocr_image(img, config: str) -> str:
    """Aplica OCR con pytesseract y retorna texto limpio."""
    text = pytesseract.image_to_string(img, config=config)
    clean = "\n".join(
        line.strip() for line in text.splitlines() if line.strip()
    )
    return clean


# ---------------------------------------------------------------------
# Extracción de monto (la usan OCR general y ROI)
# ---------------------------------------------------------------------
def parse_amount_text(text: str, prefer_multidigit: bool = False) -> str | None:
    """
    Devuelve el monto normalizado (ej. '154.90', '20.00') o None
    a partir de un texto crudo.

    prefer_multidigit=True => pensado para el ROI:
    si hay varios enteros, se priorizan los de 2–3 dígitos.
    """
    # Reemplazar letras como 'Q' por '0' si aparecen en el monto
    text = re.sub(r'[Qq]', '0', text)  # Reemplazar 'Q' o 'q' por '0'

    lines = text.splitlines()
    amount_str = None

    # 1) Buscar primero "S/ 154.90", "S/154.90", "S /10", etc.
    m_amount = re.search(
        r"S\s*/\s*([0-9]{1,4}(?:[.,][0-9]{2})?)",
        text,
    )
    if m_amount:
        amount_str = m_amount.group(1)
    else:
        # 1.bis) Casos como "5/110 SO" -> tomar lo que va DESPUÉS del "/"
        m_after_slash = re.search(
            r"/\s*([0-9]{1,4}(?:[.,][0-9]{2})?)",
            text,
        )
        if m_after_slash:
            amount_str = m_after_slash.group(1)

    # 2) Buscar números con decimales tipo 154.90, 109.90
    if not amount_str:
        decimal_candidates = re.findall(
            r"\b([0-9]{1,4}[.,][0-9]{2})\b",
            text,
        )
        if decimal_candidates:
            # nos quedamos con el más grande (probable monto)
            candidate = sorted(
                decimal_candidates,
                key=lambda x: float(x.replace(",", ".")),
            )[-1]
            amount_str = candidate

    # 3) Si no hay decimales, buscar enteros en las primeras líneas
    if not amount_str:
        early_lines = lines[:5]
        int_candidates: list[str] = []

        for line in early_lines:
            lower = line.lower()

            # Evitar líneas de fecha/hora/códigos
            if any(
                word in lower
                for word in [
                    "ene",
                    "feb",
                    "mar",
                    "abr",
                    "may",
                    "jun",
                    "jul",
                    "ago",
                    "set",
                    "sep",
                    "oct",
                    "nov",
                    "dic",
                    "código",
                    "codigo",
                    "seguridad",
                    "operación",
                    "operacion",
                ]
            ):
                continue

            # Evitar líneas tipo "6 :" al inicio
            if re.match(r"^\s*\d+\s*[:|]", line):
                continue

            # Solo enteros de 1 a 3 dígitos
            matches = re.findall(r"\b([0-9]{1,3})\b", line)
            int_candidates.extend(matches)

        if int_candidates:
            if prefer_multidigit:
                # ROI: priorizar 2–3 dígitos
                multi = [x for x in int_candidates if len(x) >= 2]
                if multi:
                    amount_str = multi[0]
                else:
                    amount_str = int_candidates[0]
            else:
                # General: si hay multi-dígito, lo usamos; si no, aceptamos 1 dígito
                multi = [x for x in int_candidates if len(x) >= 2]
                if multi:
                    amount_str = multi[0]
                else:
                    amount_str = int_candidates[0]

    if not amount_str:
        return None

    # Normalizar (punto decimal)
    val = float(amount_str.replace(",", "."))

    # Corrección solo para montos con decimales muy grandes (tipo 1154.90)
    if val > 500 and "." in amount_str:
        val = val - 1000

    return f"{val:.2f}"


# ---------------------------------------------------------------------
# OCR específico del ROI del monto (4 pasadas)
# ---------------------------------------------------------------------
def ocr_amount_roi_multi(img_path: str) -> tuple[str | None, str]:
    """
    Prueba 4 recortes distintos donde suele estar el monto.
    Devuelve (monto_encontrado, texto_crudo_del_último_ROI).
    """
    img = cv2.imread(img_path)
    if img is None:
        return None, ""

    h, w = img.shape[:2]

    # Cuatro ROIs en porcentajes (y1, y2, x1, x2)
    # Abarcan más alto y más ancho para soportar diferentes capturas
    rois = [
        # Banda grande alrededor del monto
        (0.17, 0.37, 0.02, 0.60),
        # ROI como el original
        (0.22, 0.42, 0.08, 0.55),
        # Un poco más arriba y a la izquierda
        (0.14, 0.34, 0.00, 0.55),
        # Un poco más abajo y más ancho
        (0.24, 0.44, 0.00, 0.70),
    ]

    last_text = ""

    for (ry1, ry2, rx1, rx2) in rois:
        y1 = int(ry1 * h)
        y2 = int(ry2 * h)
        x1 = int(rx1 * w)
        x2 = int(rx2 * w)

        roi = img[y1:y2, x1:x2]
        if roi.size == 0:
            continue

        # Escalamos el ROI para ayudar a Tesseract
        roi = cv2.resize(roi, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

        # 1er intento: solo gris
        cfg = r"--oem 3 --psm 6 -l spa+eng"
        roi_text = ocr_image(gray, cfg)

        # Si salió vacío, probamos con binarización adaptativa
        if not roi_text.strip():
            gray_blur = cv2.GaussianBlur(gray, (3, 3), 0)
            roi_proc = cv2.adaptiveThreshold(
                gray_blur,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                31,
                5,
            )
            cfg = r"--oem 3 --psm 7 -l spa+eng"
            roi_text = ocr_image(roi_proc, cfg)

        last_text = roi_text

        amount = parse_amount_text(roi_text, prefer_multidigit=True)
        if amount is not None:
            return amount, roi_text

    # Si ningún ROI encontró monto
    return None, last_text


# ---------------------------------------------------------------------
# Parseo general del texto del voucher
# ---------------------------------------------------------------------
def parse_yape_text(text: str, filename: str) -> YapeTicket:
    """Extrae datos clave del texto Yape usando regex."""
    ticket = YapeTicket(file=filename, raw_text=text)

    lines = text.splitlines()

    # 🔹 Monto (primer intento con texto general)
    ticket.amount = parse_amount_text(text)

    # 🔹 Fecha
    m_date = re.search(
        r"(\d{1,2}\s+(?:ene|feb|mar|abr|may|jun|jul|ago|set|sep|oct|nov|dic)\.?[\s]+\d{4})",
        text,
        flags=re.IGNORECASE,
    )
    if m_date:
        ticket.date = m_date.group(1)

    # 🔹 Hora
    m_time = re.search(
        r"(\d{1,2}:\d{2}\s*(?:a|p)\.?\s*m\.?)",
        text,
        flags=re.IGNORECASE,
    )
    if m_time:
        ticket.time = m_time.group(1)

    # 🔹 N° operación
    m_op = re.search(
        r"Nro\.?\s*de\s*operaci[oó]n\s*[\n:]*\s*([0-9]{6,})",
        text,
        flags=re.IGNORECASE,
    )
    if not m_op:
        m_op = re.search(r"([0-9]{6,})\s*$", text, flags=re.MULTILINE)
    if m_op:
        ticket.op_number = m_op.group(1)

    # 🔹 Nombre (línea debajo de "¡Yapeaste!" o del monto)
    amount_line_idx = None
    if ticket.amount:
        for i, line in enumerate(lines):
            if ticket.amount.split(".")[0] in line:  # parte entera
                amount_line_idx = i
                break

    if amount_line_idx is None:
        for i, line in enumerate(lines):
            if "yapeaste" in line.lower():
                amount_line_idx = i
                break

    if amount_line_idx is not None and amount_line_idx + 1 < len(lines):
        possible_name = lines[amount_line_idx + 1].strip()
        if len(possible_name.split()) >= 2 and any(
            c.isupper() for c in possible_name
        ):
            ticket.name = possible_name

    return ticket


# ---------------------------------------------------------------------
# Pipeline por imagen / carpeta
# ---------------------------------------------------------------------
def process_yape_image(img_path: str) -> YapeTicket:
    """Pipeline completo para una sola imagen."""
    # 1) OCR general
    img_general = preprocess_image(img_path)
    text_general = ocr_image(img_general, r"--oem 3 --psm 6 -l spa+eng")
    ticket = parse_yape_text(text_general, filename=Path(img_path).name)

    amount_general = ticket.amount

    # 2) Siempre probamos los ROIs del monto
    amount_roi, roi_text = ocr_amount_roi_multi(img_path)
    ticket.raw_amount_text = roi_text

    # 3) Combinar general + ROI
    if amount_roi is not None:
        if amount_general is None:
            ticket.amount = amount_roi
        else:
            gv = float(amount_general)
            rv = float(amount_roi)

            # Heurística: si el ROI es muy grande (tipo 920)
            # y el general es pequeño (ej. 20), nos quedamos con el general
            if rv >= 200 and gv <= 100 and (rv - gv) >= 80:
                ticket.amount = amount_general
            else:
                ticket.amount = amount_roi

    return ticket


def process_folder(folder: str):
    """Procesa todas las imágenes .jpg/.png de una carpeta."""
    folder_path = Path(folder)
    image_files = list(folder_path.glob("*.jpg")) + list(
        folder_path.glob("*.png")
    )

    if not image_files:
        print("No se encontraron imágenes en la carpeta:", folder_path)
        return

    for img_path in image_files:
        print("=" * 80)
        print(f"📄 Procesando: {img_path.name}")
        ticket = process_yape_image(str(img_path))

        print("Resultado estructurado:")
        for k, v in asdict(ticket).items():
            if k not in ("raw_text", "raw_amount_text"):
                print(f"  {k:14}: {v}")

        print("\nTexto OCR crudo (general):")
        print(ticket.raw_text or "(vacío)")

        print("\nTexto OCR crudo (ROI monto):")
        print(ticket.raw_amount_text or "(no se intentó / vacío)")
        print()


if __name__ == "__main__":
    # 👉 Cambia esta ruta a la carpeta donde guardas tus capturas de Yape
    carpeta = r"C:\proyectos-finales\eunoia_administracion\yape"
    process_folder(carpeta)

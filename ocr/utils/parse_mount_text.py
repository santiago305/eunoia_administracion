from sympy import re


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


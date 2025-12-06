
# ─────────────────────────────────────────────
#   LÓGICA PARA ENCONTRAR NÚMERO DE OPERACIÓN
# ─────────────────────────────────────────────
import re


def find_operation_number_from_texts(text_list: list[str]) -> str | None:
    """
    Recibe la lista de textos que devuelve EasyOCR y busca el NÚMERO / CÓDIGO DE OPERACIÓN.

    Reglas:
    - Prioriza líneas que estén cerca de etiquetas como:
      'Nro. Operación', 'Número de operación', 'N° operación', 'Código de operación', etc.
    - Soporta etiquetas dañadas tipo 'Mro, deoperscion'.
    - Acepta códigos alfanuméricos (con guiones o '/') pero SIEMPRE con al menos un dígito.
    """

    lowered_lines = [t.casefold() for t in text_list]
    n = len(text_list)

    # --- helper para extraer código de una línea ---
    def extract_code_from_line(line: str) -> str | None:
        line = line.strip()
        # quitar posibles etiquetas si vienen en la misma línea
        line_clean = re.sub(
            r"(nro\.?|mro\.?|número|numero|c[oó]digo|operaci[oó]n|ref\.?|referencia)[:\s\-]*",
            "",
            line,
            flags=re.IGNORECASE,
        ).strip()

        # token alfanumérico (con - o /) de largo razonable
        m = re.search(r"\b([A-Za-z0-9][A-Za-z0-9\-/\.]{4,})\b", line_clean)
        if not m:
            return None
        candidate = m.group(1)

        # Debe tener al menos un dígito (evita 'contactos', 'salir', etc.)
        if not re.search(r"\d", candidate):
            return None

        # evitar cosas absurdamente largas (por si agarra una cuenta completa, etc.)
        if len(candidate) > 30:
            return None

        return candidate

    # Etiquetas "fuertes"
    primary_label_keywords = (
        "nro. operación",
        "nro operación",
        "nro. de operación",
        "nro de operación",
        "número de operación",
        "numero de operación",
        "número operación",
        "numero operación",
        "n° operación",
        "n° de operación",
        "código de operación",
        "codigo de operación",
        "código operación",
        "codigo operación",
        "no.ope",  
        "no ope",  
        "no. ope", 
    )

    max_lookahead = 5  # cuántas líneas hacia abajo mirar

    # 1) Buscar primero las etiquetas fuertes
    for idx, lower in enumerate(lowered_lines):
        if any(kw in lower for kw in primary_label_keywords):

            # 1.a) Mismo renglón: 'Nro. Operación 1407526'
            code_here = extract_code_from_line(text_list[idx])
            if code_here:
                return code_here

            # 1.b) Renglones siguientes: soporta casos como:
            # Nro. Operación
            # Banco
            # 1407526
            for offset in range(1, max_lookahead + 1):
                j = idx + offset
                if j >= n:
                    break

                candidate_line = text_list[j].strip()
                if not candidate_line:
                    continue

                cand_lower = candidate_line.casefold()

                # Saltar ruido entre etiqueta y número
                if cand_lower in {
                    "banco",
                    "banco de la nación",
                    "banco de la nacion",
                    "fecha",
                    "hora",
                    "monto",
                    "monto transferido",
                    "monto enviado",
                }:
                    continue

                code = extract_code_from_line(candidate_line)
                if code:
                    return code

    # 2) Plan B: etiquetas dañadas tipo "Mro, deoperscion"
    #    Buscamos líneas que contengan "oper" pero no "exitosa/completa", etc.
    for idx, lower in enumerate(lowered_lines):
        if "oper" in lower:
            # evitar "operación exitosa/completa" como etiqueta de estado
            if any(bad in lower for bad in ("exitosa", "exitoso", "completa", "completo")):
                continue

            # asumimos que el código vendrá en las líneas de abajo, NO en la misma
            for offset in range(1, max_lookahead + 1):
                j = idx + offset
                if j >= n:
                    break

                candidate_line = text_list[j].strip()
                if not candidate_line:
                    continue

                code = extract_code_from_line(candidate_line)
                if code:
                    return code

    # 3) Plan C: el código está entre 'Número de' y 'operación'
    #    Ejemplo:
    #    Número de
    #    D8A7DFE97695
    #    operación
    for idx, line in enumerate(text_list):
        code = extract_code_from_line(line)
        if not code:
            continue

        # Revisar contexto alrededor del código (dos líneas arriba/abajo)
        start = max(idx - 2, 0)
        end = min(idx + 3, n)
        for k in range(start, end):
            if k == idx:
                continue
            neighbor = lowered_lines[k]
            if "oper" in neighbor and not any(
                bad in neighbor for bad in ("exitosa", "exitoso", "completa", "completo")
            ):
                return code

    # 4) Fallback: buscar patrones 'operación 123456' en todo el texto
    full_text = " ".join(text_list)
    for m in re.finditer(
    r"(?:nro\.?|número|numero|c[oó]digo|operaci[oó]n)\s*[:#\-]?\s*([A-Za-z0-9][A-Za-z0-9\-/\.]{4,})",
    full_text,
    flags=re.IGNORECASE,
):
        code = m.group(1)
        # también aquí exigimos al menos un dígito
        if not re.search(r"\d", code):
            continue
        if 4 <= len(code) <= 30:
            return code

    return None

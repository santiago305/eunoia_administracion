# amount_extractor.py
import re


def find_amount_from_texts(text_list: list[str]) -> str | None:
    """
    Recibe la lista de textos que devuelve EasyOCR y busca el MONTO.
    - Prioriza montos que están cerca de palabras clave como:
      'yapeaste', 'operación exitosa', 'plin', 'importe enviado'.
    - Evita tomar horas/fechas como 17.04 h.
    - Para patrones tipo 5/15.00 usa 15.00.
    """
    # Texto unido (para las reglas globales)
    full_text = " ".join(text_list).replace("\n", " ")
    text_case = full_text.casefold()  # para comparar sin importar mayúsculas/acentos

    COMISION_WINDOW = 60  # ampliamos la ventana para detectar 'comision'

    def context_has_comision(start_index: int) -> bool:
        before = text_case[max(0, start_index - COMISION_WINDOW): start_index]
        # cubre 'comisión' y 'comision'
        return "comisión" in before or "comision" in before

    # Listas para candidatos globales (fallback)
    candidates_pos: list[tuple[float, str]] = []   # montos > 0
    candidates_zero: list[tuple[float, str]] = []  # montos == 0

    def add_candidate(raw_amount: str, idx: int):
        """Agrega un candidato normal (no prioritario), respetando COMISIÓN."""
        if context_has_comision(idx):
            return
        amt_str = raw_amount.replace(",", ".")
        try:
            value = float(amt_str)
        except ValueError:
            return
        if value > 0:
            candidates_pos.append((value, raw_amount))
        else:
            candidates_zero.append((value, raw_amount))

    # ─────────────────────────────────────────
    #   Helpers para la regla basada en líneas
    # ─────────────────────────────────────────

    # Detectar si una línea parece fecha/hora (para ignorar 17.04 h, 6:49 p.m., etc.)
    def line_has_date_or_time(line: str) -> bool:
        lower = line.lower()
        # Meses en español
        if re.search(
            r"(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)",
            lower,
        ):
            return True
        # Formato hora tipo 17.04 o 17:04 con h / am / pm
        if re.search(r"\b[0-2]?\d[:.][0-5]\d\b", line) and (
            "h" in lower or "a.m" in lower or "p.m" in lower or " am" in lower or " pm" in lower
        ):
            return True
        return False

    # Patrones reutilizables
    # 5/15.00  -> capturamos 15.00
    pattern_fraction = re.compile(r"\b[5]\s*/\s*([0-9]{1,4}(?:[.,][0-9]{1,2})?)\b")
    # S/15, s/ 20, S1 10, etc. (extendido para 57 ~ S/)
    money_pattern = re.compile(
        r"(?:[sS35]\s*[/71lI]|S/|s/)\s*([0-9]{1,4}(?:[.,][0-9]{1,2})?)"
    )
    # cualquier número con decimales
    decimal_pat = re.compile(r"\b[0-9]{1,4}[.,][0-9]{1,2}\b")

    def extract_amount_from_line(line: str) -> str | None:
        """
        Intenta sacar un monto de UNA sola línea:
        - Ignora líneas que parecen fecha/hora.
        - Maneja 5/15.00, S/15, s/ 20, etc.
        - Solo usa decimales sueltos si la línea NO tiene letras (para no agarrar horas con texto).
        """
        if line_has_date_or_time(line):
            return None

        # 5/15.00 -> 15.00
        m = pattern_fraction.search(line)
        if m:
            return m.group(1)

        # S/15, s/20.00, S1 10, etc.
        m = money_pattern.search(line)
        if m:
            return m.group(1)

        # Fallback: número decimal si la línea NO tiene letras (evita líneas tipo "16 octubre 2025, 17.04 h")
        if not re.search(r"[A-Za-zÁ-Üá-ü]", line):
            m = decimal_pat.search(line)
            if m:
                return m.group(0)

        return None

    def find_monto_after_keywords(
        lines: list[str],
        keywords=("yapeaste", "operación exitosa", "plin"),
        extra_labels=("importe enviado",),
        max_lines=4,
    ) -> str | None:
        """
        Busca un monto en las N líneas siguientes a:
        - 'yapeaste', 'operación exitosa', 'plin'
        - o etiquetas como 'importe enviado'

        Además maneja el patrón típico de YAPE:
            iYapeaste!
            SI
            '109
        donde toma el número entero de la línea debajo de 'SI'.
        """
        n = len(lines)
        lowered = [l.lower() for l in lines]

        for idx, lower in enumerate(lowered):
            if any(kw in lower for kw in keywords) or any(lbl in lower for lbl in extra_labels):
                # ── 1) Regla clásica: buscar monto en las siguientes líneas con extract_amount_from_line
                for offset in range(1, max_lines + 1):
                    j = idx + offset
                    if j >= n:
                        break
                    cand = extract_amount_from_line(lines[j])
                    if cand is not None:
                        return cand

                # ── 2) Regla nueva especial YAPE:
                #     Después de "yapeaste" puede venir:
                #         "SI"
                #         "'109"
                #     Tomamos el entero de la línea siguiente a "SI".
                for offset in range(1, max_lines):
                    j = idx + offset
                    if j + 1 >= n:
                        break

                    line_si = lowered[j].strip()
                    # versiones posibles de "SI"
                    if line_si in ("si", "sí", "si!", "sl", "s1", "s/"):
                        siguiente_linea = lines[j + 1]
                        m = re.search(r"([0-9]{1,4})", siguiente_linea)
                        if m:
                            return m.group(1)

        return None

    # ─────────────────────────────────────────
    #   REGLA PRIORITARIA (por líneas / contexto)
    # ─────────────────────────────────────────
    priority_amount = find_monto_after_keywords(
        text_list,
        keywords=("yapeaste", "operación exitosa", "plin"),
        extra_labels=("importe enviado", "monto transferido", "monto", "monto enviado", "pago exitoso", "Pago de servicio exitoso"),
        max_lines=4,
    )

    if priority_amount is not None:
        # Si encontramos un monto en el bloque cercano a las palabras clave,
        # lo devolvemos directo y NO dejamos que el resto elija el mayor.
        return priority_amount

    # ─────────────────────────────────────────
    #   REGLAS GLOBALES (fallback, como ya tenías)
    # ─────────────────────────────────────────

    # Regla 1: S110 / S1129.90 (S1 pegado)
    for m in re.finditer(r"\b[sS3][1lI]([0-9]+(?:[.,][0-9]+)?)\b", full_text):
        add_candidate(m.group(1), m.start())

    # Regla 2: SI110 (SI pegado al monto)
    for m in re.finditer(r"\b[sS][iI]([0-9]+(?:[.,][0-9]+)?)\b", full_text):
        add_candidate(m.group(1), m.start())

    # Regla 3: moneda separada → "S/ 20", "s/20.00", "SI 110", "S1 10", etc.
    pattern_moneda_global = re.compile(
        r"(?:\b[sS35][/71lI]|\b[sS][iI]\b)\s*([0-9]{1,4}(?:[.,][0-9]{1,2})?)"
    )
    for m in pattern_moneda_global.finditer(full_text):
        add_candidate(m.group(1), m.start())

    # Regla 4: después de palabras tipo "monto", "importe", "importe enviado"
    pattern_label = re.compile(
        r"(?:monto|importe|enviado)(?:\s+\w+)?[^\d]{0,15}([0-9]{1,4}(?:[.,][0-9]{1,2})?)",
        re.IGNORECASE,
    )
    for m in pattern_label.finditer(full_text):
        add_candidate(m.group(1), m.start())

    # Regla 5 (fallback): cualquier número con decimales
    for m in decimal_pat.finditer(full_text):
        add_candidate(m.group(0), m.start())

    # Regla 6: Detectar montos con el formato 5/15.00 (tomamos 15.00)
    for m in pattern_fraction.finditer(full_text):
        add_candidate(m.group(1), m.start())

    # ── Decisión final ───────────────────────
    if candidates_pos:
        # devolvemos el MAYOR monto positivo (solo si no hubo prioridad)
        best = max(candidates_pos, key=lambda x: x[0])
        return best[1]

    if candidates_zero:
        # Solo si no hay ningún monto > 0, devolvemos uno cero
        return candidates_zero[0][1]

    return None

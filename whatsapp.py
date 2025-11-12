from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import re, json, os, base64, time, csv, unicodedata
from pathlib import Path

# ===================== CONFIG =====================
PROFILE_PATH = r"C:\chrome-fuvex"        # Perfil de Chrome (logueado)
CHAT_NAME    = "Comprobantes Eunoia"     # Nombre exacto del chat
CACHE_FILE   = f"wa_cache_{CHAT_NAME}.json"

OUT_DIR      = Path("outputs")
IMG_DIR      = OUT_DIR / "images"
CSV_FILE     = OUT_DIR / "comprobantes.csv"
JSONL_FILE   = OUT_DIR / "comprobantes.jsonl"

# Desaceleradores para no saltar mensajes (ajústalos si hace falta)
TOP_SCROLL_MAX_ROUNDS = 30
TOP_SCROLL_PGUP_BURST = 6
SLOW_PER_MESSAGE_MS   = 350     # pausa entre mensajes
SLOW_AFTER_SCROLL_MS  = 400     # pausa después de cada scroll
BLOB_WAIT_MS_TOTAL    = 2500    # intenta "despertar" imagen blob este tiempo
BLOB_POLL_STEP_MS     = 200
POLL_SECONDS          = 2.0
# ==================================================

_FIELD_BOUNDARY = (
    r"(?="
    r"(?:\s{2,}(?:"
    r"Nombre\s*de\s*cliente"
    r"|N[°º]\s*de\s*cel"
    r"|Producto\s*y\s*cantidad"
    r"|Servicio"
    r"|Descripci[oó]n"
    r"|M[eé]todo\s*(?:de\s*)?pago"
    r"|Cuenta"
    r"|Detalle"
    r"|Nombre"
    r"|Remitente"
    r"|Img\s*(?:SRC|File)?"
    r"|Fecha\s*/?\s*Hora"
    r"|Capturado"
    r")\s*:"
    r")"
    r"|[\r\n]"
    r"|$)"
)

FIELD_PATTERNS = {
    "Nombre de cliente":    re.compile(r"Nombre\s*de\s*cliente:\s*(.+?)" + _FIELD_BOUNDARY, re.IGNORECASE),
    "N° de cel":            re.compile(r"(?:N[°º]\s*de\s*cel|N[°º]\s*cel|Cel(?:ular)?):\s*(\+?\d[\d\s]+?)" + _FIELD_BOUNDARY, re.IGNORECASE),
    "Producto y cantidad":  re.compile(r"Producto\s*y\s*cantidad:\s*(.+?)" + _FIELD_BOUNDARY, re.IGNORECASE),
    "Servicio":             re.compile(r"\bServicio:\s*(.+?)" + _FIELD_BOUNDARY, re.IGNORECASE),
    "Descripción":          re.compile(r"\bDescripci[oó]n:\s*(.+?)" + _FIELD_BOUNDARY, re.IGNORECASE),
    "Método de pago":       re.compile(r"M[eé]todo\s*(?:de\s*)?pago:\s*(.+?)" + _FIELD_BOUNDARY, re.IGNORECASE),
    "Cuenta":               re.compile(r"\bCuenta:\s*(.+?)" + _FIELD_BOUNDARY, re.IGNORECASE),
    "Detalle":              re.compile(r"\bDetalle:\s*(.+?)" + _FIELD_BOUNDARY, re.IGNORECASE),
}

ANTICIPO_PATTERN = re.compile(r"(?i)ANTICIPO")
KNOWN_FIELD_PREFIXES = {
    "nombre de cliente",
    "n de cel",
    "n de celular",
    "producto y cantidad",
    "producto",
    "servicio",
    "serv desc",
    "servicio descripcion",
    "descripcion",
    "metodo de pago",
    "metodo pago",
    "metodo",
    "cuenta",
    "img src",
    "img file",
    "imagen",
    "capturado",
    "fecha hora",
    "remitente",
    "nombre",
}

def ensure_dirs():
    OUT_DIR.mkdir(exist_ok=True)
    IMG_DIR.mkdir(parents=True, exist_ok=True)

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data.get("processed_ids", [])), data.get("last_id", "")
    return set(), ""

def save_cache(processed_ids, last_id):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "processed_ids": sorted(list(processed_ids)),
            "last_id": last_id
        }, f, ensure_ascii=False, indent=2)

def init_csv():
    if not CSV_FILE.exists():
        with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "data_id","timestamp","sender",
                "Nombre de cliente","N° de cel","Producto y cantidad",
                "servicio_o_descripcion","Método de pago","Cuenta","Detalle",
                "img_src_blob","img_src_data","img_file"
            ])

def append_csv(row_dict):
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            row_dict.get("data_id",""),
            row_dict.get("timestamp",""),
            row_dict.get("sender",""),
            row_dict.get("Nombre de cliente",""),
            row_dict.get("N° de cel",""),
            row_dict.get("Producto y cantidad",""),
            row_dict.get("servicio_o_descripcion",""),
            row_dict.get("Método de pago",""),
            row_dict.get("Cuenta",""),
            row_dict.get("Detalle",""),
            row_dict.get("img_src_blob",""),
            row_dict.get("img_src_data",""),
            row_dict.get("img_file",""),
        ])

def append_jsonl(row_dict):
    with open(JSONL_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(row_dict, ensure_ascii=False) + "\n")

def launch_context(p):
    return p.chromium.launch_persistent_context(
        user_data_dir=PROFILE_PATH,
        channel="chrome",  # requiere: playwright install chrome
        headless=False,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
        ],
    )

def open_chat(page):
    page.goto("https://web.whatsapp.com/", wait_until="networkidle")
    page.wait_for_selector('div[role="textbox"]', timeout=60000)

    search_box = page.locator('div[role="textbox"]').first
    search_box.click()
    search_box.fill(CHAT_NAME)
    page.wait_for_timeout(500)

    candidate = page.locator(f'xpath=//span[@title="{CHAT_NAME}"]')
    candidate.first.wait_for(timeout=15000)
    candidate.first.click()

    page.wait_for_selector('div[data-virtualized="false"]', timeout=30000)
    get_msgs_container(page).focus()

def get_msgs_container(page):
    # contenedor principal donde se scrollea la conversación
    return page.locator('div[data-scrolltracepolicy="wa.web.conversation.messages"]').first

def first_message_id(page):
    els = page.locator('div[role="row"] div[data-id]')
    if els.count() == 0:
        return ""
    return els.first.get_attribute("data-id") or ""

def scroll_to_very_top(page):
    msgs = get_msgs_container(page)
    try:
        msgs.focus()
    except Exception:
        pass

    prev_top_id = ""
    rounds_without_change = 0

    for _ in range(TOP_SCROLL_MAX_ROUNDS):
        for _ in range(TOP_SCROLL_PGUP_BURST):
            page.keyboard.press("PageUp")
            page.wait_for_timeout(SLOW_AFTER_SCROLL_MS)
        try:
            page.evaluate('(el)=>{el.scrollTop=0}', msgs)
        except Exception:
            pass
        page.wait_for_timeout(SLOW_AFTER_SCROLL_MS + 200)

        top_id = first_message_id(page)
        if not top_id:
            continue
        if top_id == prev_top_id:
            rounds_without_change += 1
        else:
            rounds_without_change = 0
        prev_top_id = top_id
        if rounds_without_change >= 3:
            break

def scroll_to_last_processed(page, last_id):
    if not last_id:
        return
    locator = page.locator(f'div[role="row"] div[data-id="{last_id}"]')
    try:
        locator.first.scroll_into_view_if_needed(timeout=3000)
        page.wait_for_timeout(SLOW_AFTER_SCROLL_MS)
        page.keyboard.press("PageDown")
        page.wait_for_timeout(SLOW_AFTER_SCROLL_MS)
    except Exception:
        for _ in range(10):
            page.keyboard.press("End")
            page.wait_for_timeout(SLOW_AFTER_SCROLL_MS)
            if locator.count() > 0:
                try:
                    locator.first.scroll_into_view_if_needed(timeout=2000)
                    page.keyboard.press("PageDown")
                    page.wait_for_timeout(SLOW_AFTER_SCROLL_MS)
                except Exception:
                    pass
                break

def iter_message_elements(page):
    rows = page.locator('div[role="row"] div[data-id]')
    count = rows.count()
    if count == 0:
        return []
    items = []
    for i in range(count):
        el = rows.nth(i)
        try:
            box = el.bounding_box()
        except Exception:
            box = None
        y = box["y"] if box else 0
        items.append((y, el))
    items.sort(key=lambda t: t[0])  # top -> down
    return [el for _, el in items]

def find_copyable_block_in(el):
    blk = el.locator('div.copyable-text[data-pre-plain-text]').first
    return blk if blk.count() > 0 else None

def get_text_block(message_el):
    blk = find_copyable_block_in(message_el)
    if not blk:
        return ""
    spans = blk.locator('span.selectable-text')
    texts = []
    n = min(spans.count(), 120)
    for i in range(n):
        try:
            t = spans.nth(i).inner_text().strip()
            if t:
                texts.append(t)
        except Exception:
            pass
    return "\n".join(texts)

def extract_timestamp_and_sender(message_el):
    blk = find_copyable_block_in(message_el)
    if not blk:
        return "", ""
    val = blk.get_attribute("data-pre-plain-text") or ""
    m = re.search(r"\[(.*?)\]\s*(.*?):\s*$", val)
    if not m:
        return "", ""
    return m.group(1).strip(), m.group(2).strip()

def fetch_blob_to_base64(page, blob_url):
    return page.evaluate(
        """async (blobUrl) => {
            const res = await fetch(blobUrl);
            const buf = await res.arrayBuffer();
            const ct = res.headers.get('content-type') || 'image/jpeg';
            const b64 = btoa(String.fromCharCode(...new Uint8Array(buf)));
            return { b64, contentType: ct };
        }""",
        blob_url
    )

def ext_from_content_type(ct):
    ct = (ct or "").lower()
    if "png" in ct:  return "png"
    if "webp" in ct: return "webp"
    if "gif" in ct:  return "gif"
    return "jpg"

def looks_like_form_alt(alt_text):
    if not alt_text:
        return False
    low = alt_text.lower()
    checks = [
        "nombre de cliente", "producto y cantidad",
        "método de pago", "metodo de pago", "servicio",
        "descripción", "descripcion", "cuenta", "detalle", "anticipo", "completo"
    ]
    return any(k in low for k in checks)

def strict_has_blob_img_inside_copyable(message_el):
    """
    Requisitos estrictos:
    - Debe haber 'div.copyable-text[data-pre-plain-text]' en el mismo mensaje.
    - Dentro de ese bloque, DEBE existir <img src="blob:..."> (preferido).
    - (Se permite que además exista un <img src="data:...">, pero no es válido si no hay blob).
    Retorna: (img_blob_element, blob_src, data_src_opt)
    """
    blk = find_copyable_block_in(message_el)
    if not blk:
        return None, "", ""

    # Busca blob primero
    blob_imgs = blk.locator('img[src^="blob:"]')
    data_imgs = blk.locator('img[src^="data:image"]')

    blob_el = None
    blob_src = ""
    data_src = ""

    # Si no hay blob todavía, intenta "despertar" la tarjeta (scroll/espera) un ratito
    if blob_imgs.count() == 0:
        # micro-scroll para forzar carga diferida
        try:
            message_el.scroll_into_view_if_needed(timeout=1500)
        except Exception:
            pass

        t0 = time.time()
        while (time.time() - t0) * 1000 < BLOB_WAIT_MS_TOTAL:
            # pequeña espera
            time.sleep(BLOB_POLL_STEP_MS / 1000.0)
            # a veces ayuda enfocar y un toque de 'End' y volver
            try:
                message_el.hover(timeout=500)
            except Exception:
                pass
            # re-evaluar
            if blk.locator('img[src^="blob:"]').count() > 0:
                break

    if blob_imgs.count() > 0:
        blob_el = blob_imgs.first
        blob_src = blob_el.get_attribute("src") or ""
        # opcionalmente, si hay data: también la registramos
        if data_imgs.count() > 0:
            data_src = data_imgs.first.get_attribute("src") or ""
        return blob_el, blob_src, data_src

    # No pasó el filtro estricto
    return None, "", ""

def get_text_fields(full_text):
    data = {}
    for field, pat in FIELD_PATTERNS.items():
        m = pat.search(full_text)
        if m:
            data[field] = m.group(1).strip()

    # Derivar Detalle cuando no viene explícito en el texto.
    if "Detalle" not in data:
        detail_candidate = _extract_implied_detail(full_text)
        if detail_candidate:
            data["Detalle"] = detail_candidate

    # Unificación Serv./Desc.
    serv = data.get("Servicio")
    desc = data.get("Descripción")
    if serv and desc:
        data["servicio_o_descripcion"] = desc
    elif serv:
        data["servicio_o_descripcion"] = serv
    elif desc:
        data["servicio_o_descripcion"] = desc

    keys_to_check = ["Nombre de cliente", "N° de cel", "Producto y cantidad",
                     "servicio_o_descripcion", "Método de pago", "Cuenta", "Detalle"]
    if not any(k in data for k in keys_to_check):
        return None
    return data


def _extract_implied_detail(text: str) -> str | None:
    segments = _segment_message(text)
    if not segments:
        return None

    for segment in reversed(segments):
        if not ANTICIPO_PATTERN.search(segment):
            continue
        extracted = _detail_from_anticipo_segment(segment)
        if extracted:
            return extracted

    for segment in reversed(segments):
        if _segment_is_known_field(segment):
            continue
        cleaned = _clean_detail_segment(segment)
        if cleaned:
            return cleaned

    return None


def _segment_message(text: str):
    segments = []
    for raw_line in re.split(r"[\r\n]+", text):
        if not raw_line:
            continue
        parts = raw_line.split("✅") if "✅" in raw_line else [raw_line]
        for part in parts:
            cleaned = part.strip()
            if cleaned:
                segments.append(cleaned)
    return segments


def _detail_from_anticipo_segment(segment: str) -> str | None:
    match = re.search(r"(?i)ANTICIPO\b[\s:\-]*([^\r\n]*)", segment)
    if match:
        remainder = match.group(1).strip()
        if remainder:
            return remainder

    trailing = re.split(r"(?i)ANTICIPO", segment)[-1].strip(" :.-")
    return trailing or None


def _segment_is_known_field(segment: str) -> bool:
    prefix = _normalize_prefix(segment)
    if not prefix:
        return False
    return any(prefix.startswith(item) for item in KNOWN_FIELD_PREFIXES)


def _normalize_prefix(segment: str) -> str:
    normalized = unicodedata.normalize("NFD", segment)
    normalized = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    normalized = normalized.replace("º", "").replace("°", "")
    normalized = normalized.lower()
    prefix = normalized.split(":", 1)[0]
    prefix = re.sub(r"[^a-z0-9]+", " ", prefix)
    prefix = re.sub(r"\s+", " ", prefix)
    return prefix.strip()


def _clean_detail_segment(segment: str) -> str:
    cleaned = segment.strip()
    cleaned = cleaned.lstrip("-•:·")
    return cleaned.strip()

def get_text_block_strict(message_el):
    # El texto también debe estar dentro del mismo copyable-text (tu estructura)
    return get_text_block(message_el)

def download_from_blob(page, blob_src, out_name_base):
    try:
        res = fetch_blob_to_base64(page, blob_src)
        ext = ext_from_content_type(res.get("contentType"))
        out_path = IMG_DIR / f"{out_name_base}.{ext}"
        with open(out_path, "wb") as f:
            f.write(base64.b64decode(res.get("b64", "")))
        return str(out_path)
    except Exception:
        return ""

def process_message_strict(page, message_el):
    data_id = message_el.get_attribute("data-id") or ""
    # 1) Estructura estricta con blob
    blob_el, blob_src, data_src = strict_has_blob_img_inside_copyable(message_el)
    if not blob_el or not blob_src:
        return None  # descartar mensajes sin blob-img en el bloque correcto

    # 2) Texto del mismo bloque
    full_text = get_text_block_strict(message_el)
    if not full_text:
        return None

    fields = get_text_fields(full_text)
    if not fields:
        return None

    # 3) Timestamp y remitente
    ts, sender = extract_timestamp_and_sender(message_el)

    # 4) Descargar blob
    img_file = download_from_blob(page, blob_src, data_id)

    result = {
        "data_id": data_id,
        "timestamp": ts,
        "sender": sender,
        "raw_text": full_text,
        "img_src_blob": blob_src,
        "img_src_data": data_src,
        "img_file": img_file,
    }
    result.update(fields)
    return result

def process_visible_top_to_bottom(page, processed_ids, last_id, verbose_print=True):
    new_count = 0
    elements = iter_message_elements(page)
    for el in elements:
        data_id = el.get_attribute("data-id") or ""
        if not data_id or data_id in processed_ids:
            continue

        # Ir pausado para no “saltar” elementos
        try:
            el.scroll_into_view_if_needed(timeout=1500)
        except Exception:
            pass
        page.wait_for_timeout(SLOW_PER_MESSAGE_MS)

        parsed = process_message_strict(page, el)
        if not parsed:
            # Mensaje que no cumple con la estructura exacta (sin blob), descartar
            continue

        append_csv(parsed)
        append_jsonl(parsed)

        processed_ids.add(parsed["data_id"])
        last_id = parsed["data_id"]
        if verbose_print:
            print("════════════════════════════════════════")
            print(f"✅ Capturado: {parsed['data_id']}")
            print(f"  Fecha/Hora : {parsed.get('timestamp','')}")
            print(f"  Remitente  : {parsed.get('sender','')}")
            print(f"  Nombre     : {parsed.get('Nombre de cliente','')}")
            print(f"  N° Cel     : {parsed.get('N° de cel','')}")
            print(f"  Producto   : {parsed.get('Producto y cantidad','')}")
            print(f"  Serv./Desc.: {parsed.get('servicio_o_descripcion','')}")
            print(f"  Método pago: {parsed.get('Método de pago','')}")
            print(f"  Cuenta     : {parsed.get('Cuenta','')}")
            print(f"  Detalle    : {parsed.get('Detalle','')}")
            print(f"  Img SRC    : {parsed.get('img_src_blob','')}")
            print(f"  Img File   : {parsed.get('img_file','')}")
        new_count += 1
        save_cache(processed_ids, last_id)

        # Pequeña espera tras procesar cada mensaje (más robustez)
        page.wait_for_timeout(SLOW_PER_MESSAGE_MS)

    return new_count, last_id

def main():
    ensure_dirs()
    init_csv()
    processed_ids, last_id = load_cache()

    with sync_playwright() as p:
        context = launch_context(p)
        page = context.pages[0] if context.pages else context.new_page()

        open_chat(page)

        if not processed_ids:
            scroll_to_very_top(page)
        else:
            scroll_to_last_processed(page, last_id)

        _, last_id = process_visible_top_to_bottom(page, processed_ids, last_id, verbose_print=True)
        save_cache(processed_ids, last_id)

        print("🔄 Conectado. Escuchando nuevos mensajes... (Ctrl+C para salir)")
        try:
            while True:
                get_msgs_container(page).focus()
                page.keyboard.press("End")
                page.wait_for_timeout(SLOW_AFTER_SCROLL_MS)

                new_count, last_id = process_visible_top_to_bottom(page, processed_ids, last_id, verbose_print=True)
                if new_count:
                    save_cache(processed_ids, last_id)

                time.sleep(POLL_SECONDS)
        except KeyboardInterrupt:
            print("👋 Saliendo por Ctrl+C")
        finally:
            save_cache(processed_ids, last_id)
            # context.close()  # opcional

if __name__ == "__main__":
    main()

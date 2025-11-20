import asyncio

from app.whatsapp_processing import processing


class DummyLocator:
    def __init__(self, count=0):
        self._count = count

    async def count(self):
        return self._count

    async def scroll_into_view_if_needed(self, timeout=None):
        return


class DummyElement:
    def __init__(self, identifier):
        self.identifier = identifier

    async def get_attribute(self, name):
        if name == "data-id":
            return self.identifier
        return ""

    async def scroll_into_view_if_needed(self, timeout=None):
        return


class DummyPage:
    def __init__(self):
        self._locator = DummyLocator()
        self.timeouts = []

    def locator(self, selector):
        return self._locator

    async def wait_for_timeout(self, value):
        self.timeouts.append(value)

class DummyRows:
    def __init__(self, elements):
        self._elements = elements

    async def count(self):
        return len(self._elements)

    def nth(self, index):
        return self._elements[index]

async def _run_process(elements, monkeypatch, processor):
    page = DummyPage()
    processed_ids = set()
    last_id = ""
    last_signature = ""

    dummy_rows = DummyRows(elements)

    monkeypatch.setattr(processing, "message_rows", lambda page: dummy_rows)
    monkeypatch.setattr(processing, "append_csv", lambda payload: None)
    monkeypatch.setattr(processing, "append_jsonl", lambda payload: None)
    monkeypatch.setattr(processing, "process_message_strict", processor)

    return await processing.process_visible_top_to_bottom(
        page,
        processed_ids,
        last_id,
        last_signature,
        verbose_print=False,
    ), processed_ids


def test_process_visible_top_to_bottom_handles_thousand(monkeypatch):
    elements = [DummyElement(f"msg-{index}") for index in range(1000)]

    async def processor(page, element):
        return {
            "data_id": element.identifier,
            "timestamp": f"ts-{element.identifier}",
            "sender": "sender",
            "raw_text": f"text-{element.identifier}",
            "img_src_blob": f"blob-{element.identifier}",
            "img_src_data": f"data-{element.identifier}",
            "img_file": f"/tmp/{element.identifier}.jpg",
        }

    (result, processed_ids) = asyncio.run(_run_process(elements, monkeypatch, processor))
    new_count, last_id, last_signature = result

    assert new_count == 1000
    assert last_id == "msg-999"
    assert last_signature
    assert len(processed_ids) == 1000


def test_process_visible_top_to_bottom_skips_errors(monkeypatch):
    elements = [DummyElement(f"msg-{index}") for index in range(10)]

    async def processor(page, element):
        if element.identifier == "msg-5":
            raise RuntimeError("boom")
        return {
            "data_id": element.identifier,
            "timestamp": "ts",
            "sender": "sender",
            "raw_text": element.identifier,
            "img_src_blob": "blob",
            "img_src_data": "data",
            "img_file": "/tmp/file.jpg",
        }

    (result, processed_ids) = asyncio.run(_run_process(elements, monkeypatch, processor))
    new_count, last_id, _ = result

    assert new_count == 9
    assert last_id == "msg-9"
    assert "msg-5" not in processed_ids
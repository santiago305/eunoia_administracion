
import asyncio

from app.whatsapp_processing import iteration


class DummyRow:
    def __init__(self, data_id: str, text: str):
        self._data_id = data_id
        self._text = text

    async def get_attribute(self, name: str):
        if name == "data-id":
            return self._data_id
        return ""

    async def inner_text(self):
        return self._text


class DummyRows:
    def __init__(self, rows):
        self._rows = rows

    async def count(self):
        return len(self._rows)

    def nth(self, index: int):
        return self._rows[index]


def test_first_message_id_skips_pinned_notice(monkeypatch):
    dummy_rows = DummyRows(
        [
            DummyRow("pin-1", "~ Eunoia Cosmetica Artesanal fijó un mensaje."),
            DummyRow("msg-1", "Contenido real del mensaje"),
        ]
    )

    monkeypatch.setattr(iteration, "message_rows", lambda page: dummy_rows)

    result = asyncio.run(iteration.first_message_id(object()))

    assert result == "msg-1"


def test_first_message_id_returns_empty_when_only_notices(monkeypatch):
    dummy_rows = DummyRows(
        [
            DummyRow("pin-1", "~ Eunoia Cosmetica Artesanal fijó un mensaje."),
            DummyRow("pin-2", "Mensaje fijado"),
        ]
    )

    monkeypatch.setattr(iteration, "message_rows", lambda page: dummy_rows)

    result = asyncio.run(iteration.first_message_id(object()))

    assert result == ""
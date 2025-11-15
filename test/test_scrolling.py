import asyncio

from app.whatsapp_processing import scrolling


class DummyKeyboard:
    def __init__(self):
        self.presses = []

    async def press(self, key):
        self.presses.append(key)


class DummyMessages:
    def __init__(self):
        self.focus_calls = 0
        self.eval_calls = 0

    async def focus(self):
        self.focus_calls += 1


class DummyPage:
    def __init__(self):
        self.keyboard = DummyKeyboard()
        self.timeouts = []

    async def wait_for_timeout(self, value):
        self.timeouts.append(value)

    async def evaluate(self, script, messages):
        messages.eval_calls += 1


def test_scroll_to_very_top_reaches_large_history(monkeypatch):
    messages = DummyMessages()
    sequence = [f"msg-{index}" for index in range(500)] + ["msg-499"] * 3
    iterator = iter(sequence)

    async def fake_first_message_id(page):
        try:
            return next(iterator)
        except StopIteration:
            return "msg-499"

    monkeypatch.setattr(scrolling, "get_messages_container", lambda page: messages)
    monkeypatch.setattr(scrolling, "first_message_id", fake_first_message_id)
    monkeypatch.setattr(scrolling, "TOP_SCROLL_PGUP_BURST", 1)
    monkeypatch.setattr(scrolling, "TOP_SCROLL_MAX_ROUNDS", 0)
    monkeypatch.setattr(scrolling, "SLOW_AFTER_SCROLL_MS", 0)

    page = DummyPage()
    asyncio.run(scrolling.scroll_to_very_top(page))

    assert len(page.keyboard.presses) >= 500
    assert messages.focus_calls >= 1
    assert messages.eval_calls >= 1
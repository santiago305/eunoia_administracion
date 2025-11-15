
import csv
import json

from app.whatsapp_processing.cache import load_cache, save_cache


def test_save_cache_handles_large_history(tmp_path):
    cache_file = tmp_path / "cache.json"
    processed = {f"id_{index}" for index in range(500)}
    last_id = "id_499"

    save_cache(processed, last_id, cache_path=str(cache_file))

    payload = json.loads(cache_file.read_text(encoding="utf-8"))
    assert len(payload["processed_ids"]) == 500
    assert payload["processed_ids"][-1] == last_id


def test_load_cache_prefers_large_csv(tmp_path):
    cache_file = tmp_path / "cache.json"
    csv_file = tmp_path / "export.csv"

    cache_file.write_text(
        json.dumps(
            {
                "processed_ids": ["legacy"],
                "last_id": "legacy",
                "last_signature": "sig",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    with csv_file.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["data_id"])
        for index in range(1000):
            writer.writerow([f"id_{index}"])

    state = load_cache(cache_path=str(cache_file), csv_path=str(csv_file))

    assert len(state.processed_ids) >= 1000
    assert state.last_id == "id_999"
    assert state.previous_id == ""
    assert state.last_signature == ""
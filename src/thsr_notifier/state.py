import json
import os
from .models import Watch, AvailableTrain

class State:
    def __init__(self, path: str):
        self._path = path
        self._data: dict[str, list[str]] = self._load()

    def _load(self) -> dict:
        if not os.path.exists(self._path):
            return {}
        try:
            with open(self._path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def _key(self, w: Watch) -> str:
        return f"{w.label}|{w.date}|{w.origin_id}|{w.destination_id}|{w.seat_class}"

    def diff(self, watch: Watch, available: list[AvailableTrain]) -> list[AvailableTrain]:
        key = self._key(watch)
        previous = set(self._data.get(key, []))
        current = {t.train_no for t in available}
        self._data[key] = sorted(current)
        return [t for t in available if t.train_no not in previous]

    def save(self) -> None:
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2, sort_keys=True)

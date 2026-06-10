import json
import os
from .models import Watch

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

    def previously_notified(self, watch: Watch) -> set[str]:
        return set(self._data.get(self._key(watch), []))

    def set_notified(self, watch: Watch, train_nos: set[str]) -> None:
        self._data[self._key(watch)] = sorted(train_nos)

    def save(self) -> None:
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2, sort_keys=True)

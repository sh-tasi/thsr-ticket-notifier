import pytest
from thsr_notifier.config import load_watches, ConfigError

def _write(tmp_path, text):
    p = tmp_path / "watches.yml"
    p.write_text(text, encoding="utf-8")
    return str(p)

def test_loads_minimal_watch(tmp_path):
    path = _write(tmp_path, """
watches:
  - label: 回家
    origin: 台北
    destination: 左營
    date: 2026-06-20
""")
    watches = load_watches(path)
    assert len(watches) == 1
    w = watches[0]
    assert w.origin_id == "1000"
    assert w.destination_id == "1070"
    assert w.trains == []
    assert w.seat_class == "standard"

def test_full_watch_fields(tmp_path):
    path = _write(tmp_path, """
watches:
  - label: 上班
    origin: 台北
    destination: 台中
    date: 2026-06-21
    time_from: "18:00"
    time_to: "21:00"
    trains: [641]
    seat_class: business
""")
    w = load_watches(path)[0]
    assert w.time_from == "18:00"
    assert w.time_to == "21:00"
    assert w.trains == ["0641"]      # 正規化為 4 位字串
    assert w.seat_class == "business"

def test_unknown_station_raises(tmp_path):
    path = _write(tmp_path, """
watches:
  - label: 壞站
    origin: 火星
    destination: 左營
    date: 2026-06-20
""")
    with pytest.raises(ConfigError):
        load_watches(path)

def test_bad_seat_class_raises(tmp_path):
    path = _write(tmp_path, """
watches:
  - label: 壞艙
    origin: 台北
    destination: 左營
    date: 2026-06-20
    seat_class: first
""")
    with pytest.raises(ConfigError):
        load_watches(path)

def test_time_from_after_time_to_raises(tmp_path):
    path = _write(tmp_path, """
watches:
  - label: 壞時段
    origin: 台北
    destination: 左營
    date: 2026-06-20
    time_from: "21:00"
    time_to: "18:00"
""")
    with pytest.raises(ConfigError):
        load_watches(path)

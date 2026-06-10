from thsr_notifier.models import Watch, AvailableTrain, AVAILABLE, LIMITED, FULL, is_buyable

def test_watch_defaults():
    w = Watch(label="x", origin_id="1000", destination_id="1070", date="2026-06-20")
    assert w.time_from is None
    assert w.trains == []
    assert w.seat_class == "standard"

def test_is_buyable():
    assert is_buyable(AVAILABLE) is True
    assert is_buyable(LIMITED) is True
    assert is_buyable(FULL) is False

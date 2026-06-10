from thsr_notifier.matcher import filter_available
from thsr_notifier.models import Watch, AvailableTrain, AVAILABLE, LIMITED, FULL

def _w(**kw):
    base = dict(label="x", origin_id="1000", destination_id="1070", date="2026-06-20")
    base.update(kw)
    return Watch(**base)

TRAINS = [
    AvailableTrain("0641", "18:30", "20:15", AVAILABLE),
    AvailableTrain("0643", "19:00", "20:45", FULL),
    AvailableTrain("0645", "21:30", "23:15", LIMITED),
]

def test_only_buyable_returned():
    out = filter_available(_w(), TRAINS)
    assert {t.train_no for t in out} == {"0641", "0645"}

def test_time_window_filters_by_departure():
    out = filter_available(_w(time_from="18:00", time_to="21:00"), TRAINS)
    assert {t.train_no for t in out} == {"0641"}  # 0645 在 21:30 超出，0643 已售完

def test_specific_trains_filter():
    out = filter_available(_w(trains=["0645"]), TRAINS)
    assert {t.train_no for t in out} == {"0645"}

def test_time_and_train_combined_empty():
    out = filter_available(_w(trains=["0645"], time_from="18:00", time_to="21:00"), TRAINS)
    assert out == []

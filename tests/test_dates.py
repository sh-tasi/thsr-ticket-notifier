from datetime import date
from thsr_notifier.dates import is_in_window

TODAY = date(2026, 6, 10)

def test_today_is_in_window():
    assert is_in_window("2026-06-10", TODAY) is True

def test_within_horizon():
    assert is_in_window("2026-07-07", TODAY) is True   # +27 天

def test_past_date_excluded():
    assert is_in_window("2026-06-09", TODAY) is False

def test_beyond_horizon_excluded():
    assert is_in_window("2026-07-08", TODAY) is False   # +28 天

def test_invalid_date_excluded():
    assert is_in_window("not-a-date", TODAY) is False

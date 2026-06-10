import pytest
from thsr_notifier.stations import to_station_id, StationNotFound

def test_known_station_returns_id():
    assert to_station_id("台北") == "1000"
    assert to_station_id("左營") == "1070"

def test_unknown_station_raises():
    with pytest.raises(StationNotFound):
        to_station_id("不存在站")

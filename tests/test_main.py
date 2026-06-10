from unittest.mock import MagicMock
from thsr_notifier.main import run
from thsr_notifier.models import Watch

def _watch():
    return Watch(label="回家", origin_id="1000", destination_id="1070",
                 date="2026-06-20", time_from="18:00", time_to="21:00",
                 seat_class="standard")

def test_run_notifies_when_available(tmp_path):
    client = MagicMock()
    client.fetch_timetable.return_value = [
        {"DailyTrainInfo": {"TrainNo": "0641"},
         "OriginStopTime": {"DepartureTime": "18:30"},
         "DestinationStopTime": {"ArrivalTime": "20:15"}},
    ]
    client.fetch_seat_status.return_value = [
        {"TrainNo": "0641", "StandardSeatStatus": "尚有座位", "BusinessSeatStatus": "已售完"},
    ]
    notifier = MagicMock()
    state_path = str(tmp_path / "state.json")

    run([_watch()], client, notifier, state_path)

    assert notifier.notify.call_count == 1

def test_run_no_notify_when_full(tmp_path):
    client = MagicMock()
    client.fetch_timetable.return_value = [
        {"DailyTrainInfo": {"TrainNo": "0641"},
         "OriginStopTime": {"DepartureTime": "18:30"},
         "DestinationStopTime": {"ArrivalTime": "20:15"}},
    ]
    client.fetch_seat_status.return_value = [
        {"TrainNo": "0641", "StandardSeatStatus": "已售完", "BusinessSeatStatus": "已售完"},
    ]
    notifier = MagicMock()
    run([_watch()], client, notifier, str(tmp_path / "state.json"))
    assert notifier.notify.call_count == 0

def test_run_continues_on_single_watch_error(tmp_path):
    client = MagicMock()
    client.fetch_timetable.side_effect = [RuntimeError("boom"), [
        {"DailyTrainInfo": {"TrainNo": "0641"},
         "OriginStopTime": {"DepartureTime": "18:30"},
         "DestinationStopTime": {"ArrivalTime": "20:15"}},
    ]]
    client.fetch_seat_status.return_value = [
        {"TrainNo": "0641", "StandardSeatStatus": "尚有座位", "BusinessSeatStatus": "已售完"},
    ]
    notifier = MagicMock()
    run([_watch(), _watch()], client, notifier, str(tmp_path / "state.json"))
    assert notifier.notify.call_count == 1  # 第一筆爆掉、第二筆仍通知

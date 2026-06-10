import datetime
from unittest.mock import MagicMock
from thsr_notifier.main import run
from thsr_notifier.models import Watch

TODAY = datetime.date(2026, 6, 10)

def _watch(date="2026-06-20"):
    return Watch(label="回家", origin_id="1000", destination_id="1070",
                 date=date, time_from="18:00", time_to="21:00",
                 seat_class="standard")

def _client(seat_status="O"):  # O=尚有座位, L=座位有限, X=已售完
    client = MagicMock()
    client.fetch_timetable.return_value = [
        {"DailyTrainInfo": {"TrainNo": "0641"},
         "OriginStopTime": {"DepartureTime": "18:30"},
         "DestinationStopTime": {"ArrivalTime": "20:15"}},
    ]
    client.fetch_seat_status.return_value = [
        {"TrainNo": "0641", "StandardSeatStatus": seat_status, "BusinessSeatStatus": "X"},
    ]
    return client

def test_run_notifies_when_available(tmp_path):
    notifier = MagicMock()
    run([_watch()], _client(), notifier, str(tmp_path / "state.json"), today=TODAY)
    assert notifier.notify_many.call_count == 1

def test_run_no_notify_when_full(tmp_path):
    notifier = MagicMock()
    run([_watch()], _client("X"), notifier, str(tmp_path / "state.json"), today=TODAY)
    assert notifier.notify_many.call_count == 0

def test_run_continues_on_single_watch_error(tmp_path):
    client = _client()
    good_timetable = client.fetch_timetable.return_value
    client.fetch_timetable.side_effect = [RuntimeError("boom"), good_timetable]
    notifier = MagicMock()
    run([_watch(), _watch()], client, notifier, str(tmp_path / "state.json"), today=TODAY)
    assert notifier.notify_many.call_count == 1  # 第一筆爆掉、第二筆仍通知

def test_run_skips_out_of_window_date(tmp_path):
    client = _client()
    notifier = MagicMock()
    run([_watch(date="2020-01-01")], client, notifier, str(tmp_path / "state.json"), today=TODAY)
    assert notifier.notify_many.call_count == 0
    client.fetch_timetable.assert_not_called()

def test_run_no_renotify_on_second_run(tmp_path):
    path = str(tmp_path / "state.json")
    notifier = MagicMock()
    run([_watch()], _client(), notifier, path, today=TODAY)
    run([_watch()], _client(), notifier, path, today=TODAY)
    assert notifier.notify_many.call_count == 1  # 只有第一輪通知

def test_run_retries_after_notify_failure(tmp_path):
    path = str(tmp_path / "state.json")
    failing = MagicMock()
    failing.notify_many.side_effect = RuntimeError("telegram down")
    run([_watch()], _client(), failing, path, today=TODAY)
    assert failing.notify_many.call_count == 1
    ok = MagicMock()  # 下一輪用正常 notifier，應重試（未被去重，因前次失敗未入庫）
    run([_watch()], _client(), ok, path, today=TODAY)
    assert ok.notify_many.call_count == 1

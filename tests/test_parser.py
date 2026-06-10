from thsr_notifier.parser import build_trains
from thsr_notifier.models import AVAILABLE, LIMITED, FULL

TIMETABLE = [
    {"DailyTrainInfo": {"TrainNo": "0641"},
     "OriginStopTime": {"DepartureTime": "18:30"},
     "DestinationStopTime": {"ArrivalTime": "20:15"}},
    {"DailyTrainInfo": {"TrainNo": "0643"},
     "OriginStopTime": {"DepartureTime": "19:00"},
     "DestinationStopTime": {"ArrivalTime": "20:45"}},
]
SEAT = [
    {"TrainNo": "0641", "StandardSeatStatus": "O", "BusinessSeatStatus": "X"},
    {"TrainNo": "0643", "StandardSeatStatus": "X", "BusinessSeatStatus": "L"},
]

def test_join_standard_class():
    trains = build_trains(TIMETABLE, SEAT, "standard")
    by_no = {t.train_no: t for t in trains}
    assert by_no["0641"].departure == "18:30"
    assert by_no["0641"].arrival == "20:15"
    assert by_no["0641"].seat_status == AVAILABLE
    assert by_no["0643"].seat_status == FULL

def test_join_business_class():
    trains = build_trains(TIMETABLE, SEAT, "business")
    by_no = {t.train_no: t for t in trains}
    assert by_no["0641"].seat_status == FULL
    assert by_no["0643"].seat_status == LIMITED

def test_train_without_seat_data_is_skipped():
    trains = build_trains(TIMETABLE, [SEAT[0]], "standard")
    assert {t.train_no for t in trains} == {"0641"}

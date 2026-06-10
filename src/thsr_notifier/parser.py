from .models import AvailableTrain, AVAILABLE, LIMITED, FULL

_STATUS_MAP = {
    "尚有座位": AVAILABLE,
    "座位有限": LIMITED,
    "已售完": FULL,
}

def _normalize_status(raw: str) -> str:
    return _STATUS_MAP.get((raw or "").strip(), FULL)

def build_trains(timetable_raw: list, seat_raw: list, seat_class: str) -> list[AvailableTrain]:
    field = "BusinessSeatStatus" if seat_class == "business" else "StandardSeatStatus"
    seat_by_no = {str(s.get("TrainNo")): s for s in seat_raw}

    trains: list[AvailableTrain] = []
    for row in timetable_raw:
        train_no = str(row.get("DailyTrainInfo", {}).get("TrainNo"))
        seat = seat_by_no.get(train_no)
        if seat is None:
            continue
        trains.append(AvailableTrain(
            train_no=train_no,
            departure=row.get("OriginStopTime", {}).get("DepartureTime", ""),
            arrival=row.get("DestinationStopTime", {}).get("ArrivalTime", ""),
            seat_status=_normalize_status(seat.get(field, "")),
        ))
    return trains

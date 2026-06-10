from .models import Watch, AvailableTrain, is_buyable

def filter_available(watch: Watch, trains: list[AvailableTrain]) -> list[AvailableTrain]:
    out = []
    for t in trains:
        if not is_buyable(t.seat_status):
            continue
        if watch.trains and t.train_no not in watch.trains:
            continue
        if watch.time_from and t.departure < watch.time_from:
            continue
        if watch.time_to and t.departure > watch.time_to:
            continue
        out.append(t)
    return out

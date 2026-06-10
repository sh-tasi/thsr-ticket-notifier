from dataclasses import dataclass, field

AVAILABLE = "AVAILABLE"
LIMITED = "LIMITED"
FULL = "FULL"

_BUYABLE = {AVAILABLE, LIMITED}

def is_buyable(status: str) -> bool:
    return status in _BUYABLE

@dataclass
class Watch:
    label: str
    origin_id: str
    destination_id: str
    date: str
    time_from: str | None = None
    time_to: str | None = None
    trains: list[str] = field(default_factory=list)
    seat_class: str = "standard"

@dataclass
class AvailableTrain:
    train_no: str
    departure: str
    arrival: str
    seat_status: str

import yaml
from .models import Watch
from .stations import to_station_id, StationNotFound

class ConfigError(Exception):
    pass

_VALID_CLASSES = {"standard", "business"}

def load_watches(path: str) -> list[Watch]:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    raw_list = data.get("watches")
    if not isinstance(raw_list, list):
        raise ConfigError("watches.yml 缺少 watches 清單")
    return [_parse_one(i, raw) for i, raw in enumerate(raw_list)]

def _parse_one(index: int, raw: dict) -> Watch:
    if not isinstance(raw, dict):
        raise ConfigError(f"第 {index} 筆 watch 格式錯誤")
    for required in ("label", "origin", "destination", "date"):
        if required not in raw:
            raise ConfigError(f"第 {index} 筆缺少必填欄位：{required}")
    try:
        origin_id = to_station_id(str(raw["origin"]))
        destination_id = to_station_id(str(raw["destination"]))
    except StationNotFound as e:
        raise ConfigError(str(e)) from e

    seat_class = str(raw.get("seat_class", "standard"))
    if seat_class not in _VALID_CLASSES:
        raise ConfigError(f"第 {index} 筆 seat_class 須為 standard 或 business，得到：{seat_class}")

    time_from = _opt_str(raw.get("time_from"))
    time_to = _opt_str(raw.get("time_to"))
    if time_from and time_to and time_from > time_to:
        raise ConfigError(f"第 {index} 筆 time_from 不可晚於 time_to")

    trains = [str(t).zfill(4) for t in raw.get("trains", []) or []]

    return Watch(
        label=str(raw["label"]),
        origin_id=origin_id,
        destination_id=destination_id,
        date=str(raw["date"]),
        time_from=time_from,
        time_to=time_to,
        trains=trains,
        seat_class=seat_class,
    )

def _opt_str(v):
    return None if v is None else str(v)

"""高鐵車站名稱 → TDX StationID 對應。"""

class StationNotFound(Exception):
    pass

# TDX THSR 車站代碼
_STATIONS = {
    "南港": "0990",
    "台北": "1000",
    "板橋": "1010",
    "桃園": "1020",
    "新竹": "1030",
    "苗栗": "1035",
    "台中": "1040",
    "彰化": "1043",
    "雲林": "1047",
    "嘉義": "1050",
    "台南": "1060",
    "左營": "1070",
}

def to_station_id(name: str) -> str:
    key = name.strip()
    if key not in _STATIONS:
        raise StationNotFound(f"未知高鐵車站：{name}")
    return _STATIONS[key]

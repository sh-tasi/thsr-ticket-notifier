# 高鐵餘票通知器 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 定時查詢 TDX 高鐵餘位，當符合使用者設定條件的車次有票時，以 Telegram 通知並附 T-EX 導訂連結。

**Architecture:** 純讀取的 Python 程式，跑在 GitHub Actions 排程上。讀 `watches.yml` 取得監控條件，對每筆條件呼叫 TDX 的「每日時刻表」與「餘位」兩支 API，以車次號 join 出「車次＋發車時間＋座位狀態」，篩選時段／車次後判定有票，與 `state.json` 比對只在「沒票→有票」時發 Telegram 通知，最後把 `state.json` commit 回 repo 維持去重。

**Tech Stack:** Python 3.11、`requests`、`PyYAML`、`pytest`、GitHub Actions。TDX OAuth2 client credentials；Telegram Bot API。

---

## 資料流與內部型別（先讀，後面所有 Task 共用）

```
watches.yml ──config──▶ list[Watch]
                         │
        每筆 Watch ──tdx_client──▶ timetable_raw（時刻表）
                   └──tdx_client──▶ seat_raw（餘位）
                         │
           build_trains(timetable_raw, seat_raw, seat_class) ──▶ list[AvailableTrain]
                         │
              matcher.filter_available(watch, trains) ──▶ list[AvailableTrain]（符合時段/車次且有票）
                         │
        state.diff(watch, available) ──▶ 新出現的有票車次（要通知的）
                         │
                 notifier.notify(watch, train) ──▶ Telegram
                         │
                 state.save() ──▶ state.json（commit 回 repo）
```

**內部正規化型別（所有模組以此溝通，與 TDX 原始欄位解耦）：**

- `Watch`：`label:str`, `origin_id:str`, `destination_id:str`, `date:str(YYYY-MM-DD)`, `time_from:str|None('HH:MM')`, `time_to:str|None`, `trains:list[str]`, `seat_class:str('standard'|'business')`
- `AvailableTrain`：`train_no:str`, `departure:str('HH:MM')`, `arrival:str('HH:MM')`, `seat_status:str`

**座位狀態正規化值（字串常數）：** `"AVAILABLE"`（尚有座位）、`"LIMITED"`（座位有限）、`"FULL"`（已售完）。`AVAILABLE` 與 `LIMITED` 視為「有票」。

---

## 檔案結構（先建立心智模型）

```
TRX/
├── watches.yml                         # 使用者監控清單（含一筆範例）
├── state.json                          # 執行期狀態（commit 回寫）；初始 {}
├── requirements.txt
├── pytest.ini
├── README.md
├── .gitignore
├── .github/workflows/check-tickets.yml # 排程 workflow
├── src/thsr_notifier/
│   ├── __init__.py
│   ├── stations.py      # 站名 → TDX StationID 對應
│   ├── models.py        # Watch, AvailableTrain（dataclass）+ 座位狀態常數
│   ├── config.py        # 讀取/驗證 watches.yml → list[Watch]
│   ├── tdx_client.py    # OAuth2 取 token；fetch_timetable / fetch_seat_status
│   ├── parser.py        # build_trains(timetable_raw, seat_raw, seat_class)
│   ├── matcher.py       # filter_available(watch, trains)
│   ├── state.py         # 讀寫 state.json、diff 去重
│   ├── notifier.py      # build_message / build_deeplink / send（Telegram）
│   └── main.py          # 串接流程
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── fixtures/
    │   ├── sample_timetable.json
    │   └── sample_seat.json
    ├── test_stations.py
    ├── test_config.py
    ├── test_parser.py
    ├── test_matcher.py
    ├── test_state.py
    └── test_notifier.py
```

---

### Task 1: 專案骨架

**Files:**
- Create: `requirements.txt`, `pytest.ini`, `.gitignore`, `src/thsr_notifier/__init__.py`, `tests/__init__.py`, `tests/conftest.py`

- [ ] **Step 1: 建立 `requirements.txt`**

```
requests==2.32.3
PyYAML==6.0.2
pytest==8.3.3
```

- [ ] **Step 2: 建立 `pytest.ini`**

```ini
[pytest]
pythonpath = src
testpaths = tests
```

- [ ] **Step 3: 建立 `.gitignore`**

```
__pycache__/
*.pyc
.venv/
.pytest_cache/
.env
```

- [ ] **Step 4: 建立空套件檔**

`src/thsr_notifier/__init__.py` → 空檔
`tests/__init__.py` → 空檔
`tests/conftest.py`：

```python
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"
```

- [ ] **Step 5: 安裝並確認 pytest 可跑**

Run: `python -m pip install -r requirements.txt && python -m pytest -q`
Expected: `no tests ran`（exit code 5，因為還沒有測試）— 表示環境就緒。

- [ ] **Step 6: Commit**

```bash
git add requirements.txt pytest.ini .gitignore src tests
git commit -m "chore: project scaffold"
```

---

### Task 2: 站名對應 `stations.py`

**Files:**
- Create: `src/thsr_notifier/stations.py`
- Test: `tests/test_stations.py`

- [ ] **Step 1: 寫失敗測試**

```python
# tests/test_stations.py
import pytest
from thsr_notifier.stations import to_station_id, StationNotFound

def test_known_station_returns_id():
    assert to_station_id("台北") == "1000"
    assert to_station_id("左營") == "1070"

def test_unknown_station_raises():
    with pytest.raises(StationNotFound):
        to_station_id("不存在站")
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `python -m pytest tests/test_stations.py -q`
Expected: FAIL，`ModuleNotFoundError: thsr_notifier.stations`

- [ ] **Step 3: 實作**

```python
# src/thsr_notifier/stations.py
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
```

- [ ] **Step 4: 跑測試確認通過**

Run: `python -m pytest tests/test_stations.py -q`
Expected: PASS（2 passed）

- [ ] **Step 5: Commit**

```bash
git add src/thsr_notifier/stations.py tests/test_stations.py
git commit -m "feat: station name to TDX id mapping"
```

---

### Task 3: 資料型別 `models.py`

**Files:**
- Create: `src/thsr_notifier/models.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: 寫失敗測試**

```python
# tests/test_models.py
from thsr_notifier.models import Watch, AvailableTrain, AVAILABLE, LIMITED, FULL, is_buyable

def test_watch_defaults():
    w = Watch(label="x", origin_id="1000", destination_id="1070", date="2026-06-20")
    assert w.time_from is None
    assert w.trains == []
    assert w.seat_class == "standard"

def test_is_buyable():
    assert is_buyable(AVAILABLE) is True
    assert is_buyable(LIMITED) is True
    assert is_buyable(FULL) is False
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `python -m pytest tests/test_models.py -q`
Expected: FAIL，`ModuleNotFoundError`

- [ ] **Step 3: 實作**

```python
# src/thsr_notifier/models.py
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
```

- [ ] **Step 4: 跑測試確認通過**

Run: `python -m pytest tests/test_models.py -q`
Expected: PASS（2 passed）

- [ ] **Step 5: Commit**

```bash
git add src/thsr_notifier/models.py tests/test_models.py
git commit -m "feat: core data models"
```

---

### Task 4: 設定載入與驗證 `config.py`

**Files:**
- Create: `src/thsr_notifier/config.py`, `watches.yml`
- Test: `tests/test_config.py`

- [ ] **Step 1: 寫失敗測試**

```python
# tests/test_config.py
import pytest
from thsr_notifier.config import load_watches, ConfigError

def _write(tmp_path, text):
    p = tmp_path / "watches.yml"
    p.write_text(text, encoding="utf-8")
    return str(p)

def test_loads_minimal_watch(tmp_path):
    path = _write(tmp_path, """
watches:
  - label: 回家
    origin: 台北
    destination: 左營
    date: 2026-06-20
""")
    watches = load_watches(path)
    assert len(watches) == 1
    w = watches[0]
    assert w.origin_id == "1000"
    assert w.destination_id == "1070"
    assert w.trains == []
    assert w.seat_class == "standard"

def test_full_watch_fields(tmp_path):
    path = _write(tmp_path, """
watches:
  - label: 上班
    origin: 台北
    destination: 台中
    date: 2026-06-21
    time_from: "18:00"
    time_to: "21:00"
    trains: [641]
    seat_class: business
""")
    w = load_watches(path)[0]
    assert w.time_from == "18:00"
    assert w.time_to == "21:00"
    assert w.trains == ["0641"]      # 正規化為 4 位字串
    assert w.seat_class == "business"

def test_unknown_station_raises(tmp_path):
    path = _write(tmp_path, """
watches:
  - label: 壞站
    origin: 火星
    destination: 左營
    date: 2026-06-20
""")
    with pytest.raises(ConfigError):
        load_watches(path)

def test_bad_seat_class_raises(tmp_path):
    path = _write(tmp_path, """
watches:
  - label: 壞艙
    origin: 台北
    destination: 左營
    date: 2026-06-20
    seat_class: first
""")
    with pytest.raises(ConfigError):
        load_watches(path)

def test_time_from_after_time_to_raises(tmp_path):
    path = _write(tmp_path, """
watches:
  - label: 壞時段
    origin: 台北
    destination: 左營
    date: 2026-06-20
    time_from: "21:00"
    time_to: "18:00"
""")
    with pytest.raises(ConfigError):
        load_watches(path)
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `python -m pytest tests/test_config.py -q`
Expected: FAIL，`ModuleNotFoundError`

- [ ] **Step 3: 實作**

```python
# src/thsr_notifier/config.py
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
```

- [ ] **Step 4: 跑測試確認通過**

Run: `python -m pytest tests/test_config.py -q`
Expected: PASS（5 passed）

- [ ] **Step 5: 建立範例 `watches.yml`（repo 根目錄）**

```yaml
# 監控清單：編輯後 push 即生效
watches:
  - label: "回家範例"
    origin: 台北          # 站名：南港/台北/板橋/桃園/新竹/苗栗/台中/彰化/雲林/嘉義/台南/左營
    destination: 左營
    date: 2026-06-20      # YYYY-MM-DD（須在今天起 27 天內 TDX 才有餘位資料）
    time_from: "18:00"    # 可選；不填=整天
    time_to: "21:00"      # 可選
    trains: []            # 可選；指定車次如 [641]；空=不限
    seat_class: standard  # standard 或 business
```

- [ ] **Step 6: Commit**

```bash
git add src/thsr_notifier/config.py tests/test_config.py watches.yml
git commit -m "feat: load and validate watches.yml"
```

---

### Task 5: TDX 客戶端 `tdx_client.py`（含真實回應抓取）

**Files:**
- Create: `src/thsr_notifier/tdx_client.py`
- Test: `tests/test_tdx_client.py`

> 注意：本 Task 的單元測試以 mock 隔離網路，**不需要**真實金鑰。Step 6 是一次性「抓真實回應」的手動步驟，用來鎖定後續 parser 的 fixture 與正確欄位；需要你已申請的 TDX 金鑰。

- [ ] **Step 1: 寫失敗測試（mock requests）**

```python
# tests/test_tdx_client.py
from unittest.mock import MagicMock, patch
from thsr_notifier.tdx_client import TdxClient

def _resp(json_body, status=200):
    m = MagicMock()
    m.status_code = status
    m.json.return_value = json_body
    m.raise_for_status.return_value = None
    return m

@patch("thsr_notifier.tdx_client.requests.post")
def test_get_token_posts_client_credentials(mock_post):
    mock_post.return_value = _resp({"access_token": "TOKEN123"})
    client = TdxClient("id", "secret")
    token = client._get_token()
    assert token == "TOKEN123"
    args, kwargs = mock_post.call_args
    assert kwargs["data"]["grant_type"] == "client_credentials"
    assert kwargs["data"]["client_id"] == "id"

@patch("thsr_notifier.tdx_client.requests.get")
@patch("thsr_notifier.tdx_client.requests.post")
def test_fetch_seat_status_uses_bearer_and_od(mock_post, mock_get):
    mock_post.return_value = _resp({"access_token": "TOKEN123"})
    mock_get.return_value = _resp([{"x": 1}])
    client = TdxClient("id", "secret")
    out = client.fetch_seat_status("1000", "1070", "2026-06-20")
    assert out == [{"x": 1}]
    args, kwargs = mock_get.call_args
    assert "1000" in args[0] and "1070" in args[0] and "2026-06-20" in args[0]
    assert kwargs["headers"]["authorization"] == "Bearer TOKEN123"
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `python -m pytest tests/test_tdx_client.py -q`
Expected: FAIL，`ModuleNotFoundError`

- [ ] **Step 3: 實作**

```python
# src/thsr_notifier/tdx_client.py
import requests

AUTH_URL = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
BASE = "https://tdx.transportdata.tw/api/basic/v2/Rail/THSR"
TIMEOUT = 20

class TdxClient:
    def __init__(self, client_id: str, client_secret: str):
        self._id = client_id
        self._secret = client_secret
        self._token: str | None = None

    def _get_token(self) -> str:
        if self._token:
            return self._token
        resp = requests.post(
            AUTH_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": self._id,
                "client_secret": self._secret,
            },
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        self._token = resp.json()["access_token"]
        return self._token

    def _get(self, url: str):
        headers = {"authorization": f"Bearer {self._get_token()}"}
        resp = requests.get(url, headers=headers, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json()

    def fetch_timetable(self, origin_id: str, dest_id: str, date: str):
        url = f"{BASE}/DailyTimetable/OD/{origin_id}/to/{dest_id}/TrainDate/{date}?$format=JSON"
        return self._get(url)

    def fetch_seat_status(self, origin_id: str, dest_id: str, date: str):
        url = f"{BASE}/AvailableSeatStatus/Train/OD/{origin_id}/to/{dest_id}/TrainDate/{date}?$format=JSON"
        return self._get(url)
```

- [ ] **Step 4: 跑測試確認通過**

Run: `python -m pytest tests/test_tdx_client.py -q`
Expected: PASS（2 passed）

- [ ] **Step 5: Commit**

```bash
git add src/thsr_notifier/tdx_client.py tests/test_tdx_client.py
git commit -m "feat: TDX OAuth2 client for timetable and seat status"
```

- [ ] **Step 6: 抓真實回應鎖定 fixture（手動，需要 TDX 金鑰）**

建立一次性腳本 `scripts/capture.py`（之後可刪），用你的金鑰抓一筆**今天、台北→左營**的真實回應存到 fixtures：

```python
# scripts/capture.py
import json, os, sys
from datetime import date
sys.path.insert(0, "src")
from thsr_notifier.tdx_client import TdxClient

client = TdxClient(os.environ["TDX_CLIENT_ID"], os.environ["TDX_CLIENT_SECRET"])
today = date.today().isoformat()
tt = client.fetch_timetable("1000", "1070", today)
seat = client.fetch_seat_status("1000", "1070", today)
json.dump(tt, open("tests/fixtures/sample_timetable.json", "w"), ensure_ascii=False, indent=2)
json.dump(seat, open("tests/fixtures/sample_seat.json", "w"), ensure_ascii=False, indent=2)
print("TIMETABLE keys:", list(tt[0].keys()) if tt else "empty")
print("SEAT keys:", list(seat[0].keys()) if seat else "empty")
```

Run（PowerShell）：
```powershell
$env:TDX_CLIENT_ID="<你的id>"; $env:TDX_CLIENT_SECRET="<你的secret>"; python scripts/capture.py
```
Expected: 在 `tests/fixtures/` 產生兩個 JSON，並印出實際欄位名。**記下實際欄位結構**——Task 6 的 parser 須對齊這些真實欄位。若欄位名與 Task 6 假設不同，以真實回應為準調整 parser 與測試。

```bash
git add tests/fixtures/sample_timetable.json tests/fixtures/sample_seat.json
git commit -m "test: capture real TDX timetable and seat fixtures"
```

---

### Task 6: 解析與 join `parser.py`

**Files:**
- Create: `src/thsr_notifier/parser.py`
- Test: `tests/test_parser.py`

> parser 把 TDX 原始回應轉成 `list[AvailableTrain]`。下方測試使用**精簡假資料**（不依賴真實 fixture 的完整內容），結構依 TDX 文件常見形狀。執行 Task 5 Step 6 後，若真實欄位不同，請同步修正 `parser.py` 與此測試的假資料欄位名。

TDX 假設結構（依文件）：
- 時刻表每筆：`{"DailyTrainInfo": {"TrainNo": "0641"}, "OriginStopTime": {"DepartureTime": "18:30"}, "DestinationStopTime": {"ArrivalTime": "20:15"}}`
- 餘位每筆：`{"TrainNo": "0641", "StandardSeatStatus": "尚有座位", "BusinessSeatStatus": "座位有限"}`

- [ ] **Step 1: 寫失敗測試**

```python
# tests/test_parser.py
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
    {"TrainNo": "0641", "StandardSeatStatus": "尚有座位", "BusinessSeatStatus": "已售完"},
    {"TrainNo": "0643", "StandardSeatStatus": "已售完", "BusinessSeatStatus": "座位有限"},
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
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `python -m pytest tests/test_parser.py -q`
Expected: FAIL，`ModuleNotFoundError`

- [ ] **Step 3: 實作**

```python
# src/thsr_notifier/parser.py
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
```

- [ ] **Step 4: 跑測試確認通過**

Run: `python -m pytest tests/test_parser.py -q`
Expected: PASS（3 passed）

- [ ] **Step 5: Commit**

```bash
git add src/thsr_notifier/parser.py tests/test_parser.py
git commit -m "feat: join timetable and seat data into trains"
```

---

### Task 7: 篩選與有票判定 `matcher.py`

**Files:**
- Create: `src/thsr_notifier/matcher.py`
- Test: `tests/test_matcher.py`

- [ ] **Step 1: 寫失敗測試**

```python
# tests/test_matcher.py
from thsr_notifier.matcher import filter_available
from thsr_notifier.models import Watch, AvailableTrain, AVAILABLE, LIMITED, FULL

def _w(**kw):
    base = dict(label="x", origin_id="1000", destination_id="1070", date="2026-06-20")
    base.update(kw)
    return Watch(**base)

TRAINS = [
    AvailableTrain("0641", "18:30", "20:15", AVAILABLE),
    AvailableTrain("0643", "19:00", "20:45", FULL),
    AvailableTrain("0645", "21:30", "23:15", LIMITED),
]

def test_only_buyable_returned():
    out = filter_available(_w(), TRAINS)
    assert {t.train_no for t in out} == {"0641", "0645"}

def test_time_window_filters_by_departure():
    out = filter_available(_w(time_from="18:00", time_to="21:00"), TRAINS)
    assert {t.train_no for t in out} == {"0641"}  # 0645 在 21:30 超出，0643 已售完

def test_specific_trains_filter():
    out = filter_available(_w(trains=["0645"]), TRAINS)
    assert {t.train_no for t in out} == {"0645"}

def test_time_and_train_combined_empty():
    out = filter_available(_w(trains=["0645"], time_from="18:00", time_to="21:00"), TRAINS)
    assert out == []
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `python -m pytest tests/test_matcher.py -q`
Expected: FAIL，`ModuleNotFoundError`

- [ ] **Step 3: 實作**

```python
# src/thsr_notifier/matcher.py
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
```

- [ ] **Step 4: 跑測試確認通過**

Run: `python -m pytest tests/test_matcher.py -q`
Expected: PASS（4 passed）

- [ ] **Step 5: Commit**

```bash
git add src/thsr_notifier/matcher.py tests/test_matcher.py
git commit -m "feat: filter trains by buyability, time window, train no"
```

---

### Task 8: 狀態去重 `state.py`

**Files:**
- Create: `src/thsr_notifier/state.py`
- Test: `tests/test_state.py`

> 去重鍵：`f"{label}|{date}|{origin_id}|{destination_id}|{seat_class}"`。每個 watch 在 state 中存「上次有票的車次號集合」。`diff()` 回傳「這次有、上次沒有」的車次（要通知者），並就地更新狀態為這次的集合。

- [ ] **Step 1: 寫失敗測試**

```python
# tests/test_state.py
import json
from thsr_notifier.state import State
from thsr_notifier.models import Watch, AvailableTrain, AVAILABLE

def _w():
    return Watch(label="回家", origin_id="1000", destination_id="1070",
                 date="2026-06-20", seat_class="standard")

def _t(no):
    return AvailableTrain(no, "18:30", "20:15", AVAILABLE)

def test_first_time_all_new(tmp_path):
    st = State(str(tmp_path / "state.json"))
    new = st.diff(_w(), [_t("0641"), _t("0643")])
    assert {t.train_no for t in new} == {"0641", "0643"}

def test_repeat_not_renotified(tmp_path):
    st = State(str(tmp_path / "state.json"))
    st.diff(_w(), [_t("0641")])
    new = st.diff(_w(), [_t("0641")])
    assert new == []

def test_train_resold_then_available_renotifies(tmp_path):
    st = State(str(tmp_path / "state.json"))
    st.diff(_w(), [_t("0641")])     # 通知過 0641
    st.diff(_w(), [])               # 又售完，集合清空
    new = st.diff(_w(), [_t("0641")])  # 再度有票
    assert {t.train_no for t in new} == {"0641"}

def test_persist_across_instances(tmp_path):
    path = str(tmp_path / "state.json")
    st = State(path)
    st.diff(_w(), [_t("0641")])
    st.save()
    st2 = State(path)
    new = st2.diff(_w(), [_t("0641")])
    assert new == []

def test_missing_file_starts_empty(tmp_path):
    st = State(str(tmp_path / "nope.json"))
    new = st.diff(_w(), [_t("0641")])
    assert {t.train_no for t in new} == {"0641"}
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `python -m pytest tests/test_state.py -q`
Expected: FAIL，`ModuleNotFoundError`

- [ ] **Step 3: 實作**

```python
# src/thsr_notifier/state.py
import json
import os
from .models import Watch, AvailableTrain

class State:
    def __init__(self, path: str):
        self._path = path
        self._data: dict[str, list[str]] = self._load()

    def _load(self) -> dict:
        if not os.path.exists(self._path):
            return {}
        try:
            with open(self._path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def _key(self, w: Watch) -> str:
        return f"{w.label}|{w.date}|{w.origin_id}|{w.destination_id}|{w.seat_class}"

    def diff(self, watch: Watch, available: list[AvailableTrain]) -> list[AvailableTrain]:
        key = self._key(watch)
        previous = set(self._data.get(key, []))
        current = {t.train_no for t in available}
        self._data[key] = sorted(current)
        return [t for t in available if t.train_no not in previous]

    def save(self) -> None:
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2, sort_keys=True)
```

- [ ] **Step 4: 跑測試確認通過**

Run: `python -m pytest tests/test_state.py -q`
Expected: PASS（5 passed）

- [ ] **Step 5: Commit**

```bash
git add src/thsr_notifier/state.py tests/test_state.py
git commit -m "feat: state-based notification dedup"
```

---

### Task 9: 通知 `notifier.py`

**Files:**
- Create: `src/thsr_notifier/notifier.py`
- Test: `tests/test_notifier.py`

> Deep Link：高鐵官方訂票系統入口為 `https://irs.thsrc.com.tw/IMINT/`。本版先以此官方訂票網址作為導訂連結（穩定可用）；待你在 T-EX App 環境實測出可預填行程的 deep link 後，再於 `build_deeplink` 內替換。`build_message` 與 `build_deeplink` 為純函式、可單元測試；`send` 以 mock 隔離網路。

- [ ] **Step 1: 寫失敗測試**

```python
# tests/test_notifier.py
from unittest.mock import MagicMock, patch
from thsr_notifier.notifier import build_message, build_deeplink, Notifier
from thsr_notifier.models import Watch, AvailableTrain, AVAILABLE, LIMITED

def _w():
    return Watch(label="回家", origin_id="1000", destination_id="1070",
                 date="2026-06-20", seat_class="standard")

def test_build_message_contains_key_info():
    t = AvailableTrain("0641", "18:30", "20:15", AVAILABLE)
    msg = build_message(_w(), t)
    assert "回家" in msg
    assert "0641" in msg
    assert "18:30" in msg
    assert "2026-06-20" in msg

def test_build_deeplink_is_url():
    link = build_deeplink(_w(), AvailableTrain("0641", "18:30", "20:15", AVAILABLE))
    assert link.startswith("https://")

@patch("thsr_notifier.notifier.requests.post")
def test_send_calls_telegram(mock_post):
    m = MagicMock(); m.raise_for_status.return_value = None
    mock_post.return_value = m
    n = Notifier(token="TOK", chat_id="123")
    n.send("hello")
    args, kwargs = mock_post.call_args
    assert "TOK" in args[0]
    assert kwargs["data"]["chat_id"] == "123"
    assert kwargs["data"]["text"] == "hello"
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `python -m pytest tests/test_notifier.py -q`
Expected: FAIL，`ModuleNotFoundError`

- [ ] **Step 3: 實作**

```python
# src/thsr_notifier/notifier.py
import requests
from .models import Watch, AvailableTrain

TIMEOUT = 15
BOOKING_URL = "https://irs.thsrc.com.tw/IMINT/"

_STATUS_LABEL = {"AVAILABLE": "尚有座位", "LIMITED": "座位有限", "FULL": "已售完"}

def build_deeplink(watch: Watch, train: AvailableTrain) -> str:
    # TODO(實測後替換)：T-EX App 可預填行程的 deep link。
    # 目前回傳官方訂票系統入口（穩定可用）。
    return BOOKING_URL

def build_message(watch: Watch, train: AvailableTrain) -> str:
    cls = "商務車廂" if watch.seat_class == "business" else "標準車廂"
    status = _STATUS_LABEL.get(train.seat_status, train.seat_status)
    link = build_deeplink(watch, train)
    return (
        f"🎫 有票了！[{watch.label}]\n"
        f"日期：{watch.date}\n"
        f"車次：{train.train_no}　{train.departure} → {train.arrival}\n"
        f"{cls}：{status}\n"
        f"訂票：{link}"
    )

class Notifier:
    def __init__(self, token: str, chat_id: str):
        self._url = f"https://api.telegram.org/bot{token}/sendMessage"
        self._chat_id = chat_id

    def send(self, text: str) -> None:
        resp = requests.post(
            self._url,
            data={"chat_id": self._chat_id, "text": text},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()

    def notify(self, watch: Watch, train: AvailableTrain) -> None:
        self.send(build_message(watch, train))
```

- [ ] **Step 4: 跑測試確認通過**

Run: `python -m pytest tests/test_notifier.py -q`
Expected: PASS（3 passed）

- [ ] **Step 5: Commit**

```bash
git add src/thsr_notifier/notifier.py tests/test_notifier.py
git commit -m "feat: telegram notifier with booking link"
```

---

### Task 10: 主流程 `main.py`

**Files:**
- Create: `src/thsr_notifier/main.py`
- Test: `tests/test_main.py`

> `main()` 從環境變數讀金鑰、串接所有模組，逐筆 watch 處理；單筆出錯記 log 不中斷其他。測試以 mock 注入的 client/notifier 驗證流程，不碰網路。

- [ ] **Step 1: 寫失敗測試**

```python
# tests/test_main.py
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
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `python -m pytest tests/test_main.py -q`
Expected: FAIL，`ModuleNotFoundError`

- [ ] **Step 3: 實作**

```python
# src/thsr_notifier/main.py
import logging
import os
import sys

from .config import load_watches
from .tdx_client import TdxClient
from .parser import build_trains
from .matcher import filter_available
from .state import State
from .notifier import Notifier

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("thsr_notifier")

WATCHES_PATH = "watches.yml"
STATE_PATH = "state.json"

def run(watches, client, notifier, state_path) -> None:
    state = State(state_path)
    for w in watches:
        try:
            timetable = client.fetch_timetable(w.origin_id, w.destination_id, w.date)
            seat = client.fetch_seat_status(w.origin_id, w.destination_id, w.date)
            trains = build_trains(timetable, seat, w.seat_class)
            available = filter_available(w, trains)
            new_trains = state.diff(w, available)
            for t in new_trains:
                notifier.notify(w, t)
                log.info("通知 %s 車次 %s", w.label, t.train_no)
        except Exception:
            log.exception("watch 處理失敗：%s", w.label)
    state.save()

def main() -> int:
    watches = load_watches(WATCHES_PATH)
    client = TdxClient(os.environ["TDX_CLIENT_ID"], os.environ["TDX_CLIENT_SECRET"])
    notifier = Notifier(os.environ["TELEGRAM_BOT_TOKEN"], os.environ["TELEGRAM_CHAT_ID"])
    run(watches, client, notifier, STATE_PATH)
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: 跑測試確認通過**

Run: `python -m pytest tests/test_main.py -q`
Expected: PASS（3 passed）

- [ ] **Step 5: 全套測試確認**

Run: `python -m pytest -q`
Expected: 全部 PASS

- [ ] **Step 6: Commit**

```bash
git add src/thsr_notifier/main.py tests/test_main.py
git commit -m "feat: orchestrate watch processing"
```

---

### Task 11: GitHub Actions 排程、初始狀態檔、README

**Files:**
- Create: `.github/workflows/check-tickets.yml`, `state.json`, `README.md`

- [ ] **Step 1: 建立初始 `state.json`**

```json
{}
```

- [ ] **Step 2: 建立 workflow**

```yaml
# .github/workflows/check-tickets.yml
name: check-tickets
on:
  schedule:
    - cron: "*/15 * * * *"   # 每 15 分鐘（UTC）；未來日期 TDX 一天只刷新 3 次，故已足夠
  workflow_dispatch: {}        # 允許手動觸發測試

permissions:
  contents: write              # 允許 commit 回寫 state.json

concurrency:
  group: check-tickets
  cancel-in-progress: false

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt
      - name: Run checker
        env:
          TDX_CLIENT_ID: ${{ secrets.TDX_CLIENT_ID }}
          TDX_CLIENT_SECRET: ${{ secrets.TDX_CLIENT_SECRET }}
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
        run: python -m thsr_notifier.main
      - name: Commit updated state
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add state.json
          git diff --staged --quiet || git commit -m "chore: update state [skip ci]"
          git push
```

> 注意：`python -m thsr_notifier.main` 需要 `src` 在 import 路徑。在 workflow 加一行讓套件可被找到——在 `run: python -m thsr_notifier.main` 前設定 `PYTHONPATH`：把該 step 的 `run` 改為 `PYTHONPATH=src python -m thsr_notifier.main`。

- [ ] **Step 3: 修正 workflow 的 PYTHONPATH**

把 `Run checker` step 的 `run:` 改為：
```yaml
        run: PYTHONPATH=src python -m thsr_notifier.main
```

- [ ] **Step 4: 建立 `README.md`**

````markdown
# 高鐵餘票通知器

定時查 TDX 高鐵餘位，符合條件就用 Telegram 通知並附訂票連結。

## 設定
1. 申請 TDX 會員，建立 API Key（client id / secret）：https://tdx.transportdata.tw/
2. 用 @BotFather 建立 Telegram Bot，取得 token；對 bot 傳一句話後，
   開 `https://api.telegram.org/bot<token>/getUpdates` 取得你的 chat id。
3. 在 GitHub repo → Settings → Secrets and variables → Actions 新增：
   `TDX_CLIENT_ID`、`TDX_CLIENT_SECRET`、`TELEGRAM_BOT_TOKEN`、`TELEGRAM_CHAT_ID`
4. 編輯 `watches.yml` 設定要監控的條件，push 即生效。

## 本機測試
```bash
pip install -r requirements.txt
pytest -q
PYTHONPATH=src TDX_CLIENT_ID=.. TDX_CLIENT_SECRET=.. \
  TELEGRAM_BOT_TOKEN=.. TELEGRAM_CHAT_ID=.. python -m thsr_notifier.main
```

## 限制
- TDX 餘位資料涵蓋今天起 27 天內；超出範圍的日期不會有資料。
- 未來日期一天只刷新 3 次（10:00/16:00/22:00），非秒級搶票。
- 本工具只通知與導訂，不自動訂票。
````

- [ ] **Step 5: 手動觸發驗證（push 後）**

push 到 GitHub，於 Actions 頁面對 `check-tickets` 按 `Run workflow` 手動觸發，確認：
- job 綠燈通過
- 若當下有符合 watch 的票，Telegram 收到通知
- `state.json` 有被更新 commit

- [ ] **Step 6: Commit**

```bash
git add .github/workflows/check-tickets.yml state.json README.md
git commit -m "ci: scheduled ticket check workflow and docs"
```

---

## 自我檢查（規格對照）

- 規格 §4 監控清單 → Task 4（config + watches.yml）✅
- 規格 §5 元件：config/tdx_client/matcher/state/notifier/main → Task 4/5/7/8/9/10；新增 parser（Task 6）處理時刻表與餘位 join（規劃時發現的細化）✅
- 規格 §6 有票判定與去重 → Task 3（is_buyable）、Task 7（filter）、Task 8（state diff）✅
- 規格 §7 狀態 commit 回寫 → Task 11 workflow ✅
- 規格 §8 通知含 Deep Link → Task 9（build_deeplink，先用官方訂票網址，T-EX deep link 待實測替換）✅
- 規格 §9 技術選型／Secrets → Task 1、Task 11 ✅
- 規格 §10 錯誤處理 → Task 4（設定錯誤）、Task 10（單筆不中斷）、Task 8（state 損毀視為空）✅
- 規格 §11 測試策略 → 各 Task TDD + Task 5 Step 6 真實 fixture ✅

**已知待實測項（非 placeholder，為外部相依不確定性）：**
1. TDX 時刻表／餘位的真實欄位名（Task 5 Step 6 抓取後，必要時校正 Task 6 parser）。
2. T-EX deep link 可預填行程的確切格式（Task 9 先用官方訂票網址，實測後替換 `build_deeplink`）。

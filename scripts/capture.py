"""一次性 TDX 連線煙霧測試 / 抓真實回應。

金鑰來源（擇一）：
  A. 環境變數：在同一個 PowerShell 視窗先設定，再跑本腳本
       $env:TDX_CLIENT_ID="你的id"
       $env:TDX_CLIENT_SECRET="你的secret"
       python scripts/capture.py
  B. .env 檔（推薦，設一次就好）：在專案根目錄建立 .env，內容兩行：
       TDX_CLIENT_ID=你的id
       TDX_CLIENT_SECRET=你的secret
     然後直接：python scripts/capture.py

可選指定起訖與日期：
    python scripts/capture.py 台北 左營 2026-06-13

會把完整回應存到 tests/fixtures/，並印出結構供核對欄位名。（不會印出你的金鑰。）
"""
import json
import os
import sys
from datetime import date

sys.path.insert(0, "src")


def _load_dotenv(path=".env"):
    """極簡 .env 讀取：KEY=VALUE，每行一組。不覆蓋已存在的環境變數。"""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


_load_dotenv()

_required = ["TDX_CLIENT_ID", "TDX_CLIENT_SECRET"]
_missing = [k for k in _required if not os.environ.get(k)]
if _missing:
    print("⚠ 缺少環境變數：" + ", ".join(_missing))
    print("目前偵測狀態（不顯示內容）：")
    for k in _required:
        print(f"  {k} = {'已設定 ✓' if os.environ.get(k) else '未設定 ✗'}")
    print()
    print("解法二選一：")
    print("  A. 同一個 PowerShell 視窗先設定再跑：")
    print('       $env:TDX_CLIENT_ID="你的id"')
    print('       $env:TDX_CLIENT_SECRET="你的secret"')
    print("       python scripts/capture.py")
    print("  B. 在專案根目錄建立 .env 檔（兩行），再跑 python scripts/capture.py：")
    print("       TDX_CLIENT_ID=你的id")
    print("       TDX_CLIENT_SECRET=你的secret")
    sys.exit(1)

from thsr_notifier.tdx_client import TdxClient
from thsr_notifier.stations import to_station_id

origin = sys.argv[1] if len(sys.argv) > 1 else "台北"
dest = sys.argv[2] if len(sys.argv) > 2 else "左營"
day = sys.argv[3] if len(sys.argv) > 3 else date.today().isoformat()

client = TdxClient(os.environ["TDX_CLIENT_ID"], os.environ["TDX_CLIENT_SECRET"])
o, d = to_station_id(origin), to_station_id(dest)
print(f"查詢 {origin}({o}) -> {dest}({d})  日期 {day}")

timetable = client.fetch_timetable(o, d, day)
seat = client.fetch_seat_status(o, d, day)

os.makedirs("tests/fixtures", exist_ok=True)
with open("tests/fixtures/sample_timetable.json", "w", encoding="utf-8") as f:
    json.dump(timetable, f, ensure_ascii=False, indent=2)
with open("tests/fixtures/sample_seat.json", "w", encoding="utf-8") as f:
    json.dump(seat, f, ensure_ascii=False, indent=2)


def show(name, data):
    print(f"\n===== {name} =====")
    length = len(data) if hasattr(data, "__len__") else "n/a"
    print(f"型別: {type(data).__name__}  筆數: {length}")
    first = data[0] if isinstance(data, list) and data else data
    print("第一筆內容：")
    print(json.dumps(first, ensure_ascii=False, indent=2)[:2500])


show("DailyTimetable（時刻表）", timetable)
show("AvailableSeatStatus（餘位）", seat)
print("\n完成。完整回應已存到 tests/fixtures/。")

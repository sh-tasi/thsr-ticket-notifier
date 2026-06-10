"""一次性 TDX 連線煙霧測試 / 抓真實回應。

用法（PowerShell，在專案根目錄）：
    $env:TDX_CLIENT_ID="你的id"; $env:TDX_CLIENT_SECRET="你的secret"; python scripts/capture.py
可選指定起訖與日期：
    python scripts/capture.py 台北 左營 2026-06-11

會把完整回應存到 tests/fixtures/，並印出結構供核對欄位名。
（不會印出你的金鑰。）
"""
import json
import os
import sys
from datetime import date

sys.path.insert(0, "src")
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

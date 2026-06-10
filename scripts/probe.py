"""TDX THSR 端點探測：一次試多個候選網址，回報哪個能通與其結構。

金鑰來源同 capture.py（.env 或環境變數）。
用法：python scripts/probe.py
"""
import json
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, "src")


def _load_dotenv(path=".env"):
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
if not os.environ.get("TDX_CLIENT_ID") or not os.environ.get("TDX_CLIENT_SECRET"):
    print("⚠ 未設定 TDX_CLIENT_ID / TDX_CLIENT_SECRET（用 .env 或 $env 設定）")
    sys.exit(1)

import requests
from thsr_notifier.tdx_client import TdxClient

client = TdxClient(os.environ["TDX_CLIENT_ID"], os.environ["TDX_CLIENT_SECRET"])
token = client._get_token()
print("認證成功，token 取得 ✓")

BASE = "https://tdx.transportdata.tw/api/basic"
o, d = "1000", "1070"            # 台北 -> 左營
today = date.today().isoformat()
soon = (date.today() + timedelta(days=3)).isoformat()

candidates = [
    ("時刻表 T1 無TrainDate(今天)", f"{BASE}/v2/Rail/THSR/DailyTimetable/OD/{o}/to/{d}/{today}"),
    ("時刻表 T1 無TrainDate(+3天)", f"{BASE}/v2/Rail/THSR/DailyTimetable/OD/{o}/to/{d}/{soon}"),
    ("時刻表 T2 有TrainDate(對照)", f"{BASE}/v2/Rail/THSR/DailyTimetable/OD/{o}/to/{d}/TrainDate/{today}"),
    ("餘位 S1 List/Today", f"{BASE}/v2/Rail/THSR/AvailableSeatStatusList/Today"),
    ("餘位 S2 List/TrainDate(今天)", f"{BASE}/v2/Rail/THSR/AvailableSeatStatusList/TrainDate/{today}"),
    ("餘位 S3 List/TrainDate(+3天)", f"{BASE}/v2/Rail/THSR/AvailableSeatStatusList/TrainDate/{soon}"),
    ("餘位 S4 OD無TrainDate(今天)", f"{BASE}/v2/Rail/THSR/AvailableSeatStatus/Train/OD/{o}/to/{d}/{today}"),
    ("餘位 S5 OD有TrainDate(今天)", f"{BASE}/v2/Rail/THSR/AvailableSeatStatus/Train/OD/{o}/to/{d}/TrainDate/{today}"),
    ("餘位 S6 List/Today/Station台北", f"{BASE}/v2/Rail/THSR/AvailableSeatStatusList/Today/Station/{o}"),
]

headers = {"authorization": f"Bearer {token}"}
for label, url in candidates:
    try:
        r = requests.get(url, headers=headers, params={"$format": "JSON"}, timeout=20)
        status = r.status_code
        if status == 200:
            body = r.json()
            n = len(body) if isinstance(body, list) else "(非list)"
            first = body[0] if isinstance(body, list) and body else body
            keys = list(first.keys()) if isinstance(first, dict) else type(first).__name__
            print(f"\n[200 ✓] {label}")
            print(f"    筆數: {n}")
            print(f"    第一筆 keys: {keys}")
            snippet = json.dumps(first, ensure_ascii=False)[:600]
            print(f"    第一筆: {snippet}")
        else:
            print(f"[{status}] {label}")
    except Exception as e:
        print(f"[ERR] {label} -> {e}")

print("\n探測完成。把上面整段貼回給我。")

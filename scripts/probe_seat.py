"""TDX THSR 餘位端點慢速探測（避開 429 限流）。

每次請求間隔數秒，遇 429 再退避重試。金鑰來源同 capture.py（.env 或環境變數）。
用法：python scripts/probe_seat.py
"""
import json
import os
import sys
import time
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
    print("⚠ 未設定 TDX_CLIENT_ID / TDX_CLIENT_SECRET")
    sys.exit(1)

import requests
from thsr_notifier.tdx_client import TdxClient

client = TdxClient(os.environ["TDX_CLIENT_ID"], os.environ["TDX_CLIENT_SECRET"])
token = client._get_token()
print("認證成功 ✓")

BASE = "https://tdx.transportdata.tw/api/basic"
o, d = "1000", "1070"            # 台北 -> 左營
today = date.today().isoformat()
soon = (date.today() + timedelta(days=3)).isoformat()
headers = {"authorization": f"Bearer {token}"}

candidates = [
    ("S1 List/Today（全線今天）", f"{BASE}/v2/Rail/THSR/AvailableSeatStatusList/Today"),
    ("S4 OD無TrainDate(今天)", f"{BASE}/v2/Rail/THSR/AvailableSeatStatus/Train/OD/{o}/to/{d}/{today}"),
    ("S4b OD無TrainDate(+3天)", f"{BASE}/v2/Rail/THSR/AvailableSeatStatus/Train/OD/{o}/to/{d}/{soon}"),
    ("S5 OD有TrainDate(今天)", f"{BASE}/v2/Rail/THSR/AvailableSeatStatus/Train/OD/{o}/to/{d}/TrainDate/{today}"),
]


def get(url):
    for attempt in range(3):
        r = requests.get(url, headers=headers, params={"$format": "JSON"}, timeout=20)
        if r.status_code == 429:
            print(f"    (429 限流，等 12 秒重試…)")
            time.sleep(12)
            continue
        return r
    return r


for i, (label, url) in enumerate(candidates):
    if i > 0:
        time.sleep(6)            # 每次請求間隔，避開限流
    r = get(url)
    if r.status_code != 200:
        print(f"[{r.status_code}] {label}")
        continue
    body = r.json()
    print(f"\n[200 ✓] {label}")
    if isinstance(body, list):
        print(f"    型別: list  筆數: {len(body)}")
        first = body[0] if body else None
    else:
        print(f"    型別: dict  keys: {list(body.keys())}")
        first = body
    if first is not None:
        print("    內容片段：")
        print("    " + json.dumps(first, ensure_ascii=False, indent=2)[:1500].replace("\n", "\n    "))

print("\n探測完成。把整段貼回給我。")

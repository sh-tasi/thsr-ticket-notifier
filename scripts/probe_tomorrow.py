"""查「明天」台北->左營餘位，試 OD 端點兩種寫法，印完整結構。

金鑰來源同 capture.py（.env 或環境變數）。用法：python scripts/probe_tomorrow.py
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
tomorrow = (date.today() + timedelta(days=1)).isoformat()
headers = {"authorization": f"Bearer {token}"}
print(f"查詢日期：{tomorrow}（明天）  台北 -> 左營\n")

candidates = [
    ("OD 無TrainDate", f"{BASE}/v2/Rail/THSR/AvailableSeatStatus/Train/OD/{o}/to/{d}/{tomorrow}"),
    ("OD 有TrainDate", f"{BASE}/v2/Rail/THSR/AvailableSeatStatus/Train/OD/{o}/to/{d}/TrainDate/{tomorrow}"),
]

for i, (label, url) in enumerate(candidates):
    if i > 0:
        time.sleep(6)
    r = requests.get(url, headers=headers, params={"$format": "JSON"}, timeout=20)
    print(f"===== {label} -> HTTP {r.status_code} =====")
    if r.status_code != 200:
        print(url)
        continue
    body = r.json()
    if isinstance(body, list):
        print(f"型別: list  筆數: {len(body)}")
        sample = body[:2]
    else:
        print(f"型別: dict  keys: {list(body.keys())}")
        sample = body
    print(json.dumps(sample, ensure_ascii=False, indent=2)[:2500])
    print()

print("探測完成。把整段貼回給我。")

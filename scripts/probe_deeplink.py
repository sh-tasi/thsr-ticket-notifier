"""探測 TDX 高鐵導訂 Deep Link API（Direct 跳 T-EX / Web 跳官網）。

會先抓明天一班真實車次，再去要 deep link，印出 HTTP 狀態與回傳內容。
金鑰來源同 capture.py（.env 或環境變數）。用法：python scripts/probe_deeplink.py
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
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()
if not os.environ.get("TDX_CLIENT_ID") or not os.environ.get("TDX_CLIENT_SECRET"):
    print("⚠ 未設定 TDX_CLIENT_ID / TDX_CLIENT_SECRET")
    sys.exit(1)

import requests
from thsr_notifier.tdx_client import TdxClient

client = TdxClient(os.environ["TDX_CLIENT_ID"], os.environ["TDX_CLIENT_SECRET"])
token = client._get_token()
print("認證成功 ✓")
headers = {"authorization": f"Bearer {token}"}

# 1) 抓明天一班真實車次（台北->左營）
tomorrow = (date.today() + timedelta(days=1)).isoformat()
tt = client.fetch_timetable("1000", "1070", tomorrow)
if not tt:
    print("明天沒有時刻表資料，換個日期再試")
    sys.exit(1)
row = tt[0]
train_no = str(row["DailyTrainInfo"]["TrainNo"])
train_time = row["OriginStopTime"]["DepartureTime"]
print(f"取用車次：{train_no}  {train_time}  日期 {tomorrow}  台北->左營\n")

MAAS = "https://tdx.transportdata.tw/api/maas-thsr"


def call(label, url, params):
    print(f"===== {label} =====")
    print(f"GET {url}")
    print(f"params={params}")
    try:
        r = requests.get(url, headers=headers, params=params, timeout=20)
        print(f"HTTP {r.status_code}")
        body = r.text
        print(body[:1200])
    except Exception as e:
        print(f"ERR: {e}")
    print()


# 2) Direct（跳 T-EX App）— 車次號試「4位」與「去前導零」兩種
call(
    "Direct(4位車次)",
    f"{MAAS}/booking/deeplink/direct/hsr",
    {"start_station": "台北", "end_station": "左營",
     "train_date": tomorrow, "train_time": train_time, "train_number": train_no},
)
time.sleep(4)
call(
    "Direct(去前導零車次)",
    f"{MAAS}/booking/deeplink/direct/hsr",
    {"start_station": "台北", "end_station": "左營",
     "train_date": tomorrow, "train_time": train_time, "train_number": str(int(train_no))},
)
time.sleep(4)

# 3) Web（跳官網訂票）— 帶票種/車廂/票數
call(
    "Web(官網)",
    f"{MAAS}/booking/deeplink/web/hsr",
    {"ticket_type": "S", "carriage_type": "Y",
     "adult_ticket": 1, "children_ticket": 0, "disabled_ticket": 0,
     "senior_ticket": 0, "student_ticket": 0,
     "start_station": "台北", "end_station": "左營",
     "departure_date": tomorrow.replace("-", ""), "departure_number": train_no},
)

print("探測完成。把整段貼回給我（若有回傳網址，等下我們在手機點點看會不會開 T-EX）。")

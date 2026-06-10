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

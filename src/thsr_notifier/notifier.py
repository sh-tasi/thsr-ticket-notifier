import requests
from .models import Watch, AvailableTrain

TIMEOUT = 15
BOOKING_URL = "https://irs.thsrc.com.tw/IMINT/"

_STATUS_LABEL = {"AVAILABLE": "尚有座位", "LIMITED": "座位有限", "FULL": "已售完"}

def build_deeplink(watch: Watch, train: AvailableTrain) -> str:
    # TODO(取得 TDX 導訂權限後替換)：T-EX App 可預填特定車次的 deep link。
    # 目前回傳官方訂票系統入口（穩定可用）。
    return BOOKING_URL

def build_digest(watch: Watch, trains: list[AvailableTrain]) -> str:
    """一筆 watch 的多班有票車次彙整成一則訊息。"""
    cls = "商務車廂" if watch.seat_class == "business" else "標準車廂"
    link = build_deeplink(watch, trains[0])
    header = f"🎫 有票了！[{watch.label}]　{watch.date}　{cls}"
    rows = []
    for t in trains:
        status = _STATUS_LABEL.get(t.seat_status, t.seat_status)
        rows.append(f"・{t.train_no}　{t.departure} → {t.arrival}　{status}")
    return "\n".join([header, *rows, f"訂票：{link}"])

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

    def notify_many(self, watch: Watch, trains: list[AvailableTrain]) -> None:
        """多班車只發一則訊息。"""
        self.send(build_digest(watch, trains))

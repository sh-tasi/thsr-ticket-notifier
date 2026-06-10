import datetime
import logging
import os
import sys

from .config import load_watches
from .tdx_client import TdxClient
from .parser import build_trains
from .matcher import filter_available
from .state import State
from .notifier import Notifier
from .dates import is_in_window
from .dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("thsr_notifier")

WATCHES_PATH = "watches.yml"
STATE_PATH = "state.json"

def run(watches, client, notifier, state_path, today=None) -> None:
    if today is None:
        today = datetime.date.today()
    state = State(state_path)
    for w in watches:
        try:
            if not is_in_window(w.date, today):
                log.info("跳過（日期超出 TDX 範圍或已過期）：%s %s", w.label, w.date)
                continue
            timetable = client.fetch_timetable(w.origin_id, w.destination_id, w.date)
            seat = client.fetch_seat_status(w.origin_id, w.destination_id, w.date)
            trains = build_trains(timetable, seat, w.seat_class)
            available = filter_available(w, trains)
            available_nos = {t.train_no for t in available}
            previous = state.previously_notified(w)
            new_trains = [t for t in available if t.train_no not in previous]
            notified_ok = set()
            if new_trains:
                try:
                    notifier.notify_many(w, new_trains)
                    notified_ok = {t.train_no for t in new_trains}
                    log.info("通知 %s：%d 班有票（%s）", w.label, len(new_trains),
                             ", ".join(t.train_no for t in new_trains))
                except Exception:
                    log.exception("通知失敗 %s（%d 班，下輪重試）", w.label, len(new_trains))
            # 只記錄「仍有票且先前已通知」+「本輪成功通知」；通知失敗者不入庫，下輪可重試
            state.set_notified(w, (available_nos & previous) | notified_ok)
        except Exception:
            log.exception("watch 處理失敗：%s", w.label)
    state.save()

def main() -> int:
    load_dotenv()  # 本機有 .env 就載入；CI 無 .env 為 no-op，用 Secrets
    watches = load_watches(WATCHES_PATH)
    client = TdxClient(os.environ["TDX_CLIENT_ID"], os.environ["TDX_CLIENT_SECRET"])
    notifier = Notifier(os.environ["TELEGRAM_BOT_TOKEN"], os.environ["TELEGRAM_CHAT_ID"])
    run(watches, client, notifier, STATE_PATH)
    return 0

if __name__ == "__main__":
    sys.exit(main())

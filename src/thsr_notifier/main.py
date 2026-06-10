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
            notified_ok = set()
            for t in available:
                if t.train_no in previous:
                    continue
                try:
                    notifier.notify(w, t)
                    notified_ok.add(t.train_no)
                    log.info("通知 %s 車次 %s", w.label, t.train_no)
                except Exception:
                    log.exception("通知失敗 %s 車次 %s", w.label, t.train_no)
            # 只記錄「仍有票且先前已通知」+「本輪成功通知」；通知失敗者不入庫，下輪可重試
            state.set_notified(w, (available_nos & previous) | notified_ok)
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

import logging
import os
import sys

from .config import load_watches
from .tdx_client import TdxClient
from .parser import build_trains
from .matcher import filter_available
from .state import State
from .notifier import Notifier

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("thsr_notifier")

WATCHES_PATH = "watches.yml"
STATE_PATH = "state.json"

def run(watches, client, notifier, state_path) -> None:
    state = State(state_path)
    for w in watches:
        try:
            timetable = client.fetch_timetable(w.origin_id, w.destination_id, w.date)
            seat = client.fetch_seat_status(w.origin_id, w.destination_id, w.date)
            trains = build_trains(timetable, seat, w.seat_class)
            available = filter_available(w, trains)
            new_trains = state.diff(w, available)
            for t in new_trains:
                notifier.notify(w, t)
                log.info("通知 %s 車次 %s", w.label, t.train_no)
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

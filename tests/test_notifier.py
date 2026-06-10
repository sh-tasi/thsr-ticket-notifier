from unittest.mock import MagicMock, patch
from thsr_notifier.notifier import build_message, build_deeplink, Notifier
from thsr_notifier.models import Watch, AvailableTrain, AVAILABLE, LIMITED

def _w():
    return Watch(label="回家", origin_id="1000", destination_id="1070",
                 date="2026-06-20", seat_class="standard")

def test_build_message_contains_key_info():
    t = AvailableTrain("0641", "18:30", "20:15", AVAILABLE)
    msg = build_message(_w(), t)
    assert "回家" in msg
    assert "0641" in msg
    assert "18:30" in msg
    assert "2026-06-20" in msg

def test_build_deeplink_is_url():
    link = build_deeplink(_w(), AvailableTrain("0641", "18:30", "20:15", AVAILABLE))
    assert link.startswith("https://")

@patch("thsr_notifier.notifier.requests.post")
def test_send_calls_telegram(mock_post):
    m = MagicMock(); m.raise_for_status.return_value = None
    mock_post.return_value = m
    n = Notifier(token="TOK", chat_id="123")
    n.send("hello")
    args, kwargs = mock_post.call_args
    assert "TOK" in args[0]
    assert kwargs["data"]["chat_id"] == "123"
    assert kwargs["data"]["text"] == "hello"

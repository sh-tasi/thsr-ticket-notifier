from unittest.mock import MagicMock, patch
from thsr_notifier.tdx_client import TdxClient

def _resp(json_body, status=200):
    m = MagicMock()
    m.status_code = status
    m.json.return_value = json_body
    m.raise_for_status.return_value = None
    return m

@patch("thsr_notifier.tdx_client.requests.post")
def test_get_token_posts_client_credentials(mock_post):
    mock_post.return_value = _resp({"access_token": "TOKEN123"})
    client = TdxClient("id", "secret")
    token = client._get_token()
    assert token == "TOKEN123"
    args, kwargs = mock_post.call_args
    assert kwargs["data"]["grant_type"] == "client_credentials"
    assert kwargs["data"]["client_id"] == "id"

@patch("thsr_notifier.tdx_client.requests.get")
@patch("thsr_notifier.tdx_client.requests.post")
def test_fetch_seat_status_extracts_available_seats(mock_post, mock_get):
    mock_post.return_value = _resp({"access_token": "TOKEN123"})
    # 真實餘位回傳是 dict，車次清單在 AvailableSeats
    mock_get.return_value = _resp({"TrainDate": "2026-06-20", "AvailableSeats": [{"TrainNo": "0641"}]})
    client = TdxClient("id", "secret")
    out = client.fetch_seat_status("1000", "1070", "2026-06-20")
    assert out == [{"TrainNo": "0641"}]
    args, kwargs = mock_get.call_args
    assert "1000" in args[0] and "1070" in args[0] and "2026-06-20" in args[0]
    assert kwargs["headers"]["authorization"] == "Bearer TOKEN123"


@patch("thsr_notifier.tdx_client.requests.get")
@patch("thsr_notifier.tdx_client.requests.post")
def test_fetch_timetable_od_has_no_traindate_segment(mock_post, mock_get):
    mock_post.return_value = _resp({"access_token": "TOKEN123"})
    mock_get.return_value = _resp([{"DailyTrainInfo": {"TrainNo": "0641"}}])
    client = TdxClient("id", "secret")
    out = client.fetch_timetable("1000", "1070", "2026-06-20")
    assert out == [{"DailyTrainInfo": {"TrainNo": "0641"}}]
    url = mock_get.call_args[0][0]
    assert "/DailyTimetable/OD/1000/to/1070/2026-06-20" in url
    assert "TrainDate" not in url  # 時刻表 OD 不帶 TrainDate 字段

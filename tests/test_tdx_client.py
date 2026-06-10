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
def test_fetch_seat_status_uses_bearer_and_od(mock_post, mock_get):
    mock_post.return_value = _resp({"access_token": "TOKEN123"})
    mock_get.return_value = _resp([{"x": 1}])
    client = TdxClient("id", "secret")
    out = client.fetch_seat_status("1000", "1070", "2026-06-20")
    assert out == [{"x": 1}]
    args, kwargs = mock_get.call_args
    assert "1000" in args[0] and "1070" in args[0] and "2026-06-20" in args[0]
    assert kwargs["headers"]["authorization"] == "Bearer TOKEN123"

import requests

AUTH_URL = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
BASE = "https://tdx.transportdata.tw/api/basic/v2/Rail/THSR"
TIMEOUT = 20

class TdxClient:
    def __init__(self, client_id: str, client_secret: str):
        self._id = client_id
        self._secret = client_secret
        self._token: str | None = None

    def _get_token(self) -> str:
        if self._token:
            return self._token
        resp = requests.post(
            AUTH_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": self._id,
                "client_secret": self._secret,
            },
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        self._token = resp.json()["access_token"]
        return self._token

    def _get(self, url: str):
        headers = {"authorization": f"Bearer {self._get_token()}"}
        resp = requests.get(url, headers=headers, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json()

    def fetch_timetable(self, origin_id: str, dest_id: str, date: str):
        url = f"{BASE}/DailyTimetable/OD/{origin_id}/to/{dest_id}/TrainDate/{date}?$format=JSON"
        return self._get(url)

    def fetch_seat_status(self, origin_id: str, dest_id: str, date: str):
        url = f"{BASE}/AvailableSeatStatus/Train/OD/{origin_id}/to/{dest_id}/TrainDate/{date}?$format=JSON"
        return self._get(url)

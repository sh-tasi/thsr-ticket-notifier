from datetime import date, timedelta

def is_in_window(date_str: str, today: date, horizon_days: int = 27) -> bool:
    """TDX 餘位資料涵蓋今天起 horizon_days 天內；超出或已過期回傳 False。"""
    try:
        d = date.fromisoformat(date_str)
    except ValueError:
        return False
    return today <= d <= today + timedelta(days=horizon_days)

"""極簡 .env 載入：本機測試方便用；CI 沒有 .env 時為 no-op。

不覆蓋既有環境變數（GitHub Actions 的 Secrets 優先）。
"""
import os


def load_dotenv(path: str = ".env") -> None:
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))

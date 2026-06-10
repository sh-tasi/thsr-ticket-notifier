# 高鐵餘票通知器

定時查 TDX 高鐵餘位，符合條件就用 Telegram 通知並附訂票連結。

## 設定
1. 申請 TDX 會員，建立 API Key（client id / secret）：https://tdx.transportdata.tw/
2. 用 @BotFather 建立 Telegram Bot，取得 token；對 bot 傳一句話後，
   開 `https://api.telegram.org/bot<token>/getUpdates` 取得你的 chat id。
3. 在 GitHub repo → Settings → Secrets and variables → Actions 新增：
   `TDX_CLIENT_ID`、`TDX_CLIENT_SECRET`、`TELEGRAM_BOT_TOKEN`、`TELEGRAM_CHAT_ID`
4. 編輯 `watches.yml` 設定要監控的條件，push 即生效。

## 本機測試
```bash
pip install -r requirements.txt
pytest -q
```
跑實際查詢：在專案根目錄建立 `.env`（4 行 `TDX_CLIENT_ID`/`TDX_CLIENT_SECRET`/`TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID`），然後：
```bash
python run.py
```
`.env` 已被 `.gitignore` 排除，不會上傳；CI 上沒有 `.env`，改用 GitHub Secrets。

## 限制
- TDX 餘位資料涵蓋今天起 27 天內；超出範圍的日期不會有資料。
- 未來日期一天只刷新 3 次（10:00/16:00/22:00），非秒級搶票。
- 本工具只通知與導訂，不自動訂票。

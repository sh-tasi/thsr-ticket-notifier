# 高鐵餘票通知器 — 設計規格

- 日期：2026-06-10
- 狀態：已核可，待寫實作計畫

## 1. 目標與範圍

讓使用者設定「想搭的高鐵條件」（起訖站、日期、可選時段、可選車次），程式定時查詢 TDX 高鐵餘位資料，當符合條件的車次「有票可買」時，透過 Telegram 通知使用者，並在通知中附上 T-EX 行動購票 App 的 Deep Link，讓使用者一鍵跳轉至官方 App／官網完成訂票與付款。

### 範圍內
- 讀取 TDX 高鐵餘位 API，判定餘票狀態
- 依使用者設定的條件比對
- 狀態變化時發 Telegram 通知（含 Deep Link 導訂）
- 以設定檔管理監控清單
- 跑在 GitHub Actions 排程上

### 範圍外（明確不做）
- **自動訂票／付款**。TDX 為唯讀開放資料，無訂票 API；高鐵官網訂票有圖形驗證碼且服務條款禁止自動化程式訂票。本專案只做「通知 + Deep Link 導訂」，實際下單由使用者在官方 App 內手動完成。
- 在 Telegram 聊天室裡互動式新增／管理監控（需 24 小時常駐伺服器，與免費排程架構衝突）。本版以設定檔管理。

## 2. 關鍵外部限制（來自 TDX / 高鐵）

| 項目 | 內容 |
|------|------|
| 餘位資料涵蓋範圍 | 今天 ~ 未來 27 天（D ~ D+27） |
| 當天（D）更新頻率 | 每 10 分鐘 |
| 未來日期（D+1~D+27）更新頻率 | 每天 3 次：10:00、16:00、22:00 |
| 座位狀態值 | 尚有座位 / 座位有限 / 已售完（標準車廂、商務車廂分別回傳） |
| 高鐵預售窗口 | 發車前 29 天 ~ 發車前約 1 小時 |

**設計意涵**：
- 這不是「秒級搶票」工具。監控未來日期時，狀態一天只可能在 3 個刷新時點變化，通知會在變化後的下一次查詢送出。
- TDX 餘位涵蓋到 D+27，比預售窗口（D+29）短。若監控日期超過 D+27，視為「資料尚未涵蓋」，程式跳過並可在日後自動納入監控。

來源：
- 雙鐵 API 資料使用注意事項 — https://motc-ptx.gitbook.io/tdx-zi-liao-shi-yong-kui-hua-bao-dian/data_notice/public_transportation_data/rail_data
- 高鐵線上訂票說明 — https://en.thsrc.com.tw/ArticleContent/906de59a-8ea0-425a-8055-ca3afded9a3e

## 3. 整體流程

```
GitHub Actions 排程觸發（cron 約每 15 分鐘）
  → 讀取並驗證 watches.yml
  → 對每筆 watch：
      → 呼叫 TDX 高鐵餘位 API（OD + 日期）
      → matcher：依時段 / 車次篩選，判定哪些車「有票」
  → 讀取 state.json，與上次狀態比對
  → 對「從沒票 → 有票」的 watch 發 Telegram 通知（含 Deep Link）
  → 將新狀態寫回 state.json 並 commit 回 repo
```

## 4. 監控清單設定檔 `watches.yml`

使用者編輯此檔並 push 即生效。

```yaml
watches:
  - label: "回家"            # 通知顯示用名稱
    origin: 台北             # 起站（站名，程式內轉為 TDX StationID）
    destination: 左營        # 訖站
    date: 2026-06-20         # 搭乘日期 YYYY-MM-DD
    time_from: "18:00"       # 可選；不填 = 整天
    time_to:   "21:00"       # 可選
    trains: []               # 可選；指定車次如 [0641]；空陣列 = 不限車次
    seat_class: standard     # standard（標準車廂）/ business（商務車廂）
```

行為：
- 不填 `trains`、填時段 → 監控該時段任一班次（主要情境）
- 填 `trains` → 只監控指定車次（時段可一併留空）
- `date` 已過期或超出 D+27 → 該輪跳過該 watch

驗證規則：
- `origin`、`destination`、`date` 為必填；站名須能對應到合法 TDX 高鐵車站
- `time_from` < `time_to`（若兩者皆有）
- `seat_class` 限 `standard` 或 `business`
- 驗證失敗 → 記錄錯誤並跳過該筆，不中斷整體執行

## 5. 元件拆解

每個元件單一職責、介面清楚、可獨立測試。

| 元件 | 職責 | 主要輸入 → 輸出 |
|------|------|----------------|
| `config` | 讀取與驗證 `watches.yml`；站名 → StationID 對應 | 檔案 → `list[Watch]` |
| `tdx_client` | TDX OAuth2 取得 token；呼叫餘位 API（純讀，含重試／逾時處理） | (OD, date) → 原始車次餘位資料 |
| `matcher` | 依日期／時段／車次篩選；依座位狀態判定「有票」 | (Watch, 餘位資料) → `list[AvailableTrain]` |
| `state` | 讀寫 `state.json`，提供「上次是否已通知」查詢與更新 | watch key → 上次狀態 |
| `notifier` | 組訊息文字 + Deep Link；呼叫 Telegram Bot API 發送 | (Watch, AvailableTrain) → 已發送 |
| `main` | 串接整個流程、彙整 log | — |

### 資料模型（概念）
- `Watch`：label, origin_id, destination_id, date, time_from?, time_to?, trains[], seat_class
- `AvailableTrain`：train_no, departure_time, arrival_time, seat_status
- `state.json`：以 watch 唯一鍵對應「上次符合且有票的車次集合」

## 6. 「有票」判定與通知去重

**有票判定**：
- 座位狀態為「尚有座位」或「座位有限」皆視為可買；僅「已售完」視為沒票。

**去重規則**：
- 每筆 watch 記錄「上次有票的車次集合」。
- 當本輪出現「上次沒有、這次有票」的車次時，發送通知（一次）。
- 狀態維持有票時不重複通知（避免洗版）。
- 若某車次又售完、之後再度有票，會再次通知。

## 7. 狀態保存

GitHub Actions 為無狀態執行環境。每輪跑完，由 workflow 以 bot 身分將更新後的 `state.json` commit 回 repo（專用 commit 訊息，例如 `chore: update state`），下一輪讀取以維持去重判斷。接受少量自動 commit 作為代價，換取最單純可靠的狀態保存。

## 8. 通知內容（Telegram）

訊息至少包含：
- watch 的 `label`
- 路線（起 → 訖）、日期
- 有票車次：車次號、出發／抵達時間、座位狀態（尚有座位／座位有限）
- **T-EX Deep Link**：將此筆行程（起訖、日期、車次）帶入官方 App／官網訂票頁的連結

> Deep Link 確切格式於實作階段查 TDX 文件並實測確認（可能為「帶參數開啟 T-EX App」或「導向官網訂票頁並預填」），以實際可用者為準。

## 9. 技術選型

- 語言：Python
- 執行：GitHub Actions 排程（`cron`，約每 15 分鐘一次）
- 設定來源：repo 內 `watches.yml`
- 狀態：repo 內 `state.json`（每輪 commit 回寫）

### 需要的 GitHub Secrets
- `TDX_CLIENT_ID`
- `TDX_CLIENT_SECRET`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

## 10. 錯誤處理原則

- TDX API 逾時／失敗：重試數次後該輪略過該 watch，記 log，不影響其他 watch。
- 單筆 watch 設定錯誤：跳過該筆並記錄，不中斷整體。
- Telegram 發送失敗：記 log；不更新該筆 state，使下一輪可重試通知。
- state.json 不存在或損毀：視為空狀態重新建立（後果是可能重發一次通知，可接受）。

## 11. 測試策略

- `config`、`matcher`、`state`、`notifier`（訊息組裝部分）以單元測試覆蓋，TDX 與 Telegram 的網路呼叫以假資料／mock 隔離。
- 提供一筆樣本 TDX 餘位回應作為測試固定資料，驗證 matcher 的時段／車次／座位狀態判定。
- 端對端在實作後以一筆真實 watch 手動驗證（取得 TDX token、收到 Telegram 通知）。

## 12. 後續可能擴充（非本版）

- Telegram 指令式管理監控（需常駐服務）
- 自動訂票（須完全理解驗證碼與條款風險後另案評估）
- 多使用者 / 多 chat 通知

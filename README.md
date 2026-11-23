# 青年百億申請幫手

在你自己的 Claude Code 或 Codex 裡，完成「青年百億海外圓夢基金計畫」海外翱翔組的申請準備：找適合的計畫、接受訪談、撰寫申請書、模擬評審，最後輸出符合簡章格式的 Word 檔。

這個專案沒有網站，也沒有伺服器。它是一包知識庫、工作流程說明和幾個小腳本，讓你的 AI 助理知道該怎麼幫你。你的資料只留在自己的電腦和你使用的 AI 服務裡。

> 本專案不是官方工具，與教育部青年發展署沒有隸屬關係。計畫的資格、日期、名額與經費以[官網](https://twpathfinder.yda.gov.tw)最新公告為準。AI 產生的內容可能有錯，也不保證錄取，送出前請自己核對每一項事實。

## 它能做什麼

| 你說 | AI 助理會做的事 |
|---|---|
| 「幫我找計畫」 | 依你的年齡、背景與興趣，從 155 個計畫中挑出 5 到 8 個，說明為什麼適合、能補足你什麼、要留意什麼 |
| 「訪談我」 | 讀完簡章和你的資料後，問出申請書還缺的內容 |
| 「開始寫」 | 分五章撰寫初稿。只用你提供的事實，缺的地方標成【待補】 |
| 「模擬評審」 | 依官方書審比重 40／20／40 打分，指出最該先改的地方 |
| 「產生 Word」 | 把章節和照片排成 A4、標楷體、固定行高 24 點、含封面與目錄的 Word 檔 |
| 其他問題 | 計畫內容、時程、面試、每一章怎麼寫 |

成品長什麼樣，可以看 [examples/林語晴](examples/林語晴)。那是一位虛構申請者的完整示範，包含背景、訪談紀錄、五章草稿和輸出的 Word 檔。

## 開始使用

需要：Python 3.10 以上，以及 Claude Code 或 Codex。

```bash
git clone https://github.com/WayneChen983/twpathfinder-helper.git
cd twpathfinder-helper
```

在這個資料夾裡啟動你的 AI 助理，然後說：

```
開始
```

助理會幫你安裝需要的套件、建立你的背景資料，再帶你一步一步往下走。你不需要自己打任何指令。

Claude Code 另有斜線指令：`/pf-setup`、`/pf-match`、`/pf-interview`、`/pf-write`、`/pf-review`、`/pf-export`。Codex 會讀 `AGENTS.md`，直接用上面表格裡的說法即可。

## 你的資料放哪裡

所有個人資料都放在 `my/` 資料夾，這個資料夾已列入 `.gitignore`，不會被提交。

```
my/
  profile.md        你的背景
  materials/        履歷、自傳等文件
  photos/           要放進申請書的照片
  M-2-1/            每個計畫一個資料夾：訪談紀錄、五章草稿、評審結果、Word 檔
```

幾件事請留意：

- 你的資料會傳送到你所使用的 AI 服務處理。請不要放身分證、護照、存摺這類文件。
- 文件會先經過 `scripts/extract_text.py`，自動遮蔽身分證字號、電話、Email、信用卡號。遮蔽是規則比對，不保證完整。
- 照片中有其他人時請先取得同意。證書上有身分證字號或生日時請先遮住。
- 如果你把這個專案 fork 成公開的 repo，確認 `my/` 沒有被提交。

## 專案結構

| 路徑 | 內容 |
|---|---|
| `AGENTS.md`、`CLAUDE.md` | 給 AI 助理的總說明 |
| `workflows/` | 每個步驟的做法 |
| `knowledge/` | 寫作指南、錄取範例拆解、常見問題、時程與面試 |
| `data/kb/` | 155 個計畫的索引與簡章全文（取自官網，116 年度第一梯次） |
| `scripts/` | 篩選計畫、擷取文字、檢查草稿、產生 Word、更新計畫資料 |
| `examples/` | 虛構申請者的完整示範 |
| `docs/`、`form-backend/` | 登記頁面與它的 Google 試算表後端。維護者使用，一般使用者不需要 |

## 更新計畫資料

計畫內容每個梯次都會變。更新方式：

```bash
python scripts/fetch_programs.py
python scripts/build_kb.py
```

抓取會刻意放慢速度，避免造成官網負擔，全部跑完大約十分鐘。

## 腳本也可以單獨使用

```bash
python scripts/find_programs.py --age 22 --country 美國 -k AI
python scripts/extract_text.py my/materials
python scripts/check_draft.py my/M-2-1
python scripts/build_docx.py my/M-2-1 --author 王小明
```

## 關於知識庫

`knowledge/` 的寫作方法由作者整理自己錄取 G-3-4 常春藤 AI 領袖培訓營的申請經驗，以及協助其他申請者的過程。為了保護其他申請者，公開版本只保留歸納後的原則，以及作者本人和虛構申請者的例子。這些是個人經驗，不是官方說法。

計畫簡章的內容來自教育部青年發展署的公開資訊，著作權屬原單位。

## 授權

程式碼與說明文件採用 [MIT License](LICENSE)。

## 作者

[WayneChen983](https://github.com/WayneChen983)。歡迎開 issue 回報錯誤或提出建議。

# 0 第一次設定

目標：環境可以用，並建立使用者的背景檔 `my/profile.md`。

## 步驟

1. 先用兩三句話告訴使用者：
   - 這不是官方工具，計畫內容以官網為準，也不保證錄取。
   - 他提供的資料會經過他正在使用的 AI 服務處理。請不要放身分證、護照、存摺這類文件。
   - 他的資料都放在 `my/` 資料夾，不會被上傳到 GitHub。

2. 檢查環境。缺什麼就直接處理，不要叫使用者自己打指令：
   - `python --version`（需要 3.10 以上）
   - `pip install -r requirements.txt`
   - `data/kb/programs.json` 是否存在。不存在時執行 `python scripts/fetch_programs.py`，再執行 `python scripts/build_kb.py`。抓取會刻意放慢速度以免造成官網負擔，大約需要十分鐘，先告訴使用者。

3. 建立資料夾：`my/materials/`、`my/photos/`。

4. 建立背景檔。問使用者有沒有現成的履歷或自傳：
   - 有：請他把檔案放進 `my/materials/`（支援 txt、md、pdf、docx），執行 `python scripts/extract_text.py my/materials`，讀產生的 `*.extracted.txt`，整理成 `my/profile.md`。
   - 沒有：用對話問。一次問兩三題，不要一次丟出整張表。

   `my/profile.md` 的欄位照 `examples/林語晴/profile.md`：出生年、目前身分、學歷、經歷、專長與技能、興趣與關注的議題、語言能力、想去的國家或地區、可以出國的時間與限制、未來想做的事、我覺得自己還缺什麼。

   整理時只寫文件或對話裡有的內容，沒提到的欄位寫「（未填）」。經歷裡的數字、角色、成果與時間要保留，不要濃縮成空泛的一句話。出生年只有在他明確說出時才填，不要從年級推算。

5. 把整理好的 `my/profile.md` 給使用者看，請他確認與補充。特別請他想一想「我覺得自己還缺什麼」，這一欄之後最重要。

6. 完成後告訴他下一步可以說「幫我找計畫」。

"""檢查申請書草稿：各章字數、估計頁數、還沒補的【待補】、圖片是否存在。

用法：
  python scripts/check_draft.py my/M-2-1

草稿資料夾裡的章節檔名以數字開頭：0_開場.md、1_學經歷.md、2_機構了解.md、3_動機與期待.md、4_回國後規劃.md。
"""
import re
import sys
from pathlib import Path

TODO = re.compile(r"【待補[:：][^】]*】")
IMG = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
CHARS_PER_PAGE = 700      # 標楷體 14 級、固定行高 24 點的實測值
TARGET = {"0": 1000, "1": 4200, "2": 3000, "3": 2500, "4": 2500}
TOTAL_LIMIT = 14000


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    folder = Path(sys.argv[1])
    files = sorted(f for f in folder.glob("[0-9]_*.md"))
    if not files:
        sys.exit(f"{folder} 裡沒有章節檔（檔名需以數字開頭，例如 1_學經歷.md）。")
    total = todo_total = images = 0
    problems = []
    print(f"{'章節':<22}{'字數':>7}{'上限':>7}  待補  圖片")
    for f in files:
        text = f.read_text(encoding="utf-8")
        body = IMG.sub("", text)
        n = len(re.sub(r"\s", "", body))
        todos = TODO.findall(text)
        imgs = IMG.findall(text)
        limit = TARGET.get(f.name[0])
        flag = " ← 超過" if limit and n > limit * 1.1 else ""
        print(f"{f.stem:<22}{n:>7}{limit or '':>7}  {len(todos):>4}  {len(imgs):>4}{flag}")
        total += n
        todo_total += len(todos)
        images += len(imgs)
        for caption, src in imgs:
            if not (f.parent / src).resolve().exists():
                problems.append(f"{f.name}：找不到圖片 {src}")
            if not caption.strip():
                problems.append(f"{f.name}：圖片 {src} 沒有圖說")
        for t in todos:
            problems.append(f"{f.name}：{t}")
    pages = total / CHARS_PER_PAGE + images * 0.35 + 2  # 封面與目錄約 2 頁
    print(f"\n合計 {total} 字（建議 {TOTAL_LIMIT} 字以內）、{images} 張圖、待補 {todo_total} 處")
    print(f"估計排版後約 {pages:.0f} 頁（簡章規定內文 15–30 頁；實際頁數以 Word 為準）")
    if total > TOTAL_LIMIT:
        print("字數偏多，建議先精簡學經歷中和計畫關聯較弱的段落。")
    if problems:
        print("\n需要處理：")
        for p in problems:
            print("  - " + p)
    else:
        print("\n沒有待補項目，圖片都找得到。")


if __name__ == "__main__":
    main()

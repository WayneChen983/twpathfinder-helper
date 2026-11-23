"""從計畫知識庫篩出候選計畫，印成精簡清單給 AI 助理或人閱讀。

用法：
  python scripts/find_programs.py --age 22                     符合年齡的全部計畫
  python scripts/find_programs.py --age 22 --country 美國      再限定國家
  python scripts/find_programs.py --age 22 -k AI -k 教育       關鍵字（任一符合即可）
  python scripts/find_programs.py --no M-2-1                   印出單一計畫的完整資料
  python scripts/find_programs.py --age 22 --json              以 JSON 輸出

需要先執行 fetch_programs.py 與 build_kb.py 建立 data/kb/。
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "data" / "kb" / "programs.json"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="篩選青年百億海外翱翔組計畫")
    ap.add_argument("--age", type=int, help="申請者年齡，用來排除年齡不符的計畫")
    ap.add_argument("--country", help="國家名稱（部分符合即可）")
    ap.add_argument("--category", help="主題類別（部分符合即可）")
    ap.add_argument("-k", "--keyword", action="append", default=[], help="關鍵字，可重複指定，任一符合即列出")
    ap.add_argument("--max-days", type=int, help="天數上限")
    ap.add_argument("--no", help="只看這個計畫編號，並印出申請資格全文")
    ap.add_argument("--json", action="store_true", help="輸出 JSON")
    a = ap.parse_args()

    if not INDEX.exists():
        sys.exit("找不到 data/kb/programs.json。請先執行：\n  python scripts/fetch_programs.py\n  python scripts/build_kb.py")
    items = json.loads(INDEX.read_text(encoding="utf-8"))

    if a.no:
        items = [p for p in items if p["no"].upper() == a.no.upper()]
    if a.age is not None:
        items = [p for p in items if p["age_min"] <= a.age <= p["age_max"]]
    if a.country:
        items = [p for p in items if a.country in (p["country"] or "")]
    if a.category:
        items = [p for p in items if a.category in (p["category"] or "")]
    if a.max_days:
        items = [p for p in items if p["days"] and p["days"] <= a.max_days]
    if a.keyword:
        def hay(p):
            return " ".join(str(p.get(k) or "") for k in ("title", "topic", "category", "description", "country", "city", "eligibility"))
        items = [p for p in items if any(k.lower() in hay(p).lower() for k in a.keyword)]

    if a.json:
        print(json.dumps(items, ensure_ascii=False, indent=1))
        return
    print(f"共 {len(items)} 個計畫\n")
    for p in items:
        grant = f"{p['grant_total']:,} 元" if p["grant_total"] else "見簡章"
        print(f"## {p['no']} {p['title']}")
        print(f"- 類別：{p['category']}｜年齡：{p['age_min']}–{p['age_max']}｜{p['country']}（{p['city']}）")
        print(f"- 天數：{p['days'] or '見簡章'}｜名額：{p['quota'] or '見簡章'}｜獎勵金：{grant}")
        print(f"- 簡介：{p['description']}")
        elig = (p["eligibility"] or "").strip()
        if elig:
            print("- 申請資格：" + (elig if a.no else elig.replace("\n", " ")[:260] + ("…" if len(elig) > 260 else "")))
        print(f"- 簡章全文：data/kb/programs/{p['no']}.md｜官網：{p['source_url']}\n")


if __name__ == "__main__":
    main()

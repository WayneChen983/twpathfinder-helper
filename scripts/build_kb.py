"""把官網計畫清單與簡章 PDF 整理成知識庫。

用法： python scripts/build_kb.py
輸入： data/programs_raw.json、data/prospectus/*.pdf
輸出： data/kb/programs.json（結構化索引，媒合用）
       data/kb/programs/<計畫編號>.md（簡章全文，生成計畫書與問答用）
       data/kb/盤點報告.md
"""
import json
import re
import sys
import warnings
from collections import Counter
from pathlib import Path

warnings.filterwarnings("ignore")
import pymupdf  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
PDF_DIR = DATA / "prospectus"
KB = DATA / "kb"
BASE = "https://twpathfinder.yda.gov.tw"

BOILER = re.compile(
    r"^(青年百億海外圓夢基金計畫－海外翱翔組|以上內容教育部青年發展署及合作單位保有調整及最終解釋之權利|\d+\s*／\s*\d+)\s*$")


def safe(name):
    return re.sub(r"[^A-Za-z0-9_-]", "_", name)


def pdf_text(path, title_line):
    doc = pymupdf.open(path)
    pages = []
    for i, page in enumerate(doc, 1):
        lines = []
        for ln in page.get_text().splitlines():
            s = ln.strip()
            if not s or BOILER.match(s):
                continue
            if i > 1 and s.replace(" ", "") == title_line.replace(" ", ""):
                continue
            lines.append(s)
        pages.append(f"<!-- 第 {i} 頁 -->\n" + "\n".join(lines))
    return "\n\n".join(pages), len(doc)


def section(text, name):
    """取出「◆name」到下一個「◆」之間的內容。"""
    m = re.search(r"◆" + name + r"[^\n]*\n(.*?)(?=\n◆|\Z)", text, re.S)
    if not m:
        return ""
    return re.sub(r"<!-- 第 \d+ 頁 -->\n?", "", m.group(1)).strip()


def num(s):
    return int(re.sub(r"[^\d]", "", s)) if s and re.search(r"\d", s) else None


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    raw = json.loads((DATA / "programs_raw.json").read_text(encoding="utf-8"))
    (KB / "programs").mkdir(parents=True, exist_ok=True)
    index, missing = [], []
    for p in raw:
        no = p["no"]
        pdf = PDF_DIR / f"{safe(no)}.pdf"
        text, pages = "", 0
        if pdf.exists():
            text, pages = pdf_text(pdf, f"{no} {p['title']}")
        else:
            missing.append(no)

        flat = re.sub(r"\s+", "", text)
        m_total = re.search(r"獎勵金總經費共?([\d,，]+)元", flat)
        m_days = re.search(r"共\s*(\d+)\s*日", p.get("duration") or "")
        m_age = re.search(r"(\d{2})\s*歲?[至到～~\-－]\s*(\d{2})\s*歲", section(text, "青年申請資格"))
        default_age = (18, 30) if p["type"] == "overview1830" else (15, 17)
        entry = {
            "id": p["id"],
            "no": no,
            "title": p["title"],
            "age_group": "18-30" if p["type"] == "overview1830" else "15-17",
            "age_min": int(m_age.group(1)) if m_age else default_age[0],
            "age_max": int(m_age.group(2)) if m_age else default_age[1],
            "category": re.sub(r"^（.+?）", "", p["overview_cate"]["title"]).strip(),
            "category_full": p["overview_cate"]["title"],
            "organization": p.get("organization"),
            "country": p.get("country"),
            "city": p.get("city"),
            "topic": p.get("topic"),
            "duration": p.get("duration"),
            "days": int(m_days.group(1)) if m_days else None,
            "quota": num(str(p.get("quota") or "")),
            "description": p.get("description"),
            "grant_total": num(m_total.group(1)) if m_total else None,
            "eligibility": section(text, "青年申請資格"),
            "pre_training": section(text, "行前培訓")[:1500],
            "signup_heat": p.get("signup_heat"),
            "publication_date": p.get("publication_date"),
            "pdf_pages": pages,
            "has_prospectus": bool(text),
            "source_url": f"{BASE}/overview_pdf/{p['id']}",
        }
        index.append(entry)
        if text:
            head = (f"# {no} {p['title']}\n\n"
                    f"- 來源：{entry['source_url']}（官網簡章，公告日 {entry['publication_date']}）\n"
                    f"- 年齡組別：{entry['age_group']} 歲｜主辦：{entry['organization']}\n"
                    f"- 一句話：{entry['description']}\n\n---\n\n")
            (KB / "programs" / f"{safe(no)}.md").write_text(head + text, encoding="utf-8")

    (KB / "programs.json").write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")

    cats = Counter((e["age_group"], e["category"]) for e in index)
    countries = Counter(e["country"] for e in index)
    lines = ["# 計畫知識庫盤點報告", "",
             f"- 計畫總數：{len(index)}（18–30 歲 {sum(e['age_group']=='18-30' for e in index)}、"
             f"15–17 歲 {sum(e['age_group']=='15-17' for e in index)}）",
             f"- 已取得簡章全文：{sum(e['has_prospectus'] for e in index)}",
             f"- 缺簡章：{', '.join(missing) or '無'}",
             f"- 解析出獎勵金總額：{sum(e['grant_total'] is not None for e in index)}",
             f"- 解析出申請資格：{sum(bool(e['eligibility']) for e in index)}",
             "", "## 依主題類別", "", "| 年齡組 | 主題類別 | 計畫數 |", "|---|---|---|"]
    lines += [f"| {a} | {c} | {n} |" for (a, c), n in sorted(cats.items())]
    lines += ["", "## 依國家（前 20）", "", "| 國家 | 計畫數 |", "|---|---|"]
    lines += [f"| {c} | {n} |" for c, n in countries.most_common(20)]
    lines += ["", "## 全部計畫", "", "| 編號 | 名稱 | 年齡 | 國家 | 天數 | 名額 | 獎勵金 | 簡章頁數 |", "|---|---|---|---|---|---|---|---|"]
    lines += [f"| {e['no']} | {e['title']} | {e['age_min']}–{e['age_max']} | {e['country']} | {e['days'] or '—'} | "
              f"{e['quota'] or '—'} | {e['grant_total'] or '—'} | {e['pdf_pages'] or '缺'} |" for e in index]
    (KB / "盤點報告.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:9]))


if __name__ == "__main__":
    main()

"""從青年百億官網抓取海外翱翔組全部計畫清單與簡章 PDF。

用法： python scripts/fetch_programs.py
輸出： data/programs_raw.json、data/prospectus/<計畫編號>.pdf
可重複執行；已下載的 PDF 會跳過。
"""
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = "https://twpathfinder.yda.gov.tw"
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
PDF_DIR = DATA / "prospectus"
UA = "Mozilla/5.0 (compatible; program-catalog-fetcher)"
DELAY = 3


def get(url, as_json=False, timeout=60):
    headers = {"User-Agent": UA}
    if as_json:
        headers["X-Requested-With"] = "XMLHttpRequest"
        headers["Accept"] = "application/json"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read()
        ctype = r.headers.get("Content-Type", "")
    return (json.loads(body) if as_json else body), ctype


def list_programs(kind):
    items, page = [], 1
    while True:
        d, _ = get(f"{BASE}/{kind}?page={page}", as_json=True)
        items += d["data"]
        last = d["pagination"]["last_page"]
        print(f"  {kind} 第 {page}/{last} 頁，累計 {len(items)}")
        if page >= last:
            return items
        page += 1
        time.sleep(DELAY)


def safe(name):
    return re.sub(r"[^A-Za-z0-9_-]", "_", name)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    programs = []
    for kind in ("overview1830", "overview1517"):
        programs += list_programs(kind)
    (DATA / "programs_raw.json").write_text(
        json.dumps(programs, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"計畫總數：{len(programs)}")

    ok = skipped = failed = 0
    for p in programs:
        out = PDF_DIR / f"{safe(p['no'])}.pdf"
        if out.exists() and out.stat().st_size > 1000:
            skipped += 1
            continue
        if p.get("portal_prospectus_id") and p.get("prospectus_pdf_available"):
            url = f"{BASE}/overview_pdf/{p['id']}"
        elif p.get("file") and p.get("file") != "null":
            url = f"{BASE}/overview_d/{p['id']}"
        else:
            print(f"  {p['no']} 沒有簡章檔")
            failed += 1
            continue
        try:
            for attempt in range(4):
                try:
                    body, ctype = get(url, timeout=120)
                    break
                except urllib.error.HTTPError as e:
                    if e.code != 429 or attempt == 3:
                        raise
                    wait = 60 * (attempt + 1)
                    print(f"  {p['no']} 被限流，等 {wait} 秒", flush=True)
                    time.sleep(wait)
            if not body.startswith(b"%PDF"):
                print(f"  {p['no']} 回傳不是 PDF（{ctype}, {len(body)} bytes）")
                failed += 1
            else:
                out.write_bytes(body)
                ok += 1
        except Exception as e:  # noqa: BLE001
            print(f"  {p['no']} 下載失敗：{e}")
            failed += 1
        time.sleep(DELAY)
    print(f"PDF：新下載 {ok}、已存在 {skipped}、失敗 {failed}")


if __name__ == "__main__":
    main()

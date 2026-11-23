"""把履歷、自傳等文件（txt / md / pdf / docx）轉成純文字，並遮蔽高風險個資。

用法：
  python scripts/extract_text.py my/materials/履歷.pdf my/materials/自傳.docx
  python scripts/extract_text.py my/materials            處理整個資料夾

每個檔案會在旁邊產生 *.extracted.txt（例如 履歷.pdf → 履歷.pdf.extracted.txt）。AI 助理請讀這些檔案，
不要直接讀原始檔：遮蔽過的文字才適合送進模型。

遮蔽項目：身分證字號、手機與市話號碼、Email、信用卡號。遮蔽是規則比對，不保證完整，
送出前請自己再看一眼。
"""
import re
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

PATTERNS = [
    ("身分證字號", re.compile(r"(?<![A-Za-z0-9])[A-Z][1289]\d{8}(?!\d)")),
    ("手機號碼", re.compile(r"(?<!\d)(?:\+886[\s-]?9|09)\d{2}[\s-]?\d{3}[\s-]?\d{3}(?!\d)")),
    ("市話", re.compile(r"(?<!\d)\(?0\d{1,2}\)?[\s-]\d{3,4}[\s-]?\d{4}(?!\d)")),
    ("Email", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("信用卡號", re.compile(r"(?<!\d)(?:\d{4}[\s-]){3}\d{4}(?!\d)")),
]
SUPPORTED = {".txt", ".md", ".pdf", ".docx"}


def mask(text):
    total = 0
    for label, pat in PATTERNS:
        text, n = pat.subn(f"【已遮蔽{label}】", text)
        total += n
    return text, total


def compact(text):
    """去掉多餘空白與連續空行，減少送進模型的字數。"""
    lines = [re.sub(r"[ \t　]{2,}", " ", ln).strip() for ln in text.splitlines()]
    out, blank = [], False
    for ln in lines:
        if ln:
            out.append(ln)
            blank = False
        elif not blank and out:
            out.append("")
            blank = True
    return "\n".join(out).strip()


def extract(path):
    ext = path.suffix.lower()
    data = path.read_bytes()
    if ext in (".txt", ".md"):
        for enc in ("utf-8-sig", "utf-16", "big5", "cp950"):
            try:
                return data.decode(enc)
            except UnicodeDecodeError:
                continue
        raise ValueError("無法判讀文字編碼")
    if ext == ".pdf":
        import pymupdf
        with pymupdf.open(stream=data, filetype="pdf") as doc:
            text = "\n".join(page.get_text() for page in doc)
        if not text.strip():
            raise ValueError("PDF 裡沒有可擷取的文字（可能是掃描檔）")
        return text
    if ext == ".docx":
        from docx import Document
        doc = Document(str(path))
        lines = [p.text for p in doc.paragraphs]
        for t in doc.tables:
            lines += [" | ".join(c.text for c in row.cells) for row in t.rows]
        return "\n".join(lines)
    raise ValueError("只支援 txt、md、pdf、docx")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    targets = []
    for arg in sys.argv[1:]:
        p = Path(arg)
        if p.is_dir():
            targets += [f for f in sorted(p.iterdir()) if f.suffix.lower() in SUPPORTED and not f.name.endswith(".extracted.txt")]
        else:
            targets.append(p)
    if not targets:
        sys.exit("沒有找到可處理的檔案（支援 txt、md、pdf、docx）。")
    for p in targets:
        try:
            text, n = mask(compact(extract(p)))
        except Exception as e:  # noqa: BLE001
            print(f"✗ {p}：{e}")
            continue
        out = p.with_name(p.name + ".extracted.txt")
        out.write_text(text, encoding="utf-8")
        print(f"✓ {p.name} → {out.name}（{len(text)} 字" + (f"，已遮蔽 {n} 處個資）" if n else "）"))


if __name__ == "__main__":
    main()

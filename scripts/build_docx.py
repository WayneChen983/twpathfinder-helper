"""把草稿資料夾裡的章節 Markdown 與照片，排成符合簡章格式的 Word 檔。

用法：
  python scripts/build_docx.py my/M-2-1 --author 王小明
  python scripts/build_docx.py my/M-2-1 --author 王小明 --title "M-2-1 常春藤 AI 領袖培訓營" -o 申請書.docx

輸入：資料夾裡以數字開頭的章節檔，依檔名排序：
  0_開場.md、1_學經歷.md、2_機構了解.md、3_動機與期待.md、4_回國後規劃.md
章節檔的第一行若是「# 標題」，就用它當章標題；否則用預設的章名。

章節內可用的 Markdown：
  ### 小標題          **粗體**          - 清單          1. 編號清單          | 表格 |
  ![圖說](../photos/檔名.jpg)   圖片，路徑相對於章節檔。連續兩行圖片會並排。
  【待補：…】          在 Word 裡以黃底標出

輸出格式：A4 直式、標楷體＋Times New Roman、大標 18／小標 16／內文 14、固定行高 24 點、
頁碼、封面與可更新的目錄。圖片會先壓縮（長邊 1200 像素、去除 EXIF）再放進文件。
"""
import argparse
import io
import json
import re
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

from docx import Document  # noqa: E402
from docx.enum.table import WD_TABLE_ALIGNMENT  # noqa: E402
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX, WD_LINE_SPACING  # noqa: E402
from docx.oxml import OxmlElement  # noqa: E402
from docx.oxml.ns import qn  # noqa: E402
from docx.shared import Cm, Pt, RGBColor  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ZH_FONT, EN_FONT = "標楷體", "Times New Roman"
ACCENT = RGBColor(0x1C, 0x6B, 0x3C)
HEADER_FILL = "DDF3E8"
PAGE_WIDTH_CM = 21 - 2.54 * 2
TODO_RE = re.compile(r"(【待補[:：][^】]*】)")
IMG_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
DEFAULT_TITLES = {
    "0": "開場：一頁重點摘要",
    "1": "一、申請青年之學經歷",
    "2": "二、對見習機構及此項圓夢機會的了解",
    "3": "三、申請原因、動機及期待",
    "4": "四、回國後規劃與影響力",
}


def load_image(path, max_side=1200, quality=72):
    """壓成文件用得到的最小尺寸並去掉 EXIF。回傳 (BytesIO, 寬, 高)。"""
    from PIL import Image, ImageOps
    img = ImageOps.exif_transpose(Image.open(path))
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        img = bg
    else:
        img = img.convert("RGB")
    img.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=quality, optimize=True, progressive=True)
    buf.seek(0)
    return buf, img.width, img.height


def _set_fonts(el):
    rpr = el.get_or_add_rPr()
    fonts = rpr.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        rpr.append(fonts)
    fonts.set(qn("w:eastAsia"), ZH_FONT)
    for attr in ("w:ascii", "w:hAnsi", "w:cs"):
        fonts.set(qn(attr), EN_FONT)


def _run(p, text, size, bold=False, color=None, highlight=False):
    run = p.add_run(text)
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.name = EN_FONT
    if color is not None:
        run.font.color.rgb = color
    if highlight:
        run.font.highlight_color = WD_COLOR_INDEX.YELLOW
    _set_fonts(run._element)
    return run


def _inline(p, text, size, bold=False, color=None):
    for i, seg in enumerate(re.split(r"\*\*(.+?)\*\*", text)):
        if not seg:
            continue
        for part in TODO_RE.split(seg):
            if part:
                _run(p, part, size, bold or i % 2 == 1, color, highlight=bool(TODO_RE.fullmatch(part)))


def _para(container, text, size=14, bold=False, align=None, fixed=True, color=None):
    p = container.add_paragraph()
    fmt = p.paragraph_format
    if fixed:  # 簡章規定：固定行高 24 點
        fmt.line_spacing_rule = WD_LINE_SPACING.EXACTLY
        fmt.line_spacing = Pt(24)
    fmt.space_after = Pt(6)
    if align is not None:
        p.alignment = align
    _inline(p, text, size, bold, color)
    return p


def _heading(doc, text, level):
    p = doc.add_paragraph(style=f"Heading {level}")
    fmt = p.paragraph_format
    fmt.space_before = Pt(18 if level == 1 else 12)
    fmt.space_after = Pt(8)
    fmt.keep_with_next = True
    _inline(p, text, 18 if level == 1 else 16, True, ACCENT)
    if level == 1:
        ppr = p._p.get_or_add_pPr()
        border = OxmlElement("w:pBdr")
        bottom = OxmlElement("w:bottom")
        for k, v in (("w:val", "single"), ("w:sz", "8"), ("w:space", "4"), ("w:color", "1C6B3C")):
            bottom.set(qn(k), v)
        border.append(bottom)
        ppr.append(border)


def _fld(kind):
    el = OxmlElement("w:fldChar")
    el.set(qn("w:fldCharType"), kind)
    return el


def _instr(text):
    el = OxmlElement("w:instrText")
    el.set(qn("xml:space"), "preserve")
    el.text = text
    return el


def _page_number(section):
    p = section.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    run.font.size = Pt(12)
    _set_fonts(run._element)
    for el in (_fld("begin"), _instr("PAGE"), _fld("separate"), _fld("end")):
        run._element.append(el)


def _table(doc, rows):
    cols = max(len(r) for r in rows)
    t = doc.add_table(rows=len(rows), cols=cols)
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, r in enumerate(rows):
        for j in range(cols):
            cell = t.cell(i, j)
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = 1.15
            _inline(p, r[j] if j < len(r) else "", 12, bold=(i == 0))
            if i == 0:
                shd = OxmlElement("w:shd")
                for k, v in (("w:val", "clear"), ("w:color", "auto"), ("w:fill", HEADER_FILL)):
                    shd.set(qn(k), v)
                cell._tc.get_or_add_tcPr().append(shd)
    t.rows[0]._tr.get_or_add_trPr().append(OxmlElement("w:tblHeader"))  # 表頭跨頁重複
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def _figures(doc, figs, counter):
    """一張置中，兩張並排。圖說為「圖 N　說明」。"""
    for i in range(0, len(figs), 2):
        pair = figs[i:i + 2]
        if len(pair) == 1:
            buf, w, h, caption = pair[0]
            width = min(12.5, PAGE_WIDTH_CM * (0.55 if h > w else 0.8))
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(6)
            p.paragraph_format.keep_with_next = True
            p.add_run().add_picture(buf, width=Cm(width))
            counter[0] += 1
            cap = _para(doc, f"圖 {counter[0]}　{caption}", size=12, align=WD_ALIGN_PARAGRAPH.CENTER, fixed=False)
            cap.paragraph_format.space_after = Pt(10)
        else:
            t = doc.add_table(rows=2, cols=2)
            t.alignment = WD_TABLE_ALIGNMENT.CENTER
            borders = OxmlElement("w:tblBorders")
            for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
                el = OxmlElement(f"w:{side}")
                el.set(qn("w:val"), "nil")
                borders.append(el)
            t._tbl.tblPr.append(borders)
            for j, (buf, w, h, caption) in enumerate(pair):
                p = t.cell(0, j).paragraphs[0]
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                cell_w = PAGE_WIDTH_CM / 2 - 0.5
                p.add_run().add_picture(buf, width=Cm(cell_w * (0.7 if h > w else 1)))
                counter[0] += 1
                c = t.cell(1, j).paragraphs[0]
                c.alignment = WD_ALIGN_PARAGRAPH.CENTER
                _inline(c, f"圖 {counter[0]}　{caption}", 12)
            doc.add_paragraph().paragraph_format.space_after = Pt(4)


def _render(doc, md, base, counter, warnings_out):
    table, figs = [], []

    def flush():
        if table:
            _table(doc, table[:])
            table.clear()
        if figs:
            _figures(doc, figs[:], counter)
            figs.clear()

    for raw in md.splitlines():
        line = raw.strip()
        m = IMG_RE.fullmatch(line)
        if m:
            if table:
                flush()
            src = (base / m.group(2)).resolve()
            if src.exists():
                try:
                    buf, w, h = load_image(src)
                    figs.append((buf, w, h, m.group(1).strip() or src.stem))
                except Exception as e:  # noqa: BLE001
                    warnings_out.append(f"圖片無法讀取：{m.group(2)}（{e}）")
            else:
                warnings_out.append(f"找不到圖片：{m.group(2)}")
            continue
        if line.startswith("|") and line.endswith("|") and len(line) > 1:
            if figs:
                flush()
            cells = [c.strip() for c in line.strip("|").split("|")]
            if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                table.append(cells)
            continue
        if not line:
            if table:
                flush()
            continue
        flush()
        if re.fullmatch(r"-{3,}", line):
            continue
        h = re.match(r"(#{2,6})\s+(.*)", line)
        if h:
            _heading(doc, h.group(2), 2)
        elif re.match(r"[-*・]\s+", line):
            p = _para(doc, "• " + re.sub(r"^[-*・]\s+", "", line))
            p.paragraph_format.left_indent = Cm(0.6)
            p.paragraph_format.first_line_indent = Cm(-0.45)
        elif re.match(r"\d+[.、]\s+", line):
            p = _para(doc, line)
            p.paragraph_format.left_indent = Cm(0.7)
            p.paragraph_format.first_line_indent = Cm(-0.7)
        else:
            _para(doc, line, align=WD_ALIGN_PARAGRAPH.JUSTIFY)
    flush()


def build(folder, title, author):
    files = sorted(folder.glob("[0-9]_*.md"))
    if not files:
        sys.exit(f"{folder} 裡沒有章節檔（檔名需以數字開頭，例如 1_學經歷.md）。")
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(sec, side, Cm(2.54))
    sec.different_first_page_header_footer = True  # 封面不編頁碼
    _page_number(sec)
    for name in ("Normal", "Heading 1", "Heading 2"):
        style = doc.styles[name]
        style.font.name = EN_FONT
        style.font.color.rgb = ACCENT if name != "Normal" else RGBColor(0, 0, 0)
        _set_fonts(style.element)
    upd = OxmlElement("w:updateFields")  # 開啟檔案時請 Word 更新目錄頁碼
    upd.set(qn("w:val"), "true")
    doc.settings.element.append(upd)

    center = WD_ALIGN_PARAGRAPH.CENTER
    for _ in range(5):
        _para(doc, "", fixed=False)
    _para(doc, "青年百億海外圓夢基金計畫", size=22, bold=True, align=center, fixed=False, color=ACCENT)
    _para(doc, "海外翱翔組　申請計畫書", size=20, bold=True, align=center, fixed=False)
    for _ in range(2):
        _para(doc, "", fixed=False)
    _para(doc, title, size=18, bold=True, align=center, fixed=False)
    for _ in range(6):
        _para(doc, "", fixed=False)
    _para(doc, f"申請人：{author}", size=16, align=center, fixed=False)
    doc.add_page_break()

    p = _para(doc, "目錄", size=18, bold=True, fixed=False, color=ACCENT)
    p.paragraph_format.space_after = Pt(12)
    toc = doc.add_paragraph()
    r1 = toc.add_run()
    for el in (_fld("begin"), _instr('TOC \\o "1-2" \\h \\z \\u'), _fld("separate")):
        r1._element.append(el)
    hint = toc.add_run("（開啟檔案時 Word 會詢問是否更新功能變數，選「是」就會顯示目錄與頁碼。）")
    hint.font.size = Pt(12)
    _set_fonts(hint._element)
    toc.add_run()._element.append(_fld("end"))

    counter, notes = [0], []
    for f in files:
        text = f.read_text(encoding="utf-8").strip()
        first, _, rest = text.partition("\n")
        if first.startswith("# "):
            chapter, body = first[2:].strip(), rest
        else:
            chapter, body = DEFAULT_TITLES.get(f.name[0], f.stem.split("_", 1)[-1]), text
        doc.add_page_break()
        _heading(doc, chapter, 1)
        _render(doc, body, f.parent, counter, notes)
    return doc, counter[0], notes


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="把章節 Markdown 與照片排成符合簡章格式的 Word 檔")
    ap.add_argument("folder", help="草稿資料夾，例如 my/M-2-1")
    ap.add_argument("--author", required=True, help="封面上的申請人姓名")
    ap.add_argument("--title", help="封面上的計畫名稱；省略時依資料夾名稱從計畫知識庫查")
    ap.add_argument("-o", "--output", help="輸出檔名，預設為 草稿資料夾/申請書_<資料夾名>.docx")
    a = ap.parse_args()
    folder = Path(a.folder)
    title = a.title
    if not title:
        index = ROOT / "data" / "kb" / "programs.json"
        if index.exists():
            hit = [p for p in json.loads(index.read_text(encoding="utf-8")) if p["no"].upper() == folder.name.upper()]
            if hit:
                title = f"{hit[0]['no']} {hit[0]['title']}"
        title = title or folder.name
    doc, figures, notes = build(folder, title, a.author)
    out = Path(a.output) if a.output else folder / f"申請書_{folder.name}.docx"
    doc.save(str(out))
    todo = sum(len(TODO_RE.findall(f.read_text(encoding="utf-8"))) for f in folder.glob("[0-9]_*.md"))
    print(f"已產生 {out}（{out.stat().st_size // 1024} KB，{figures} 張圖）")
    if todo:
        print(f"還有 {todo} 處【待補】，在 Word 裡以黃底標出。")
    for n in notes:
        print("注意：" + n)
    print("開啟時 Word 會詢問是否更新功能變數，選「是」。確認頁數在 15–30 頁後另存成 PDF（10 MB 以內）。")


if __name__ == "__main__":
    main()

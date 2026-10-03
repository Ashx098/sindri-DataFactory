#!/usr/bin/env python3
"""Convert a design .docx into text-native Markdown so agents can read and diff it.

Usage:
    python scripts/docx_to_md.py docs/reference/X.docx docs/architecture/X.md [--img-dir DIR]

Handles headings, bullet/numbered lists, tables, code blocks, callouts, bold/italic runs,
hyperlinks and embedded images. Stdlib only. The generated file carries a header naming its source;
regenerate it rather than hand-editing when the .docx changes.
"""

import argparse
import hashlib
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}
W = "{{{}}}".format(NS["w"])
R = "{{{}}}".format(NS["r"])

HEADINGS = {
    "Title": "#", "Heading1": "#", "Heading2": "##", "Heading3": "###", "Heading4": "####",
}
CODE_STYLES = {"Code", "CodeBlock"}
QUOTE_STYLES = {"Callout", "Quote", "SmallNote"}


class Converter:
    def __init__(self, docx: Path, img_dir: Path, img_link_prefix: str) -> None:
        self.zip = zipfile.ZipFile(docx)
        self.img_dir = img_dir
        self.img_link_prefix = img_link_prefix
        self.rels = self._load_rels()
        self.num_formats = self._load_numbering()
        self.counters: dict[tuple[str, str], int] = {}

    def _load_rels(self) -> dict[str, str]:
        root = ET.fromstring(self.zip.read("word/_rels/document.xml.rels"))
        return {r.get("Id", ""): r.get("Target", "") for r in root.findall("rel:Relationship", NS)}

    def _load_numbering(self) -> dict[tuple[str, str], str]:
        """Map (numId, ilvl) -> numFmt ('bullet', 'decimal', ...)."""
        try:
            root = ET.fromstring(self.zip.read("word/numbering.xml"))
        except KeyError:
            return {}
        abstract: dict[str, dict[str, str]] = {}
        for an in root.findall("w:abstractNum", NS):
            levels = {}
            for lvl in an.findall("w:lvl", NS):
                fmt = lvl.find("w:numFmt", NS)
                fmt_val = fmt.get(W + "val", "bullet") if fmt is not None else "bullet"
                levels[lvl.get(W + "ilvl", "0")] = fmt_val
            abstract[an.get(W + "abstractNumId", "")] = levels
        out = {}
        for num in root.findall("w:num", NS):
            ref = num.find("w:abstractNumId", NS)
            if ref is None:
                continue
            for ilvl, fmt in abstract.get(ref.get(W + "val", ""), {}).items():
                out[(num.get(W + "numId", ""), ilvl)] = fmt
        return out

    # ---- inline content -------------------------------------------------------------------

    def runs_text(self, el: ET.Element, code: bool = False) -> str:
        parts: list[str] = []
        for child in el:
            tag = child.tag
            if tag == W + "r":
                parts.append(self.run_text(child, code))
            elif tag == W + "hyperlink":
                text = self.runs_text(child, code)
                target = self.rels.get(child.get(R + "id", ""), "")
                parts.append(f"[{text}]({target})" if target and not code else text)
            elif tag in (W + "ins", W + "smartTag", W + "sdt", W + "sdtContent"):
                parts.append(self.runs_text(child, code))
        return "".join(parts)

    def run_text(self, run: ET.Element, code: bool) -> str:
        text = []
        for node in run:
            if node.tag == W + "t":
                text.append(node.text or "")
            elif node.tag == W + "tab":
                text.append("    " if code else " ")
            elif node.tag in (W + "br", W + "cr"):
                text.append("\n")
            elif node.tag == W + "drawing":
                text.append(self.image(node))
        s = "".join(text)
        if code or not s.strip():
            return s
        rpr = run.find("w:rPr", NS)
        bold = rpr is not None and _on(rpr.find("w:b", NS))
        italic = rpr is not None and _on(rpr.find("w:i", NS))
        lead, core, trail = re.match(r"^(\s*)(.*?)(\s*)$", s, re.S).groups()  # type: ignore[union-attr]
        if bold:
            core = f"**{core}**"
        if italic:
            core = f"*{core}*"
        return lead + core + trail

    def image(self, drawing: ET.Element) -> str:
        blip = drawing.find(".//a:blip", NS)
        if blip is None:
            return ""
        target = self.rels.get(blip.get(R + "embed", ""), "")
        if not target:
            return ""
        data = self.zip.read("word/" + target)
        name = f"{hashlib.sha256(data).hexdigest()[:12]}{Path(target).suffix}"
        self.img_dir.mkdir(parents=True, exist_ok=True)
        (self.img_dir / name).write_bytes(data)
        return f"![figure]({self.img_link_prefix}{name})"

    # ---- block content --------------------------------------------------------------------

    def paragraph(self, p: ET.Element) -> tuple[str, str]:
        """Return (kind, markdown) for one paragraph."""
        ppr = p.find("w:pPr", NS)
        style = ""
        num = None
        if ppr is not None:
            st = ppr.find("w:pStyle", NS)
            style = st.get(W + "val", "") if st is not None else ""
            num = ppr.find("w:numPr", NS)
        if style in CODE_STYLES:
            return "code", self.runs_text(p, code=True)
        text = self.runs_text(p).strip()
        if not text:
            return "blank", ""
        if text.startswith("\u2022"):  # literal bullet glyph typed into the paragraph
            return "list", "- " + text.lstrip("\u2022").strip()
        if style in HEADINGS:
            return "heading", f"{HEADINGS[style]} {_strip_bold(text)}"
        if style in QUOTE_STYLES:
            return "quote", "\n".join("> " + ln for ln in text.splitlines())
        if num is not None:
            ilvl_el = num.find("w:ilvl", NS)
            numid_el = num.find("w:numId", NS)
            ilvl = ilvl_el.get(W + "val", "0") if ilvl_el is not None else "0"
            numid = numid_el.get(W + "val", "") if numid_el is not None else ""
            indent = "  " * int(ilvl)
            if self.num_formats.get((numid, ilvl), "bullet") == "bullet":
                return "list", f"{indent}- {text}"
            key = (numid, ilvl)
            self.counters[key] = self.counters.get(key, 0) + 1
            return "list", f"{indent}{self.counters[key]}. {text}"
        if style == "ListParagraph":
            return "list", f"- {text}"
        return "para", text

    def table(self, tbl: ET.Element) -> str:
        rows = []
        for tr in tbl.findall("w:tr", NS):
            cells = []
            for tc in tr.findall("w:tc", NS):
                paras = [self.paragraph(p)[1] for p in tc.findall(".//w:p", NS)]
                cell = "<br>".join(x.replace("\n", "<br>") for x in paras if x)
                cells.append(cell.replace("|", "\\|"))
            rows.append(cells)
        if not rows:
            return ""
        width = max(len(r) for r in rows)
        rows = [r + [""] * (width - len(r)) for r in rows]
        out = ["| " + " | ".join(rows[0]) + " |", "|" + "---|" * width]
        out += ["| " + " | ".join(r) + " |" for r in rows[1:]]
        return "\n".join(out)

    def convert(self) -> str:
        body = ET.fromstring(self.zip.read("word/document.xml")).find("w:body", NS)
        assert body is not None
        blocks: list[str] = []
        prev = ""
        code_buf: list[str] = []

        def flush_code() -> None:
            if code_buf:
                blocks.append("```\n" + "\n".join(code_buf).rstrip() + "\n```")
                code_buf.clear()

        for el in body:
            if el.tag == W + "tbl":
                flush_code()
                blocks.append(self.table(el))
                prev = "table"
            elif el.tag == W + "p":
                kind, md = self.paragraph(el)
                if kind == "code":
                    code_buf.append(md)
                    prev = kind
                    continue
                flush_code()
                if kind == "blank":
                    continue
                if kind != "list":
                    self.counters.clear()
                if kind == "list" and prev == "list":
                    blocks[-1] += "\n" + md
                else:
                    blocks.append(md)
                prev = kind
        flush_code()
        return "\n\n".join(b for b in blocks if b.strip()) + "\n"


def _on(el: ET.Element | None) -> bool:
    return el is not None and el.get(W + "val", "true") not in ("0", "false")


def _strip_bold(text: str) -> str:
    return text.replace("**", "")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("docx", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--img-dir", type=Path, help="default: <out dir>/img")
    args = ap.parse_args()
    img_dir = args.img_dir or args.out.parent / "img"
    link_prefix = str(img_dir.resolve().relative_to(args.out.parent.resolve())) + "/"
    md = Converter(args.docx, img_dir, link_prefix).convert()
    header = (
        f"<!-- GENERATED by scripts/docx_to_md.py from {args.docx.as_posix()}. "
        "Do not hand-edit; regenerate from the source document. -->\n\n"
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(header + md)
    print(f"{args.out} ({len(md.split())} words)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

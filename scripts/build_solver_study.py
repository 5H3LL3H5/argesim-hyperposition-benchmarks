"""Typeset the Markdown chapters as one linked PDF.

Requires Pandoc, WeasyPrint, lxml and Matplotlib. Repository links outside
the book point to the supplied source revision. No network assets are used.
"""

import argparse
import base64
import io
import re
import subprocess
import sys
from html import escape
from pathlib import Path
from urllib.parse import urlsplit

from lxml import etree, html
from matplotlib import rc_context
from matplotlib.font_manager import FontProperties
from matplotlib.mathtext import math_to_image
from weasyprint import HTML

if __package__:
    from .lehrbuch_layout import AUTHOR, CSS_BOOK, LESSONS, TITLE, anchor, front_matter
else:
    from lehrbuch_layout import AUTHOR, CSS_BOOK, LESSONS, TITLE, anchor, front_matter

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
GITHUB = "https://github.com/5H3LL3H5/argesim-hyperposition-benchmarks"
CHAPTERS = {
    "QSS_DEVS_HISTORY.md": ("history", "DEVS and QSS"),
    "SOLVER_SELECTION.md": ("selection", "Solver selection"),
    "SOLVER_METHODS.md": ("methods", "Method foundations"),
    "SOLVER_COMPARISON.md": ("archive", "Original eight-case study"),
}
BOOK = {
    **{
        "lehrbuch/" + name: (anchor(name), labels[0])
        for name, labels in LESSONS.items()
    },
    **CHAPTERS,
}

CSS = """
@page {
  size: A4; margin: 17mm 16mm 17mm;
  @top-left { content: "ARGESIM   /   NUMERICAL METHODS"; color: #13646b;
    font: bold 8pt "Open Sans", sans-serif; letter-spacing: 1px; }
  @top-right { content: string(chapter); color: #425a65; font: 8pt "Open Sans", sans-serif; }
  @bottom-left { content: "Technical report   ·   Source REVISION";
    color: #425a65; font: 8pt "Open Sans", sans-serif; }
  @bottom-right { content: counter(page) " / " counter(pages); color: #425a65;
    font: 8pt "Open Sans", sans-serif; }
}
body { margin: 0; color: #202c34; font: 9.7pt/1.32 "Open Sans", sans-serif; }
article + article { break-before: page; }
h1, h2, h3 { color: #075b61; break-after: avoid; line-height: 1.15; }
h1 { font: 700 22pt/1.1 "DejaVu Serif", serif; margin: 0 0 3mm;
  padding-top: 3.5mm; border-top: 2px solid #197279; string-set: chapter attr(data-chapter); }
h2 { font-size: 15pt; margin: 4mm 0 2mm; }
h3 { font-size: 11.8pt; margin: 3mm 0 2mm; }
p { margin: 1.8mm 0 2.4mm; orphans: 3; widows: 3; }
a { color: #08656d; text-decoration: underline; text-decoration-thickness: .5pt; }
code { font: 8.5pt "DejaVu Sans Mono", monospace; }
pre { background: #eff5f4; padding: 2.6mm; white-space: pre-wrap; overflow-wrap: anywhere;
  break-inside: avoid; line-height: 1.32; }
pre code { font-size: 8pt; }
table { border-collapse: collapse; width: 100%; margin: 2.5mm 0 3mm;
  font-size: 8.6pt; line-height: 1.23; }
thead { display: table-header-group; }
th { background: #155c61; color: white; font-weight: 650; text-align: left; }
th,td { padding: 1.15mm 1.5mm; vertical-align: top; }
td { border-bottom: .5pt solid #bfd0d1; }
td:first-child { font-weight: 650; }
tbody tr:nth-child(even) { background: #f3f7f7; }
tr { break-inside: avoid; }
figure { margin: 3mm 0; break-inside: avoid; }
img:not(.math) { display: block; max-width: 100%; width: 100%; height: auto; }
img.math { vertical-align: middle; }
figcaption { font: italic 8.8pt "Open Sans", sans-serif; color: #405861; }
img:not(.math) { max-height: 76mm; object-fit: contain; }
#methods img:not(.math) { max-height: 48mm; }
#selection-passing-settings-by-method + p + table td,
#selection-the-eight-argesim-repeats + p + table td { padding-top: .88mm; padding-bottom: .88mm; }
#history-a-quantizer-receives-an-external-event, #history-two-embedded-rk-pairs-for-comparison,
#history-evidence-at-the-same-physical-target,
#selection-measured-results, #selection-passing-settings-by-method,
#selection-interpreting-a-solver-choice, #selection-reproduction-and-scope,
#methods-coupled-and-mixed-methods, #methods-idas-for-a-residual-form-dae,
#archive-a-direct-dae-check-on-the-c21-diode { break-before: page; }
nav { display: flex; gap: 4mm; font-size: 9pt; margin: 2mm 0 3.2mm; }
nav a { font-weight: bold; }
"""


def typeset_math(node):
    tex = node.xpath("string(.//annotation[@encoding='application/x-tex'])")
    tex = tex.replace(r"\lVert", r"\Vert").replace(r"\rVert", r"\Vert")
    out = io.BytesIO()
    in_table = any(ancestor.tag == "table" for ancestor in node.iterancestors())
    in_header = any(ancestor.tag == "th" for ancestor in node.iterancestors())
    with rc_context({"savefig.transparent": True, "svg.hashsalt": "argesim-formeln"}):
        depth = math_to_image(
            "$" + tex + "$",
            out,
            prop=FontProperties(size=8.8 if in_table else 10),
            format="svg",
            color="white" if in_header else "#202c34",
        )
    encoded = base64.b64encode(out.getvalue()).decode("ascii")
    replacement = html.Element(
        "img",
        src="data:image/svg+xml;base64," + encoded,
        alt=tex,
        attrib={"class": "math", "style": f"vertical-align: -{depth}pt"},
    )
    replacement.tail = node.tail
    node.getparent().replace(node, replacement)


def chapter(filename, revision):
    prefix, title = BOOK[filename]
    source = DOCS / filename
    student = filename.startswith("lehrbuch/")
    output = subprocess.check_output(
        [
            "pandoc",
            "-f",
            "gfm+tex_math_dollars",
            "-t",
            "html5",
            "--mathml",
            "--fail-if-warnings",
            "--no-highlight",
            "--wrap=none",
            str(source),
        ],
        text=True,
    )
    book = html.fragment_fromstring(output, create_parent="article")
    book.set("id", prefix)
    book.set("lang", "de" if student else "en")
    for node in book.xpath(".//*[@id]"):
        node.set("id", prefix + "-" + node.get("id"))
    heading = book.find("h1")
    heading.set("data-chapter", title)
    if student:
        book.set("class", "lesson")
        label = html.Element("div", attrib={"class": "section-number"})
        label.text = (
            "KAPITEL " + source.name[:2] if source.name[:2].isdigit() else "QUELLEN"
        )
        heading.addprevious(label)
        for img in book.xpath(".//img"):
            path = (source.parent / img.get("src")).resolve()
            if not path.is_file():
                raise FileNotFoundError(path)
            img.set("src", path.relative_to(DOCS).as_posix())
            paragraph = img.getparent()
            if paragraph.tag == "p" and len(paragraph) == 1:
                paragraph.tag = "figure"
                caption = etree.SubElement(paragraph, "figcaption")
                number, separator, description = img.get("alt", "").partition(" · ")
                if separator:
                    etree.SubElement(caption, "strong").text = number
                    caption[0].tail = "  " + description
                else:
                    caption.text = number
    if prefix == "history":
        nav = html.Element("nav")
        for chapter_id, label in CHAPTERS.values():
            link = html.Element("a", href="#" + chapter_id)
            link.text = label
            nav.append(link)
        heading.addnext(nav)
    for node in book.xpath(".//math"):
        if student and node.get("display") == "block" and node.getparent().tag == "p":
            node.getparent().set("class", "equation")
        typeset_math(node)
    for link in book.xpath(".//a[@href]"):
        href = urlsplit(link.get("href"))
        if href.scheme:
            continue
        if not href.path and href.fragment in {v[0] for v in CHAPTERS.values()}:
            continue
        dest = (source.parent / href.path).resolve() if href.path else source
        if not dest.is_file():
            raise FileNotFoundError(dest)
        key = dest.relative_to(DOCS).as_posix() if dest.is_relative_to(DOCS) else None
        if dest == DOCS / "ARGESIM_SOLVER_STUDY.pdf":
            target = "#inhalt"
        elif key in BOOK:
            target = "#" + BOOK[key][0]
            if href.fragment:
                target += "-" + href.fragment
        else:
            target = f"{GITHUB}/blob/{revision}/{dest.relative_to(ROOT).as_posix()}"
            if href.fragment:
                target += "#" + href.fragment
        link.set("href", target)
    return etree.tostring(book, encoding="unicode", method="html")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--revision",
        required=True,
        help="40-hex Git revision of the sources and evidence",
    )
    parser.add_argument(
        "--output", type=Path, default=DOCS / "ARGESIM_SOLVER_STUDY.pdf"
    )
    args = parser.parse_args()
    if not re.fullmatch(r"[a-f0-9]{40}", args.revision):
        parser.error("specify a full Git commit SHA")
    if args.output.resolve() == (DOCS / "ARGESIM_SOLVER_STUDY.pdf").resolve():
        subprocess.run([sys.executable, str(ROOT / "scripts" / "build_studienbuch.py")], check=True)
        return
    contents = front_matter() + "".join(chapter(name, args.revision) for name in BOOK)
    page = (
        f"<html lang='de'><head><meta charset='UTF-8'><title>{TITLE} · ARGESIM</title>"
        f'<meta name="author" content="{escape(AUTHOR)}">'
        f"<style>{(CSS + CSS_BOOK).replace('REVISION', args.revision[:10])}</style></head>"
        f"<body>{contents}</body></html>"
    )
    document = html.fromstring(page)
    ids = document.xpath("//@id")
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate book destination")
    for href in document.xpath("//a[starts-with(@href, '#')]/@href"):
        if href[1:] not in ids:
            raise ValueError(f"Missing book destination: {href}")
    # Base URL resolves the local scientific figures without network requests.
    HTML(string=page, base_url=DOCS.as_uri() + "/").write_pdf(args.output)


if __name__ == "__main__":
    main()


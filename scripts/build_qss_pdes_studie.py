"""Typeset the QSS/PDES paper with Pandoc, XeLaTeX and Inkscape."""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / 'docs/lehrbuch/QSS_PDES_Studie.md'
BASE = 'https://github.com/5H3LL3H5/argesim-hyperposition-benchmarks'
HEADER = r'''
\usepackage{fancyhdr,titlesec}
\definecolor{Ink}{HTML}{193747}
\definecolor{Sea}{HTML}{00675E}
\definecolor{Slate}{HTML}{49616D}
\pagestyle{fancy}\fancyhf{}
\fancyhead[L]{\sffamily\small\color{Slate}Numerische Simulation dynamischer Systeme}
\fancyhead[R]{\sffamily\small\color{Sea}QSS und PDES}
\fancyfoot[L]{\sffamily\footnotesize\color{Slate}Forschungsstudie zur Gesamtausgabe v9.19}
\fancyfoot[R]{\sffamily\bfseries\color{Sea}\thepage}
\renewcommand{\headrulewidth}{0.3pt}
\titleformat{\section}{\sffamily\bfseries\LARGE\color{Ink}}{}{0pt}{}
\titleformat{\subsection}{\sffamily\bfseries\Large\color{Ink}}{}{0pt}{}
\titleformat{\subsubsection}{\sffamily\bfseries\large\color{Sea}}{}{0pt}{}
\AtBeginDocument{\hypersetup{pdftitle={Wann lässt sich ein QSS-Ereignis parallel verarbeiten?},pdflang={de-DE}}}
\AtBeginDocument{\renewcommand{\figurename}{Abbildung}}
\setlength{\emergencystretch}{3em}
'''

# Reserve width for prose, formulae and quantities in their respective columns.
TABLES = """
function Table(t)
  local first = pandoc.utils.stringify(t.head.rows[1].cells[1].contents)
  local by_heading = {
    Architektur = {0.19, 0.36, 0.45}, Ordnung = {0.15, 0.34, 0.51},
    Merkmal = {0.17, 0.415, 0.415}, ["Serielle Kontrolle"] = {0.52, 0.23, 0.25},
    ["Messgröße"] = {0.23, 0.77}
  }
  local widths = by_heading[first]
  if widths then
    for i, width in ipairs(widths) do t.colspecs[i][2] = width end
  end
  return t
end
"""


def print_link(match):
    target, _, fragment = match[1].partition('#')
    if target.startswith(('http://', 'https://')) or not target:
        return match[0]
    if target.endswith('.svg'):
        return '](rollback.pdf){width=76%}'
    item = (PAPER.parent / target).resolve()
    if not item.exists():
        raise ValueError(f'Missing paper reference: {target}')
    kind = 'tree' if item.is_dir() else 'blob'
    path = quote(item.relative_to(ROOT).as_posix())
    return f']({BASE}/{kind}/main/{path}' + (f'#{fragment}' if fragment else '') + ')'


def build(output):
    env = {**os.environ, 'SOURCE_DATE_EPOCH': '1795651200', 'FORCE_SOURCE_DATE': '1', 'TZ': 'UTC'}
    with TemporaryDirectory() as tmp:
        work = Path(tmp)
        svg = PAPER.with_name('QSS_PDES_Rollback.svg')
        subprocess.run(['inkscape', str(svg), '--export-type=pdf', '--export-filename=rollback.pdf'], cwd=work, check=True, env=env)
        markdown = re.sub(r'\]\(([^)]+)\)', print_link, PAPER.read_text(encoding='utf-8'))
        # The four main sections are also the natural reading breaks in print.
        markdown = re.sub(r'(?m)^## ([2-4]\. )', lambda m: '\\clearpage\n\n## ' + m[1], markdown)
        (work/'paper.md').write_text(markdown, encoding='utf-8')
        # xdvipdfmx otherwise includes its temporary directory in the document ID.
        inputs = markdown.encode() + svg.read_bytes() + HEADER.encode() + TABLES.encode()
        identity = hashlib.sha256(inputs).hexdigest()[:32]
        trailer = rf'\AtBeginDvi{{\special{{pdf:trailerid [<{identity}><{identity}>]}}}}'
        (work/'header.tex').write_text(HEADER + trailer, encoding='utf-8')
        (work/'columns.lua').write_text(TABLES, encoding='utf-8')
        subprocess.run(['pandoc', 'paper.md', '-f', 'markdown+raw_tex', '--pdf-engine=xelatex',
                        '-V', 'mainfont=Noto Serif', '-V', 'sansfont=Noto Sans Display',
                        '-V', 'monofont=DejaVu Sans Mono', '-V', 'monofontoptions=Scale=0.78',
                        '-V', 'mathfont=Latin Modern Math', '-V', 'geometry=a4paper,margin=21mm,headheight=15pt',
                        '-V', 'fontsize=10pt', '-V', 'colorlinks=true', '-V', 'urlcolor=Sea',
                        '--include-in-header=header.tex', '--lua-filter=columns.lua', '--no-highlight', '-o', str(output.resolve())],
                       cwd=work, env=env, check=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=PAPER.with_suffix('.pdf'))
    build(parser.parse_args().output)

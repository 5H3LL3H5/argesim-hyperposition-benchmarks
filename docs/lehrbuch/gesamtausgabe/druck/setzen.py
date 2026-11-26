import re
import subprocess
from pathlib import Path

work = Path(__file__).resolve().parent.parent
tex = work / "druck"
md = (work / "lehrbuch_numerische_simulation.md").read_text()
md = re.sub(
    r'<a id="([^"]+)"></a>\s*\n(#{1,3} [^\n]+)', lambda m: m[2] + " {#" + m[1] + "}", md
)
# A text or table can also carry a stable reference without becoming a heading.
md = re.sub(
    r'<a id="([^"]+)"></a>',
    lambda m: (
        "\x60"
        + r"\phantomsection\hypertarget{"
        + m[1]
        + r"}{}\label{"
        + m[1]
        + "}\x60{=latex}"
    ),
    md,
)
paginas = md.split("<!-- Buchseite -->")
chunks = []
teil = "Kapitel 1"
for i, p in enumerate(paginas):
    clean = p.lstrip()
    chapter = re.match(r"^# Kapitel (\d+) ·", clean)
    if clean.startswith("# Mathematische Grundlagen"):
        teil = "Mathematische Grundlagen"
    if chapter:
        teil = "Kapitel " + chapter[1]
    if clean.startswith("# Anhang A"):
        teil = "Anhang A"
    if clean.startswith("# Anhang B"):
        teil = "Anhang B"
    if clean.startswith("# Anhang C"):
        teil = "Anhang C"
    if clean.startswith("# Anhang D"):
        teil = "Anhang D"
    if clean.startswith("# Quellen und Rechenstand"):
        teil = "Quellen und Rechenstand"
    if i:
        head = "Kapitelfahrplan" if i < 4 else teil
        s = r"\buchseite{" + head + "}"
        if i == 1:
            s += r"\kleinsatz"
        if i == 4:
            s += r"\normalsatz"
        chunks.append("\n\n```{=latex}\n" + s + "\n```\n\n")
    chunks.append(p.strip() + "\n")
frag = subprocess.run(
    ["pandoc", "-f", "markdown", "-t", "latex", "--no-highlight", "--wrap=none"],
    input="".join(chunks),
    text=True,
    capture_output=True,
    check=True,
).stdout
header = r"""\documentclass[11pt,a4paper]{article}
\usepackage[a4paper,left=19.5mm,right=19.5mm,top=19mm,bottom=20mm,headheight=24pt,headsep=9pt,footskip=27pt]{geometry}
\usepackage{fontspec,amsmath,unicode-math}
\setmainfont{Noto Serif}
\setsansfont{Noto Sans Display}
\setmonofont[Scale=0.85]{DejaVu Sans Mono}
\setmathfont{Latin Modern Math}
\usepackage{graphicx,xcolor,booktabs,array,longtable,tabularx,fancyvrb,fancyhdr,titlesec,enumitem}
\definecolor{ink}{HTML}{1D3240}
\definecolor{navy}{HTML}{173549}
\definecolor{sea}{HTML}{00675E}
\definecolor{slate}{HTML}{49616D}
\definecolor{rulegray}{HTML}{C2D4D3}
\usepackage[unicode=true,bookmarksopen=true,bookmarksopenlevel=2,bookmarksnumbered=false,pdfdisplaydoctitle=true,colorlinks=true,linkcolor=sea,urlcolor=sea]{hyperref}
\usepackage{bookmark}
\hypersetup{pdftitle={Numerische Simulation dynamischer Systeme · Revision v9.21 · Druckfassung},pdfauthor={Christian Stenzel},pdfsubject={Druckfassung v9.21, mathematische Grundlagen, Kapitel 1 bis 18 und Anhänge A bis D},pdflang={de-DE}}
\setcounter{secnumdepth}{-1}\setcounter{tocdepth}{3}
\pagestyle{fancy}\fancyhf{}
\newcommand{\kopfteil}{}
\fancyhead[L]{{\sffamily\fontsize{8.4}{10}\selectfont\color{slate}Numerische Simulation dynamischer Systeme}}
\fancyhead[R]{{\sffamily\fontsize{8.4}{10}\selectfont\color{sea}\kopfteil}}
\fancyfoot[L]{{\sffamily\fontsize{8.4}{10}\selectfont\color{slate}Christian Stenzel}}
\fancyfoot[R]{{\sffamily\bfseries\small\color{sea}\thepage}}
\renewcommand{\headrulewidth}{.35pt}
\renewcommand{\headrule}{\hbox to\headwidth{\color{rulegray}\leaders\hrule height \headrulewidth\hfill}}
\fancypagestyle{titel}{\fancyhf{}\renewcommand{\headrulewidth}{0pt}\fancyfoot[L]{{\sffamily\fontsize{8.4}{10}\selectfont\color{slate}Revision v9.21 · Parallele QSS und Kavität im Vollgitter}}\fancyfoot[R]{{\sffamily\bfseries\small\color{sea}\thepage}}}
\titleformat{\section}{\sffamily\bfseries\color{navy}\fontsize{25.5}{30.5}\selectfont}{}{0pt}{}
\titleformat{\subsection}{\sffamily\bfseries\color{sea}\fontsize{17.4}{21.3}\selectfont}{}{0pt}{}
\titleformat{\subsubsection}{\sffamily\bfseries\color{navy}\fontsize{14}{18}\selectfont}{}{0pt}{}
\titlespacing*{\section}{0pt}{0pt}{9pt}
\titlespacing*{\subsection}{0pt}{9pt}{7pt}
\titlespacing*{\subsubsection}{0pt}{8pt}{5pt}
\setlength{\parindent}{0pt}\setlength{\parskip}{5pt}
\newcommand{\normalsatz}{\fontsize{11.1}{14.9}\selectfont}
\newcommand{\kleinsatz}{\fontsize{10.5}{13.9}\selectfont}
\newcommand{\buchseite}[1]{\clearpage\renewcommand{\kopfteil}{#1}}
\newcommand{\buchtitel}{\pdfbookmark[0]{Numerische Simulation dynamischer Systeme · Revision v9.21 · Druckfassung}{buchanfang}{\sffamily\bfseries\color{navy}\fontsize{33}{37}\selectfont Numerische Simulation\\dynamischer Systeme\par}\vspace{4pt}}
\newcommand{\autorenzeile}{{\sffamily\bfseries\large\color{sea}Christian Stenzel}\par\vspace{-2pt}{\sffamily\small\color{slate}Gesamtausgabe · Revision v9.21 · Parallele QSS und Kavität im Vollgitter · 18 Fachkapitel und vier Anhänge}\par\vspace{8pt}}
\newcommand{\tightlist}{\setlength{\itemsep}{4pt}\setlength{\parskip}{0pt}}
\setlist[enumerate]{leftmargin=1.65em,labelsep=.5em,topsep=2pt}
\newcommand{\bild}[2]{\par\addvspace{6pt}\noindent\includegraphics[width=0.99\linewidth]{#1}\par\nopagebreak\vspace{-2pt}{\sffamily\fontsize{9.4}{12}\selectfont\color{slate}#2\par}\addvspace{5pt}}
\setlength{\abovedisplayskip}{7pt}\setlength{\belowdisplayskip}{7pt}
\setlength{\abovedisplayshortskip}{4pt}\setlength{\belowdisplayshortskip}{4pt}
\linespread{1.02}
\begin{document}
\color{ink}\normalsatz\raggedright\setlength{\emergencystretch}{2em}
\thispagestyle{titel}
"""
frag = frag.replace(
    r"\section{Numerische Simulation dynamischer Systeme}\label{numerische-simulation-dynamischer-systeme}",
    r"\buchtitel",
)
frag = frag.replace(
    r"\textbf{Christian Stenzel}\\"
    + "\nGesamtausgabe · Revision v9.21 · Parallele QSS und Kavität im Vollgitter · 18 Fachkapitel und vier Anhänge",
    r"\autorenzeile",
)
frag = re.sub(
    r"\\begin\{figure\}\s*\\centering\s*\\includesvg\{abbildungen/(\w+)\.svg\}\s*\\caption\{(.*?)\}\s*\\end\{figure\}",
    lambda m: r"\bild{" + m[1] + ".pdf}{" + m[2] + "}",
    frag,
    flags=re.DOTALL,
)
tabellen = iter(
    [
        r"@{}p{0.29\linewidth}X@{}",
        r"@{}p{0.23\linewidth}X@{}",
        r"@{}Xrrr@{}",
        r"@{}Xrrr@{}",
        r"@{}rXr@{}",
        r"@{}Xrrr@{}",
        r"@{}Xrrrrr@{}",
        r"@{}Xrrr@{}",
        r"@{}>{\raggedright\arraybackslash}p{.18\linewidth}>{\raggedright\arraybackslash}X>{\raggedright\arraybackslash}X@{}",
        r"@{}>{\raggedright\arraybackslash}p{.18\linewidth}>{\raggedright\arraybackslash}X>{\raggedright\arraybackslash}X@{}",
    ]
)
tabellen = iter([*tabellen, r"@{}Xrrr@{}", r"@{}>{\raggedright\arraybackslash}Xrr@{}"])


def tabelle(m, spalten=None):
    raw = m[1]
    kopf = raw.split("\\toprule\\noalign{}\n", 1)[1].split("\\midrule", 1)[0].strip()
    kopf = (
        re.sub(
            r"\\begin\{minipage\}\[b\]\{\\linewidth\}\\(?:raggedright|raggedleft|centering)",
            "",
            kopf,
        )
        .replace(r"\end{minipage}", "")
        .removesuffix(r"\\")
        .strip()
    )
    kopf = " & ".join(r"\textbf{" + x.strip() + "}" for x in kopf.split("&"))
    body = raw.split(r"\endlastfoot", 1)[1].strip()
    return (
        r"\par\addvspace{4pt}{\sffamily\fontsize{10.1}{13.2}\selectfont\renewcommand{\arraystretch}{1.14}\setlength{\tabcolsep}{5pt}\begin{tabularx}{\linewidth}{"
        + (next(tabellen) if spalten is None else spalten)
        + "}\n"
        + r"\toprule"
        + "\n"
        + kopf
        + r" \\"
        + "\n"
        + r"\midrule"
        + "\n"
        + body
        + "\n"
        + r"\bottomrule\end{tabularx}\par}\addvspace{4pt}"
    )


operator_tables = 0
operator_width = {
    "Prüfvariante": [0.225] + [0.775 / 7] * 7,
    "Fehlerzerlegung": [0.56, 0.22, 0.22],
    "Knickvariante": [0.18, 0.18, 0.18, 0.19, 0.27],
    "Kavitätsvariante": [0.22, 0.17, 0.17, 0.145, 0.145, 0.15],
    "Zeitvariante": [0.14, 0.14, 0.15, 0.15, 0.14, 0.14, 0.14],
    "Kalibriervariante": [0.22, 0.195, 0.195, 0.195, 0.195],
}
table_count = 0
raumtabelle_count = 0
mess_tabelle_count = 0
studien_tabelle_count = 0


def gesamt_tabelle(m):
    global \
        table_count, \
        raumtabelle_count, \
        operator_tables, \
        mess_tabelle_count, \
        studien_tabelle_count
    if all(
        kopf in m[1]
        for kopf in ("Raumverfahren", "Typische Stärke", "Eigene Prüfaufgabe")
    ):
        raumtabelle_count += 1
        return tabelle(
            m,
            r"@{}>{\raggedright\arraybackslash}p{0.19\linewidth}"
            r">{\raggedright\arraybackslash}X>{\raggedright\arraybackslash}X@{}",
        )
    raw = m[1]
    first = raw.index(r"\toprule")
    first_row = raw[first:].split(r"\midrule", 1)[0]
    for label, spec in (
        ("konservativ (ms)", r"@{}l*{5}{>{\raggedleft\arraybackslash}X}@{}"),
        ("MPI-Prozesse", r"@{}l*{5}{>{\raggedleft\arraybackslash}X}@{}"),
        ("Serieller Aufruf", r"@{}lrrX@{}"),
        ("zu D2Q9 (", r"@{}l*{4}{>{\raggedleft\arraybackslash}X}@{}"),
        ("QSS3 (s)", r"@{}l*{4}{>{\raggedleft\arraybackslash}X}@{}"),
        ("Integrator im Vollgitter", r"@{}Xrrr@{}"),
        ("Aufteilung der Kavität", r"@{}Xrrrr@{}"),
        ("Vollgitterverfahren", r"@{}Xrrrr@{}"),
        ("QSS-Lauf", r"@{}Xrrrrr@{}"),
        ("Eingangskern", r"@{}lXX@{}"),
    ):
        if label in first_row:
            return (
                tabelle(m, spec)
                .replace(r"\fontsize{10.1}{13.2}", r"\fontsize{9.15}{11}")
                .replace("{5pt}", "{3pt}")
            )
    supplements = {
        "Operatorversuch": r"@{}>{\raggedright\arraybackslash}p{.14\linewidth}>{\raggedright\arraybackslash}p{.245\linewidth}>{\raggedright\arraybackslash}p{.27\linewidth}>{\raggedright\arraybackslash}X@{}",
        "Vergleichsfall": r"@{}>{\raggedright\arraybackslash}p{.14\linewidth}>{\raggedright\arraybackslash}p{.235\linewidth}>{\raggedright\arraybackslash}p{.24\linewidth}>{\raggedright\arraybackslash}X@{}",
        "Quelltest": r"@{}Xrrr@{}",
        "Kandidat auf": r"@{}Xrrrr@{}",
        "Zeitkern": r"@{}Xrrrrr@{}",
        "Neue Innenstarts": r"@{}Xrr@{}",
        "Tankanfrage": r"@{}>{\raggedright\arraybackslash}p{.16\linewidth}>{\raggedright\arraybackslash}p{.18\linewidth}>{\raggedright\arraybackslash}p{.25\linewidth}>{\raggedright\arraybackslash}X@{}",
        "Breitentest": r"@{}Xrrr@{}",
    }
    for label, format_spec in supplements.items():
        if label in first_row:
            table = tabelle(m, format_spec)
            if label == "Operatorversuch":
                table = table.replace(
                    r"\textbf{Operatorversuch}", r"\textbf{Operator\-versuch}"
                )
            if label in ("Operatorversuch", "Vergleichsfall"):
                table = table.replace(
                    r"\fontsize{10.1}{13.2}", r"\fontsize{9.3}{12}"
                ).replace("{5pt}", "{4pt}")
            if label in ("Kandidat auf", "Zeitkern"):
                table = table.replace(
                    r"\fontsize{10.1}{13.2}", r"\fontsize{8.4}{10.9}"
                ).replace("{5pt}", "{3pt}")
            return table
    if "Atlasauftrag" in first_row:
        return tabelle(m, r"@{}lrrrrrr@{}")
    if "Transformationskern" in first_row:
        return tabelle(m, r"@{}lrrrr@{}")
    if "Studienversuch" in first_row:
        studien_tabelle_count += 1
        return tabelle(
            m,
            r"@{}>{\raggedright\arraybackslash}p{.19\linewidth}"
            r">{\raggedright\arraybackslash}p{.32\linewidth}"
            r">{\raggedright\arraybackslash}X@{}",
        )
    if "Messaufgabe" in first_row:
        mess_tabelle_count += 1
        return tabelle(
            m,
            r"@{}>{\raggedright\arraybackslash}p{.21\linewidth}"
            r">{\raggedright\arraybackslash}X"
            r">{\raggedright\arraybackslash}p{.25\linewidth}rr@{}",
        )
    special = next(
        (widths for label, widths in operator_width.items() if label in first_row), None
    )
    if special is not None:
        operator_tables += 1
    else:
        table_count += 1
        if table_count <= 12:
            return tabelle(m)
    heads = (
        raw[first:]
        .split(r"\midrule", 1)[0]
        .split(r"\toprule", 1)[1]
        .replace(r"\noalign{}", "")
        .strip()
        .removesuffix(r"\\")
        .strip()
    )

    def strips(x):
        x = re.sub(
            r"\\begin\{minipage\}\[[tbc]\]\{\\linewidth\}\\(?:raggedright|raggedleft|centering)\s*",
            "",
            x,
        )
        return x.replace(r"\end{minipage}", "").replace(r"\strut", "").strip()

    h = [strips(k) for k in re.split(r"(?<!\\)&", heads)]
    body = strips(raw.split(r"\endlastfoot", 1)[1])
    n = len(h)
    width = {
        13: [0.21, 0.79],
        14: [0.21, 0.16, 0.10, 0.26, 0.27],
        15: [0.16, 0.22, 0.62],
        16: [0.08, 0.23, 0.21, 0.26, 0.22],
        17: [0.08, 0.21, 0.21, 0.22, 0.28],
        18: [0.24, 0.32, 0.44],
        19: [0.38, 0.34, 0.28],
        21: [0.28, 0.23, 0.21, 0.28],
        22: [0.11, 0.17, 0.17, 0.17, 0.22, 0.16],
        32: [0.16, 0.32, 0.19, 0.18, 0.15],
        33: [0.23, 0.40, 0.37],
        36: [0.22, 0.78],
        37: [0.24] + [0.095] * 8,
        39: [0.13, 0.48, 0.39],
        48: [0.32, 0.18, 0.19, 0.15, 0.16],
        49: [0.32, 0.21, 0.21, 0.26],
        50: [0.30, 0.70],
        **{i: [0.12, 0.30, 0.58] for i in range(51, 55)},
        55: [0.13, 0.18, 0.15, 0.54],
    }.get(table_count, [1 / n] * n)
    if special is not None:
        width = special
    if len(width) != n:
        width = [1 / n] * n
    spec = (
        "@{}"
        + "".join(
            r">{\raggedright\arraybackslash}p{\dimexpr "
            + f"{w:.4f}"
            + r"\linewidth-"
            + f"{max(0, 2 * (n - 1)) * w:.4f}"
            + r"\tabcolsep\relax}"
            for w in width
        )
        + "@{}"
    )
    row = " & ".join(r"\textbf{" + x + "}" for x in h) + r" \\"
    return (
        r"\par\begingroup\sffamily"
        + (
            r"\fontsize{10.4}{14.4}"
            if special is not None or table_count >= 40
            else r"\fontsize{9.0}{11.6}"
        )
        + r"\selectfont\setlength{\tabcolsep}{3pt}\setlength{\LTpre}{4pt}\setlength{\LTpost}{4pt}\renewcommand{\arraystretch}{1.12}\begin{longtable}{"
        + spec
        + "}\n"
        + r"\toprule"
        + "\n"
        + row
        + "\n"
        + r"\midrule\endfirsthead"
        + "\n"
        + row
        + "\n"
        + r"\midrule\endhead\bottomrule\endfoot\bottomrule\endlastfoot"
        + "\n"
        + body
        + "\n"
        + r"\end{longtable}\endgroup"
    )


frag = re.sub(
    r"\\begin\{longtable\}(.*?)\\end\{longtable\}", gesamt_tabelle, frag, flags=re.DOTALL
)

vstart = r"\begin{Verbatim}[fontsize=\small,formatcom=\color{navy},frame=leftline,framesep=8pt,xleftmargin=9pt,rulecolor=\color{sea}]"
vend = r"\end{Verbatim}"
frag = frag.replace(r"\begin{verbatim}", vstart).replace(r"\end{verbatim}", vend)


def code_umbruch(stelle, titel):
    global frag
    if not frag.count(stelle) == 1:
        raise RuntimeError(stelle)
    frag = frag.replace(
        stelle,
        "\n"
        + vend
        + "\n"
        + r"\buchseite{Kapitel 1}\subsubsection{"
        + titel
        + "}\n"
        + vstart
        + "\n"
        + stelle.lstrip("\n"),
    )


code_umbruch(
    '\n\n\nif __name__ == "__main__":\n    h, n = 0.003, 4',
    "Die Schrittfolgen mit der Referenz vergleichen",
)
frag = frag.replace("−", r"\ensuremath{-}").replace(
    "Geschwindigkeitsprofile", r"Geschwindigkeits\-profile"
)
frag = frag.replace(
    r"\texttt{5H3LL3H5/argesim-hyperposition-benchmarks}",
    r"\texttt{5H3LL3H5/\allowbreak argesim-hyperposition-\allowbreak benchmarks}",
)
frag = frag.replace(
    r"\section{Kapitel 5 · Hybride Systeme, Diskontinuitäten und Ereignissteuerung}",
    r"\section[Kapitel 5 · Hybride Systeme, Diskontinuitäten und Ereignissteuerung]{Kapitel 5 · Hybride Systeme,\\Diskontinuitäten und Ereignissteuerung}",
)
for title, lines in [
    (
        "Kapitel 7 · Räumliche Diskretisierung und Linienmethode",
        r"Kapitel 7 · Räumliche Diskretisierung\\und Linienmethode",
    ),
    (
        "Kapitel 8 · Mesoskopische Strömungssimulation mit der Lattice-Boltzmann-Methode",
        r"Kapitel 8 · Mesoskopische\\Strömungssimulation mit der\\Lattice-Boltzmann-Methode",
    ),
]:
    original = r"\section{" + title + "}"
    assert original in frag, title
    frag = frag.replace(
        original, r"\section[" + title + r"]{\raggedright " + lines + "}"
    )
# In der Druckfassung nennt jede verlinkte Kapitelbeschreibung auch die Einstiegsseite.
# Nur der Fahrplan vor dem ersten Volltextkapitel wird ersetzt.
roadmap, rest = frag.split(r"\section{Mathematische Grundlagen}", 1)
roadmap = re.sub(
    r"(\\textbf\{\\hyperref\[([^\]]+)\]\{(?:Mathematische Grundlagen|(?:\d+ ·|Anhang [ABCD] ·)[^{}]+)\})\}",
    lambda m: m[1] + r"\,\textnormal{\small(S.\,\pageref*{" + m[2] + "})}}",
    roadmap,
)
frag = roadmap + r"\section{Mathematische Grundlagen}" + rest

# Provide named PDF destinations for the revision findings that are also section labels.
frag = re.sub(
    r"(\\(?:sub)*section\{[^\n]*?\}\\label\{((?:revision|auflage|druck)-[^}]+)\})",
    lambda m: m[1] + r"\hypertarget{" + m[2] + r"}{}",
    frag,
)
counts = (
    frag.count(r"\bild{"),
    table_count,
    raumtabelle_count,
    operator_tables,
    mess_tabelle_count,
    studien_tabelle_count,
)
assert counts == (92, 55, 1, 6, 4, 1), counts
(tex / "buch.tex").write_text(header + frag + "\n" + r"\end{document}" + "\n")

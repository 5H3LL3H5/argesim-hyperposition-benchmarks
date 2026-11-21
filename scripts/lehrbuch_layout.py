"""Book front matter, contents and print styles for the student edition."""

from html import escape

# Filenames, short running titles and the reader's question for the contents.
LESSONS = {
    "01-anfangswertproblem.md": (
        "Anfangswertprobleme und Fehler",
        "Wie genau ist ein Rechenschritt?",
    ),
    "02-runge-kutta.md": (
        "Explizite Runge–Kutta-Verfahren",
        "Wie wählen wir Stufen und Schrittweite?",
    ),
    "03-steifheit.md": (
        "Steife und nichtsteife Systeme",
        "Warum kann eine glatte Lösung teuer sein?",
    ),
    "04-pde.md": (
        "Partielle Differentialgleichungen",
        "Was ändert ein feineres Ortsgitter?",
    ),
    "05-dae.md": (
        "Differential-algebraische Gleichungen",
        "Welche Startwerte sind miteinander verträglich?",
    ),
    "06-devs.md": (
        "DEVS und die Geschichte von QSS",
        "Wie wird aus einem Zustand eine Nachricht?",
    ),
    "07-qss.md": ("QSS-Verfahren und Solverwahl", "Wann spart Quantisierung Arbeit?"),
    "08-argesim.md": ("ARGESIM-Fallstudien", "Was zeigen C12, C05, C21 und C13?"),
    "09-praktikum.md": ("Numerisches Praktikum", "Wie reproduziere ich den Vergleich?"),
    "10-loesungen.md": ("Musterlösungen und Glossar", "Wie prüfe ich meine Rechnung?"),
    "literatur.md": (
        "Bibliographie und Quellenverzeichnis",
        "Wo finde ich Theorie, Originalarbeiten und Daten?",
    ),
}


def anchor(filename):
    return "literatur" if filename == "literatur.md" else "kap-" + filename[:2]


TITLE = "Numerische Simulation dynamischer Systeme"
AUTHOR = "Christian Stenzel"
CSS_BOOK = """
@page lehrbuch {
  size: A4; margin: 18mm 20mm 17mm;
  @top-left { content: "ARGESIM   /   NUMERISCHE SIMULATION"; font: bold 7.7pt "Open Sans",sans-serif;
    letter-spacing: .7pt; color: #00685f; }
  @top-right { content: string(kapitel); font: 7.7pt "Open Sans", sans-serif; color: #465c68; }
  @bottom-left { content: "Lehrbuch   ·   Quellenstand REVISION"; font: 8pt "Open Sans", sans-serif; color: #465c68; }
}
@page coverpage {
  size: A4; margin: 0; background: #102e3c;
  @top-left { content: none; } @top-right { content: none; }
  @bottom-left { content: none; } @bottom-right { content: none; }
}
.cover { page: coverpage; break-after: page; box-sizing: border-box;
  padding: 25mm 21mm 10mm; color: #f6f3e9; }
.cover .imprint { border-top: 1.5pt solid #81c9b3; padding-top: 4mm; color: #b7e1cf;
  font: 700 10pt "Open Sans", sans-serif; letter-spacing: 1.2pt; }
.cover h1 { color: #f8f5ea; border: 0; margin: 24mm 0 7mm; padding: 0;
  font: bold 43pt/1.03 "DejaVu Serif",serif; letter-spacing: -1.8pt; bookmark-level: none; }
.cover .subtitle { font: 16pt/1.45 "Open Sans",sans-serif; color: #d0dfdd; }
.cover .byline { margin: 5mm 0 0; font: 600 14pt/1.3 "Open Sans",sans-serif; color: #f8f5ea; }
.cover figure { margin: 12mm -2mm 10mm; }
.cover img:not(.math) { width: 100%; max-height: none; }
.cover .meta { margin-top: 9mm; border-top: .65pt solid #6a8791; padding-top: 4mm;
  font: 10pt/1.55 "Open Sans",sans-serif; color: #d4e2df; }
.toc,.lesson { page: lehrbuch; break-before: page; }
.toc h1,.lesson h1,.lesson h2 { font-family: "DejaVu Serif",serif; color: #153748; }
.toc h1,.lesson h1 { font-size: 23pt; line-height: 1.12; padding-top: 2.8mm; margin: 0 0 4mm;
  border-top: 1.4pt solid #00776f; letter-spacing: -.5pt; }
.toc h1 { string-set: kapitel "Inhalt"; }
.lesson h1 { string-set: kapitel attr(data-chapter); }
.lesson h2 { font-size: 19pt; margin: 0 0 4mm; line-height: 1.16; break-before: page;
  border-top: 1pt solid #90b9af; padding-top: 3.5mm; letter-spacing: -.4pt; }
.lesson h3 { font: bold 11.1pt/1.2 "Open Sans",sans-serif; color: #00695f; margin: 3mm 0 1.4mm; }
.lesson { font: 10.4pt/1.39 "Open Sans",sans-serif; color:#213747; }
.lesson p { margin: 2mm 0; }
.lesson strong { color: #18394b; }
.lesson blockquote { margin: 3.5mm 0 0; padding: 2.1mm 4mm; background: #edf5f0;
  border-left: 2.5pt solid #04796c; break-inside: avoid; }
.lesson blockquote p { margin: 0; }
.lesson figure { margin: 3.8mm 0 3.3mm; padding: 2mm 0; border-block: .55pt solid #c9dcd6; }
.lesson figure img { width:100%; max-height:68mm; display:block; }
.lesson figcaption { font: 8.7pt/1.32 "Open Sans",sans-serif; margin-top: 1.6mm; color:#344c59; }
.lesson figcaption strong { color: #00665c; }
.lesson .equation { background:#f1f5f3; padding:2mm 3mm; margin:2.5mm 0; text-align:center; }
.lesson .equation img { max-width:100%; }
.lesson table { font: 9.15pt/1.29 "Open Sans",sans-serif; }
.lesson th,.lesson td { padding: 1.35mm 1.75mm; }
.lesson thead th { background:#154b59; color: white; }
.lesson td:first-child { font-weight: 600; }
.lesson code { font-size:8.9pt; }
.lesson pre { background:#eff3f4; border-left:2pt solid #41968b; margin:3mm 0; }
.lesson pre code { font-size:8.5pt; }
.lesson .section-number { color:#007365; font: bold 8pt "Open Sans",sans-serif;
  letter-spacing:1pt; margin-bottom:2mm; break-after:avoid; }
.toc { font: 10pt/1.4 "Open Sans",sans-serif; }
.toc h2 { font: bold 12pt "Open Sans",sans-serif; color:#00695f; margin:4mm 0 1mm; }
.toc .entry { margin:0; padding:1.35mm 0; border-bottom:.5pt solid #dbe4e1; }
.toc .entry a { display:block; text-decoration:none; color:#18394b; }
.toc .entry a::after { content:leader(dotted) target-counter(attr(href),page); color:#007365; font-weight:bold; }
.toc .num { color:#007365; font: bold 8.5pt "Open Sans",sans-serif; }
.toc .question { color:#465e6a; margin-left:2mm; font-size:8.1pt; }
.toc p { margin:1.4mm 0; }
"""


def front_matter():
    cover = f"""<section class="cover" lang="de"><div class="imprint">ARGESIM · LEHRBUCH</div>
<h1>Numerische<br>Simulation<br>dynamischer Systeme</h1>
<div class="subtitle">Von Runge–Kutta zur Zustandsquantisierung<br>
mit durchgerechneten ARGESIM-Fallstudien</div>
<p class="byline">Autor · {escape(AUTHOR)}</p>
<figure><img src="lehrbuch/abbildungen/titel.svg"
alt="Eine stetig fallende und wieder ansteigende Kurve, ihr stufiger Ausgang und die zugehörigen Meldungen"></figure>
<div class="meta">Studienausgabe · November 2026<br>
Grundlagen, Rechenexperimente und Musterlösungen</div></section>"""

    def entry(number, target, title, question=""):
        text = f'<span class="num">{number}</span>  <b>{escape(title)}</b>'
        if question:
            text += f'<span class="question">{escape(question)}</span>'
        return f'<p class="entry"><a href="#{target}">{text}</a></p>'

    toc = [
        '<section class="toc" id="inhalt"><h1>Inhalt und Lesewege</h1>',
        (
            "<p>Für Studierende der Ingenieurwissenschaften, Informatik und angewandten Mathematik. "
            "Vorausgesetzt werden Ableitungen, einfache Integrale und Grundkenntnisse in linearer Algebra. "
            "Für die Rechenversuche genügen elementare Python-Kenntnisse.</p>"
        ),
    ]
    for i, (key, (title, question)) in enumerate(LESSONS.items(), 1):
        if i in (1, 6, 9):
            toc.append(
                "<h2>"
                + {
                    1: "Grundlagen und Gleichungsmodelle",
                    6: "Ereignisse, QSS und ARGESIM",
                    9: "Selbststudium und Nachweise",
                }[i]
                + "</h2>"
            )
        toc.append(entry(f"{i:02}" if i <= 10 else "Q", anchor(key), title, question))
    toc += [
        "<h2>Technischer Studienanhang · englisch</h2>",
        entry("A", "history", "DEVS-Geschichte und RK-Paare"),
        entry("B", "selection", "Solverauswahl und Messprotokoll"),
        entry("C", "methods", "Methodenkatalog und DAE-Schnittstelle"),
        entry("D", "archive", "Acht ARGESIM-Fälle im Vergleich"),
        (
            "<p><b>Zum Einstieg</b> verfolgen Sie den Fühler von Kapitel 1 über 2 bis 7. "
            "Für ein Simulationspraktikum führen Kapitel 4, 5 und 8 von der Modellgleichung zur überprüfbaren Messgröße.</p></section>"
        ),
    ]
    return cover + "".join(toc)

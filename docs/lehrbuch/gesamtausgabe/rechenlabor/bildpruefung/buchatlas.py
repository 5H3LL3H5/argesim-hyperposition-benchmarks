"""Verify all captions, native source files and page numbers; build the linked print atlas."""

import csv
import re
from argparse import ArgumentParser
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile

import fitz

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def print_files(root, paths):
    """Read registered plates from the repository volume or the unpacked offline lab."""
    volume = root / "druck" / "Druckabbildungen.zip"
    if volume.is_file():
        with ZipFile(volume) as archive:
            return {
                path: archive.read(Path(path).relative_to("druck").as_posix())
                for path in paths
            }
    return {path: (root / path).read_bytes() for path in paths}


def update_index(book):
    """Bind each current caption to its SVG, vector PDF and actual printed folio."""
    index = HERE / "abbildungsverzeichnis.csv"
    with index.open(encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        headers = reader.fieldnames
        by_file = {row["grafik"]: row for row in reader}
    md = (ROOT / "lehrbuch_numerische_simulation.md").read_text()
    figures = re.findall(
        r"^!\[Abbildung ([A-G0-9]+[.][0-9]+)\. .*?\]\((abbildungen/[\w-]+[.]svg)\)",
        md,
        re.M,
    )
    pages = {}
    flags = fitz.TEXTFLAGS_DICT & ~fitz.TEXT_PRESERVE_IMAGES
    for number, page in enumerate(book, 1):
        for block in page.get_text("dict", flags=flags)["blocks"]:
            for line in block.get("lines", []):
                for span in line["spans"]:
                    match = re.match(
                        r"^Abbildung ([A-G0-9]+[.][0-9]+)[.] ", span["text"]
                    )
                    if (
                        match
                        and span["color"] == 4809069
                        and abs(span["size"] - 9.4) < 0.1
                    ):
                        if match[1] in pages:
                            raise ValueError("Doppelte Bildnummer " + match[1])
                        pages[match[1]] = number
    if not figures or [num for num, _ in figures] != list(pages):
        raise ValueError(
            "Bildfolge in Manuskript und Druckausgabe stimmt nicht überein."
        )
    vectors = {svg: "druck/" + Path(svg).stem + ".pdf" for _, svg in figures}
    plates = print_files(ROOT, vectors.values())
    rows = []
    for num, svg in figures:
        vector = vectors[svg]
        row = dict(by_file.get(svg, {}))
        with fitz.open(stream=plates[vector], filetype="pdf") as plate:
            page = plate[0]
            row.update(
                abbildung=num,
                buchseite=pages[num],
                grafik=svg,
                druck=vector,
                breite_pt=round(page.rect.width, 3),
                hoehe_pt=round(page.rect.height, 3),
                vektorpfade=len(page.get_drawings()),
                bildobjekte=len(page.get_images()),
                sha256_svg=sha256((ROOT / svg).read_bytes()).hexdigest(),
                sha256_pdf=sha256(plates[vector]).hexdigest(),
            )
        if num == "G.1":
            row.update(
                titel="Zwei Uhren für dieselbe Temperaturmessung",
                befund="Skalen und drei Messwerte aus dem Abkühlgesetz, neu in v9.15",
            )
        if num == "9.9":
            row.update(
                titel="Populationsbahn, Fehler und früher Räubergipfel",
                befund="Dritter Bildteil mit gemessenem Innenstart ergänzt",
            )
        if num == "16.11":
            row.update(
                titel="Deckelumkehr und Fehler auf zwei Referenzgittern",
                befund="Lokale Felder und Fehlervergleich gegen 33² und 65² ergänzt",
            )
        if num == "16.13":
            row.update(
                titel="Strömungsbetrag und lokaler Modellabstand",
                befund="Volles 257er-Gitter, Endtakt 350 000. Beide Farbskalen und beide Ortsachsen ausgewiesen.",
            )
        if num == "16.14":
            row.update(
                titel="QSS-Zeitfehler und Kosten der Vorhersage",
                befund="Sieben Zeiten, zwei Referenzen und Messung für alle sieben Kernfamilien.",
            )
        titles_qss = {
            "6.3": "Die erste Schwelle bei QSS1 bis QSS4",
            "6.4": "Zellmitte bei CQSS1 und Halten bei BQSS1",
            "6.5": "Selbstkopplung, Paarupdate und Partition",
            "6.6": "Bandformen bei eLIQSS und CheQSS",
            "6.7": "Relative Quanten und Gruppenmeldungen",
        }
        if num in titles_qss:
            row.update(
                titel=titles_qss[num],
                befund="Neue Vektorgrafik aus Formeln oder Solverprotokollen. Bilddaten in qss_pruefung/messung/bildkurven.csv.",
            )
        if num == "6.8":
            row.update(
                titel="Berührung, Fasttreffer und zwei Durchtritte",
                befund="Schwellenparabeln mit exakt dargestelltem Abstand. Quelle: qss_pruefung/kontaktbild.py.",
            )
        if num == "6.9":
            row.update(
                titel="Aktive Zellen und Partitionsgrenzen im Grundwasser",
                befund="Zählung aller 65.292 Nennfallereignisse und beide Achtprozesskarten. Quelle: pdes_partitionierung/partitionen_zeichnen.py.",
            )
        rows.append(row)
    with index.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def read_and_check(book):
    with (HERE / "abbildungsverzeichnis.csv").open(encoding="utf-8") as source:
        rows = list(csv.DictReader(source))
    expected = [(row["abbildung"], int(row["buchseite"])) for row in rows]
    captions = []
    flags = fitz.TEXTFLAGS_DICT & ~fitz.TEXT_PRESERVE_IMAGES
    for number, page in enumerate(book, 1):
        for block in page.get_text("dict", flags=flags)["blocks"]:
            for line in block.get("lines", []):
                for span in line["spans"]:
                    caption = re.match(
                        r"^Abbildung ([A-G0-9]+[.][0-9]+)[.] ", span["text"]
                    )
                    if (
                        caption
                        and span["color"] == 4809069
                        and abs(span["size"] - 9.4) < 0.1
                    ):
                        captions.append((caption[1], number))
    if captions != expected:
        raise ValueError(
            "Die Bildnummern oder ihre Buchseiten passen nicht zum Verzeichnis der Druckfassung."
        )
    plates = print_files(ROOT, (row["druck"] for row in rows))
    for row in rows:
        if sha256((ROOT / row["grafik"]).read_bytes()).hexdigest() != row["sha256_svg"]:
            raise ValueError("Andere Bilddatei: " + row["grafik"])
        if sha256(plates[row["druck"]]).hexdigest() != row["sha256_pdf"]:
            raise ValueError("Andere Bilddatei: " + row["druck"])
    return expected, {row["abbildung"]: row["titel"] for row in rows}


def atlas(book, ordered, output, titles):
    pdf = fitz.open()
    groups = [
        (
            i,
            min(i + 18, len(ordered)),
            f"Bildregister {ordered[i][0]} bis {ordered[min(i + 18, len(ordered)) - 1][0]}",
        )
        for i in range(0, len(ordered), 18)
    ]
    # The first four sheets are a printable clickable figure register.
    for unused in groups:
        pdf.new_page(width=595.28, height=841.89)
    source_pages = list(dict.fromkeys(p - 1 for _, p in ordered))
    loc = {p: i + len(groups) for i, p in enumerate(source_pages)}
    for k, p in enumerate(source_pages):
        pdf.insert_pdf(
            book,
            from_page=p,
            to_page=p,
            links=False,
            annots=False,
            final=int(k == len(source_pages) - 1),
        )
    for old, idx in loc.items():
        for link in book[old].get_links():
            if link.get("uri"):
                pdf[idx].insert_link(
                    {"kind": fitz.LINK_URI, "uri": link["uri"], "from": link["from"]}
                )
            elif link.get("page") in loc:
                pdf[idx].insert_link(
                    dict(
                        kind=fitz.LINK_GOTO,
                        page=loc[link["page"]],
                        **{"from": link["from"]},
                    )
                )
    ink = (0.09, 0.20, 0.26)
    teal = (0.01, 0.39, 0.36)
    gray = (0.28, 0.36, 0.39)
    family = "/usr/share/fonts/truetype/dejavu/"
    audit_page = len(pdf)
    pdf.new_page(width=595.28, height=841.89)
    toc = []

    def put(page, x, y, text, size=11, font="sans", color=ink):
        page.insert_text((x, y), text, fontname=font, fontsize=size, color=color)

    for j, (start, end, title) in enumerate(groups):
        p = pdf[j]
        for alias, file in [
            ("sans", "DejaVuSans.ttf"),
            ("bold", "DejaVuSans-Bold.ttf"),
            ("serif", "DejaVuSerif.ttf"),
        ]:
            p.insert_font(fontname=alias, fontfile=family + file)
        put(
            p,
            46,
            45,
            "CHRISTIAN STENZEL   /   NUMERISCHE SIMULATION DYNAMISCHER SYSTEME",
            8,
            "bold",
            teal,
        )
        put(p, 44, 92, "Bildatlas zum Lehrbuch", 29, "serif")
        put(
            p,
            46,
            119,
            f"Druckfassung · {len(ordered)} Abbildungen · Vollgitterstudie",
            10,
            "sans",
            gray,
        )
        put(p, 46, 155, title, 15, "bold", teal)
        put(
            p,
            46,
            179,
            "Jeder Eintrag öffnet die Originalseite mit ihrer Bildunterschrift.",
            10,
        )
        put(p, 46, 200, "ABB.", 8, "bold", gray)
        put(p, 111, 200, "ABBILDUNG", 8, "bold", gray)
        put(p, 480, 200, "BUCHSEITE", 8, "bold", gray)
        p.draw_line((45, 207), (548, 207), color=(0.63, 0.74, 0.75), width=0.6)
        toc.append([1, title, j + 1])
        for k, (num, page_no) in enumerate(ordered[start:end]):
            y = 226 + 22.5 * k
            put(p, 48, y, num, 10, "bold", teal)
            put(p, 111, y, titles[num], 10)
            put(p, 502, y, str(page_no), 10, "sans", gray)
            p.insert_link(
                {
                    "kind": fitz.LINK_GOTO,
                    "from": fitz.Rect(44, y - 12, 549, y + 4),
                    "page": loc[page_no - 1],
                }
            )
            toc.append([2, f"{num} · {titles[num]}", loc[page_no - 1] + 1])
        put(p, 46, 720, "Befunde der Abbildungsprüfung", 10, "bold", teal)
        p.insert_link(
            {
                "kind": fitz.LINK_GOTO,
                "from": fitz.Rect(44, 705, 280, 725),
                "page": audit_page,
            }
        )
        put(p, 46, 753, "Verzeichnisseiten", 9, "sans", gray)
        for z in range(len(groups)):
            x = 165 + 30 * z
            put(p, x, 753, str(z + 1), 10, "bold", teal if j != z else ink)
            p.insert_link(
                {
                    "kind": fitz.LINK_GOTO,
                    "from": fitz.Rect(x - 7, 739, x + 14, 758),
                    "page": z,
                }
            )
        put(p, 46, 797, f"Bildverzeichnis {j + 1} / {len(groups)}", 9, "sans", gray)
    p = pdf[audit_page]
    for alias, file in [
        ("sans", "DejaVuSans.ttf"),
        ("bold", "DejaVuSans-Bold.ttf"),
        ("serif", "DejaVuSerif.ttf"),
    ]:
        p.insert_font(fontname=alias, fontfile=family + file)
    put(p, 46, 46, "CHRISTIAN STENZEL   /   BILDATLAS ZUM LEHRBUCH", 8, "bold", teal)
    put(p, 45, 94, "Befunde der Abbildungsprüfung", 24, "serif")
    put(
        p,
        46,
        122,
        "Bildnachweise zu den Buchfassungen v9.12 bis v9.21",
        10,
        "sans",
        gray,
    )
    findings = [
        (
            "Bildfolge und Achsen",
            [
                "D.1 enthielt bereits den Kran links und den Bolus rechts. D.2 zeigte links das",
                "Raum-Zeit-Feld, rechts den Sensor. Beide Tafeln tragen nun A/B und Messgröße.",
                "Die Ghia-Profile in 16.6 und 16.8 haben nun dieselbe Achsenorientierung.",
                "Auf der vertikalen Mittellinie steht u/U waagerecht und y/L senkrecht.",
            ],
        ),
        (
            "Nummerierung und Bildnachweise",
            [
                "Federwagen, RC-Kreis und Euler-Vergleich tragen 1.1, 1.2 und 1.3. Beide",
                "Euler-Teilbilder waren vorhanden. 17.1 gehört zur C19R-Messplanung und",
                "18.1 zum Status der 456 Läufe. 3.1, 3.3, 5.1 und 9.5 sind im Original belegt.",
                "9.6 ist ein Balkendiagramm. 11.1 und 14.1 sind gezeichnete Zeitverläufe.",
            ],
        ),
        (
            "Drucksatz und native Auflösung",
            [
                "7.1 zeigt auf der Gitterachse nur 8, 16, 32 und 64. In 8.1 passt der ganze",
                "Deckelrandtitel ins Bild. 16.1 und 16.4 zeigen ihre gemessenen Zellen.",
                "16.10 ergänzt den Anlauf auf 257 × 257 Knoten und die Hybridfehler auf",
                "65 × 65 und 421 × 421 Zellen. Die vier Raster sind in Originalgröße eingebettet.",
            ],
        ),
        (
            "Die 456 wiederholten Läufe",
            [
                "224 Läufe bestehen, 126 überschreiten das numerische Budget.",
                "81 Zeitlimits, 13 abweichende Ereigniszahlen und 12 Solverfehler.",
                "Abb. 18.2 zeigt 350 abgeschlossene Zeit-Fehler-Paare.",
                "Abb. 18.3 enthält alle acht Modellfenster im Nenner.",
            ],
        ),
    ]
    for k, (heading, paragraph) in enumerate(findings):
        y = 174 + k * 132
        put(p, 46, y, heading, 15, "bold", teal)
        for j, line in enumerate(paragraph):
            put(p, 46, y + 24 + j * 16, line, 10)
    put(
        p,
        46,
        687,
        "G.1 verbindet seit v9.15 Laboruhr, normierte Zeit und Anzeige des Fühlers.",
        10,
    )
    put(
        p,
        46,
        703,
        f"Die Verweise auf alle {len(ordered)} Abbildungen wurden aus dem Buch gelesen.",
        10,
    )
    put(
        p,
        46,
        719,
        "6.3 bis 6.8 zeigen die Entscheidungen der QSS-Verfahren und ihrer Varianten.",
        10,
    )
    put(p, 46, 746, "Zum Bildverzeichnis", 10, "bold", teal)
    p.insert_link(
        {"kind": fitz.LINK_GOTO, "from": fitz.Rect(43, 730, 225, 752), "page": 0}
    )
    toc.append([1, "Befunde der Abbildungsprüfung", audit_page + 1])
    pdf.set_toc(toc)
    pdf.set_metadata(
        {
            "title": "Bildatlas zum Lehrbuch · Numerische Simulation dynamischer Systeme",
            "author": "Christian Stenzel",
            "subject": f"Alle {len(ordered)} Abbildungen der Druckfassung",
        }
    )
    pdf.subset_fonts()
    pdf.save(output, garbage=4, deflate=True)
    with fitz.open(output) as verified:
        assert len(verified) == len(groups) + len(source_pages) + 1
        for group_idx, (start, end, _) in enumerate(groups):
            links = [
                link
                for link in verified[group_idx].get_links()
                if len(groups) <= link["page"] < audit_page
            ]
            assert [link["page"] for link in links] == [
                loc[p - 1] for _, p in ordered[start:end]
            ]
        assert len(verified.get_toc()) == len(ordered) + 1 + len(groups)
        for num, p in ordered:
            assert "Abbildung " + num + "." in verified[loc[p - 1]].get_text(), num
    return len(pdf)


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("buch", type=Path, help="Gesetztes Lehrbuch")
    parser.add_argument(
        "--atlas", type=Path, help="Ziel für den neu zu erzeugenden Bildatlas"
    )
    parser.add_argument(
        "--register-aktualisieren",
        action="store_true",
        help="Buchseiten und Prüfsummen aus dem gesetzten PDF ableiten",
    )
    args = parser.parse_args()
    with fitz.open(args.buch) as book:
        if args.register_aktualisieren:
            update_index(book)
        ordered, titles = read_and_check(book)
        if args.atlas is not None:
            if args.atlas.resolve() == args.buch.resolve():
                parser.error("Buch und Atlas benötigen unterschiedliche Ausgabepfade.")
            atlas(book, ordered, args.atlas, titles)
        print(f"{len(ordered)} Bildnummern, Seiten und Quelldateipaare geprüft.")

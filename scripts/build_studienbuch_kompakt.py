"""Build the German textbook and lab together, or verify the committed edition."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
SOURCE = DOCS / 'lehrbuch' / 'studienbuch'
MATERIAL = SOURCE / 'material'
EVIDENCE = DOCS / 'evidence' / 'cp2-operators.json'
PDF = 'ARGESIM_SOLVER_STUDY.pdf'
LAB = 'ARGESIM_Bachelor_Rechenlabor.zip'
RECORD = 'ARGESIM_Buchstand.json'
MATERIAL_TYPES = {'.csv', '.json', '.npy', '.npz', '.pdf', '.py', '.txt'}


def material_files():
    return sorted(p for p in MATERIAL.rglob('*') if p.is_file() and p.suffix in MATERIAL_TYPES)


def source_digest(material):
    files = [Path(__file__).resolve(), ROOT / 'scripts' / 'c19_profiles.py', EVIDENCE, *SOURCE.rglob('*.tex'),
             *(SOURCE / 'abbildungen').glob('*.pdf'), *material]
    files.append(ROOT / 'scripts' / 'lehrbuch_verfahrensbilder.py')
    studies = ROOT / 'scripts' / 'cp2_accuracy'
    files.extend(p for p in studies.iterdir() if p.suffix in {'.py', '.cpp'})
    experiments = ROOT / 'argesim_benchmarks' / 'experiments'
    files.extend(experiments / name for name in (
        'cp2_fields.py', 'cp2_operators.py', 'cp2_accuracy.py',
        'cp2_residual_fno.py', 'cp2_parameter_fno.py'))
    digest = hashlib.sha256()
    for path in sorted(files):
        digest.update(path.relative_to(ROOT).as_posix().encode() + b'\0')
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def verify_measurements():
    evidence = json.loads(EVIDENCE.read_text(encoding='utf-8'))
    for name in ('rope', 'cavity'):
        path = MATERIAL / 'cp2_feldlabor' / name / f'{name}-metrics.json'
        if json.loads(path.read_text(encoding='utf-8')) != evidence[name]:
            raise ValueError(f'{path.name} differs from {EVIDENCE.name}')


def distribution_record(out, digest):
    return {'sources_sha256': digest,
            'outputs_sha256': {name: hashlib.sha256((out / name).read_bytes()).hexdigest()
                               for name in (PDF, LAB)}}


def check(out):
    verify_measurements()
    expected = json.loads((out / RECORD).read_text(encoding='utf-8'))
    actual = distribution_record(out, source_digest(material_files()))
    if expected != actual:
        raise ValueError('Textbook sources, PDF or lab changed. Run python scripts/build_studienbuch.py and commit the three outputs together.')


def zip_bytes(files):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w') as archive:
        for path in files:
            item = zipfile.ZipInfo(path.relative_to(MATERIAL).as_posix(), (2026, 1, 1, 0, 0, 0))
            item.compress_type = zipfile.ZIP_DEFLATED
            item.external_attr = 0o100644 << 16
            archive.writestr(item, path.read_bytes())
    return stream.getvalue()


def write_run_tables(stage):
    """Typeset each archived configuration directly from the downloadable data."""
    data = MATERIAL / 'qss-extension.csv'
    if data.read_bytes() != (DOCS / 'evidence' / data.name).read_bytes():
        raise ValueError('Die Labordaten stimmen nicht mit dem Studienarchiv überein.')
    with data.open(encoding='utf-8', newline='') as stream:
        rows = list(csv.DictReader(stream))
    cases = ('C03', 'C05', 'C07', 'C09', 'C11', 'C12', 'C13', 'C21')
    status = {'pass': 'OK', 'accuracy_miss': 'Ziel', 'event_mismatch': 'Ereig.',
              'timeout': 'Limit', 'solver_error': 'Fehler'}
    keys = {(r['case'], r['method'], r['quantum_factor']) for r in rows}
    if len(rows) != 456 or len(keys) != 456 or {r['case'] for r in rows} != set(cases):
        raise ValueError('Ungültiger Umfang der Acht-Fälle-Matrix.')
    lines = []
    for case in cases:
        block = sorted((r for r in rows if r['case'] == case),
                       key=lambda r: (r['method'], float(r['quantum_factor'] or 0)))
        if len(block) != 57:
            raise ValueError(f'{case} enthält nicht 57 Konfigurationen.')
        for group, start in enumerate(range(0, 57, 19)):
            label = f'run{case}{chr(ord("a") + group)}'
            title = f'{case} · Konfigurationen {start + 1}–{start + 19}'
            lines += [rf'\seite{{Einzelmessungen}}{{Anhang B.1}}\anchorpage{{3}}{{{label}}}{{{title}}}\ptitle{{{title}}}',
                      r'{\tblstart\begin{tabularx}{\linewidth}{@{}Yrrlrrrr@{}}\toprule',
                      r'\hd{Methode}&\hd{Faktor}&\hd{Score}&\hd{Status}&\hd{A}&\hd{V}&\hd{RHS}&\hd{ms}\\\midrule']
            for row in block[start:start + 19]:
                method = row['method']
                if not re.fullmatch(r'[a-z0-9-]+', method):
                    raise ValueError(f'Ungültiger Verfahrensname {method!r}')
                score = row['error_over_limit']
                median = row['median_ms']
                cells = [method, row['quantum_factor'] or '–',
                         format(float(score), '.4g') if score else '–', status[row['status']],
                         *(str(int(row[k])) if row[k] else '–' for k in ('accepted', 'rejected', 'rhs')),
                         format(float(median), '.4g') if median else '–']
                lines.append(' & '.join(cells) + r'\\')
            lines += [r'\bottomrule\end{tabularx}\par}',
                      r'\srcs{\see{runs}{Spalten und Status lesen} · \texttt{qss-extension.csv}, vollständige Messwerte im Rechenlabor.}']
    (stage / 'einzellaeufe.tex').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def typeset(stage):
    write_run_tables(stage)
    env = {**os.environ, 'TEXINPUTS': str(stage) + os.pathsep + os.environ.get('TEXINPUTS', ''),
           'TZ': 'UTC', 'SOURCE_DATE_EPOCH': '1795219200'}
    command = ['xelatex', '-no-pdf', '-halt-on-error', '-interaction=nonstopmode',
               f'-output-directory={stage}', 'kurs.tex']
    for _ in range(2):
        result = subprocess.run(command, cwd=SOURCE, env=env, check=False, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True)
        if result.returncode:
            raise ValueError(result.stdout[-4500:])
    for warning in ('multiply defined', 'undefined references', 'Missing character'):
        if warning in result.stdout:
            raise ValueError(f'XeLaTeX: {warning}')
    subprocess.run(['xdvipdfmx', '-q', '-o', str(stage / 'text.pdf'), str(stage / 'kurs.xdv')],
                   cwd=SOURCE, env=env, check=True)


def verify_navigation(book):
    targets = book.resolve_names()
    links_by_page = []
    for page in book:
        names = set()
        for link in page.get_links():
            name = link.get('nameddest')
            if name:
                if name not in targets or not 0 <= targets[name]['page'] < len(book):
                    raise ValueError(f'Invalid PDF link on page {page.number + 1}: {name}')
                names.add(name)
        links_by_page.append(names)

    pairs = [(f'frage{i}', f'antwort{i}') for i in range(1, 13)]
    pairs.extend((f'aufgabe{i}', f'loes{i}') for i in range(1, 7))
    for first, second in pairs:
        for source, dest in ((first, second), (second, first)):
            if source not in targets or dest not in links_by_page[targets[source]['page']]:
                raise ValueError(f'Missing exercise link: {source} -> {dest}')


def build(out):
    import pymupdf

    verify_measurements()
    material = material_files()
    digest = source_digest(material)
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=out) as tmp:
        stage = Path(tmp)
        typeset(stage)
        (stage / LAB).write_bytes(zip_bytes(material))
        attachments = {p.name: p.read_bytes() for p in material
                       if p.parent == MATERIAL and p.name != 'START_HIER.txt'}
        fields = [p for p in material if 'cp2_feldlabor' in p.relative_to(MATERIAL).parts]
        attachments['CP2_Feldlabor.zip'] = zip_bytes(fields)
        accuracy = [p for p in material if 'cp2_genauigkeit' in p.relative_to(MATERIAL).parts]
        attachments['CP2_Genauigkeit.zip'] = zip_bytes(accuracy)
        with pymupdf.open(stage / 'text.pdf') as book:
            toc = book.get_toc()
            if sorted(page for _, _, page in toc) != list(range(1, len(book) + 1)):
                raise ValueError('Every page needs exactly one working bookmark. Check page breaks and labels.')
            marks = [title for _, title, _ in toc]
            if [int(m.group(1)) for title in marks if (m := re.match(r'^(\d+) · ', title))] != list(range(1, 18)):
                raise ValueError('Das Buch benötigt genau 17 Hauptkapitel in der vereinbarten Reihenfolge.')
            if sum(bool(re.match(r'^A\.\d+ · ', title)) for title in marks) != 24:
                raise ValueError('Der Referenzkatalog benötigt alle 24 Projektmodelle.')
            verify_navigation(book)
            if book.metadata['author'] != 'Christian Stenzel':
                raise ValueError('Missing textbook author')
            for name, data in attachments.items():
                xref = book.embfile_add(name, data, filename=name, ufilename=name, desc=name)
                for field in ('CreationDate', 'ModDate'):
                    book.xref_set_key(xref, 'Params/' + field, '(D:20261121000000Z)')
            metadata = book.metadata
            metadata.update(subject='Modellbildung, numerische Verfahren und ARGESIM-Python-Praktikum',
                            keywords=f'MOL, LBM, NN, CP2, Newmark, Verlet, FNO; sources-sha256={digest}')
            book.set_metadata(metadata)
            book.save(stage / PDF, garbage=3, deflate=True, no_new_id=True)
        with pymupdf.open(stage / PDF) as book:
            if set(book.embfile_names()) != set(attachments) or any(
                book.embfile_get(name) != data for name, data in attachments.items()
            ):
                raise ValueError('Invalid course material embedded in the textbook')
        record = distribution_record(stage, digest)
        (stage / RECORD).write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
        if digest != source_digest(material_files()):
            raise ValueError('Textbook inputs changed during typesetting. Repeat the build.')
        for name in (PDF, LAB, RECORD):
            (stage / name).replace(out / name)
    check(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='verify hashes without installing typesetting tools')
    parser.add_argument('--output-dir', type=Path, default=ROOT / "build" / "kompakt")
    args = parser.parse_args()
    out = args.output_dir.resolve()
    try:
        if args.check:
            check(out)
        else:
            build(out)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        sys.exit(str(exc))
    print(f'Verified {out / PDF} and {out / LAB}')


if __name__ == '__main__':
    main()

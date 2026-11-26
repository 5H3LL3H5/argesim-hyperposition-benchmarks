"""Check the published PDF and exercises with the core standard-library suite."""
import json
import math
import shutil
import tempfile
import unittest
from pathlib import Path
from runpy import run_path

from scripts import build_studienbuch as book

LAB = run_path(str(book.MATERIAL / 'methodenlabor.py'))
CHAPTERS = run_path(str(book.MATERIAL / 'kapitelproben.py'))


class TextbookTests(unittest.TestCase):
    def test_published_textbook_and_lab_match_their_inputs(self):
        book.check(book.DOCS)

    def test_detects_changed_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            for name in (book.PDF, book.LAB, book.RECORD):
                shutil.copyfile(book.DOCS / name, out / name)
            with (out / book.PDF).open('ab') as pdf:
                pdf.write(b'changed')
            with self.assertRaisesRegex(ValueError, 'changed'):
                book.check(out)

    def test_compact_edition_worked_examples_cover_all_17_chapters(self):
        checks = run_path(str(book.MATERIAL / 'kapitelvergleich.py'))
        results = [*checks['theorie'](), *checks['benchmark']()]
        self.assertEqual([number for number, _ in results], list(range(1, 18)))

    def test_published_qss_replays_preserve_results_and_work_counts(self):
        measurements = book.EDITION / book.AUDIT / "messung"
        self.assertEqual(
            (measurements / "vertragsproben.csv").read_bytes(),
            (measurements / "vertragsproben_skalenfix.csv").read_bytes(),
        )
        runs = []
        for name in ("gegenlauf_v918.jsonl", "gegenlauf_skalenfix.jsonl"):
            records = {}
            for line in (measurements / name).read_text(encoding="utf-8").splitlines():
                row = json.loads(line)
                case = (row["case"], row["method"], row["quantum_factor"])
                self.assertNotIn(case, records)
                records[case] = tuple(
                    row[key] for key in ("status", "error_over_limit", "accepted", "rejected", "rhs")
                )
            runs.append(records)
        self.assertEqual(len(runs[0]), 12)
        self.assertEqual(runs[0], runs[1])

    def test_transport_and_collision_invariants(self):
        upwind, lax_wendroff = LAB['transport']()
        self.assertEqual(upwind, [0, 0.5, 1, 0.5])
        self.assertEqual(lax_wendroff, [-0.125, 0.625, 1.125, 0.375])
        self.assertEqual(sum(upwind), sum(lax_wendroff))
        before, after = LAB['kollidieren']()
        for field in (before, after):
            self.assertAlmostEqual(math.fsum(field), 1)
            self.assertEqual(field[1], field[3])
        self.assertAlmostEqual(after[1] - 1/9, (before[1] - 1/9)/2)

    def test_contact_tolerance_rejects_correct_count_with_late_event(self):
        check = CHAPTERS['pruefe_kontaktzeiten']
        self.assertEqual(check((0.4, 1.1), (0.4, 1.1), 0.001), 0)
        with self.assertRaisesRegex(ValueError, 'Score 2'):
            check((0.402, 1.1), (0.4, 1.1), 0.001)
        with self.assertRaisesRegex(ValueError, 'Ereigniszahl'):
            check((0.4,), (0.4, 1.1), 0.001)

    def test_learning_step(self):
        for actual, expected in zip(LAB['lernschritt'](), (0.8, 1.6, 0.18)):
            self.assertAlmostEqual(actual, expected)

    def test_verlet_against_reflected_wave(self):
        fine = LAB['saite'](501)
        coarse = LAB['saite'](65)
        for actual, expected in zip(coarse + fine, (2.4840, 0.9306, 0.2313, 0.0946)):
            self.assertAlmostEqual(100 * actual, expected, delta=0.000051)
        with self.assertRaisesRegex(ValueError, 'dt/dx'):
            LAB['saite'](1001)
        with self.assertRaisesRegex(ValueError, 'Messzeiten'):
            LAB['saite'](65, 0.03)

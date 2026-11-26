"""Independent readback of the published selection experiment (R77-N-C05)."""

import csv
import json
import math
import statistics
import unittest
from collections import Counter
from pathlib import Path

EDITION = Path(__file__).resolve().parents[1] / "docs/lehrbuch/gesamtausgabe"


class TextbookSelectionHoldout(unittest.TestCase):
    def test_eight_folds_and_c05_failure(self):
        archive = EDITION / "rechenlabor/qss_pruefung/messung/kontakt_v919"
        data = EDITION / "daten/qss-selection.csv"
        self.assertEqual(data.read_bytes(), (archive / "selection.csv").read_bytes())
        with data.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 520)
        families = sorted({r["case"] for r in rows if r["case"].startswith("C")})
        index = {(r["case"], r["method"], r["level"]): r for r in rows}
        self.assertEqual(len(index), len(rows))
        candidates = set.intersection(
            *({(m, q) for c, m, q in index if c == f} for f in families)
        )
        self.assertEqual((len(families), len(candidates)), (8, 17))

        def scores(family):
            successful = {
                k: float(index[(family, *k)]["median_ms"])
                for k in candidates
                if index[(family, *k)]["status"] == "pass"
            }
            if not successful:
                return {}
            self.assertTrue(all(math.isfinite(v) and v > 0 for v in successful.values()))
            best = min(successful.values())
            return {k: v / best for k, v in successful.items()}

        ratios = {f: scores(f) for f in families}
        counts = Counter(index[("C05", *key)]["status"] for key in candidates)
        self.assertEqual(counts, {"accuracy_miss": 3, "timeout": 10, "solver_error": 4})
        self.assertFalse(ratios["C05"])
        actual = []
        for holdout in families:
            training = [f for f in families if f != holdout]

            def rank(key):
                vals = [ratios[f][key] for f in training if key in ratios[f]]
                return 7 - len(vals), statistics.mean(vals) if vals else math.inf, key

            key = min(candidates, key=rank)
            actual.append(
                {
                    "test": holdout,
                    "method": key[0],
                    "level": key[1],
                    "status": index[(holdout, *key)]["status"],
                    "relativ": ratios[holdout].get(key),
                }
            )
        declared = json.loads((archive / "bilanz.json").read_text())["selection"]
        self.assertEqual(actual, declared["folds"])
        self.assertEqual(Counter(r["status"] for r in actual), {"pass": 7, "timeout": 1})
        self.assertEqual(next(r for r in actual if r["status"] == "timeout")["test"], "C05")

"""Regression checks for the release audit itself."""

import csv
import json
import subprocess
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from zipfile import ZipFile

from scripts import pruefe_studienbuch_befunde as audit


class PdfNode(dict):
    def get_object(self):
        return self


class FindingTest(unittest.TestCase):
    def test_pdf_attachment_keys_are_ordered_across_leaves(self):
        for keys, expected_pass in (
            ((b"A", b"Z", b"a"), True),
            ((b"A", b"Z", b"B"), False),
            ((b"A", b"B", b"B"), False),
        ):
            with self.subTest(keys=keys):
                first = PdfNode({"/Names": [keys[0], None, keys[1], None]})
                last = PdfNode({"/Names": [keys[2], None]})
                tree = PdfNode({"/Kids": [first, last]})
                book = SimpleNamespace(
                    trailer={"/Root": {"/Names": {"/EmbeddedFiles": tree}}}
                )
                self.assertEqual(not audit.check_pdf_names(book), expected_pass)

    def test_pdf_attachment_tree_with_repeated_node_fails(self):
        tree = PdfNode({"/Kids": []})
        tree["/Kids"].append(tree)
        book = SimpleNamespace(trailer={"/Root": {"/Names": {"/EmbeddedFiles": tree}}})
        self.assertTrue(audit.check_pdf_names(book))

    def test_brent_uses_exact_error_and_checks_both_signs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lab = root / audit.LAB
            lab.parent.mkdir(parents=True)
            with ZipFile(lab, "w") as archive:
                archive.writestr("beispiele/ereignis.py", "")
            module = {"EventBracket": type("EventBracket", (), {})}
            with patch.object(audit.runpy, "run_path", return_value=module):
                module["brent"] = lambda func, left, right, tol: 0.0
                self.assertEqual(audit.check_brent(root), ())
                module["brent"] = lambda func, left, right, tol: (
                    tol if right == 2 else -tol
                )
                problems = audit.check_brent(root)
        self.assertEqual(len(problems), 2)
        self.assertTrue(all(str(2**55) in failure for failure in problems))

    def test_brent_iteration_limit_is_reported_without_aborting_other_checks(self):
        message = "Brent-Dekker hat seine Iterationsgrenze erreicht"
        with (
            patch.object(audit, "check_brent", side_effect=ArithmeticError(message)),
            patch.object(audit, "check_pdf_names", return_value=()),
            patch.object(audit, "check_measurement_sources", return_value=()),
        ):
            results = audit.finding_checks(Path("."), SimpleNamespace(outline=[]))
        self.assertEqual(
            {result.id: result.outcome for result in results},
            {"R90-K-01": "error", "R90-PDF-01": "pass", "R91-LAB-01": "pass"},
        )
        self.assertEqual(results[0].evidence, (message,))

    def test_measurement_commit_and_script_hash_are_both_required(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = root / audit.CODANO
            data.mkdir(parents=True)
            commit = "a" * 40
            content = b"print('recorded experiment')\n"
            names = (
                "saite_tfno_messung.json",
                "messung.json",
                "messung_kapazitaet.json",
            )
            metadata = {
                "source_commit": commit,
                "source_script_sha256": sha256(content).hexdigest(),
            }
            for name in names:
                (data / name).write_text(json.dumps(metadata), encoding="utf-8")
            with patch.object(audit, "git_blob", return_value=content) as blob:
                self.assertEqual(audit.check_measurement_sources(root), ())
                blob.assert_any_call(root, commit, f"{audit.CODANO}/saite_tfno.py")
                (data / names[0]).write_text(
                    json.dumps({**metadata, "source_script_sha256": "0" * 64}),
                    encoding="utf-8",
                )
                problems = audit.check_measurement_sources(root)
                self.assertEqual(len(problems), 1)
                self.assertIn("source_script_sha256", problems[0])
                blob.return_value = None
                self.assertEqual(len(audit.check_measurement_sources(root)), 3)

    def test_archive_requires_commit_bound_links_and_existing_pages(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            index = root / audit.ARCHIVES
            index.parent.mkdir()
            commit = "b" * 40

            def link(page):
                return f"{audit.GITHUB}/blob/{commit}/{audit.PDF}?raw=true#page={page}"

            row = {
                "id": "F-01",
                "status": "Entfallen",
                "aktuelle_seite": "",
                "ausgabe": commit,
                "seitenart": "Hauptbuch",
                "archivseiten": "3",
                "archivlinks": link(3),
            }
            with index.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, row)
                writer.writeheader()
                writer.writerow(row)
                writer.writerow({**row, "id": "F-02", "archivlinks": link(2)})
                writer.writerow(
                    {**row, "id": "F-03", "archivseiten": "4", "archivlinks": link(4)}
                )
            (root / audit.ARCHIVE_INVENTORY).write_text(
                "id,status\nF-01,Entfallen\nF-02,Entfallen\nF-03,Entfallen\n",
                encoding="utf-8",
            )
            with patch.object(audit, "git_blob", return_value=b"pdf") as blob:
                result = audit.archive_entries(
                    root,
                    lambda _: SimpleNamespace(pages=range(3)),
                )
            blob.assert_called_once_with(root, commit, audit.PDF)
            self.assertEqual([r.outcome for r in result], ["pass", "fail", "fail"])
            self.assertEqual(result[0].evidence, (link(3),))

    def test_archive_inventory_failure_blocks_release_and_survives_worklist(self):
        source = audit.ROOT / audit.ARCHIVES
        with source.open(encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            fields = reader.fieldnames
            rows = list(reader)
        self.assertEqual(len(rows), 33)
        ident = "R77-G-01"
        retained = [row for row in rows if row["id"] != ident]
        self.assertEqual(len(retained), 32)
        replacement = {
            **next(row for row in rows if row["id"] == ident),
            "id": "FAKE-01",
        }
        reclassified = [
            {**row, "status": "Nur Archiv"} if row["id"] == ident else row
            for row in rows
        ]
        for alternate, problems in (
            (rows, set()),
            (retained, {ident}),
            ([*retained, replacement], {ident, "FAKE-01"}),
            (reclassified, {ident}),
        ):
            with (
                self.subTest(problems=problems),
                tempfile.TemporaryDirectory() as directory,
            ):
                root = Path(directory)
                index = root / audit.ARCHIVES
                index.parent.mkdir()
                with index.open("w", encoding="utf-8", newline="") as stream:
                    writer = csv.DictWriter(stream, fields)
                    writer.writeheader()
                    writer.writerows(alternate)
                (root / audit.ARCHIVE_INVENTORY).write_bytes(
                    (audit.ROOT / audit.ARCHIVE_INVENTORY).read_bytes()
                )
                (root / audit.MANIFEST).write_text(
                    json.dumps(
                        {
                            "edition": "test",
                            "outputs_sha256": {Path(audit.PDF).name: "a" * 64},
                        }
                    ),
                    encoding="utf-8",
                )
                for worklist in (None, root / "worklist.csv"):
                    with (
                        patch.object(audit, "checkout_commit", return_value="a" * 40),
                        patch.object(audit.subprocess, "run"),
                        patch.object(audit, "git_blob", return_value=b"pdf"),
                        patch.object(audit, "finding_checks", return_value=[]),
                        patch.object(
                            audit,
                            "coverage",
                            return_value=(
                                "a" * 40,
                                {
                                    ident: audit.Result(
                                        ident, "manual", "", "", kind="manual"
                                    )
                                }
                                if worklist
                                else {},
                            ),
                        ),
                    ):
                        report = audit.run_audit(
                            root,
                            None,
                            worklist,
                            lambda _: SimpleNamespace(pages=range(600)),
                        )
                    failures = {
                        item["id"]
                        for item in report["results"]
                        if item["outcome"] == "fail"
                    }
                    self.assertEqual(failures, problems)
                    self.assertEqual(
                        audit.exit_status(report, strict=True), int(bool(problems))
                    )
                    self.assertEqual(audit.exit_status(report, strict=False), 0)

    def test_checkout_rejects_uncommitted_inputs_and_wrong_commit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            def git(*args):
                subprocess.run(
                    ("git", *args), cwd=root, capture_output=True, check=True
                )

            git("init", "--quiet")
            pdf = root / audit.PDF
            pdf.parent.mkdir()
            pdf.write_bytes(b"original")
            git("add", audit.PDF)
            git(
                "-c",
                "user.name=Test",
                "-c",
                "user.email=test@example.invalid",
                "-c",
                "commit.gpgsign=false",
                "commit",
                "-qm",
                "fixture",
            )
            head = audit.checkout_commit(root, None)
            self.assertEqual(audit.git_blob(root, head, audit.PDF), b"original")
            self.assertIsNone(audit.git_blob(root, head, audit.MANIFEST))
            with self.assertRaisesRegex(ValueError, "Checkout ist"):
                audit.checkout_commit(root, "0" * 40)
            pdf.write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "geändert"):
                audit.checkout_commit(root, head)

    def test_report_only_and_release_exit_codes(self):
        for counts, expected in (
            ({"fail": 0, "error": 0, "manual": 1}, (0, 0)),
            ({"fail": 1, "error": 0, "manual": 0}, (0, 1)),
            ({"fail": 0, "error": 1, "manual": 0}, (2, 2)),
        ):
            with self.subTest(counts=counts):
                report = {"counts": counts}
                self.assertEqual(
                    (audit.exit_status(report, False), audit.exit_status(report, True)),
                    expected,
                )


if __name__ == "__main__":
    unittest.main()

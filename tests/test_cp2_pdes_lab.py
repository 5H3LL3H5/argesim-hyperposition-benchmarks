"""Regressions for the published CP2 measurements, restarts and offline lab."""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from runpy import run_path

from scripts import build_studienbuch as book

LAB = book.EDITION / book.PDES
NUMERICS = all(importlib.util.find_spec(name) for name in ('numpy', 'scipy'))


class Cp2PdesLabTests(unittest.TestCase):
    @unittest.skipUnless(NUMERICS and shutil.which('taskset'), 'requires Linux lab runtime')
    def test_group_launcher_records_only_successful_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            executable = root / 'gq'
            executable.write_text(
                f'#!{sys.executable}\n'
                'import json, os, pathlib, sys\n'
                'out = pathlib.Path(sys.argv[-1])\n'
                'out.mkdir()\n'
                '(out / "affinity").write_text(json.dumps(sorted(os.sched_getaffinity(0))))\n'
            )
            executable.chmod(0o755)
            command = [sys.executable, str(LAB / 'skalierung.py'), 'groups', str(book.ROOT), tmp]
            subprocess.run(command, check=True, capture_output=True)
            for order in (3, 4):
                output = root / f'gqss{order}'
                timing = json.loads((output / 'run.json').read_text())
                self.assertGreater(timing['launcher_wall_s'], 0)
                self.assertEqual(timing['cpu_ids'], [min(os.sched_getaffinity(0))])
                self.assertEqual(timing['cpu_ids'], json.loads((output / 'affinity').read_text()))
            executable.write_text('#!/bin/sh\nexit 1\n')
            self.assertNotEqual(subprocess.run(command, check=False, capture_output=True).returncode, 0)
            self.assertFalse((root / 'gqss3/run.json').exists())

    @unittest.skipUnless(importlib.util.find_spec('numpy'), 'requires NumPy')
    def test_cavity_cli_rejects_invalid_rank_layout_and_mode_before_work(self):
        # Use the published copy with a nonexistent source root: validation must
        # run before loading any solver code or launching processes.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with zipfile.ZipFile(book.DOCS / book.LAB) as archive:
                for name in ('cavity_pdes.py', 'buchquellen.py'):
                    archive.extract((book.PDES / name).as_posix(), root)
            command = [
                sys.executable, str(root / book.PDES / 'cavity_pdes.py'),
                str(root / 'unavailable'), '--order', '3',
            ]
            for args, message in (
                (['--ranks', '3', '--layouts', 'tiles'], '1 or an even number of ranks'),
                (['--modes', 'optimstic'], 'invalid choice'),
            ):
                with self.subTest(args=args):
                    result = subprocess.run(
                        [*command, *args], capture_output=True, text=True, timeout=10
                    )
                    self.assertEqual(result.returncode, 2)
                    self.assertIn(message, result.stderr)
                    self.assertEqual(result.stdout, '')

    def test_c19_archives_keep_distinct_repetitions_and_speedup_baselines(self):
        verify = run_path(str(LAB / 'skalierung_pruefen.py'))
        result = verify['summaries']()
        paired = result['c19_paired_conservative']
        scaling = result['c19']['conservative']
        self.assertEqual((paired['archive'], paired['data'], paired['repeats']),
                         ('PDES_Partitionierung_Messpaket.zip', 'c19_paired.jsonl', 3))
        for rows, times in ((paired['rows'], [31.7, 353.9]), (scaling, [37.6, 383.7])):
            one, eight = rows[0], rows[-1]
            self.assertEqual([one['ranks'], eight['ranks']], [1, 8])
            self.assertEqual([round(r['median_s'] * 1000, 1) for r in (one, eight)], times)
            self.assertEqual(eight['speedup'], one['median_s'] / eight['median_s'])

    def test_frozen_restart_sources_and_seed_hashes(self):
        check = run_path(str(LAB / 'fortsetzungsprobe.py'))
        manifest = check['verify_manifest']()
        self.assertNotEqual(manifest['historical_integrator_sha256'],
                            manifest['continuation_integrator_sha256'])
        self.assertFalse(manifest['historical_integrator_bytes_available'])
        self.assertEqual(manifest['runtime'], {'python': '3.12.14', 'numpy': '2.3.5', 'scipy': '1.17.0'})

    def test_mpi_kernel_preparation_works_without_checkout_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            offline, output1, output2 = (root / name for name in ('offline', 'a', 'b'))
            for path in (offline, output1, output2):
                path.mkdir()
            source = 'rechenlabor/kavitaet_vollgitter/src/d2q9.cpp'
            with zipfile.ZipFile(book.PACKAGES / 'Laborquellen.zip') as archive:
                archive.extract(source, offline)
            self.assertFalse((offline / 'docs').exists())
            command = [sys.executable, str(LAB / 'prepare_d2q9.py')]
            subprocess.run([*command, str(book.ROOT)], cwd=output1, check=True, capture_output=True)
            subprocess.run([*command, str(offline)], cwd=output2, check=True, capture_output=True)
            for name in ('d2q9_book.cpp', 'kernel_local.hpp'):
                self.assertEqual((output1 / name).read_bytes(), (output2 / name).read_bytes())

    def test_completion_requires_the_endpoint_and_every_observation(self):
        verifier = run_path(str(LAB / 'skalierung_pruefen.py'))
        check = verifier['check_component_status']
        finish = {
            'target_ticks': 350000, 'equivalent_ticks': 350000, 'complete': True,
            't_star': 136.71875, 'observations': 7,
        }
        start = dict(finish, t_star=0, complete=False, equivalent_ticks=0, observations=0)
        check(start)
        check(finish)
        for bad in (dict(start, complete=True), dict(finish, complete=False),
                    dict(finish, observations=6), dict(finish, t_star=float('nan')),
                    dict(start, t_star=-1), dict(finish, equivalent_ticks=349999)):
            with self.subTest(record=bad), self.assertRaises(ValueError):
                check(bad)

    def test_compact_lab_verifies_both_printed_tables_after_extraction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with zipfile.ZipFile(book.DOCS / book.LAB) as archive:
                archive.extractall(root)
            command = [sys.executable, str(root / book.PDES / 'nachweis.py')]
            subprocess.run(command, cwd=root, check=True, capture_output=True)
            for name in ('kapitel/16.md', book.MANUSCRIPT):
                with self.subTest(name=name):
                    target = root / name
                    original = target.read_bytes()
                    target.write_text('Missing table')
                    proc = subprocess.run(command, cwd=root, check=False, capture_output=True, text=True)
                    self.assertNotEqual(proc.returncode, 0)
                    self.assertIn('Printed full-grid table differs', proc.stderr)
                    target.write_bytes(original)

    @unittest.skipUnless(NUMERICS, 'requires the numerical lab dependencies')
    def test_offline_restart_rejects_changed_dynamics(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            member = Path('rechenlabor/kavitaet_vollgitter/basis/kavitaet.py')
            with zipfile.ZipFile(book.PACKAGES / 'Laborquellen.zip') as archive:
                prefix = member.parent.as_posix() + '/'
                archive.extractall(root, [name for name in archive.namelist() if name.startswith(prefix)])
            package = root / member.parent / 'original/argesim_benchmarks'
            args = [sys.executable, str(LAB / 'qss_langlauf.py'), str(root),
                    str(root / 'output'), '--order', '3', '--stop-after']
            subprocess.run([*args, '1'], check=True, capture_output=True)
            resume = [*args, '2', '--resume']
            for path in (root / member, package / 'solvers/advanced_qss.py',
                         package / 'solvers/_polynomial.py'):
                with self.subTest(file=path.name):
                    original = path.read_bytes()
                    path.write_bytes(original + b'\n# Different model source\n')
                    proc = subprocess.run(resume, check=False, capture_output=True, text=True)
                    self.assertNotEqual(proc.returncode, 0)
                    self.assertIn('different or unverified experiment', proc.stderr)
                    path.write_bytes(original)
            proc = subprocess.run(resume, check=True, capture_output=True, text=True)
            self.assertEqual(json.loads(proc.stdout)['segments'], 2)

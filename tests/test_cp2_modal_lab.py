"""Offline acceptance for the packaged CP2 postprocessing and modal claims."""

import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

LAB = (
    Path(__file__).resolve().parents[1]
    / "docs/lehrbuch/studienbuch/material/cp2_genauigkeit"
)


def _check_lab_command(tmp_path, bad, label):
    local = tmp_path / "cp2_genauigkeit"
    local.mkdir()
    for name in (
        "auswerten.py",
        "saite.npz",
        "saite_beispiel.npz",
        "kavitaet_beispiel.npz",
        "kavitaet_profile.npz",
    ):
        shutil.copyfile(LAB / name, local / name)
    if bad == "new":
        path = local / "kavitaet_beispiel.npz"
        with np.load(path, allow_pickle=False) as source:
            fields = dict(source)
        fields["new"].fill(0)
        np.savez(path, **fields)
    elif bad is not None:
        path = local / "kavitaet_profile.npz"
        with np.load(path, allow_pickle=False) as source:
            fields = dict(source)
        fields["profile_257"][1 if bad == "u" else 2] += 1
        np.savez(path, **fields)
    result = subprocess.run(
        [sys.executable, "cp2_genauigkeit/auswerten.py"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    if label is not None:
        assert result.returncode != 0
        assert label in result.stderr
    else:
        assert result.returncode == 0, result.stderr
        assert "analytische Faktoren 0.04303 %" in result.stdout
        assert "analytische Faktoren 0.01416 %" in result.stdout
        assert "new: 0.04581 %" in result.stdout
        assert "0.009612" in result.stdout
        assert "0.002441" in result.stdout


class Cp2ModalLabTests(unittest.TestCase):
    def test_lab_command_enforces_each_output_budget(self):
        for bad, label in (
            (None, None),
            ("new", "Einzelfeldfehler"),
            ("u", "Profilfehler u/U"),
            ("v", "Profilfehler v/U"),
        ):
            with self.subTest(case=bad), tempfile.TemporaryDirectory() as directory:
                _check_lab_command(Path(directory), bad, label)


    def test_modal_bound_parameters_and_first_excluded_mode(self):
        with np.load(LAB / "saite.npz", allow_pickle=False) as model:
            times = model["times"]
            kernels = model["kernels"]
        assert kernels.shape == (321, 192)
        np.testing.assert_array_equal(times[[0, -1]], [0.0, 8.0])
        assert np.all(np.diff(times) > 0)
        step = np.diff(times).max()
        assert step <= 0.025000000000001
        assert (0.06 * np.pi / 0.5) ** 2 * step**2 * 192 / 8 + 1.36e-13 < 0.002132
        x = np.linspace(0.0, 0.5, 501)
        g = np.sqrt(2 / 0.5) * np.sin(193 * np.pi * x / 0.5) / 193
        predicted = runpy.run_path(str(LAB / "auswerten.py"))["saite"](g, 0)
        # For a single excluded mode a_193 = 1/193 the weighted radius is
        # exactly 1, and the omitted L² coefficient reaches the bound at t=0.
        np.testing.assert_allclose(
            np.sqrt((0.5 / 500) * np.sum((predicted - g) ** 2)), 1 / 193, rtol=2e-14
        )
        np.testing.assert_allclose(np.linalg.norm(predicted - g) / np.linalg.norm(g), 1)


    def test_measured_string_sweep_against_independent_dalembert(self):
        functions = runpy.run_path(str(LAB / "auswerten.py"))
        predict = functions["saite"]
        exact = functions["exakte_saite"]
        initial = functions["dreieck"]
        with np.load(LAB / "saite_zeitreihen.npz", allow_pickle=False) as sweep:
            rows = sweep["rows"]
        assert rows.shape == (6 * 4 * 99, 6)
        assert len(set(map(tuple, rows[:, :3]))) == len(rows)
        abs_errors = []
        for n, pos, t, old_abs, old_ref, old_rel in rows:
            x = np.linspace(0, 0.5, int(n))
            y = exact(x, t, pos * 0.5)
            p = predict(initial(x, pos * 0.5), t)
            rms = np.sqrt(np.mean((p - y) ** 2))
            reference = np.sqrt(np.mean(y**2))
            np.testing.assert_allclose(
                (rms, reference), (old_abs, old_ref), rtol=0, atol=1e-13
            )
            if reference <= 0.05e-10:
                assert np.isnan(old_rel)
            else:
                np.testing.assert_allclose(rms / reference, old_rel, rtol=0, atol=1e-10)
            abs_errors.append(rms)
        i = int(np.argmax(abs_errors))
        np.testing.assert_allclose(rows[i, :3], (65, 0.13, 2.693))
        self.assertAlmostEqual(abs_errors[i] * 1e6, 68.2067753, delta=1e-6)

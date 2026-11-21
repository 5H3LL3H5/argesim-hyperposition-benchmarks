"""Read the published C09R curves and replay Fig. 7's recorded valve signal.

Supply the original C9R-solution-MATLAB-Simulink-Fuzzy.pdf. Requires
PyMuPDF, Pillow and NumPy. All calibrations are tied to this PDF edition.
"""

import argparse
import hashlib
import io
import json
import math
import sys
from pathlib import Path

import fitz
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from argesim_benchmarks.models.c09_fuzzy_tanks import (
    C09Controller,
    C09PlantParameters,
    _c09_rk4_step,
    c09_validate,
    simulate_c09,
)


def pixels(pdf, xref):
    with Image.open(io.BytesIO(pdf.extract_image(xref)["image"])) as image:
        return np.asarray(image.convert("L")) < 128


def level_observation(ink, window, peak):
    height, width = ink.shape
    left, right = np.flatnonzero(ink.sum(axis=0) > 0.78 * height)
    top, bottom = np.flatnonzero(ink.sum(axis=1) > 0.80 * width)
    x0, x1 = np.rint(left + np.array(window) * (right - left) / 60000).astype(int)
    # Restrict to h2, excluding the dashed h1 and the legend. For plateaus
    # the dotted setpoint cannot fill 95% of the columns as the solid h2 does.
    high, low = (70, 56) if peak else (47, 35)
    y0, y1 = (round(bottom - h * (bottom - top) / 100) for h in (high, low))
    counts = ink[y0 : y1 + 1, x0 : x1 + 1].sum(axis=1)
    rows = np.flatnonzero(counts >= (2 if peak else 0.95 * (x1 - x0 + 1)))
    if not len(rows) or (not peak and np.ptp(rows) > 1):
        raise ValueError("h2 trace is missing or ambiguous")
    row = y0 + (rows[0] if peak else rows.mean())
    return float(100 * (bottom - row) / (bottom - top))


def valve_trace(ink, y14, y22):
    # Lower panels of Figures 6 and 7, tick centres at 1.4 and 2.2.
    left, right = np.flatnonzero(ink.sum(axis=0) > 0.75 * ink.shape[0])
    if (left, right) != (95, 1119) or not ink[[y14, y22], left + 3].all():
        raise ValueError("unexpected valve axes")
    xs = np.arange(left + 11, right - 10)
    # Omit the frame and tick marks. Extend the first and last readable
    # samples across the cropped margins (under 650 s per end).
    (bottom,) = np.flatnonzero(ink.sum(axis=1) > 0.80 * ink.shape[1])
    rows = [np.flatnonzero(ink[: bottom - 10, x]) for x in xs]
    if any(len(y) == 0 for y in rows):
        raise ValueError("missing valve trace")
    values = 1.4 + (y14 - np.array([np.median(y) for y in rows])) * 0.8 / (y14 - y22)
    return (xs - left) * 60000 / (right - left), values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("solution_pdf", type=Path)
    path = parser.parse_args().solution_pdf
    if hashlib.sha256(path.read_bytes()).hexdigest() != (
        "b8dda22e51839570986839a9f76ccbdbbfde0bad0a50ae19dabe117fcc3f8461"
    ):
        parser.error("expected the original C09R Simulink solution PDF")
    with fitz.open(path) as pdf:
        figure_levels = [
            level_observation(pixels(pdf, xref), window, peak)
            for xref, window, peak in (
                (8, (24000, 28000), True),
                (16, (44000, 46000), False),
                (16, (54000, 56000), False),
            )
        ]
        calibration_t, calibration_u = valve_trace(pixels(pdf, 10), 220, 26)
        replay_t, replay_u = valve_trace(pixels(pdf, 14), 234, 40)
    checks = c09_validate().figure_checks
    for observed, check in zip(figure_levels, checks):
        if abs(observed - check.reference_cm) > 1e-6:
            raise ValueError("digitization differs from the stored figure reference")

    def plateau(start):
        in_window = (calibration_t >= start) & (calibration_t <= start + 2000)
        return float(np.median(calibration_u[in_window]))

    # Same regulated h2 on both sides in Fig. 6. The balance at h2=0.4 m
    # gives the SI valve scale before disturbance, then its drop gives the step.
    plant = C09PlantParameters()
    volts_per_unit = plant.c2 * plant.v2 * math.sqrt(0.4) / (plant.c1 * plateau(44000))
    step_v = (plateau(44000) - plateau(54000)) * volts_per_unit
    pfc = simulate_c09(C09Controller.PFC, disturbance=step_v)
    pfc_post = np.median(
        [100 * h for time, h in zip(pfc.times, pfc.h2) if 54000 <= time <= 56000]
    )

    # Expressing the printed coefficients on the plotted 0..100 level axis
    # yields one tenth of the SI level rate after converting cm back to m:
    # sqrt(100 h)/100 = sqrt(h)/10. This is a diagnostic convention.
    chart_plant = C09PlantParameters(
        c1=plant.c1 / 10, c2=plant.c2 / 10, c3=plant.c3 / 10
    )
    h1 = h2 = peak_cm = 0.0
    voltages = np.interp(np.arange(28000), replay_t, replay_u) * volts_per_unit
    for second, voltage in enumerate(voltages):
        h1, h2 = _c09_rk4_step(h1, h2, voltage, 1.0, chart_plant)
        if second + 1 >= 24000:
            peak_cm = max(peak_cm, 100 * h2)
    print(
        json.dumps(
            {
                "reference_h2_cm": figure_levels,
                "default_h2_cm": [c.model_cm for c in checks],
                "valve_plateaus_plot_units": [plateau(44000), plateau(54000)],
                "inferred_volts_per_plot_unit": volts_per_unit,
                "inferred_step_V": step_v,
                "pfc_post_with_inferred_step_cm": float(pfc_post),
                "ifc2_recorded_input_peak_cm": peak_cm,
            },
            indent=2,
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()

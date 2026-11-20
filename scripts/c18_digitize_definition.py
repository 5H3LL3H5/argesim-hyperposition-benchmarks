"""Reconstruct the four plotted C18 signals from the pinned definition PDF.

Only this offline extraction needs PyMuPDF. The benchmark reads the packaged
CSV. The PDF contains display curves, including cubic Béziers, rather than
a table of the original sensor samples.
"""

import argparse
import csv
import hashlib
import io
import sys
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from argesim_benchmarks.models.c18_nonlinear_identification import C18_FIGURE_PDF_SHA256

# First page of this exact edition. Each axes frame is followed by ticks,
# axes lines and 21 curve strokes stored in right-to-left chunk order.
PANELS = {
    "training_thickening": (69, 112, 132),
    "training_force": (4, 47, 67),
    "validation_thickening": (200, 243, 263),
    "validation_force": (135, 178, 198),
}


def cubic(t, a, b, c, d):
    v = 1.0 - t
    return v**3 * a + 3 * v * t * (v * b + t * c) + t**3 * d


def ordinate(points, fraction):
    if fraction == 0:
        return points[0].y
    if len(points) == 2:
        return points[0].y + fraction * (points[-1].y - points[0].y)
    # PDF curves are parametrized in both axes. Solve x(t) before reading y(t).
    x = tuple(p.x for p in points)
    target = x[0] + fraction * (x[-1] - x[0])
    low, high = 0.0, 1.0
    for _ in range(45):
        mid = (low + high) / 2
        if cubic(mid, *x) < target:
            low = mid
        else:
            high = mid
    return cubic((low + high) / 2, *(p.y for p in points))


def samples(drawings, frame, first, last):
    bounds = drawings[frame]["rect"]

    # The horizontal scale is 0..20 s and the vertical scale is 0..1.
    def sample_index(x):
        tick = (x - bounds.x0) * 2000 / bounds.width
        nearest = round(tick)
        if abs(tick - nearest) > 0.26:
            raise ValueError("curve vertex is off the 100 Hz sample grid")
        return nearest

    result = []
    previous = None
    for path in reversed(drawings[first : last + 1]):
        for kind, *points in path["items"]:
            if kind not in ("l", "c"):
                raise ValueError(f"unexpected curve operator {kind!r}")
            start, end = sample_index(points[0].x), sample_index(points[-1].x)
            if start != len(result) or end <= start:
                raise ValueError("discontinuous or reversed C18 trace")
            if previous is not None and abs(points[0].y - previous.y) > 0.002:
                raise ValueError("C18 trace is discontinuous in amplitude")
            for i in range(start, end):
                y = ordinate(points, (i - start) / (end - start))
                result.append((bounds.y1 - y) / bounds.height)
            previous = points[-1]
    if len(result) != 1999 or previous is None:
        raise ValueError("C18 trace must end at sample 1999 (19.99 s)")
    result.append((bounds.y1 - previous.y) / bounds.height)
    return result


def extract(source):
    data = source.read_bytes()
    if hashlib.sha256(data).hexdigest() != C18_FIGURE_PDF_SHA256:
        raise ValueError("expected the published C18-definition.pdf SHA-256")
    with pymupdf.open(stream=data, filetype="pdf") as pdf:
        drawings = pdf[0].get_drawings()
        columns = [samples(drawings, *panel) for panel in PANELS.values()]
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(("time_s", *PANELS))
    for index, values in enumerate(zip(*columns, strict=True)):
        writer.writerow((f"{index / 100:.2f}", *(f"{v:.6f}" for v in values)))
    return output.getvalue().encode("ascii")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("definition_pdf", type=Path)
    parser.add_argument("output_csv", type=Path)
    args = parser.parse_args()
    args.output_csv.write_bytes(extract(args.definition_pdf))

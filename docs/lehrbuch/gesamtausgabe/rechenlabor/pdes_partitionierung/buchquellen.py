"""Resolve the same named laboratory sources in an export or repository checkout."""
import zipfile
from pathlib import Path

CAVITY_BASIS = Path("rechenlabor/kavitaet_vollgitter/basis")
CAVITY_SOURCE = Path("rechenlabor/kavitaet_vollgitter/src")
CHECKOUT_ARCHIVE = Path("docs/lehrbuch/gesamtausgabe/pakete/Laborquellen.zip")


def read_book_source(root, relative):
    path = root / relative
    if path.is_file():
        return path.read_bytes()
    with zipfile.ZipFile(root / CHECKOUT_ARCHIVE) as archive:
        return archive.read(relative.as_posix())


def solver_root(root):
    # The full lab carries its own snapshot. Never fall back to an installed
    # argesim_benchmarks when neither supported layout is present.
    for path in (root / CAVITY_BASIS / "original", root):
        if (path / "argesim_benchmarks/__init__.py").is_file():
            return path
    raise FileNotFoundError(f"No laboratory solver sources under {root}")

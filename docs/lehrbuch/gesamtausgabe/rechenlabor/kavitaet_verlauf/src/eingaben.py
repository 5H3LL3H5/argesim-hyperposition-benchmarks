"""Read and verify the frozen CP2 inputs from a checkout or its complete offline lab."""

import hashlib
import io
import json
import zipfile
from pathlib import Path

if __package__:
    from .design import ticks
else:
    from design import ticks

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "rechenlabor/kavitaet_vollgitter/"


def copy_members(members, read, output):
    for name, expected in members.items():
        data = read(name)
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError(f"Falsche Prüfsumme für {name}")
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)


def prepare(output, archive=None):
    groups = json.loads((ROOT / "eingaben.json").read_text())
    all_members = {name: sha for group in groups.values() for name, sha in group.items()}
    packages = ROOT.parents[1] / "pakete"
    expanded = ROOT.parent / "kavitaet_vollgitter"
    if archive is not None:
        with zipfile.ZipFile(archive) as source:
            copy_members(all_members, lambda name: source.read(PREFIX + name), output)
    elif (expanded / "src/d2q9.cpp").is_file():
        copy_members(all_members, lambda name: (expanded / name).read_bytes(), output)
    elif (packages / "Feldpakete.json").is_file():
        index = json.loads((packages / "Feldpakete.json").read_text())
        for archive_name, members in groups.items():
            if archive_name == "Laborquellen.zip":
                payload = packages / archive_name
            else:
                record = index[archive_name]
                data = b"".join((packages / part).read_bytes() for part in record["parts"])
                if len(data) != record["size"] or hashlib.sha256(data).hexdigest() != record["sha256"]:
                    raise ValueError(f"Unvollständiges Feldarchiv {archive_name}")
                payload = io.BytesIO(data)
            with zipfile.ZipFile(payload) as source:
                copy_members(members, lambda name: source.read(PREFIX + name), output)
    else:
        raise FileNotFoundError(
            "Zum Nachrechnen die Gesamtausgabe auschecken oder das vollständige "
            "Offline-Labor mit --input-archive ZIP angeben (siehe README.md)."
        )

    original = list(map(int, (output / "src/zeitpunkte.txt").read_text().split()))
    schedule = ticks(original)
    for scale, n in ((1, 257), (4, 65)):
        (output / f"ticks{n}.txt").write_text("".join(f"{k // scale}\n" for k in schedule))

"""Draw the measured C19R cell activity and the two eight-rank partitions."""
from pathlib import Path
import json
import sys
from zipfile import ZipFile

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.collections import PatchCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle
import numpy as np


def draw(archive, target):
    with ZipFile(archive) as package:
        counts = np.frombuffer(package.read("c19_nom/base.counts"), dtype="<u8").reshape(33, 65)
        partitions = json.loads(package.read("c19_nom/maps.json"))
    colors = ["#f4f7f5", "#c7e2dc", "#73b0ad", "#2c777d", "#123e54"]
    thresholds = [0, 1, 10, 100, 1000, int(max(1001, counts.max() + 1))]
    cmap = ListedColormap(colors)
    bands = BoundaryNorm(thresholds, cmap.N)(counts)
    rectangles = [[] for _ in colors]
    for y, row in enumerate(bands):
        edges = np.r_[0, np.flatnonzero(np.diff(row)) + 1, len(row)]
        for left, right in zip(edges[:-1], edges[1:], strict=True):
            if row[left] > 0:
                rectangles[row[left]].append(Rectangle((left - .5, y - .5), right-left, 1))
    mpl.rcParams.update({"font.family": "DejaVu Sans", "svg.fonttype": "none", "svg.hashsalt": "C19R-v920"})
    fig, axes = plt.subplots(1, 2, figsize=(8, 3.05))
    for ax, (layout, name) in zip(axes, [("tiles", "Gleich große Kacheln"), ("weighted", "Ereignisgewichtete Streifen")], strict=True):
        part = next(p for p in partitions if p["ranks"] == 8 and p["layout"] == layout)
        ax.set(xlim=(-.5,64.5), ylim=(-.5,32.5), facecolor=colors[0])
        for color, patches in zip(colors[1:], rectangles[1:], strict=True):
            ax.add_collection(PatchCollection(patches, facecolor=color, edgecolor="none"))
        for cut in part["cx"]:
            ax.axvline(cut - 0.5, color="#B44B23", lw=1.15)
        for cut in part["cy"]:
            ax.axhline(cut - 0.5, color="#B44B23", lw=1.15)
        ax.plot(12, 16, marker="D", ms=5, mec="#222222", mfc="#f4bd4b")
        ax.set(aspect="equal", xticks=[0, 16, 32, 48, 64], yticks=[0, 16, 32], xlabel="Spalte")
        ax.set_title(name, fontsize=12, color="#163849")
        ax.tick_params(length=2, labelsize=9)
    axes[0].set_ylabel("Zeile")
    labels = ["0", "1–9", "10–99", "100–999", "ab 1.000"]
    handles = [Patch(facecolor=c, edgecolor="#809698", linewidth=.5, label=s) for c, s in zip(colors, labels, strict=True)]
    handles += [Line2D([], [], color="#B44B23", label="Schnitt"),
                Line2D([], [], color="none", marker="D", ms=5, mfc="#f4bd4b", mec="#222222", label="Quelle")]
    fig.legend(handles=handles, loc="lower center", ncol=7, frameon=False, fontsize=8.5)
    fig.subplots_adjust(left=.075, right=.99, top=.92, bottom=.27, wspace=.12)
    fig.savefig(target, metadata={"Date": None})
    plt.close(fig)


if __name__ == "__main__":
    directory = Path(__file__).resolve().parent
    draw(directory/"PDES_Partitionierung_Messpaket.zip", Path(sys.argv[1]))

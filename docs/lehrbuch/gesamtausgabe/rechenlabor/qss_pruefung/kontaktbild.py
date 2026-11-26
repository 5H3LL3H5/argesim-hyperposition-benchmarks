"""Schwellenparabeln mit exakt skalierter Abszisse und Ordinate (Abb. 6.8)."""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

edition = Path(__file__).resolve().parents[2]
plt.rcParams["svg.hashsalt"] = "qss-kontakt-919"
z = np.linspace(-1.55, 1.55, 311)
fig, ax = plt.subplots(figsize=(7.2, 3.1), layout="constrained")
ax.axhline(0, color="0.35", lw=1)
for offset, style, color, label in (
    (1, "--", "#a43d29", "Band verfehlt"),
    (0, "-", "#305888", "Berührung"),
    (-1, "-.", "#176452", "zwei Durchtritte"),
):
    ax.plot(z, z**2 + offset, style, color=color, label=label, lw=2)
ax.scatter([-1, 1], [0, 0], color="#176452")
ax.scatter([0], [0], color="#305888")
ax.set(xlabel=r"Zeit relativ zum Minimum   $z=2^{26}(s-1)$",
       ylabel=r"Skalierter Schwellenabstand   $2^{52}p(s)$",
       xlim=(-1.6, 1.6), ylim=(-1.2, 3.65))
ax.legend(loc="upper center", frameon=False)
ax.spines[["right", "top"]].set_visible(False)
for folder, fmt in (("abbildungen", "svg"), ("druck", "pdf")):
    metadata = {"Date": None} if fmt == "svg" else {"CreationDate": None}
    fig.savefig(edition / folder / f"qss_kontakt.{fmt}", metadata=metadata)

"""Rebuild textbook figure revisions from the equations and archived lab fields."""

import runpy

import matplotlib.pyplot as plt
import numpy as np
from figures import DEST, GOLD, INK, RUST, TEAL, save
from matplotlib.patches import Rectangle

MATERIAL = DEST.parent / "material"
GRID = "#71848a"


def thermal_diagram():
    fig, ax = plt.subplots(figsize=(6.8, 1.66), layout="constrained")
    ax.axis("off")
    ax.set(xlim=(0, 10.6), ylim=(0, 3.1))
    ax.add_patch(Rectangle((1.55, 0.85), 4.2, 0.9, facecolor="#e0efe9", edgecolor=TEAL))
    for x in (1.29, 1.37, 1.45):
        ax.plot([x, x], [0.69, 1.91], color=GRID, lw=1.3)
    ax.text(0.05, 1.29, "isoliert", va="center")
    ax.text(3.66, 1.29, "Stab · Länge L, Querschnitt A", ha="center", va="center")
    for x in (2.3, 3.66, 5.0):
        ax.annotate(
            "", (x, 1.77), (x, 2.33), arrowprops={"arrowstyle": "-|>", "color": GOLD}
        )
    ax.text(3.66, 2.55, "gleichmäßig zugeführte Leistung P", ha="center", color=GOLD)
    ax.text(1.55, 0.37, "x = 0", ha="center")
    ax.text(5.75, 0.37, "x = L", ha="center")
    ax.plot([5.75, 9.45], [1.29, 1.29], c=TEAL)
    for x, label in ((6, "R₁"), (7.66, "R₂")):
        ax.add_patch(
            Rectangle(
                (x, 1.05), 0.72, 0.48, edgecolor=TEAL, facecolor="white", zorder=3
            )
        )
        ax.text(x + 0.36, 1.29, label, ha="center", va="center", zorder=4)
    ax.scatter([7.18], [1.29], s=26, c=TEAL)
    ax.text(7.18, 0.37, "Kontakt Tₛ", ha="center")
    ax.annotate(
        "", (9.45, 1.29), (8.38, 1.29), arrowprops={"arrowstyle": "-|>", "color": TEAL}
    )
    ax.text(9.62, 1.29, "Tₐ", va="center")
    ax.text(9.43, 0.37, "Umgebung", ha="center")
    ax.text(8.6, 2.01, "Wärmestrom Q̇", ha="center", color=TEAL)
    save("stab", fig)


def temperature():
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(6.65, 2.25), layout="constrained")
    t = np.linspace(0, 1440, 300)
    ax.plot(t, 20 + 40 * (1 - np.exp(-t / 480)), color=TEAL, label="Stab T")
    ax.plot(
        t, 20 + 30 * (1 - np.exp(-t / 480)), color=GOLD, ls="--", label="Kontakt Tₛ"
    )
    ax.axvline(480, color=GRID, ls=":", lw=1)
    ax.set(xlabel="Zeit [s]", ylabel="Temperatur [°C]", xlim=(0, 1440), ylim=(17, 63))
    ax.legend(loc="lower right")
    x = np.linspace(0, 0.05)
    bx.plot(
        100 * x,
        60 + 10 * (0.05**2 - x**2) / (2 * 0.2 * 0.05),
        color=TEAL,
        label="Feld T(x)",
    )
    bx.axhline(60, color=GOLD, ls="--", label="Ein-Speicher-Modell")
    bx.set(xlabel="Ort [cm]", ylabel="Stationär [°C]", xlim=(0, 5), ylim=(59.8, 61.55))
    bx.legend(loc="lower center", bbox_to_anchor=(0.5, 1), ncol=2)
    for axis in (ax, bx):
        axis.grid(axis="y", alpha=0.22)
    save("thermisch", fig)


def stability():
    fig, ax = plt.subplots(figsize=(6.1, 2.2), layout="constrained")
    v = np.logspace(-2, 2, 400)
    ax.semilogx(v, 1 - v, color=GRID, ls=":", label="Euler vorwärts")
    ax.semilogx(v, (1 - v / 2) / (1 + v / 2), color=GOLD, ls="--", label="Trapezregel")
    ax.semilogx(v, 1 / (1 + v), color=INK, ls="-.", label="Euler rückwärts")
    ax.semilogx(
        v,
        (1 - 2 * v / 5 + v * v / 20) / (1 + 3 * v / 5 + 3 * v * v / 20 + v**3 / 60),
        color=TEAL,
        label="Radau IIA (3 Stufen)",
    )
    ax.axhline(0, color=GRID, lw=0.5)
    ax.scatter([1, 2], [0, -1], color=INK, zorder=4, s=13)
    ax.annotate("(1; 0)", (1, 0), xytext=(-33, -14), textcoords="offset points")
    ax.annotate("(2; −1)", (2, -1), xytext=(6, 4), textcoords="offset points")
    ax.set(
        xlabel="Betrag des negativen Arguments |hλ|",
        ylabel="Verstärkung R(hλ)",
        ylim=(-1.17, 1.1),
        xlim=(0.01, 100),
    )
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1), ncol=4)
    save("stabil", fig)


def contacts():
    fig, ax = plt.subplots(figsize=(6.3, 1.7), layout="constrained")
    t = np.linspace(0, 4, 401)
    for j, (color, style) in enumerate(
        zip((TEAL, GOLD, INK, GRID), ("-", "--", "-.", ":"))
    ):
        travel = np.clip(t - j, 0, 1) if j < 3 else np.maximum(0, t - 3)
        ax.plot(t, j + travel, color=color, ls=style, label=f"Kugel {j + 1}")
    ax.scatter([1, 2, 3], [1, 2, 3], s=12, color=INK, zorder=4)
    ax.set(
        xlabel="Zeit [s]",
        ylabel="Verschobene Lage [m]",
        xlim=(0, 4),
        ylim=(-0.13, 4.2),
        xticks=range(5),
        yticks=range(5),
    )
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1), ncol=4)
    ax.grid(alpha=0.22)
    save("kontakte", fig)


def pendulum():
    hits, pieces = runpy.run_path(str(MATERIAL / "labor.py"))["c07"]()
    fig, (angle, velocity, detail) = plt.subplots(
        1, 3, figsize=(7.2, 2.15), layout="constrained"
    )
    for length, solution in pieces:
        t = np.linspace(
            solution.t[0], solution.t[-1], max(6, int(120 * np.ptp(solution.t)))
        )
        phi, omega = solution.sol(t)
        color, style = (TEAL, "-") if length == 1 else (RUST, "--")
        angle.plot(t, phi, style, color=color, label="1 m" if length == 1 else "0,3 m")
        for axis in (velocity, detail):
            axis.plot(t, omega, style, color=color)
    for t, before, after in hits:
        angle.axvline(t, color=GRID, lw=0.5)
        velocity.plot([t, t], [before, after], color=GRID, lw=0.65)
    for (t, before, after), label in zip(hits[-2:], ("7", "8")):
        detail.plot([t, t], [before, after], color=GRID, lw=0.85)
        detail.axvline(t, color=GRID, lw=0.55)
        detail.text(
            t,
            0.96,
            label,
            ha="center",
            va="top",
            transform=detail.get_xaxis_transform(),
        )
    angle.axhline(-np.pi / 12, color=GRID, ls=":", lw=0.8)
    handles, captions = angle.get_legend_handles_labels()
    labels = dict(zip(captions, handles))
    angle.legend(labels.values(), labels.keys(), ncol=2, fontsize=7, loc="upper right")
    angle.set(ylabel="Winkel [rad]", xlim=(0, 10))
    velocity.set(ylabel="Winkeltempo [rad/s]", xlim=(0, 10))
    detail.set(
        title="Letzte zwei Wechsel",
        xlim=(6.6, 6.8),
        ylim=(-0.6, 0.6),
        xticks=(6.6, 6.7, 6.8),
    )
    for axis in (angle, velocity, detail):
        axis.set_xlabel("Zeit [s]")
        axis.grid(axis="y", alpha=0.22)
    save("c07kurven", fig)


def cavity():
    with np.load(
        MATERIAL / "cp2_feldlabor/cavity/cavity-fields.npz", allow_pickle=False
    ) as data:
        ref, prediction = data["reference"], data["fno"]
    fig, axes = plt.subplots(1, 3, figsize=(6.3, 2.55), layout="constrained")
    for ax, values, title in zip(
        axes,
        (ref, prediction, abs(prediction - ref)),
        ("D2Q9", "FNO", "Absoluter Fehler"),
    ):
        error = title == "Absoluter Fehler"
        img = ax.imshow(
            values,
            origin="lower",
            interpolation="nearest",
            vmin=0,
            vmax=0.16 if error else 1,
            cmap="magma" if error else "cividis",
        )
        ax.set(title=title, xlabel="Gitterspalte", xticks=(0, 8, 16), yticks=(0, 8, 16))
        fig.colorbar(
            img,
            ax=ax,
            orientation="horizontal",
            shrink=0.9,
            pad=0.17,
            ticks=(0, 0.08, 0.16) if error else (0, 0.5, 1),
        )
        if error:
            ax.add_patch(
                Rectangle(
                    (0.5, 0.5), 15, 15, fill=False, edgecolor="white", lw=1.1, ls="--"
                )
            )
    axes[0].set_ylabel("Gitterzeile")
    save("cp2kavitaet", fig)


if __name__ == "__main__":
    thermal_diagram()
    temperature()
    stability()
    contacts()
    pendulum()
    cavity()

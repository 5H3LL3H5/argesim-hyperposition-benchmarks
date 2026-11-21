"""Handrechnungen und die CP2-Saite, nur mit der Python-Standardbibliothek."""
from math import fsum, sqrt


def transport():
    """Ein Schritt mit Courant-Zahl 1/2 auf dem periodischen Vier-Zellen-Gitter."""
    starts = (0.0, 1.0, 1.0, 0.0)
    courant = 0.5
    upwind, lax_wendroff = [], []
    for index, center in enumerate(starts):
        left, right = starts[index - 1], starts[(index + 1) % len(starts)]
        upwind.append(center - courant * (center - left))
        lax_wendroff.append(center - courant * (right - left) / 2
                            + courant**2 * (right - 2 * center + left) / 2)
    return upwind, lax_wendroff


def kollidieren():
    """Ruhendes D2Q9 mit symmetrischer Störung in Ost- und Westrichtung."""
    # Reihenfolge: Ruhe, Ost, Nord, West, Süd, vier Diagonalen.
    equilibrium = (4 / 9, *([1 / 9] * 4), *([1 / 36] * 4))
    before = list(equilibrium)
    before[0] -= 0.04
    before[1] += 0.02
    before[3] += 0.02
    after = [f + 0.5 * (eq - f) for f, eq in zip(before, equilibrium)]
    return before, after


def lernschritt():
    """Ein Gradientenabstieg für ReLU(w·x) im positiven linearen Ast."""
    weight, x, target, rate = 1.0, 2.0, 1.0, 0.1
    estimate = max(0.0, weight * x)
    gradient = (estimate - target) * x
    new_weight = weight - rate * gradient
    new_estimate = max(0.0, new_weight * x)
    return new_weight, new_estimate, (new_estimate - target)**2 / 2


def referenz(x, t, length=0.5, height=0.05, speed=0.06):
    """d’Alembert mit ungerader periodischer Fortsetzung der Anfangsauslenkung."""
    def spiegeln(s):
        r = (s / length + 1.0) % 2.0 - 1.0
        a = abs(r)
        value = 2 * height * min(a, 1 - a)
        return -value if r < 0 else value

    return (spiegeln(x - speed * t) + spiegeln(x + speed * t)) / 2


def saite(knoten, schritt=0.01):
    """Relativer L2-Fehler von Störmer–Verlet nach 5 und 8 s am CP2-Dreieck."""
    if not isinstance(knoten, int) or knoten < 3 or not 0 < schritt <= 5:
        raise ValueError('Mindestens drei Knoten und ein positiver Zeitschritt bis 5 s sind erforderlich.')
    length, speed, height = 0.5, 0.06, 0.05
    dx = length / (knoten - 1)
    courant = speed * schritt / dx
    if courant > 1:
        raise ValueError('Für diese explizite Wellenrechnung muss c·dt/dx ≤ 1 gelten.')
    times = (5.0, 8.0)
    indices = [round(t / schritt) for t in times]
    if any(abs(i * schritt - t) > 1e-12 for i, t in zip(indices, times)):
        raise ValueError('Beide Messzeiten müssen auf das Schrittgitter fallen.')
    x = [j * dx for j in range(knoten)]
    prev = [2 * height * min(s, length - s) / length for s in x]
    curr = [0.0] * knoten
    c2 = courant**2
    # Bei Anfangsruhe liefert eine halbe Beschleunigung den ersten Zeitschritt.
    for j in range(1, knoten - 1):
        curr[j] = prev[j] + 0.5 * c2 * (prev[j-1] - 2*prev[j] + prev[j+1])
    errors = []
    for step in range(1, indices[-1] + 1):
        if step in indices:
            exact = [referenz(s, step * schritt) for s in x]
            errors.append(sqrt(fsum((a-b)**2 for a, b in zip(curr, exact))
                               / fsum(a*a for a in exact)))
        if step < indices[-1]:
            nxt = [0.0] * knoten
            for j in range(1, knoten - 1):
                nxt[j] = (2*curr[j] - prev[j]
                          + c2 * (curr[j-1] - 2*curr[j] + curr[j+1]))
            prev, curr = curr, nxt
    return errors


if __name__ == '__main__':
    upwind, lw = transport()
    print('Upwind', upwind, 'Lax–Wendroff', lw)
    before, after = kollidieren()
    print(f'D2Q9 Ost {before[1]:.6f} → {after[1]:.6f}, Dichte {fsum(after):.6f}')
    w, y, loss = lernschritt()
    print(f'Gewicht {w:.2f}, Vorhersage {y:.2f}, Verlust {loss:.3f}')
    for n in (65, 501):
        for t, error in zip((5, 8), saite(n)):
            print(f'CP2-Saite, Verlet, {n} Knoten, {t} s: {100*error:.4f} %')

"""D2Q9 startup followed by the archived coarse-grid Hankel correction."""

import json
from pathlib import Path

import numpy as np
from design import N
from fields import Frozen
from native import Lattice

PROTOCOL = json.loads(
    (Path(__file__).resolve().parents[1] / "switch_protocol.json").read_text()
)
SWITCH = PROTOCOL["switch_inclusive_k"]


class Switched:
    def __init__(self, inputs, native_lib):
        self.coarse_net = Frozen(inputs, "korrektur", "hankel")
        self.lattice = Lattice(native_lib)

    def predict(self, ticks, re):
        ticks = np.asarray(ticks, dtype=np.int32)
        if (
            not len(ticks)
            or ticks[0] != 0
            or np.any(np.diff(ticks) <= 0)
            or np.any(ticks % 4)
        ):
            raise ValueError(
                "start at zero with increasing common fine/coarse output times"
            )
        cut = int(np.searchsorted(ticks, SWITCH, side="right"))
        if cut == len(ticks):
            return self.lattice.fields(N, re, ticks)
        out = np.empty((len(ticks), N, N, 2), dtype=float)
        out[:cut] = self.lattice.fields(N, re, ticks[:cut])
        late = ticks[cut:]
        coarse = self.lattice.fields(65, re, np.r_[0, late // 4])[1:]
        for i in range(0, len(late), 12):
            end = min(i + 12, len(late))
            out[cut + i : cut + end] = self.coarse_net.predict(
                late[i:end], re, coarse[i:end]
            )
        return out


SMOOTH = json.loads(
    (Path(__file__).resolve().parents[1] / "smooth_protocol.json").read_text()
)
START, STOP = SMOOTH["start_k"], SMOOTH["end_k"]


def weight(ticks):
    s = np.clip((np.asarray(ticks) - START) / (STOP - START), 0.0, 1.0)
    return s * s * (3 - 2 * s)


class Smoothed(Switched):
    def predict(self, ticks, re):
        ticks = np.asarray(ticks, dtype=np.int32)
        if (
            not len(ticks)
            or ticks[0] != 0
            or np.any(np.diff(ticks) <= 0)
            or np.any(ticks % 4)
        ):
            raise ValueError(
                "start at zero with increasing common fine/coarse output times"
            )
        first = int(np.searchsorted(ticks, START, side="right"))
        # The fine solution has zero weight right at STOP.
        stop = int(np.searchsorted(ticks, STOP, side="left"))
        if first == len(ticks):
            return self.lattice.fields(N, re, ticks)
        out = np.empty((len(ticks), N, N, 2))
        out[:stop] = self.lattice.fields(N, re, ticks[:stop])
        late = ticks[first:]
        coarse = self.lattice.fields(65, re, np.r_[0, late // 4])[1:]
        for i in range(0, len(late), 12):
            end = min(i + 12, len(late))
            lo = first + i
            hi = first + end
            hybrid = self.coarse_net.predict(late[i:end], re, coarse[i:end])
            mid = max(0, min(hi, stop) - lo)
            if mid:
                w = weight(late[i : i + mid])[:, None, None, None]
                out[lo : lo + mid] += w * (hybrid[:mid] - out[lo : lo + mid])
            out[lo + mid : hi] = hybrid[mid:]
        return out

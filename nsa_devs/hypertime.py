"""Restricted time values of the form ``a + b epsilon``.

The class is a superdense-time encoding sufficient for the reference
NSA-DEVS experiments. It deliberately does not pretend to implement the full
hyperreal field.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction
from functools import total_ordering

Scalar = int | float | str | Fraction


def _as_fraction(value: Scalar) -> Fraction:
    if isinstance(value, bool):
        raise TypeError("time values must be numeric, not bool")
    if isinstance(value, Fraction):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("time values must be finite")
        return Fraction(str(value))
    return Fraction(value)


@total_ordering
@dataclass(frozen=True)
class HyperTime:
    """A non-negative macro time and a non-negative microstep coefficient."""

    macro: Fraction
    micro: int = 0

    def __post_init__(self) -> None:
        macro = _as_fraction(self.macro)
        object.__setattr__(self, "macro", macro)
        if macro < 0:
            raise ValueError("macro time must be non-negative")
        if not isinstance(self.micro, int) or isinstance(self.micro, bool):
            raise TypeError("microstep must be an integer")
        if self.micro < 0:
            raise ValueError("microstep must be non-negative")

    @classmethod
    def at(cls, macro: Scalar, micro: int = 0) -> HyperTime:
        return cls(_as_fraction(macro), micro)

    def after_epsilon(self, steps: int = 1) -> HyperTime:
        if not isinstance(steps, int) or isinstance(steps, bool):
            raise TypeError("epsilon steps must be an integer")
        if steps <= 0:
            raise ValueError("epsilon steps must be positive")
        return HyperTime(self.macro, self.micro + steps)

    def after_finite(self, delay: Scalar) -> HyperTime:
        finite_delay = _as_fraction(delay)
        if finite_delay <= 0:
            raise ValueError("finite delay must be positive")
        return HyperTime(self.macro + finite_delay, 0)

    def standard_part(self) -> Fraction:
        """Return the macro projection for this restricted time domain."""

        return self.macro

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, HyperTime):
            return NotImplemented
        return (self.macro, self.micro) < (other.macro, other.micro)

    def __str__(self) -> str:
        if self.micro == 0:
            return str(self.macro)
        return f"{self.macro}+{self.micro}epsilon"

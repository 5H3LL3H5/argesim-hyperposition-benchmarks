"""Root-finding algorithms for boundary value problems."""

import math
import sys
from collections.abc import Callable

from ..ivp import IntegrationError


def _evaluate_finite(f: Callable[[float], float], x: float) -> float:
    raw_value = f(x)
    if isinstance(raw_value, bool):
        raise TypeError("root function must return a real number")
    value = float(raw_value)
    if not math.isfinite(value):
        raise IntegrationError("root function returned a non-finite value")
    return value


def brentq(
    f: Callable[[float], float],
    a: float,
    b: float,
    tol: float = 1e-12,
    maxiter: int = 100,
) -> float:
    """Find a root of a function in a bracketing interval using Brent's method.

    This combines root bracketing, interval bisection, and inverse quadratic
    interpolation.
    """
    if not callable(f):
        raise TypeError("f must be callable")
    if isinstance(tol, bool):
        raise TypeError("tol must be a real number")
    tolerance = float(tol)
    if not math.isfinite(tolerance) or tolerance <= 0.0:
        raise ValueError("tol must be positive and finite")
    if not isinstance(maxiter, int) or isinstance(maxiter, bool):
        raise TypeError("maxiter must be an integer")
    if maxiter <= 0:
        raise ValueError("maxiter must be positive")
    if isinstance(a, bool) or isinstance(b, bool):
        raise TypeError("bracket endpoints must be real numbers")
    left = float(a)
    right = float(b)
    if not math.isfinite(left) or not math.isfinite(right):
        raise ValueError("bracket endpoints must be finite")

    a = left
    b = right
    fa = _evaluate_finite(f, a)
    fb = _evaluate_finite(f, b)
    if fa == 0.0:
        return a
    if fb == 0.0:
        return b
    if (fa > 0.0) == (fb > 0.0):
        raise ValueError("f(a) and f(b) must have different signs (root not bracketed)")

    if abs(fa) < abs(fb):
        a, b = b, a
        fa, fb = fb, fa

    c = a
    fc = fa
    d = b - a
    e = d

    for _ in range(maxiter):
        if abs(fc) < abs(fb):
            a, b, c = b, c, b
            fa, fb, fc = fb, fc, fb

        tol1 = 2.0 * sys.float_info.epsilon * abs(b) + 0.5 * tolerance
        xm = 0.5 * (c - b)

        if abs(xm) <= tol1 or fb == 0.0:
            return b

        if abs(e) >= tol1 and abs(fa) > abs(fb):
            s = fb / fa
            if a == c:
                p = 2.0 * xm * s
                q = 1.0 - s
            else:
                q = fa / fc
                r = fb / fc
                p = s * (2.0 * xm * q * (q - r) - (b - a) * (r - 1.0))
                q = (q - 1.0) * (r - 1.0) * (s - 1.0)
            if p > 0.0:
                q = -q
            p = abs(p)

            min1 = 3.0 * xm * q - abs(tol1 * q)
            min2 = abs(e * q)
            if 2.0 * p < (min1 if min1 < min2 else min2):
                e = d
                d = p / q
            else:
                d = xm
                e = d
        else:
            d = xm
            e = d

        a = b
        fa = fb
        if abs(d) > tol1:
            b += d
        else:
            b += tol1 if xm >= 0.0 else -tol1
        fb = _evaluate_finite(f, b)

        if (fb > 0.0 and fc > 0.0) or (fb < 0.0 and fc < 0.0):
            c = a
            fc = fa
            d = b - a
            e = d

    raise IntegrationError("brentq did not converge within maxiter")

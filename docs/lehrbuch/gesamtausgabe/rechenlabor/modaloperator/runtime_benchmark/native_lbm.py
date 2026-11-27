"""Array-based interface for the compiled D2Q5 diffusion and CP2 D2Q9 kernels."""

import ctypes
import math
import subprocess
import time
from pathlib import Path

import numpy as np

SOURCE = Path(__file__).resolve().parent / "native" / "lbm.cpp"
FLAGS = [
    "-std=c++17",
    "-O3",
    "-march=native",
    "-ffp-contract=off",
    "-fopenmp-simd",
    "-fPIC",
    "-shared",
    "-Wall",
    "-Wextra",
    "-Werror",
]


def build(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    subprocess.run(["c++", *FLAGS, str(SOURCE), "-o", str(path)], check=True)
    return time.perf_counter() - start


def diffusion_steps(n, p):
    return max(1, math.ceil(6.0 * max(p.du, p.dv) * p.time * (n - 1) ** 2))


class Native:
    def __init__(self, path):
        self.lib = ctypes.CDLL(str(Path(path).resolve()))
        array = np.ctypeslib.ndpointer(
            dtype=np.float64, flags=("C_CONTIGUOUS", "ALIGNED")
        )
        args = [array, array, ctypes.c_int, ctypes.c_int]
        self.lib.d2q5.argtypes = [*args, *([ctypes.c_double] * 4)]
        self.lib.d2q9.argtypes = [*args, ctypes.c_double]
        self.lib.d2q5.restype = self.lib.d2q9.restype = ctypes.c_int

    def diffusion(self, x, p):
        a = np.ascontiguousarray(x, dtype=np.float64)
        n = a.shape[-1]
        if a.shape != (1, 2, n, n):
            raise ValueError("expected one two-channel square field")
        y = np.empty_like(a)
        ret = self.lib.d2q5(a, y, n, diffusion_steps(n, p), p.du, p.dv, p.rate, p.time)
        if ret:
            raise ValueError(f"D2Q5 failed, status {ret}")
        return y

    def cavity(self, x, lid=0.1, steps=16):
        a = np.ascontiguousarray(x, dtype=np.float64)
        n = a.shape[-1]
        if a.shape != (1, n, n):
            raise ValueError("expected one square density field")
        y = np.empty((1, 2, n, n), dtype=np.float64)
        ret = self.lib.d2q9(a, y, n, steps, lid)
        if ret:
            raise ValueError(f"D2Q9 failed, status {ret}")
        return y

"""Compile the frozen kernels and expose velocity outputs in RAM."""

import argparse
import ctypes
import hashlib
import subprocess
from pathlib import Path

import numpy as np

EXPECTED = "19af37840e3a86d8f9938af78d8277bc8e857314dfe034162e85f8fca2dc8de5"
FLAGS = [
    "-std=c++20",
    "-O3",
    "-march=native",
    "-ffp-contract=off",
    "-Wall",
    "-Wextra",
    "-Werror",
    "-fopenmp",
]


def build(inputs, build_dir):
    build_dir.mkdir(parents=True, exist_ok=True)
    cpp = inputs / "src/d2q9.cpp"
    data = cpp.read_bytes()
    if hashlib.sha256(data).hexdigest() != EXPECTED:
        raise ValueError("unrecognized upstream D2Q9 source")
    header, separator, _ = data.partition(b"int main(int argc,char**argv){")
    if not separator:
        raise ValueError("invalid source signature")
    (build_dir / "cp2_kernels.hpp").write_bytes(header)
    subprocess.run(["g++", *FLAGS, str(cpp), "-o", str(build_dir / "d2q9")], check=True)
    subprocess.run(
        [
            "g++",
            *FLAGS,
            "-shared",
            "-fPIC",
            "-I",
            str(build_dir),
            str(Path(__file__).with_name("memory.cpp")),
            "-o",
            str(build_dir / "cp2.so"),
        ],
        check=True,
    )


class Lattice:
    def __init__(self, lib):
        self.lib = ctypes.CDLL(str(lib.resolve()))
        array = np.ctypeslib.ndpointer
        self.lib.cp2_fields.argtypes = [
            ctypes.c_int,
            ctypes.c_double,
            array(np.int32, ndim=1, flags="C_CONTIGUOUS"),
            ctypes.c_int,
            array(np.float64, ndim=4, flags="C_CONTIGUOUS"),
        ]
        self.lib.cp2_fields.restype = ctypes.c_int

    def fields(self, n, re, ticks):
        k = np.ascontiguousarray(ticks, dtype=np.int32)
        out = np.empty((len(k), n, n, 2), dtype=np.float64)
        status = self.lib.cp2_fields(n, re, k, len(k), out)
        if status:
            raise RuntimeError(f"D2Q9 returned status {status}")
        return out


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("inputs", type=Path)
    p.add_argument("build", type=Path)
    a = p.parse_args()
    build(a.inputs, a.build)

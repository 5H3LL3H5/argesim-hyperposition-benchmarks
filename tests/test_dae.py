import importlib.util
import math
import unittest

from argesim_benchmarks import solve_dae


@unittest.skipUnless(importlib.util.find_spec("casadi"), "optional DAE backend")
class ResidualDAETests(unittest.TestCase):
    def test_nonlinear_implicit_rate_and_constraint(self):
        # x'=-x, z=x²+t; rate enters through a nonsingular nonlinear mass term.
        def residual(t, x, v, z):
            return ((1 + z[0]) * (v[0] + x[0]), z[0] - x[0] ** 2 - t)

        sol = solve_dae(
            residual, times=(0, 0.013, 0.4, 1), x0=(1,), xdot0=(-1,), z0=(1,)
        )
        for t, x, z, v in zip(
            sol.times, sol.differential, sol.algebraic, sol.derivatives
        ):
            self.assertAlmostEqual(x[0], math.exp(-t), delta=2e-7)
            self.assertAlmostEqual(z[0], math.exp(-2 * t) + t, delta=3e-7)
            self.assertAlmostEqual(v[0], -x[0], delta=1e-7)
        self.assertLess(sol.max_residual, 1e-6)

    def test_invalid_initial_data_and_index(self):
        opts = {"times": (0, 1), "x0": (1,), "xdot0": (0,), "z0": (0,)}
        with self.assertRaisesRegex(ValueError, "initial tuple"):
            solve_dae(lambda t, x, v, z: (v[0], z[0] - x[0]), **opts)
        with self.assertRaisesRegex(ValueError, "singular"):
            solve_dae(lambda t, x, v, z: (v[0], x[0] - 1), **opts)

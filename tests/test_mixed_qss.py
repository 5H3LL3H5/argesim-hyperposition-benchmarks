import math
import unittest

from argesim_benchmarks import InitialValueProblem, liqss_bdf
from argesim_benchmarks.runtime import normalise_solver_name, solve_ivp


class MixedLiqssBdfTests(unittest.TestCase):
    def test_all_bdf_partition_is_stable_on_a_stiff_scalar(self) -> None:
        problem = InitialValueProblem(
            lambda _time, state: (-1000.0 * state[0],),
            0.0,
            (1.0,),
            1.0,
            name="stiff-bdf-scalar",
            autonomous=True,
        )
        result = liqss_bdf(
            problem,
            1.0e-4,
            jacobian=lambda _time, _state: ((-1000.0,),),
            rtol=1.0e-3,
            atol=1.0e-6,
            max_step=0.1,
        )
        self.assertEqual(result.final_time, 1.0)
        self.assertLess(abs(result.final_state[0]), 1.0e-9)
        self.assertLess(result.stats.accepted_steps, 300)

    def test_partitioned_liqss2_bdf_matches_a_triangular_solution(self) -> None:
        problem = InitialValueProblem(
            lambda _time, state: (
                -state[0] + state[1],
                -10.0 * state[1],
            ),
            0.0,
            (0.0, 1.0),
            1.0,
            name="mixed-triangular",
            autonomous=True,
        )
        result = liqss_bdf(
            problem,
            (5.0e-4, 1.0e-6),
            bdf_partition=(1,),
            jacobian=lambda _time, _state: ((-1.0, 1.0), (0.0, -10.0)),
            rtol=1.0e-4,
            atol=1.0e-7,
            max_step=0.05,
        )
        exact = (
            (math.exp(-1.0) - math.exp(-10.0)) / 9.0,
            math.exp(-10.0),
        )
        self.assertEqual(result.final_time, 1.0)
        self.assertAlmostEqual(result.final_state[0], exact[0], delta=2.0e-4)
        self.assertAlmostEqual(result.final_state[1], exact[1], delta=2.0e-7)
        self.assertGreater(result.stats.accepted_steps, len(result.times) - 1)

    def test_bdf_error_control_converges_on_smooth_decay(self) -> None:
        problem = InitialValueProblem(
            lambda _time, state: (-state[0],),
            0.0,
            (1.0,),
            1.0,
            autonomous=True,
        )
        exact = math.exp(-1.0)
        coarse = liqss_bdf(
            problem,
            1.0e-3,
            rtol=1.0e-2,
            atol=1.0e-5,
            max_step=0.25,
        )
        fine = liqss_bdf(
            problem,
            1.0e-3,
            rtol=6.25e-4,
            atol=6.25e-7,
            max_step=0.25,
        )
        self.assertLess(
            abs(fine.final_state[0] - exact),
            abs(coarse.final_state[0] - exact),
        )

    def test_dispatch_aliases_and_non_autonomous_all_bdf(self) -> None:
        problem = InitialValueProblem(
            lambda time, _state: (time,), 0.0, (0.0,), 1.0
        )
        result = solve_ivp(
            problem,
            "LIQSS_BDF",
            options={
                "quantum": 1.0e-4,
                "rtol": 1.0e-4,
                "atol": 1.0e-7,
                "max_step": 0.05,
            },
        )
        self.assertEqual(normalise_solver_name("liqssbdf"), "liqss-bdf")
        self.assertAlmostEqual(result.final_state[0], 0.5, delta=2.0e-4)

    def test_partition_validation_is_strict(self) -> None:
        problem = InitialValueProblem(
            lambda _time, state: (-state[0], -state[1]),
            0.0,
            (1.0, 1.0),
            1.0,
            autonomous=True,
        )
        with self.assertRaises(ValueError):
            liqss_bdf(problem, 0.1, bdf_partition=())
        with self.assertRaises(ValueError):
            liqss_bdf(problem, 0.1, bdf_partition=(0, 0))
        with self.assertRaises(TypeError):
            liqss_bdf(problem, 0.1, bdf_partition=(True,))
        with self.assertRaises(ValueError):
            liqss_bdf(problem, 0.1, coupling_tolerance=0.0)

        non_autonomous = InitialValueProblem(
            lambda time, state: (time - state[0], -state[1]),
            0.0,
            (1.0, 1.0),
            1.0,
        )
        with self.assertRaisesRegex(ValueError, "requires problem.autonomous"):
            liqss_bdf(non_autonomous, 0.1, bdf_partition=(1,))


if __name__ == "__main__":
    unittest.main()

import itertools
import math
import unittest

from argesim_benchmarks.catalog import BENCHMARKS, BenchmarkStatus
from argesim_benchmarks.models.c17_sir_epidemic import (
    C17_INITIAL_STATE,
    C17HardMeasure,
    C17Intervention,
    C17Movement,
    C17Parameters,
    C17SoftParameter,
    c17_contact_rate,
    c17_lattice_size,
    c17_rhs,
    c17_task1_parameter_study,
    simulate_c17_ca,
    simulate_c17_ode_intervention,
    solve_c17,
)


class C17Tests(unittest.TestCase):
    def test_c17r_catalog_status(self) -> None:
        c17r = next(b for b in BENCHMARKS if b.identifier == "C17R")
        self.assertEqual(c17r.status, BenchmarkStatus.VALIDATED)

    def test_default_ode_against_independent_scalar_reference(self):
        # Eq. 3 gives S(R) = 9500 exp(-4 R / 10000). Only R is integrated
        # here, with classical RK4 and steps of at most 0.025 time units.
        def rate(r):
            return -math.log1p(-0.1) * (10000 - 9500 * math.exp(-0.0004 * r) - r)

        errors = []
        for method, quantum, limit in (
            ("rk45", None, 3e-5), ("qss2", 1.0, 1.0),
            ("qss2", 0.1, 0.1), ("qss2", 0.01, 0.01),
        ):
            with self.subTest(method=method, quantum=quantum):
                options = {} if quantum is None else {"quantum": (quantum,) * 3}
                result = solve_c17(method, t_bound=100.0, options=options)
                self.assertEqual((result.times[0], result.times[-1]), (0.0, 100.0))
                self.assertEqual(len(result.times), len(result.states))
                r = time = worst = 0.0
                for target, state in zip(result.times, result.states):
                    steps = max(1, math.ceil((target - time) / 0.025))
                    h = (target - time) / steps
                    for _ in range(steps):
                        a = rate(r)
                        b = rate(r + h * a / 2)
                        c = rate(r + h * b / 2)
                        d = rate(r + h * c)
                        r += h * (a + 2 * b + 2 * c + d) / 6
                    time = target
                    s = 9500 * math.exp(-0.0004 * r)
                    expected = (s, 10000 - s - r, r)
                    self.assertEqual(len(state), 3)
                    self.assertTrue(all(math.isfinite(v) for v in state))
                    worst = max(worst, *(abs(v - ref) for v, ref in zip(state, expected)))
                self.assertLess(worst, limit)
                if quantum is not None:
                    errors.append(worst)
        for coarse, fine in itertools.pairwise(errors):
            self.assertLess(fine, 0.15 * coarse)

    def test_c17_parameters_validation(self) -> None:
        with self.assertRaises(ValueError):
            C17Parameters(n=0.0)
        with self.assertRaises(ValueError):
            C17Parameters(c=-1.0)
        with self.assertRaises(ValueError):
            C17Parameters(alpha=1.0)
        with self.assertRaises(ValueError):
            C17Parameters(beta=2.0)

    def test_c17_rhs_conservation(self) -> None:
        # S' + I' + R' should always be exactly 0
        rhs = c17_rhs()
        state = (100.0, 50.0, 20.0)
        derivative = rhs(0.0, state)
        self.assertAlmostEqual(sum(derivative), 0.0)
        # S should be strictly decreasing
        self.assertLess(derivative[0], 0.0)
        # R should be strictly increasing
        self.assertGreater(derivative[2], 0.0)

    def test_solve_c17_long_term_equilibrium(self) -> None:
        # At very large t, I(t) should -> 0
        result = solve_c17("rk45", t_bound=300.0, options={"max_step": 1.0})
        self.assertEqual(result.final_time, 300.0)
        self.assertAlmostEqual(sum(result.final_state), sum(C17_INITIAL_STATE))

        S_final, I_final, R_final = result.final_state
        # Infections should have died out
        self.assertLess(I_final, 1.0)
        # R should make up the vast majority of the population
        self.assertGreater(R_final, 9000.0)
        # S should be the remainder
        self.assertAlmostEqual(S_final + I_final + R_final, sum(C17_INITIAL_STATE))

    def test_qss1_solve_c17(self) -> None:
        result = solve_c17("qss1", t_bound=1.0, options={"quantum": (1.0, 1.0, 1.0)})
        self.assertEqual(result.final_time, 1.0)

    def test_qss2_solve_c17(self) -> None:
        result = solve_c17("qss2", t_bound=1.0, options={"quantum": (1.0, 1.0, 1.0)})
        self.assertEqual(result.final_time, 1.0)

    def test_unsupported_solver(self) -> None:
        with self.assertRaises(ValueError):
            solve_c17("unsupported_solver")

    def test_revised_lattice_identification_rounds_up(self) -> None:
        self.assertEqual(c17_lattice_size(1000, 4.0), 15)

    def test_discrete_hard_measure_rounds_affected_population_down(self) -> None:
        intervention = C17Intervention(
            0.0,
            hard_measure=C17HardMeasure.VACCINATION,
            hard_fraction=0.0002,
        )
        result = simulate_c17_ca(
            steps=1,
            seed=4,
            intervention=intervention,
        )
        vaccination = next(
            event for event in result.interventions if event.kind == "vaccination"
        )
        self.assertEqual(vaccination.affected, 1)

    def test_fhp_ca_identification_and_population_conservation(self) -> None:
        size = c17_lattice_size(10000, 4.0)
        self.assertEqual(size, 46)
        self.assertAlmostEqual(c17_contact_rate(10000, size), 3.9381646317447814)
        for movement in C17Movement:
            result = simulate_c17_ca(steps=5, seed=3, movement=movement)
            self.assertTrue(
                all(
                    susceptible + infected + recovered == 10000
                    for susceptible, infected, recovered in zip(
                        result.susceptible, result.infected, result.recovered
                    )
                )
            )

    def test_threshold_intervention_is_recorded(self) -> None:
        intervention = C17Intervention(
            0.04,
            soft_factor=0.5,
            duration=3,
            hard_measure=C17HardMeasure.VACCINATION,
            hard_fraction=0.1,
        )
        result = simulate_c17_ca(steps=2, seed=4, intervention=intervention)
        self.assertEqual({event.kind for event in result.interventions}, {"soft", "vaccination"})

    def test_soft_parameter_is_separate_and_persists(self) -> None:
        intervention = C17Intervention(
            0.0,
            soft_factor=0.0,
            soft_parameter=C17SoftParameter.INFECTION,
            duration=0,
        )
        ca = simulate_c17_ca(steps=5, seed=4, intervention=intervention)
        self.assertEqual(ca.susceptible, (9500,) * 6)

        ode = simulate_c17_ode_intervention(
            intervention,
            t_bound=5.0,
            method="rk45",
        )
        self.assertEqual(len(ode.events), 1)
        self.assertAlmostEqual(ode.final_state[0], 9500.0, delta=1.0e-8)
        self.assertAlmostEqual(sum(ode.final_state), 10000.0, delta=1.0e-8)

    def test_ode_intervention_uses_shared_qss2_hybrid_runtime(self) -> None:
        result = simulate_c17_ode_intervention(
            C17Intervention(
                0.06,
                hard_measure=C17HardMeasure.QUARANTINE,
                hard_fraction=0.25,
            ),
            t_bound=5.0,
            method="qss2",
            options={"quantum": (1.0, 1.0, 1.0)},
        )
        self.assertTrue(result.method.startswith("qss2"))
        self.assertEqual(len(result.events), 1)
        self.assertEqual(result.events[0].name, "threshold-intervention")
        self.assertAlmostEqual(sum(result.final_state), 10000.0, delta=1.0e-8)

    def test_ode_recovery_ramp_has_analytic_reference_and_rejects_qss(self) -> None:
        settings = C17Intervention(
            0.01, soft_factor=0.0, soft_parameter=C17SoftParameter.RECOVERY, duration=10,
        )
        parameters = C17Parameters(alpha=0.0)
        # With no transfers into I, integrate log(0.9 + 0.01*t) on [0, 10].
        expected = 500 * math.exp(100 * (-0.1 - 0.9 * math.log(0.9)))
        result = simulate_c17_ode_intervention(
            settings, parameters=parameters, t_bound=20,
            options={"rtol": 1e-11, "atol": 1e-12, "max_step": 0.1},
        )
        self.assertAlmostEqual(result.final_state[1], expected, delta=1e-8)
        for method in ("qss1", "qss2", "qss3", "liqss2", "eliqss2"):
            with self.subTest(method=method), self.assertRaisesRegex(ValueError, "autonomous"):
                simulate_c17_ode_intervention(
                    settings, parameters=parameters, t_bound=20, method=method,
                )

    def test_constant_ode_intervention_still_supports_qss2(self) -> None:
        result = simulate_c17_ode_intervention(
            C17Intervention(0.01, soft_factor=0.0, duration=10, profile="constant"),
            method="qss2", t_bound=2,
        )
        self.assertEqual(result.final_time, 2.0)
        self.assertEqual(len(result.events), 1)
        self.assertAlmostEqual(result.final_state[0], 9500.0, delta=1e-8)

    def test_task1_parameter_study_accepts_initial_infection_sweeps(self) -> None:
        cases = c17_task1_parameter_study(
            cases=(("I0-test", C17Parameters(), (9900, 100, 0)),),
            steps=2,
            replications=2,
        )
        self.assertEqual(cases[0].initial_state, (9900, 100, 0))
        self.assertEqual(len(cases[0].comparison.ca_mean), 3)

    def test_task1_default_contact_sweep_fits_fhp_capacity(self) -> None:
        cases = c17_task1_parameter_study(steps=1, replications=1)
        high = next(case for case in cases if case.label == "alpha-C-high")
        self.assertEqual(high.parameters.c * high.parameters.alpha, 0.4)
        self.assertEqual(len(high.comparison.ca_mean), 2)


if __name__ == "__main__":
    unittest.main()

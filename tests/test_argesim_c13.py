"""Tests for the ARGESIM C13 benchmark implementation."""

import math
import unittest
from unittest.mock import patch

from argesim_benchmarks.catalog import BENCHMARKS, BenchmarkStatus
from argesim_benchmarks.models.c13_crane import (
    C13_INITIAL_STATE,
    C13Controller,
    C13Parameters,
    _c13_disturbance_force,
    c13_linear_rhs,
    c13_nonlinear_rhs,
    c13_task_a,
    c13_task_b_study,
    c13_task_c_study,
)


class C13Tests(unittest.TestCase):
    def test_2006_load_friction_reproduces_old_task_a_scale(self):
        """Independent RK4 stepping guards the identified revision difference."""
        def terminal_load_position(load_friction):
            parameters = C13Parameters(dl=load_friction)
            state = C13_INITIAL_STATE
            dt = 0.1
            for duration, disturbance, drive in (
                (4.0, 0.0, 160.0),
                (3.0, -750.0, 160.0),
                (8.0, 0.0, 160.0),
                (1985.0, 0.0, 0.0),
            ):
                rhs = c13_linear_rhs(parameters, fc_desired=drive,
                                     fd=disturbance)
                for _ in range(round(duration / dt)):
                    k1 = rhs(0.0, state)
                    k2 = rhs(0.0, tuple(x + dt * y / 2 for x, y in zip(state, k1)))
                    k3 = rhs(0.0, tuple(x + dt * y / 2 for x, y in zip(state, k2)))
                    k4 = rhs(0.0, tuple(x + dt * y for x, y in zip(state, k3)))
                    state = tuple(
                        x + dt * (a + 2 * b + 2 * c + d) / 6
                        for x, a, b, c, d in zip(state, k1, k2, k3, k4)
                    )
            return state[0] + parameters.r * state[2]

        old = terminal_load_position(0.01)
        revised = terminal_load_position(0.001)
        self.assertAlmostEqual(old, 294.084453, delta=0.15)
        self.assertAlmostEqual(revised, 299.361523, delta=0.15)
        self.assertGreater(revised - old, 5.0)

    def test_c13_catalog_status(self):
        c13 = next(b for b in BENCHMARKS if b.identifier == "C13")
        self.assertEqual(c13.status, BenchmarkStatus.VALIDATED)

    def test_task_a_returns_all_results(self):
        result = c13_task_a()
        self.assertIn(-750.0, result)
        self.assertIn(-800.0, result)
        self.assertIn(-850.0, result)

        self.assertTrue(math.isfinite(result[-750.0]["linear"]))
        self.assertTrue(math.isfinite(result[-750.0]["nonlinear"]))

        # Independent Cartesian cart/load matrix exponential at 2000 s.
        # scripts/benchmark_spec_probe.py regenerates these three endpoints.
        for force, position in (
            (-750.0, 299.3615227886293),
            (-800.0, -0.005706868827346057),
            (-850.0, -299.37293652627955),
        ):
            with self.subTest(force=force):
                self.assertAlmostEqual(result[force]["linear"], position, delta=1e-5)

        # The revised definition asks for the position after about 2000 s.
        # The 2006 solution used d_l=0.01 and reports ~294 m; the 2007
        # definition uses d_l=0.001 and gives ~299 m (see the C13 audit).
        # Net impulse ±150 Ns implies a rough ±300 m scale at d_c=0.5.
        # Check that both models preserve that symmetry and cancel at -800 N.
        for model in ("linear", "nonlinear"):
            self.assertAlmostEqual(result[-750.0][model], 300.0, delta=1.0)
            self.assertAlmostEqual(result[-800.0][model], 0.0, delta=0.02)
            self.assertAlmostEqual(result[-850.0][model], -300.0, delta=1.0)
            self.assertAlmostEqual(
                result[-750.0][model] + result[-850.0][model],
                2 * result[-800.0][model], delta=0.02,
            )

    def test_revised_parameters_and_controller_sampling(self) -> None:
        self.assertEqual(C13Parameters().dl, 0.001)
        self.assertEqual(C13Controller().dt, 0.1)

    def test_holding_brake_requires_more_than_three_seconds_and_releases(self):
        for diagnosis in (False, True):
            with self.subTest(diagnosis=diagnosis):
                controller = C13Controller(with_diagnosis=diagnosis)
                for _ in range(30):
                    controller.step(0.0, 0.0)
                    self.assertFalse(controller.brake_active)
                self.assertEqual(controller.time_fc_small, 3.0)
                controller.step(0.0, 0.0)
                self.assertTrue(controller.brake_active)
                self.assertEqual(controller.fc_desired, 0.0)
                controller.step(0.0, 3.0)
                self.assertFalse(controller.brake_active)
                self.assertEqual(controller.fc_desired, controller.ForceMax)

    def test_threshold_equality_interrupts_dwell_in_both_directions(self):
        for sign in (-1, 1):
            with self.subTest(sign=sign):
                controller = C13Controller()
                for _ in range(29):
                    controller.step(0.0, 0.0)
                controller.step(0.0, sign * controller.BrakeCondition / controller.V)
                self.assertEqual(abs(controller.fc_desired), controller.BrakeCondition)
                self.assertEqual(controller.time_fc_small, 0.0)
                controller.step(0.0, 0.0)
                self.assertFalse(controller.brake_active)

    def test_only_diagnosis_latches_the_emergency_brake(self):
        for limit in (-5.0, 5.0):
            for diagnosis in (False, True):
                with self.subTest(limit=limit, diagnosis=diagnosis):
                    controller = C13Controller(with_diagnosis=diagnosis)
                    controller.step(limit, 1.0)
                    self.assertFalse(controller.emergency_mode)
                    controller.step(limit * 1.01, 1.0)
                    controller.step(0.0, 3.0)
                    self.assertEqual(controller.emergency_mode, diagnosis)
                    self.assertEqual(controller.brake_active, diagnosis)
                    if diagnosis:
                        self.assertEqual(controller.fc_desired, 0.0)

    def test_revised_task_b_c_disturbance_scenarios(self) -> None:
        self.assertEqual(
            _c13_disturbance_force(42.5, with_diagnosis=False),
            -200.0,
        )
        self.assertEqual(
            _c13_disturbance_force(46.5, with_diagnosis=False),
            0.0,
        )
        self.assertEqual(
            _c13_disturbance_force(42.5, with_diagnosis=True),
            -200.0,
        )
        self.assertEqual(
            _c13_disturbance_force(46.5, with_diagnosis=True),
            200.0,
        )

    def test_task_b_applies_and_records_holding_friction_at_the_sample_time(self):
        # Start the normal plant at rest for four seconds, then issue its
        # scheduled demand. Retain the real observer, controller and integrator.
        step = C13Controller.step
        ticks = 0
        def stationary_start(controller, position, target, *, initial_sample=False):
            nonlocal ticks
            step(controller, position, 0.0 if ticks < 40 else target,
                 initial_sample=initial_sample)
            ticks += 1
        with (
            patch.object(C13Controller, "step", stationary_start),
            patch("argesim_benchmarks.models.c13_crane.c13_nonlinear_rhs",
                  wraps=c13_nonlinear_rhs) as plant,
        ):
            study = c13_task_b_study()
        for sample, braking in ((30, False), (31, True), (39, True), (40, False)):
            with self.subTest(time=study.result.times[sample]):
                self.assertEqual(study.brake_active[sample], braking)
                damping = plant.call_args_list[sample].kwargs["dc_current"]
                self.assertEqual(damping, 100000.0 if braking else 0.5)

    def test_task_b_runs_and_returns_complete_trajectory(self):
        study = c13_task_b_study()
        res = study.result
        self.assertEqual(res.method, "rk45-dormand-prince-5(4)")
        self.assertGreater(len(res.times), 10)
        self.assertAlmostEqual(res.times[-1], 60.0, places=5)
        self.assertEqual(len(res.states[0]), 5)
        self.assertEqual(len(study.load_position), len(res.times))
        self.assertEqual(len(study.brake_active), len(res.times))
        self.assertEqual(len(study.emergency_stop), len(res.times))
        self.assertFalse(any(study.emergency_stop))

    def test_task_c_runs_and_returns_diagnosis_trajectory(self):
        study = c13_task_c_study()
        res = study.result
        self.assertEqual(res.method, "rk45-dormand-prince-5(4)")
        self.assertGreater(len(res.times), 10)
        self.assertAlmostEqual(res.times[-1], 60.0, places=5)
        self.assertEqual(len(res.states[0]), 5)
        self.assertEqual(len(study.load_position), len(res.times))
        self.assertEqual(len(study.brake_active), len(res.times))
        self.assertEqual(len(study.emergency_stop), len(res.times))


if __name__ == "__main__":
    unittest.main()

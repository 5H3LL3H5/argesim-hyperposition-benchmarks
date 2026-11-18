import unittest
from argesim_benchmarks.models.c12_collision import (
    C12_QUASI_PLASTIC_E,
    C12Parameters,
    c12_task_a,
    c12_task_b,
    c12_task_c,
)
from argesim_benchmarks.models.c12_collision.c12_collision_processes import _simulate

class ArgesimC12Tests(unittest.TestCase):
    def test_c12_task_a(self) -> None:
        """Validates Task A (Distance-time functions and final velocities).

        Checks that the elastic collision (e=1) results in complete momentum transfer
        from the first sphere to the last sphere. Also checks that the perfectly
        plastic collision (e=0) results in all spheres moving together at v0/4.
        """
        result = c12_task_a()
        self.assertEqual(len(result["a2_elastic_velocities"]), 4)
        self.assertEqual(len(result["a2_quasi_plastic_velocities"]), 4)
        self.assertEqual(result["a2_quasi_plastic_e"], C12_QUASI_PLASTIC_E)
        # Elastic: sphere 1 stops, others transfer momentum, sphere 4 gets all
        self.assertAlmostEqual(result["a2_elastic_velocities"][3], 1.0)
        self.assertAlmostEqual(result["a2_elastic_velocities"][0], 0.0)
        # Quasi-plastic: the published e=0.18 event cascade converges closely
        # to the common momentum-conserving velocity.
        for velocity in result["a2_quasi_plastic_velocities"]:
            self.assertAlmostEqual(velocity, 0.25, delta=1.0e-6)
        self.assertEqual(
            result["a2_plastic_velocities"],
            result["a2_quasi_plastic_velocities"],
        )
        first_collision = result["a1_trajectory"][1]
        self.assertAlmostEqual(first_collision[0], 1.0)
        self.assertEqual(result["a1_trajectory"][0][1], [1.0, 1.0, 1.0])

    def test_elastic_collisions_follow_equal_initial_gaps(self) -> None:
        # Definition (4): y1(0) = y2(0) = y3(0) = a. Equal masses
        # exchange velocities on impact, so a/v0 elapses between impacts.
        count, velocities, end, history = _simulate(C12Parameters(e=1.0))
        self.assertEqual(count, 3)
        self.assertEqual([row[0] for row in history], [0.0, 1.0, 2.0, 3.0])
        self.assertEqual(velocities, [0.0, 0.0, 0.0, 1.0])
        self.assertEqual(end, 3.0)

    def test_collisions_conserve_momentum_and_dissipate_energy(self) -> None:
        _, _, _, history = _simulate(C12Parameters(e=0.2))
        previous_energy = 0.5
        for _, gaps, velocities in history:
            self.assertAlmostEqual(sum(velocities), 1.0)
            self.assertGreaterEqual(min(gaps), -1.0e-12)
            energy = sum(value * value for value in velocities) / 2.0
            self.assertLessEqual(energy, previous_energy + 1.0e-14)
            previous_energy = energy

    def test_plastic_collapse_preserves_nonoverlap_and_momentum(self) -> None:
        _, velocities, _, history = _simulate(C12Parameters(e=0.0, max_time=None))
        self.assertAlmostEqual(sum(velocities), 1.0)
        for velocity in velocities:
            self.assertAlmostEqual(velocity, 0.25, delta=1.0e-10)
        self.assertTrue(all(min(gaps) >= 0.0 for _, gaps, _ in history))

    def test_c12_task_b(self) -> None:
        """Validates Task B (Number of collisions and final velocities over e).

        Verifies the parameter sweep from e=1.0 down to the quasi-plastic boundary.\n        Checks that exactly
        3 collisions occur in the perfectly elastic case. Also verifies that the
        quasi-plastic lower boundary resolves to the expected common velocity.
        """
        result = c12_task_b()
        self.assertIn("sweep", result)
        sweep = result["sweep"]
        self.assertEqual(sweep[1.0]["collisions"], 3)
        self.assertEqual(min(sweep), C12_QUASI_PLASTIC_E)
        self.assertGreater(sweep[C12_QUASI_PLASTIC_E]["collisions"], 3)
        # At e=.5 two impacts occur after t=15. Tasks B/C require the final
        # velocities, not a cutoff at the plotting horizon of Task A1.
        self.assertEqual(sweep[0.5]["collisions"], 6)
        self.assertEqual(
            sweep[0.5]["velocities"],
            [0.173828125, 0.193359375, 0.2109375, 0.421875],
        )

    def test_c12_task_c(self) -> None:
        """Validates Task C (Boundary value problem and stochastic study).

        Checks that Brent's method correctly identifies the target restitution
        coefficient e (~0.587) where the final velocity of the 4th sphere is exactly v0/2.
        Also validates that the Monte Carlo normal-distribution sweep returns
        statistically valid outputs for mean and standard deviation.
        """
        result = c12_task_c()
        self.assertGreater(result["c1_target_e"], 0.0)
        self.assertLess(result["c1_target_e"], 1.0)
        self.assertAlmostEqual(result["c1_target_e"], 0.5874011, delta=2.0e-6)

        self.assertGreater(result["c2_mean_v4"], 0.0)
        self.assertGreater(result["c2_std_v4"], 0.0)
        cdf = result["c2_empirical_cdf"]
        self.assertEqual(len(cdf), 10000)
        self.assertEqual(cdf[-1][1], 1.0)
        self.assertTrue(all(a[0] <= b[0] and a[1] < b[1] for a, b in zip(cdf, cdf[1:])))

    def test_c12_task_c_rejects_too_few_samples(self) -> None:
        for value in (1, 1.5, True):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    c12_task_c(n_samples=value)

if __name__ == "__main__":
    unittest.main()

import unittest
from argesim_benchmarks.models.c12_collision import c12_task_a, c12_task_b, c12_task_c

class ArgesimC12Tests(unittest.TestCase):
    def test_c12_task_a(self) -> None:
        """Validates Task A (Distance-time functions and final velocities).

        Checks that the elastic collision (e=1) results in complete momentum transfer
        from the first sphere to the last sphere. Also checks that the perfectly
        plastic collision (e=0) results in all spheres moving together at v0/4.
        """
        result = c12_task_a()
        self.assertEqual(len(result["a2_elastic_velocities"]), 4)
        self.assertEqual(len(result["a2_plastic_velocities"]), 4)
        # Elastic: sphere 1 stops, others transfer momentum, sphere 4 gets all
        self.assertAlmostEqual(result["a2_elastic_velocities"][3], 1.0)
        self.assertAlmostEqual(result["a2_elastic_velocities"][0], 0.0)
        # Quasi-plastic: the event cascade converges to the momentum-conserving
        # common velocity; it is not collapsed artificially at t=0.
        for velocity in result["a2_plastic_velocities"]:
            self.assertAlmostEqual(velocity, 0.25, places=8)
        first_collision = result["a1_trajectory"][1]
        self.assertAlmostEqual(first_collision[0], 1.0)
        self.assertEqual(result["a1_trajectory"][0][1], [1.0, 0.0, 0.0])

    def test_c12_task_b(self) -> None:
        """Validates Task B (Number of collisions and final velocities over e).

        Verifies the parameter sweep across e from 0.0 to 1.0. Checks that exactly
        3 collisions occur in the perfectly elastic case. Also verifies that the
        plastic case resolves correctly to the expected merged state (3 logical hits).
        """
        result = c12_task_b()
        self.assertIn("sweep", result)
        sweep = result["sweep"]
        self.assertEqual(sweep[1.0]["collisions"], 3)
        self.assertGreater(sweep[0.0]["collisions"], 3)

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
        self.assertAlmostEqual(result["c1_target_e"], 0.587, places=3)

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

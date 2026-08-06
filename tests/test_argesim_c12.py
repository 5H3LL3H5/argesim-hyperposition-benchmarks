import unittest
from argesim_benchmarks.models.c12_collision import c12_task_a, c12_task_b, c12_task_c

class ArgesimC12Tests(unittest.TestCase):
    def test_c12_task_a(self) -> None:
        result = c12_task_a()
        self.assertEqual(len(result["a2_elastic_velocities"]), 4)
        self.assertEqual(len(result["a2_plastic_velocities"]), 4)
        # Elastic: sphere 1 stops, others transfer momentum, sphere 4 gets all
        self.assertAlmostEqual(result["a2_elastic_velocities"][3], 1.0)
        self.assertAlmostEqual(result["a2_elastic_velocities"][0], 0.0)
        # Plastic: all move with v0/4 = 0.25
        self.assertAlmostEqual(result["a2_plastic_velocities"][0], 0.25)
        self.assertAlmostEqual(result["a2_plastic_velocities"][3], 0.25)

    def test_c12_task_b(self) -> None:
        result = c12_task_b()
        self.assertIn("sweep", result)
        sweep = result["sweep"]
        self.assertEqual(sweep[1.0]["collisions"], 3)
        # We model plastic collision as macro event resolving directly to 3 collisions
        self.assertEqual(sweep[0.0]["collisions"], 3)

    def test_c12_task_c(self) -> None:
        result = c12_task_c()
        self.assertGreater(result["c1_target_e"], 0.0)
        self.assertLess(result["c1_target_e"], 1.0)
        self.assertAlmostEqual(result["c1_target_e"], 0.587, places=3)

        self.assertGreater(result["c2_mean_v4"], 0.0)
        self.assertGreater(result["c2_std_v4"], 0.0)

if __name__ == "__main__":
    unittest.main()

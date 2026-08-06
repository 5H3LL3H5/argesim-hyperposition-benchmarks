import unittest
from argesim_benchmarks.models import solve_c02

class C02Tests(unittest.TestCase):
    def test_solve_c02_20_pallets(self):
        result = solve_c02(20)
        self.assertIn("throughput", result)
        self.assertIn("average_throughput_time", result)
        self.assertGreater(result["throughput"], 0)
        self.assertGreater(result["average_throughput_time"], 0)

    def test_solve_c02_40_pallets(self):
        result = solve_c02(40)
        self.assertGreater(result["throughput"], 0)

    def test_solve_c02_60_pallets(self):
        result = solve_c02(60)
        self.assertGreater(result["throughput"], 0)

if __name__ == "__main__":
    unittest.main()

import unittest

from argesim_benchmarks.parallel import OrderedExecutor, benchmark_ordered_map


def square(value: int) -> int:
    return value * value


class ParallelRuntimeTests(unittest.TestCase):
    def test_reusable_ordered_executor(self) -> None:
        with OrderedExecutor(2) as executor:
            self.assertEqual(executor.map(square, range(5)), (0, 1, 4, 9, 16))
            self.assertEqual(executor.map(square, (5, 6)), (25, 36))

    def test_benchmark_validates_same_workload(self) -> None:
        result = benchmark_ordered_map(
            square,
            range(10),
            workers=2,
            warmups=0,
            repeats=2,
        )
        self.assertEqual(result.serial_values, result.parallel_values)
        self.assertEqual(result.maximum_error, 0.0)
        self.assertGreaterEqual(result.serial_timing.median, 0.0)

    def test_invalid_timing_and_error_metrics_are_rejected(self) -> None:
        with self.assertRaises(TypeError):
            benchmark_ordered_map(square, (1,), warmups=True)
        with self.assertRaises(ValueError):
            benchmark_ordered_map(
                square,
                (1,),
                warmups=0,
                repeats=1,
                error=lambda _left, _right: float("nan"),
            )


if __name__ == "__main__":
    unittest.main()

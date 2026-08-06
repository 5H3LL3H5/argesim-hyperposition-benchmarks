import argparse
import time
from argesim_benchmarks.models.c13_crane import c13_task_a, c13_task_b, c13_task_c


def main():
    parser = argparse.ArgumentParser(description="Benchmark ARGESIM C13.")
    parser.add_argument("--repeat", type=int, default=1, help="Number of repetitions.")
    parser.add_argument("--warmup", type=int, default=0, help="Number of warmup runs.")
    args = parser.parse_args()

    for _ in range(args.warmup):
        c13_task_a()
        c13_task_b()
        c13_task_c()

    start = time.perf_counter()
    for _ in range(args.repeat):
        c13_task_a()
        c13_task_b()
        c13_task_c()
    duration = time.perf_counter() - start
    print(f"Total time for {args.repeat} repetition(s): {duration:.3f} seconds")


if __name__ == "__main__":
    main()

"""CP2 trajectory audit: fixed output grid, declared before scoring the target."""

N = 257
END = 350_000
RE = 1000
LID = 0.1
ORIGINAL = (256, 4096, 16384, 65536, 131072, 262144, END)


def ticks(archive_times):
    """Positive common ticks of both grids, with the original 37 kept intact."""
    values = set(range(4, 257, 4))
    values.update(range(288, 4_097, 32))
    values.update(range(4_352, 16_385, 256))
    values.update(range(20_480, END, 4_096))
    values.update(archive_times)
    values.add(END)
    return sorted(values)

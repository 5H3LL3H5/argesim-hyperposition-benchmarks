"""Optional external solver-oracle boundaries.

External engines are observations used for cross-checking.  Their successful
execution does not promote an ARGESIM evidence gate.
"""

from .base import OracleCapabilities, OracleResult, OracleStatus, SolverOracle
from .cifasis import CIFASIS_PINNED_COMMIT, CifasisOracle

__all__ = [
    "CIFASIS_PINNED_COMMIT",
    "CifasisOracle",
    "OracleCapabilities",
    "OracleResult",
    "OracleStatus",
    "SolverOracle",
]

"""Contracts shared by optional external solver oracles."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Mapping


class OracleStatus(str, Enum):
    """Machine-readable outcome of an external-oracle operation."""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    UNSUPPORTED_METHOD = "unsupported-method"
    BUILD_REQUIRED = "build-required"
    EXECUTION_FAILED = "execution-failed"
    SUCCEEDED = "succeeded"


@dataclass(frozen=True)
class OracleCapabilities:
    """Versioned, declared capabilities returned by an oracle driver."""

    oracle: str
    status: OracleStatus
    executable: tuple[str, ...] = ()
    protocol_version: int | None = None
    engine: str | None = None
    engine_commit: str | None = None
    methods: tuple[str, ...] = ()
    model_formats: tuple[str, ...] = ()
    reason: str | None = None
    schema_version: int = 1

    @property
    def available(self) -> bool:
        return self.status is OracleStatus.AVAILABLE

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        payload["available"] = self.available
        return payload


@dataclass(frozen=True)
class OracleResult:
    """A solver-oracle observation and its reproducibility metadata."""

    oracle: str
    status: OracleStatus
    request_hash: str
    model_hash: str
    method: str | None
    capabilities: OracleCapabilities
    output_directory: str | None = None
    duration_seconds: float | None = None
    exit_code: int | None = None
    timed_out: bool = False
    result: Mapping[str, Any] | None = None
    error: str | None = None
    provenance: Mapping[str, Any] = field(default_factory=dict)
    schema_version: int = 1
    scope: str = "external execution observation only"

    @property
    def succeeded(self) -> bool:
        return self.status is OracleStatus.SUCCEEDED

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        payload["capabilities"] = self.capabilities.to_dict()
        payload["succeeded"] = self.succeeded
        return payload


class SolverOracle(ABC):
    """Abstract boundary for a separately executed solver engine."""

    @abstractmethod
    def capabilities(self) -> OracleCapabilities:
        """Probe availability, version and declared methods."""

    @abstractmethod
    def run(
        self,
        request: Mapping[str, Any],
        output_directory: Path,
        *,
        timeout_seconds: float = 300.0,
    ) -> OracleResult:
        """Execute one request and publish an immutable artifact bundle."""

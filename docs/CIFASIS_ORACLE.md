# Optional CIFASIS/qss-solver oracle boundary

The CIFASIS integration is an optional, process-isolated cross-check.  It does
not import, copy or link CIFASIS source code.  A successful run is an external
execution observation; it is neither an independent validation by itself nor
a reason to promote an ARGESIM evidence gate.

The initially qualified engine revision is the `qss-solver-dev` commit
`4d53893958048273cb2dfd6fbd6e736f9dd0bbca`.  A different revision produces
the structured status `build-required` unless the caller deliberately selects
a different expected commit.  The selected and observed commits are always
recorded.

## Adapter protocol version 1

`qss-solver` does not expose one stable generic command for arbitrary ARGESIM
models.  Therefore the suite calls a separately supplied adapter executable.
That adapter owns model translation and the native CIFASIS build/run details.
It must not be silently replaced with an internal Python solver.
This repository defines the boundary but does not ship a native adapter or a
translated benchmark model in this initial delta.

Capability probe:

```text
ADAPTER --argesim-oracle-probe --format json
```

Standard output must contain only one JSON object:

```json
{
  "protocol_version": 1,
  "engine": "CIFASIS/qss-solver",
  "engine_commit": "4d53893958048273cb2dfd6fbd6e736f9dd0bbca",
  "methods": ["QSS1", "QSS2", "LIQSS2"],
  "model_formats": ["mu-modelica"]
}
```

The advertised method list is descriptive capability data from the adapter,
not a claim of numerical correctness or equivalence.  Duplicate, malformed or
empty lists and malformed commit identifiers are rejected. Method identifiers
are case-sensitive; the request must use the exact spelling advertised by the
adapter.

Execution:

```text
ADAPTER --argesim-oracle-run REQUEST.json --output DRIVER-RESULT.json
```

`REQUEST.json` must be a finite canonicalizable JSON object containing at
least `model` and `method`.  The adapter must create a JSON object at the exact
output path and return zero.  The initial boundary deliberately leaves the
model payload extensible; model-specific schemas and numerical comparison
tolerances belong to later, separately reviewed qualification PRs.

The runner executes an argument vector with `shell=False`, closes standard
input, captures bounded standard output and error, applies a timeout, and
terminates the process group on timeout. Requests and result objects are each
limited to 16 MiB. Non-finite JSON values are rejected.

## CLI

Configure an adapter using `--executable`, or set
`ARGESIM_CIFASIS_ORACLE` to an argv string.  If neither is configured, the
suite looks for `argesim-cifasis-oracle` on `PATH`.

```bash
argesim oracle probe cifasis
argesim oracle capabilities cifasis
argesim oracle run cifasis \
  --request examples/linear-decay-qss2.json \
  --output-dir benchmark-results/cifasis-linear-decay-qss2
```

Fixed adapter arguments can be supplied with repeatable `--adapter-arg`
options.  They are passed as separate argv entries and are never interpreted
by a shell.

Expected absence is represented as `unavailable`; a non-matching pinned build
is `build-required`; an undeclared method is `unsupported-method`; process,
timeout and result-contract failures are `execution-failed`.  Probe commands
print these statuses as machine-readable JSON.  `oracle run` returns exit code
2 for unavailable/build-required/unsupported, 1 for execution failure and 0
only for a completed adapter result.

## Artifacts and provenance

A run is assembled in a private sibling directory and atomically renamed to a
new output directory.  Existing output is never overwritten.  The bundle
contains:

- `request.json`: canonical input;
- `driver-result.json`: the adapter's unmodified JSON result;
- `stdout.txt` and `stderr.txt`: bounded diagnostic streams;
- `oracle-result.json`: normalized status, process evidence and provenance;
- `manifest.json`: SHA-256 digest of every other artifact.

Provenance includes the request and model hashes, the observed and expected
CIFASIS commits, the ARGESIM commit when the tree is clean or explicitly
verified through `ARGESIM_GIT_SHA`, and a secret-free Python/platform summary.
No environment-variable dump is recorded.

The configured adapter is executable code running with the current user's
permissions. Process isolation is an integration and licensing boundary, not
a security sandbox; only a trusted, locally reviewed adapter should be used.

## Reuse boundary

`argesim_benchmarks.external` contains only semantic-neutral primitives:
`ExternalBackendProcess`, `ExecutionEvidence`, `AtomicArtifactDirectory`,
canonical JSON, hashes and environment provenance.  Learned neural/FNO
backends may reuse that layer, but must define their own candidate/result
contracts.  They must not be represented as `SolverOracle` or `OracleResult`.

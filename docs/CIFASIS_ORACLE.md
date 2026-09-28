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
models.  Therefore the suite calls a separate adapter executable.  The
repository now ships `argesim-cifasis-oracle`, a deliberately narrow native
adapter for the analytic scalar linear-decay pilot.  It owns deterministic
micro-Modelica generation and the native CIFASIS build/run details without
copying, importing or linking CIFASIS code.  It must not be silently replaced
with an internal Python solver.

The pilot advertises only `QSS1` and `QSS2`, mapped to CIFASIS `QSS` and
`QSS2`.  That list is an integration capability, not a numerical-validation
claim.  Additional models and methods require separately reviewed
qualification deltas.

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
  "methods": ["QSS1", "QSS2"],
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
output path and return zero.  The native pilot rejects unknown fields and raw
model source.  Its accepted request is exemplified by
`examples/cifasis-linear-decay-qss2.json`; model-specific schemas and
numerical comparison tolerances for ARGESIM benchmarks belong to later,
separately reviewed qualification PRs.

The runner executes an argument vector with `shell=False`, closes standard
input, captures bounded standard output and error, applies a timeout, and
terminates the process group on timeout. Requests and result objects are each
limited to 16 MiB. Non-finite JSON values are rejected.

## CLI

Configure an adapter using `--executable`, or set
`ARGESIM_CIFASIS_ORACLE` to an argv string.  If neither is configured, the
suite looks for `argesim-cifasis-oracle` on `PATH`.

The native adapter requires two separate locations:

- `ARGESIM_CIFASIS_SOURCE`: a clean Git checkout used to establish the exact
  engine commit;
- `ARGESIM_CIFASIS_ROOT`: an installation containing executable
  `bin/mmoc`, `bin/compile.sh`, `bin/simulate.sh` and `bin/khmetis`.

For the qualified baseline, check out the source commit exactly and build it
with the upstream Ubuntu 24.04 dependencies:

```bash
git clone https://github.com/CIFASIS/qss-solver.git cifasis-qss-solver
git -C cifasis-qss-solver checkout \
  4d53893958048273cb2dfd6fbd6e736f9dd0bbca
cmake -S cifasis-qss-solver/src -B cifasis-qss-solver/src/build \
  -DCMAKE_BUILD_TYPE=Release
cmake --build cifasis-qss-solver/src/build --parallel
cmake --install cifasis-qss-solver/src/build

export ARGESIM_CIFASIS_SOURCE="$PWD/cifasis-qss-solver"
export ARGESIM_CIFASIS_ROOT="$PWD/cifasis-qss-solver"
```

The upstream top-level CMake project sets its own install location and copies
the installed tools into the checkout's `bin/` and `lib/` directories; it does
not honor a caller-selected `CMAKE_INSTALL_PREFIX` at that level.  Those build
outputs are ignored by the upstream repository.  A downstream packaged build
may set `ARGESIM_CIFASIS_ROOT` to a separate installation while retaining the
clean source checkout solely for commit provenance.

The adapter refuses dirty source trees.  A different clean commit is reported
by the probe and the outer oracle classifies it as `build-required` against the
pinned baseline.

```bash
argesim oracle probe cifasis
argesim oracle capabilities cifasis
argesim oracle run cifasis \
  --request examples/cifasis-linear-decay-qss2.json \
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

The adapter invokes upstream `compile.sh` and `simulate.sh` with fixed argv
entries and controlled run-local `MMOC_*` paths.  It does not accept arbitrary
compiler flags or caller-supplied micro-Modelica.  Compiler and solver child
processes receive only a small allowlist of ordinary process-location
variables plus the controlled paths and locale; the caller's complete
environment is not forwarded.  The generated model source,
its SHA-256 digest, normalized trajectory, bounded stage diagnostics and
measured compile/simulation wall times are returned in `driver-result.json`.
No QSS event-count or peak-memory value is emitted until a native source for
those measurements is qualified.

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

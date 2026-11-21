# Optional CIFASIS/qss-solver oracle boundary

The optional CIFASIS integration runs the external engine in a separate process. Its scalar-decay pilot compares emitted samples with the analytic solution. ARGESIM family validation uses the case-specific references in the [comparison report](PUBLISHED_REFERENCE_CHECKS.md).

The initially qualified engine revision is the `qss-solver-dev` commit
`4d53893958048273cb2dfd6fbd6e736f9dd0bbca`.  A different revision produces
the structured status `build-required` unless the caller deliberately selects
a different expected commit.  The selected and observed commits are always
recorded.

## Adapter protocol version 1

`qss-solver` does not expose one stable generic command for arbitrary ARGESIM
models.  Therefore the suite calls a separate adapter executable.  The
repository ships `argesim-cifasis-oracle`, a deliberately narrow native
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
output path and return zero for a successful execution.  The native pilot rejects unknown fields and raw
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

Install the suite with `python -m pip install -e .` from the repository root to place both console commands on the active environment’s PATH. The native adapter needs two locations.

- `ARGESIM_CIFASIS_SOURCE`: a clean Git checkout used to establish the exact
  engine commit;
- `ARGESIM_CIFASIS_ROOT`: an installation containing executable
  `bin/mmoc`, `bin/compile.sh` and `bin/simulate.sh`. The adapter first looks
  for `bin/khmetis` and otherwise uses the executable at the upstream source
  location `src/engine/3rd-party/partitioners/hmetis/khmetis`.

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

The exact pinned revision was configured, built and installed successfully in
an Ubuntu 24.04-compatible x86_64 environment on 2026-09-28. Both pilot methods
then completed through the public oracle boundary. QSS1 emitted 10,001 samples
and had a maximum scaled analytic error of 0.499; QSS2 emitted 72 samples and
had a maximum scaled error of 0.333. Both stayed within the requested tolerance
at every emitted sample. QSS1's last sample was within the terminal-time tolerance. QSS2's last emitted
point was `0.9970234151851755`, leaving a terminal gap of about `0.00298`.
These are integration and analytic pilot results, not ARGESIM benchmark
qualification or performance claims. The concise machine-readable record is
[`docs/evidence/cifasis-linear-decay-20260928.json`](evidence/cifasis-linear-decay-20260928.json).

The upstream top-level CMake project sets its own install location and copies
the installed tools into the checkout's `bin/` and `lib/` directories; it does
not honor a caller-selected `CMAKE_INSTALL_PREFIX` at that level.  Those build
outputs are ignored by the upstream repository.  A downstream packaged build
may set `ARGESIM_CIFASIS_ROOT` to a separate installation while retaining the
clean source checkout solely for commit provenance.

At the pinned revision, the top-level install does not copy `khmetis` into
`bin/`, although `simulate.sh` requires it there. The adapter stages a private
run-local `MMOC_BIN` containing links to the installed `mmoc` and the verified
`khmetis` executable; it does not mutate the CIFASIS checkout or installation.
It also supplies the complete path-only `MMOC_*` environment required by the
generated native makefile while continuing to exclude unrelated caller
variables.

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
For this analytic pilot, the result also compares every emitted sample against
`x(t)=initial_value*exp(-rate*(t-start_time))`. It reports absolute, relative,
RMSE and tolerance-scaled errors, where the per-sample budget is
`absolute_tolerance + relative_tolerance * abs(reference)`. Endpoint coverage
is reported separately because event-based QSS output need not emit a sample
at the requested stop time. Passing emitted samples therefore does not imply
that a terminal sample exists and does not promote ARGESIM evidence by itself.
The time-boundary tolerance is `1e-12 * (stop_time - start_time)`, so a short
interval or a large time origin cannot make its initial point count as its
terminal point. Samples outside that interval (beyond the boundary tolerance)
are rejected. RMSE is evaluated with scaled squares to avoid unnecessary
overflow and underflow; unrepresentable error metrics or tolerance budgets
produce a controlled adapter error instead of a non-finite JSON result.
No QSS event-count or peak-memory value is emitted until a native source for
those measurements is qualified.

## Artifacts and provenance

An unavailable engine, wrong revision or unsupported method returns a status
before creating an output directory. Once adapter execution begins, the runner
assembles the bundle in a private sibling directory and publishes it to the
requested new path. Each published bundle contains the canonical
`request.json`, bounded `stdout.txt` and `stderr.txt`, normalized
`oracle-result.json` and a `manifest.json` with SHA-256 digests of the other
files. A successful driver supplies `driver-result.json`. A driver that
exits early may leave diagnostics without that file. [Oracle runner](../argesim_benchmarks/oracles/cifasis.py)

The provenance records the request and model hashes, the expected and observed
engine commits when available, and a Python/platform summary. For the suite
commit, this adapter accepts a caller-supplied 40-character lowercase hex
`ARGESIM_GIT_SHA`, or tries Git from the package location. For installed
copies, use the verified source commit when relying on this field.

The configured adapter is executable code running with the current user's
permissions. Process isolation is an integration and licensing boundary, not
a security sandbox; only a trusted, locally reviewed adapter should be used.

## Reuse boundary

`argesim_benchmarks.external` contains only semantic-neutral primitives:
`ExternalBackendProcess`, `ExecutionEvidence`, `AtomicArtifactDirectory`,
canonical JSON, hashes and environment provenance.  Learned neural/FNO
backends may reuse that layer, but must define their own candidate/result
contracts.  They must not be represented as `SolverOracle` or `OracleResult`.

"""ARGESIM C18: nonlinear dynamic identification benchmark.

The original measurement files are unavailable. The explicit figure demo
reconstructs the four PDF curves on their published 100 Hz time grid.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import random
from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files
from pathlib import Path

from ._c18_recurrent import fit_sequence

C18_PUBLISHED_TRANSFER = (1.586, -0.5985, 0.5289, -0.5206)
C18_PUBLISHED_CORRELATIONS = {
    "linear_training": 0.95,
    "linear_validation": 0.94,
    "parallel_ann_training": 0.98,
    "parallel_ann_validation": 0.98,
    "dynamic_ann_training": 0.99,
    "dynamic_ann_validation": 0.98,
}
C18_PUBLISHED_ERROR_TRENDS = {
    "linear_training": -0.177,
    "linear_validation": -0.02,
    "parallel_ann_training": -0.151,
    "parallel_ann_validation": -0.07,
    "dynamic_ann_training": -0.155,
    "dynamic_ann_validation": -0.178,
}

C18_FIGURE_PDF_SHA256 = "af31e3a2c385d498529c89482f20764b8629f42e353b25a7017f0bd3d7507886"


@dataclass(frozen=True)
class C18DataSet:
    thickening: tuple[float, ...]
    force: tuple[float, ...]
    sampling_hz: float = 100.0
    provenance: str = "user-supplied"
    kind: str = "supplied"
    source_sha256: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "thickening", tuple(float(value) for value in self.thickening))
        object.__setattr__(self, "force", tuple(float(value) for value in self.force))
        if len(self.thickening) != len(self.force) or len(self.force) < 5:
            raise ValueError("C18 signals must have one common length >= 5")
        if any(
            not math.isfinite(float(value))
            for signal in (self.thickening, self.force)
            for value in signal
        ):
            raise ValueError("C18 signals must be finite")
        if not math.isfinite(self.sampling_hz) or self.sampling_hz <= 0.0:
            raise ValueError("sampling_hz must be positive and finite")
        if self.kind not in {"supplied", "csv", "digitized"}:
            raise ValueError("unknown C18 data kind")
        if not isinstance(self.provenance, str) or not self.provenance.strip():
            raise ValueError("C18 data need a nonempty provenance description")
        if self.source_sha256 is not None:
            _validate_sha256(self.source_sha256)


@dataclass(frozen=True)
class C18DataEvidence:
    """Reproducible data identity, without asserting original-data authenticity."""

    kind: str
    provenance: str
    samples: int
    sampling_hz: float
    signal_sha256: str
    source_sha256: str | None


def _validate_sha256(value: str) -> None:
    if not isinstance(value, str) or len(value) != 64 or any(char not in "0123456789abcdefABCDEF" for char in value):
        raise ValueError("SHA-256 must contain exactly 64 hexadecimal characters")


def load_c18_csv(
    path: str | Path, *, sampling_hz: float = 100.0,
    expected_sha256: str | None = None,
) -> C18DataSet:
    """Read time_s/thickening/force CSV without resampling or filling gaps.

    By default samples must be uniformly spaced at the specified 100 Hz.
    An optional checksum pins the input bytes; it does not authenticate their
    authorship. The result always records the actual input-file checksum.
    """
    if not math.isfinite(sampling_hz) or sampling_hz <= 0:
        raise ValueError("sampling_hz must be positive and finite")
    if expected_sha256 is not None:
        _validate_sha256(expected_sha256)
    source = Path(path)
    raw = source.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256.lower():
        raise ValueError("C18 input-file SHA-256 mismatch")
    reader = csv.reader(io.StringIO(raw.decode("utf-8-sig")))
    header = next(reader, [])
    required = ("time_s", "thickening", "force")
    if len(header) != 3 or set(header) != set(required):
        raise ValueError("C18 CSV requires exactly time_s, thickening, force columns")
    columns = tuple(header.index(name) for name in required)
    signals: list[list[float]] = [[], [], []]
    for line, row in enumerate(reader, 2):
        if len(row) != 3:
            raise ValueError(f"C18 CSV line {line} must contain three values")
        try:
            values = tuple(float(row[index]) for index in columns)
        except ValueError as error:
            raise ValueError(f"C18 CSV line {line} contains a non-numeric value") from error
        if not all(math.isfinite(value) for value in values):
            raise ValueError(f"C18 CSV line {line} contains a non-finite value")
        if signals[0] and not math.isclose(values[0] - signals[0][-1], 1.0 / sampling_hz, rel_tol=1e-7, abs_tol=1e-10):
            raise ValueError(f"C18 CSV line {line} is not on the uniform {sampling_hz:g} Hz time grid")
        for signal, value in zip(signals, values):
            signal.append(value)
    return C18DataSet(tuple(signals[1]), tuple(signals[2]), sampling_hz,
                      f"CSV input: {source.name}", "csv", digest)


def _data_evidence(data: C18DataSet) -> C18DataEvidence:
    payload = json.dumps({"sampling_hz": float(data.sampling_hz), "thickening": data.thickening,
                          "force": data.force}, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return C18DataEvidence(data.kind, data.provenance, len(data.force), data.sampling_hz,
                           hashlib.sha256(payload.encode("utf-8")).hexdigest(), data.source_sha256)


@dataclass(frozen=True)
class C18LinearModel:
    a1: float
    a2: float
    b0: float
    b1: float

    @property
    def coefficients(self) -> tuple[float, float, float, float]:
        return self.a1, self.a2, self.b0, self.b1


def _standardized_value(value: float, mean: float, scale: float) -> float:
    delta = value - mean
    if math.isfinite(delta):
        return delta / scale
    # Opposite signs can overflow the subtraction before division by a large scale.
    return value / scale - mean / scale


@dataclass(frozen=True)
class C18MLP:
    input_mean: tuple[float, ...]
    input_scale: tuple[float, ...]
    target_mean: float
    target_scale: float
    hidden_weights: tuple[tuple[float, ...], ...]
    hidden_bias: tuple[float, ...]
    output_weights: tuple[float, ...]
    output_bias: float

    def predict_one(self, features: Sequence[float]) -> float:
        if len(features) != len(self.input_mean):
            raise ValueError("feature dimension does not match C18MLP")
        normalized = tuple(
            _standardized_value(float(value), mean, scale)
            for value, mean, scale in zip(features, self.input_mean, self.input_scale)
        )
        hidden = tuple(
            math.tanh(bias + sum(weight * value for weight, value in zip(row, normalized)))
            for row, bias in zip(self.hidden_weights, self.hidden_bias)
        )
        normalized_output = self.output_bias + sum(
            weight * value for weight, value in zip(self.output_weights, hidden)
        )
        return self.target_mean + self.target_scale * normalized_output


@dataclass(frozen=True)
class C18Metrics:
    training_correlation: float
    validation_correlation: float
    training_error_trend: float
    validation_error_trend: float


@dataclass(frozen=True)
class C18DynamicTrial:
    seed: int
    training_free_run_rmse: float


@dataclass(frozen=True)
class C18Tasks:
    training_data: C18DataEvidence
    validation_data: C18DataEvidence
    linear_model: C18LinearModel
    parallel_model: C18MLP
    dynamic_model: C18MLP
    linear: C18Metrics
    parallel_ann: C18Metrics
    dynamic_ann: C18Metrics
    dynamic_ann_one_step: C18Metrics
    linear_training: tuple[float, ...]
    linear_validation: tuple[float, ...]
    parallel_training: tuple[float, ...]
    parallel_validation: tuple[float, ...]
    dynamic_training: tuple[float, ...]
    dynamic_validation: tuple[float, ...]
    dynamic_training_one_step: tuple[float, ...]
    dynamic_validation_one_step: tuple[float, ...]
    dynamic_trials: tuple[C18DynamicTrial, ...] = ()
    dynamic_selected_seed: int = 18
    first_scored_sample: int = 2
    dynamic_fit: str = "one-step"
    dynamic_epochs: int | None = None


@lru_cache(maxsize=1)
def _figure_curves() -> tuple[tuple[float, ...], ...]:
    path = (
        files("argesim_benchmarks").joinpath("data").joinpath("c18_figure_traces.csv")
    )
    with path.open("r", encoding="ascii", newline="") as source:
        reader = csv.reader(source)
        next(reader)  # time, training thickening/force, validation thickening/force
        rows = [tuple(map(float, row[1:])) for row in reader]
    return tuple(zip(*rows, strict=True))


def c18_digitized_data(*, sampling_hz: int = 100) -> tuple[C18DataSet, C18DataSet]:
    """Sample the published vector traces over their actual span, 0..19.99 s."""
    if type(sampling_hz) is not int or sampling_hz <= 0 or sampling_hz % 5:
        raise ValueError("sampling_hz must be a positive integer multiple of 5")

    def resample(curve):
        if sampling_hz == 100:
            return curve
        result = []
        for i in range((len(curve) - 1) * sampling_hz // 100 + 1):
            left, remainder = divmod(i * 100, sampling_hz)
            value = curve[left]
            if remainder:
                value += (curve[left + 1] - value) * remainder / sampling_hz
            result.append(value)
        return tuple(result)

    curves = _figure_curves()

    def dataset(start, figure):
        return C18DataSet(
            resample(curves[start]),
            resample(curves[start + 1]),
            float(sampling_hz),
            f"digitized official C18 Figure {figure}, PDF vector traces on a 100 Hz grid",
            "digitized",
            C18_FIGURE_PDF_SHA256,
        )

    return dataset(0, 1), dataset(2, 2)


def _least_squares(rows: list[tuple[float, ...]], target: Sequence[float],
                   ridge: float) -> tuple[float, ...]:
    """Column-scaled Householder QR, without squaring the condition number.

    Ridge regularization is represented by extra sqrt(ridge)*I observations,
    preserving its original units. Column scaling changes coordinates only;
    it does not change the least-squares objective or penalization.
    """
    width = len(rows[0])
    matrix = [list(row) for row in rows]
    rhs = list(target)
    if ridge:
        for index in range(width):
            matrix.append([math.sqrt(ridge) if index == j else 0.0
                           for j in range(width)])
            rhs.append(0.0)
    scales = [math.hypot(*(row[j] for row in matrix)) for j in range(width)]
    if len(matrix) < width or any(scale == 0 for scale in scales):
        raise ValueError("rank-deficient C18 regression; supply nonzero ridge")
    matrix = [[value / scale for value, scale in zip(row, scales)] for row in matrix]
    for column in range(width):
        vector = [matrix[i][column] for i in range(column, len(matrix))]
        norm = math.hypot(*vector)
        if norm <= 1e-12:
            raise ValueError("rank-deficient C18 regression; supply nonzero ridge")
        vector[0] += math.copysign(norm, vector[0])
        scale = math.hypot(*vector)
        vector = [value / scale for value in vector]
        for j in range(column, width):
            projection = 2 * math.fsum(
                value * matrix[i][j] for i, value in enumerate(vector, column)
            )
            for i, value in enumerate(vector, column):
                matrix[i][j] -= projection * value
        projection = 2 * math.fsum(
            value * rhs[i] for i, value in enumerate(vector, column)
        )
        for i, value in enumerate(vector, column):
            rhs[i] -= projection * value
    solution = [0.0] * width
    for i in range(width - 1, -1, -1):
        solution[i] = (rhs[i] - math.fsum(
            matrix[i][j] * solution[j] for j in range(i + 1, width)
        )) / matrix[i][i]
    return tuple(value / scale for value, scale in zip(solution, scales))


def fit_c18_linear(data: C18DataSet, *, ridge: float = 1.0e-10) -> C18LinearModel:
    """Least-squares second-order ARX transfer-function identification."""

    if not math.isfinite(ridge) or ridge < 0:
        raise ValueError("ridge must be non-negative and finite")
    rows = [
        (
            data.force[index - 1],
            data.force[index - 2],
            data.thickening[index],
            data.thickening[index - 1],
        )
        for index in range(2, len(data.force))
    ]
    target = data.force[2:]
    return C18LinearModel(*_least_squares(rows, target, ridge))


def predict_c18_linear(model: C18LinearModel, data: C18DataSet) -> tuple[float, ...]:
    """Free-run simulation of the identified transfer function."""

    output = [data.force[0], data.force[1]]
    for index in range(2, len(data.force)):
        output.append(
            model.a1 * output[-1]
            + model.a2 * output[-2]
            + model.b0 * data.thickening[index]
            + model.b1 * data.thickening[index - 1]
        )
    return tuple(output)


def c18_correlation(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right) or len(left) < 2:
        raise ValueError("correlation signals must have common length >= 2")
    if not all(math.isfinite(value) for signal in (left, right) for value in signal):
        raise ValueError("correlation signals must be finite")

    def centered_unit(signal):
        # Power-of-two scaling before subtraction handles large opposite
        # signs. Centering relative to an observation preserves small spreads.
        exponent = math.frexp(max(map(abs, signal)))[1]
        origin = math.ldexp(signal[0], -exponent)
        offsets = [math.ldexp(x, -exponent) - origin for x in signal]
        mean = math.fsum(offsets) / len(offsets)
        centered = [x - mean for x in offsets]
        norm = math.hypot(*centered)
        return [x / norm for x in centered] if norm else []

    x, y = centered_unit(left), centered_unit(right)
    if not x or not y:
        return 0.0
    return max(-1.0, min(1.0, math.fsum(a * b for a, b in zip(x, y))))


def c18_error_trend(
    measured: Sequence[float],
    simulated: Sequence[float],
    *,
    sampling_hz: float,
) -> float:
    """Return the least-squares slope of measured-minus-simulated error."""

    if len(measured) != len(simulated) or len(measured) < 2:
        raise ValueError("error signals must have common length >= 2")
    if not all(math.isfinite(value) for signal in (measured, simulated) for value in signal):
        raise ValueError("error signals must be finite")
    if not math.isfinite(sampling_hz) or sampling_hz <= 0.0:
        raise ValueError("sampling_hz must be positive and finite")
    count = len(measured)
    mean_index = 0.5 * (count - 1)
    mean_error = sum(
        float(actual) - float(predicted)
        for actual, predicted in zip(measured, simulated)
    ) / count
    numerator = sum(
        ((index - mean_index) / sampling_hz)
        * (float(actual) - float(predicted) - mean_error)
        for index, (actual, predicted) in enumerate(zip(measured, simulated))
    )
    denominator = sum(
        ((index - mean_index) / sampling_hz) ** 2 for index in range(count)
    )
    return numerator / denominator


def _c18_metrics(
    training: C18DataSet,
    validation: C18DataSet,
    training_prediction: Sequence[float],
    validation_prediction: Sequence[float],
) -> C18Metrics:
    return C18Metrics(
        c18_correlation(training.force[2:], training_prediction[2:]),
        c18_correlation(validation.force[2:], validation_prediction[2:]),
        c18_error_trend(
            training.force[2:],
            training_prediction[2:],
            sampling_hz=training.sampling_hz,
        ),
        c18_error_trend(
            validation.force[2:],
            validation_prediction[2:],
            sampling_hz=validation.sampling_hz,
        ),
    )


def fit_c18_mlp(
    features: Sequence[Sequence[float]],
    targets: Sequence[float],
    *,
    hidden: int,
    seed: int = 18,
    epochs: int = 400,
    learning_rate: float = 0.02,
) -> C18MLP:
    """Train a deterministic single-hidden-layer tanh network by batch GD."""

    rows = tuple(tuple(float(value) for value in row) for row in features)
    values = tuple(float(value) for value in targets)
    if not rows or len(rows) != len(values):
        raise ValueError("features and targets must have one non-empty common length")
    dimension = len(rows[0])
    if dimension == 0 or any(len(row) != dimension for row in rows):
        raise ValueError("all feature rows must have one positive dimension")
    if any(type(value) is not int or value <= 0 for value in (hidden, epochs)):
        raise ValueError("hidden and epochs must be positive integers")
    if not math.isfinite(learning_rate) or learning_rate <= 0.0:
        raise ValueError("learning_rate must be positive and finite")
    if type(seed) is not int:
        raise TypeError("seed must be an integer")
    if not all(math.isfinite(value) for row in rows for value in row) or not all(
        math.isfinite(value) for value in values
    ):
        raise ValueError("features and targets must be finite")
    means = tuple(sum(row[index] for row in rows) / len(rows) for index in range(dimension))
    scales = tuple(
        max(
            1.0e-12,
            math.sqrt(
                sum((row[index] - means[index]) ** 2 for row in rows) / len(rows)
            ),
        )
        for index in range(dimension)
    )
    target_mean = sum(values) / len(values)
    target_scale = max(
        1.0e-12,
        math.sqrt(sum((value - target_mean) ** 2 for value in values) / len(values)),
    )
    x = tuple(
        tuple(
            (value - mean) / scale
            for value, mean, scale in zip(row, means, scales)
        )
        for row in rows
    )
    y = tuple((value - target_mean) / target_scale for value in values)
    rng = random.Random(seed)
    width = 1.0 / math.sqrt(dimension)
    weights = [
        [rng.uniform(-width, width) for _ in range(dimension)]
        for _ in range(hidden)
    ]
    biases = [0.0] * hidden
    output_weights = [rng.uniform(-0.2, 0.2) for _ in range(hidden)]
    output_bias = 0.0
    count = float(len(rows))

    for _ in range(epochs):
        grad_weights = [[0.0] * dimension for _ in range(hidden)]
        grad_biases = [0.0] * hidden
        grad_output = [0.0] * hidden
        grad_output_bias = 0.0
        for row, target in zip(x, y):
            activations = [
                math.tanh(
                    bias
                    + sum(
                        weight * value
                        for weight, value in zip(hidden_row, row)
                    )
                )
                for hidden_row, bias in zip(weights, biases)
            ]
            prediction = output_bias + sum(
                weight * value
                for weight, value in zip(output_weights, activations)
            )
            error = prediction - target
            grad_output_bias += error
            for unit in range(hidden):
                grad_output[unit] += error * activations[unit]
                delta = error * output_weights[unit] * (1.0 - activations[unit] ** 2)
                grad_biases[unit] += delta
                for index in range(dimension):
                    grad_weights[unit][index] += delta * row[index]
        rate = learning_rate / count
        output_bias -= rate * grad_output_bias
        for unit in range(hidden):
            output_weights[unit] -= rate * grad_output[unit]
            biases[unit] -= rate * grad_biases[unit]
            for index in range(dimension):
                weights[unit][index] -= rate * grad_weights[unit][index]
    return C18MLP(
        means,
        scales,
        target_mean,
        target_scale,
        tuple(tuple(row) for row in weights),
        tuple(biases),
        tuple(output_weights),
        output_bias,
    )


def fit_c18_dynamic(data: C18DataSet, *, seed: int = 18, epochs: int = 50) -> C18MLP:
    """Fit the ten-unit C18 network using its own two delayed outputs."""
    if type(epochs) is not int or epochs <= 0:
        raise ValueError("epochs must be a positive integer")
    if type(seed) is not int:
        raise TypeError("seed must be an integer")

    def standardize(signal):
        # Compute moments in scaled units to avoid intermediate overflow.
        exponent = math.frexp(max(map(abs, signal)))[1]
        scaled = [math.ldexp(v, -exponent) for v in signal]
        center = math.fsum(scaled) / len(scaled)
        spread = math.hypot(*(v - center for v in scaled)) / math.sqrt(len(scaled))
        mean = math.ldexp(center, exponent)
        scale = max(math.ldexp(spread, exponent), math.ulp(0.0)) if spread else 1.0
        return tuple(_standardized_value(v, mean, scale) for v in signal), mean, scale

    inputs, input_mean, input_scale = standardize(data.thickening)
    targets, force_mean, force_scale = standardize(data.force)
    parameters = fit_sequence(inputs, targets, hidden=10, epochs=epochs, seed=seed)
    units = [parameters[i : i + 6] for i in range(0, len(parameters) - 1, 6)]
    return C18MLP(
        (force_mean, force_mean, input_mean, input_mean),
        (force_scale, force_scale, input_scale, input_scale),
        force_mean,
        force_scale,
        tuple(tuple(unit[:4]) for unit in units),
        tuple(unit[4] for unit in units),
        tuple(unit[5] for unit in units),
        parameters[-1],
    )


def _parallel_features(data: C18DataSet) -> tuple[tuple[float, ...], ...]:
    # The published seven-unit static ANN has one input: the current
    # thickening sample.  It learns the residual in parallel with G(z).
    return tuple((data.thickening[index],) for index in range(2, len(data.force)))


def _dynamic_features(data: C18DataSet) -> tuple[tuple[float, ...], ...]:
    return tuple(
        (
            data.force[index - 1],
            data.force[index - 2],
            data.thickening[index - 1],
            data.thickening[index - 2],
        )
        for index in range(2, len(data.force))
    )


def _predict_dynamic(model: C18MLP, data: C18DataSet) -> tuple[float, ...]:
    output = [data.force[0], data.force[1]]
    for index in range(2, len(data.force)):
        output.append(
            model.predict_one(
                (output[-1], output[-2], data.thickening[index - 1], data.thickening[index - 2])
            )
        )
    return tuple(output)


def run_c18_tasks(
    training: C18DataSet | str | Path | None = None,
    validation: C18DataSet | str | Path | None = None,
    *,
    epochs: int | None = None,
    use_digitized: bool = False,
    dynamic_seeds: Sequence[int] = (18, 19, 20),
    dynamic_fit: str = "output-feedback",
) -> C18Tasks:
    """Run the three identification methods on an explicit data pair.

    Task C defaults to 50 recurrent epochs. An explicit epochs limit applies
    to both neural networks. The previous one-step fit is selectable.

    CSV paths are accepted for CLI use. ``use_digitized=True`` explicitly runs
    the figure reconstruction demo; it does not validate the original measured
    data experiment. Missing one member is never filled with unrelated data.
    """
    if dynamic_fit not in ("output-feedback", "one-step"):
        raise ValueError("dynamic_fit must be 'output-feedback' or 'one-step'")
    if epochs is not None and (type(epochs) is not int or epochs <= 0):
        raise ValueError("epochs must be a positive integer")
    parallel_epochs = 400 if epochs is None else epochs
    dynamic_epochs = (
        50 if epochs is None and dynamic_fit == "output-feedback" else parallel_epochs
    )
    if use_digitized:
        if training is not None or validation is not None:
            raise ValueError("use_digitized cannot be combined with supplied C18 data")
        training, validation = c18_digitized_data()
    elif training is None or validation is None:
        raise ValueError(
            "C18 requires both training and validation data; use_digitized=True selects only the reconstruction demo"
        )
    if isinstance(training, (str, Path)):
        training = load_c18_csv(training)
    if isinstance(validation, (str, Path)):
        validation = load_c18_csv(validation)
    if not isinstance(training, C18DataSet) or not isinstance(validation, C18DataSet):
        raise TypeError("C18 inputs must be C18DataSet instances or CSV paths")
    if training.sampling_hz != validation.sampling_hz:
        raise ValueError("C18 training and validation sampling rates must match")
    if (
        training.kind == "digitized" or validation.kind == "digitized"
    ) and training.kind != validation.kind:
        raise ValueError("C18 digitized data cannot be mixed with another data source")
    if (
        training.thickening == validation.thickening
        and training.force == validation.force
    ):
        raise ValueError("C18 validation must use a distinct recording from training")
    seeds = tuple(dynamic_seeds)
    if (
        not seeds
        or any(type(seed) is not int for seed in seeds)
        or len(set(seeds)) != len(seeds)
    ):
        raise ValueError(
            "dynamic_seeds must contain distinct integers and cannot be empty"
        )
    linear_model = fit_c18_linear(training)
    linear_training = predict_c18_linear(linear_model, training)
    linear_validation = predict_c18_linear(linear_model, validation)

    residual = tuple(
        actual - predicted
        for actual, predicted in zip(training.force[2:], linear_training[2:])
    )
    parallel_model = fit_c18_mlp(
        _parallel_features(training), residual, hidden=7, epochs=parallel_epochs
    )
    parallel_training = tuple(
        base
        if index < 2
        else base + parallel_model.predict_one((training.thickening[index],))
        for index, base in enumerate(linear_training)
    )
    parallel_validation = tuple(
        base
        if index < 2
        else base + parallel_model.predict_one((validation.thickening[index],))
        for index, base in enumerate(linear_validation)
    )

    # Task C repeats training from independent starts. Select on a training
    # rollout with feedback, excluding the two measured initialization values.
    features = _dynamic_features(training)
    targets = training.force[2:]
    trials = []
    best_score = math.inf
    for seed in seeds:
        if dynamic_fit == "output-feedback":
            candidate = fit_c18_dynamic(training, epochs=dynamic_epochs, seed=seed)
        else:
            candidate = fit_c18_mlp(
                features, targets, hidden=10, epochs=dynamic_epochs, seed=seed
            )
        rollout = _predict_dynamic(candidate, training)
        score = math.hypot(*(a - b for a, b in zip(targets, rollout[2:]))) / math.sqrt(
            len(targets)
        )
        if not math.isfinite(score):
            raise ValueError(f"non-finite C18 training rollout for seed {seed}")
        trials.append(C18DynamicTrial(seed, score))
        if score < best_score:
            best_score, selected_seed = score, seed
            dynamic_model, dynamic_training = candidate, rollout
    dynamic_training_one_step = training.force[:2] + tuple(
        dynamic_model.predict_one(row) for row in features
    )
    dynamic_validation_one_step = validation.force[:2] + tuple(
        dynamic_model.predict_one(row) for row in _dynamic_features(validation)
    )
    # Task C is a true simulation with delayed network outputs fed back.  Keep
    # the teacher-forced one-step metric separate so it cannot be mistaken for
    # that harder validation problem.
    dynamic_validation = _predict_dynamic(dynamic_model, validation)
    return C18Tasks(
        training_data=_data_evidence(training),
        validation_data=_data_evidence(validation),
        linear_model=linear_model,
        parallel_model=parallel_model,
        dynamic_model=dynamic_model,
        linear=_c18_metrics(training, validation, linear_training, linear_validation),
        parallel_ann=_c18_metrics(
            training, validation, parallel_training, parallel_validation
        ),
        dynamic_ann=_c18_metrics(
            training, validation, dynamic_training, dynamic_validation
        ),
        dynamic_ann_one_step=_c18_metrics(
            training,
            validation,
            dynamic_training_one_step,
            dynamic_validation_one_step,
        ),
        linear_training=linear_training,
        linear_validation=linear_validation,
        parallel_training=parallel_training,
        parallel_validation=parallel_validation,
        dynamic_training=dynamic_training,
        dynamic_validation=dynamic_validation,
        dynamic_training_one_step=dynamic_training_one_step,
        dynamic_validation_one_step=dynamic_validation_one_step,
        dynamic_trials=tuple(trials),
        dynamic_selected_seed=selected_seed,
        dynamic_fit=dynamic_fit,
        dynamic_epochs=dynamic_epochs,
    )

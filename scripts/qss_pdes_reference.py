"""Recompute the serial physical controls for the QSS/PDES study from the book lab."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import expm_multiply

EDITION = Path(__file__).resolve().parents[1] / 'docs/lehrbuch/gesamtausgabe'


def no_flux_laplacian(size):
    diagonal = np.full(size, -2.0)
    diagonal[[0, -1]] = -1.0
    return sparse.diags([1.0, diagonal, 1.0], [-1, 0, 1], shape=(size, size))


def groundwater(model, profiles):
    """Independent FV generator with the book's east outflow and eight source bins."""
    rates = np.asarray(profiles['test_rates_mg_s'])
    nx, ny = len(model.X), len(model.Y)
    diffusion = model.DIFFUSION / model.DX**2
    drift = model.VELOCITY / model.DX
    upwind = sparse.diags([drift, -drift], [-1, 0], shape=(nx, nx))
    generator = sparse.kronsum(diffusion * no_flux_laplacian(nx) + upwind,
                               diffusion * no_flux_laplacian(ny), format='csr')
    size = nx * ny
    source = np.zeros((size, 1))
    source[np.ravel_multi_index(model.SOURCE, (ny, nx))] = 1 / model.CELL_WATER
    east = np.zeros((1, size))
    east[0, nx-1::nx] = model.VELOCITY * model.DX * model.WATER_COLUMN
    projected = np.arange(size, dtype=float).reshape(1, ny, nx) / size
    flux, exported = model.flux_derivative(projected, np.array([1.0]))
    np.testing.assert_allclose(generator @ projected.ravel() + source[:, 0], flux.ravel(), atol=1e-18)
    np.testing.assert_allclose(east @ projected.ravel(), exported)
    # Last two states integrate the exported mass and hold the current release.
    dynamics = sparse.bmat([[generator, None, sparse.csr_matrix(source)],
                            [sparse.csr_matrix(east), sparse.csr_matrix((1, 1)), None],
                            [None, None, sparse.csr_matrix((1, 1))]], format='csr')
    duration = model.HORIZON / model.SEGMENTS
    state = np.zeros((size + 2, len(rates)))
    for release in rates.T:
        state[-1] = release
        state = expm_multiply(duration * dynamics, state)
    fields = state[:size].T.reshape(-1, ny, nx)
    field_reference = model.observation_field(rates, model.green_basis(192))
    wells = rates @ model.point_basis()
    injected = duration * rates.sum(axis=1)
    scores = model.report_scores(fields, field_reference, wells, injected)
    rk4, _ = model.finite_volume(rates, step=model.DT / 2)
    diff = np.linalg.norm((rk4 - fields).reshape(len(rates), size), axis=1)
    diff /= np.linalg.norm(fields.reshape(len(rates), size), axis=1)
    mass_error = abs(model.mass(fields) + state[-2] - injected) / injected
    if max(diff) >= 1e-6 or max(mass_error) >= 1e-12:
        raise ValueError('C19R semidiscrete time or mass control failed')
    return {'profiles': profiles['test_names'], 'physical_scores': scores['score'],
            'physical_passes': sum(scores['pass']), 'max_field_relative': max(scores['field_relative']),
            'max_well_relative': max(scores['well_relative']), 'max_mass_closure_fraction': float(max(mass_error)),
            'max_relative_to_half_step_rk4': float(max(diff))}


def rope(modal_rope, intervals):
    """Force the semidiscrete string with two exact boundary-state equations."""
    n = intervals - 1
    kroot = intervals / (10 * np.sqrt(2.0))
    lap = sparse.diags([1.0, -2.0, 1.0], [-1, 0, 1], shape=(n, n))
    boundary = sparse.csr_matrix(([kroot], ([n-1], [0])), shape=(n, 2))
    forcing = sparse.csr_matrix([[-0.2, 1.0], [-1.0, -0.2]])
    dynamics = sparse.bmat([[None, kroot * sparse.eye(n), None],
                            [kroot * lap, None, boundary], [None, None, forcing]], format='csr')
    initial = np.zeros(2*n + 2)
    initial[-1] = 1.0
    times = np.linspace(0.0, 30.0, 121)
    exact_time = expm_multiply(dynamics, initial, start=0, stop=30, num=len(times))
    field = exact_time[:, :n]
    modal = modal_rope(times, [1.0], intervals=intervals)[0]
    relative = np.linalg.norm(field-modal) / np.linalg.norm(modal)
    # Right endpoint belongs to the drive. Interpolate at fixed physical probes.
    grid = np.linspace(0.0, 1.0, intervals + 1)
    positions = np.array([0.10, 0.25, 0.50, 0.75, 0.90])
    endpoints = np.column_stack((np.zeros(len(times)), np.exp(-0.2*times) * np.sin(times)))
    def probe_values(states):
        padded = np.column_stack((endpoints[:, 0], states, endpoints[:, 1]))
        return np.stack([np.interp(positions, grid, row) for row in padded])
    sensors = probe_values(field)
    sensor_error = np.max(abs(sensors - probe_values(modal)))
    nearest = np.rint(positions * intervals).astype(int)
    nearest_offset = np.max(abs(sensors - field[:, nearest-1]))
    if relative >= 1e-9 or sensor_error >= 1e-9:
        raise ValueError('CP1/C modal and matrix-exponential controls disagree')
    return {'nodes_including_ends': intervals+1, 'intervals': intervals, 'interior_nodes': n,
            'ode_states': 2*n, 'time_samples': len(times), 'relative_field_difference': float(relative),
            'max_sensor_difference_m': float(sensor_error),
            'max_nearest_vs_linear_m': float(nearest_offset),
            'score_between_semidiscrete_references': float(max(relative/0.01, sensor_error/0.001))}


def main():
    files = ('rechenlabor/fno_benchmarks/c19r.py', 'rechenlabor/fno_transfer/linear.py',
             'rechenlabor/fno_transfer/fourier_layer.py')
    with TemporaryDirectory() as work, ZipFile(EDITION/'pakete/Laborquellen.zip') as archive:
        for name in files:
            (Path(work)/Path(name).name).write_bytes(archive.read(name))
        profiles = json.loads(archive.read('rechenlabor/fno_benchmarks/messung/vergleich.json'))['c19r']
        sys.path.insert(0, work)
        try:
            import c19r
            from linear import modal_rope
            results = {'c19r': groundwater(c19r, profiles),
                       'cp1c': [rope(modal_rope, n) for n in (799, 800)]}
        finally:
            sys.path.remove(work)
    print(json.dumps(results, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()

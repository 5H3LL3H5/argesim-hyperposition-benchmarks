"""Repeat the CP2 MPI and grouped full runs or the C19R and componentwise LP series."""
import argparse
import hashlib
import json
import os
import random
import subprocess
import sys
import time
import zipfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
FLAGS = ['-std=c++20', '-O3', '-march=native', '-ffp-contract=off', '-Wall', '-Wextra', '-Werror']
LP_COUNTS = (1, 2, 4, 8)
TOPOLOGIES = ((1, 1), (1, 2), (2, 2), (2, 4))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(repo, work):
    work.mkdir(parents=True, exist_ok=True)
    srcpath = 'rechenlabor/kavitaet_vollgitter/src/'
    archive = repo / 'docs/lehrbuch/gesamtausgabe/pakete/Laborquellen.zip'
    if archive.exists():
        with zipfile.ZipFile(archive) as sources:
            original = sources.read(srcpath + 'gruppen_qss.cpp').decode()
            marks = sources.read(srcpath + 'zeitpunkte.txt')
    else:
        original = (repo / srcpath / 'gruppen_qss.cpp').read_text()
        marks = (repo / srcpath / 'zeitpunkte.txt').read_bytes()
    grid = original[original.index('extern "C"'):original.index('inline double defect')]
    (work/'wirbel_gitter.hpp').write_text(grid)
    (work/'marks').write_bytes(marks)
    with zipfile.ZipFile(HERE/'PDES_Partitionierung_Messpaket.zip') as data:
        for name in data.namelist():
            if name.startswith('c19_nom/') or name in ('sparse_pdes.cpp', 'cavity_pdes.py',
                    'run_sparse.py', 'partitions.py', 'd2q9_halos.cpp', 'prepare_d2q9.py'):
                data.extract(name, work)
    subprocess.run([sys.executable, 'prepare_d2q9.py', str(repo)], cwd=work, check=True)
    subprocess.run(['mpicxx', '-DOMPI_SKIP_MPICXX', *FLAGS, '-fopenmp-simd',
                    'd2q9_halos.cpp', '-o', 'd2q9_halos'], cwd=work, check=True)
    subprocess.run(['mpicxx', '-DOMPI_SKIP_MPICXX', *FLAGS, 'sparse_pdes.cpp',
                    '-o', 'sparse_pdes'], cwd=work, check=True)
    subprocess.run(['g++', '-I.', *FLAGS, str(HERE/'gruppen_qss34.cpp'),
                    '-Wl,-l:libfftw3.so.3', '-o', 'gq'], cwd=work, check=True)


def lbm(work):
    expected = json.loads((HERE/'vollgitter.json').read_text())['runs']['lbm1']['field_sha256']['350000']
    for px, py in TOPOLOGIES:
        ranks = px*py
        start = time.perf_counter()
        run = subprocess.run(['mpiexec', '--oversubscribe', '--bind-to', 'none', '-n', str(ranks),
                              './d2q9_halos', str(px), str(py), '350000', f'mpi-{ranks}'],
                             cwd=work, capture_output=True, text=True, check=True)
        wall = time.perf_counter()-start
        row = json.loads(next(s for s in reversed(run.stdout.splitlines()) if s.startswith('{')))
        row.update(launcher_wall_s=wall, field_sha256=digest(work/f'mpi-{ranks}.fields'))
        if row['steps'] != 350000 or row['field_sha256'] != expected:
            raise ValueError('MPI field differs from the published serial field')
        (work/f'log-{ranks}.json').write_text(json.dumps(row, indent=2)+'\n')


def c19(work):
    sys.path.insert(0, str(work))
    from partitions import enumerate_grid
    from run_sparse import trial
    case = Path('c19_nom')
    os.chdir(work)
    counts = np.fromfile(case/'base.counts', dtype='<u8')
    for layout, owner, _ in enumerate_grid(json.loads((case/'metadata.json').read_text()), counts, 2):
        if layout == 'weighted':
            np.savetxt(case/'weighted-2.map', owner, fmt='%d')
    rng = random.Random(20261126)
    with (work/'c19-scaling.jsonl').open('w', buffering=1) as out:
        for repeat in range(1, 6):
            cases = [(p, m, w) for p in LP_COUNTS for m, w in [('conservative',108000),('optimistic',13500)]]
            rng.shuffle(cases)
            for p, mode, window in cases:
                row = trial(case, p, 'one' if p == 1 else 'weighted', mode, window, repeat)
                if not row['verified']:
                    raise ValueError('C19R state or event trace differs from the one-LP run')
                out.write(json.dumps(row)+'\n')


def prefix(repo, work):
    for order, layout in [(3,'rows'),(4,'tiles')]:
        with (work/f'qss{order}-lps.jsonl').open('w') as out:
            subprocess.run([sys.executable, 'cavity_pdes.py', str(repo), '--order', str(order),
                            '--segments','8','--ranks', *map(str, LP_COUNTS), '--modes','conservative',
                            '--layouts',layout,'--repeats','3'], cwd=work, stdout=out, check=True)


def groups(work):
    for order in (3, 4):
        subprocess.run(['./gq','257',str(order),'0.001','marks',f'gqss{order}'], cwd=work, check=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare','lbm','c19','prefix','groups'])
    parser.add_argument('repo', type=Path, help='repository checkout containing the published book')
    parser.add_argument('work', type=Path, help='a separate measurement directory')
    args = parser.parse_args()
    repo, work = args.repo.resolve(), args.work.resolve()
    if args.action in ('lbm','c19','prefix') and len(os.sched_getaffinity(0)) < 8:
        parser.error('Eight available CPUs are required for this series')
    os.environ.update(OMPI_MCA_pml='ob1', UCX_VFS_ENABLE='n', OMP_NUM_THREADS='1',
                      OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', NUMEXPR_NUM_THREADS='1')
    if args.action == 'prepare':
        prepare(repo,work)
    elif args.action == 'lbm':
        lbm(work)
    elif args.action == 'groups':
        groups(work)
    elif args.action == 'c19':
        c19(work)
    else:
        prefix(repo,work)

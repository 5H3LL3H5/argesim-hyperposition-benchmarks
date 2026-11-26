"""Restore one QSS checkpoint, run a bounded work interval and verify progress or completion."""
import argparse
import hashlib
import json
import os
import platform
import signal
import subprocess
import sys
import time
import zipfile
from pathlib import Path

import numpy as np
import scipy
from qss_langlauf import CHECKS, END, FINAL

HERE = Path(__file__).resolve().parent


def state(path):
    with np.load(path / 'restart.npz', allow_pickle=False) as saved:
        return int(saved['segments']), float(saved['now']), int(saved['next_mark'])


def seed(directory, order):
    directory.mkdir(parents=True, exist_ok=True)
    prefix = f'qss{order}/'
    allowed = {'restart.npz', 'progress.jsonl', *(f'z_{k}.bin' for k in CHECKS)}
    with zipfile.ZipFile(HERE/'QSS34_Fortsetzung.zip') as archive:
        for line in archive.read('SHA256SUMS').decode().splitlines():
            expected, name = line.split('  ', 1)
            if name.startswith(prefix):
                member = name[len(prefix):]
                data = archive.read(name)
                if member not in allowed or hashlib.sha256(data).hexdigest() != expected:
                    raise ValueError('Invalid seed member')
                (directory/member).write_bytes(data)


def run(repo, output, order, seconds):
    if not (output/'restart.npz').exists():
        seed(output, order)
    before, start_time, old_marks = state(output)
    if not math_valid(start_time, old_marks):
        raise ValueError('Invalid starting state')
    command = [sys.executable, '-u', str(HERE/'qss_langlauf.py'), str(repo), str(output),
               '--resume', '--order', str(order)]
    start = time.monotonic()
    with subprocess.Popen(command) as worker:
        try:
            status = worker.wait(timeout=seconds)
        except subprocess.TimeoutExpired:
            worker.send_signal(signal.SIGTERM)
            status = worker.wait(timeout=180)
        if status:
            raise RuntimeError(f'Solver exited with code {status}')
    after, stop_time, marks = state(output)
    complete = stop_time == FINAL and marks == len(CHECKS)
    if not math_valid(stop_time, marks) or (not complete and (after <= before or stop_time <= start_time)):
        raise ValueError('Checkpoint did not advance')
    hashes = {}
    for tick in CHECKS[:marks]:
        field = output/f'z_{tick}.bin'
        a = np.fromfile(field, dtype='<f8')
        if a.size != 255*255 or not np.isfinite(a).all():
            raise ValueError(f'Invalid observation at {tick}')
        hashes[str(tick)] = hashlib.sha256(field.read_bytes()).hexdigest()
    row = {'order': order, 't_start': start_time, 't_star': stop_time, 'target_tick': END, 'new_segments': after-before,
               'wall_s': time.monotonic()-start, 'complete': complete, 'fields_sha256': hashes,
               'platform': platform.platform(), 'numpy': np.__version__, 'scipy': scipy.__version__,
               'python': platform.python_version(), 'source_sha256': hashlib.sha256((HERE/'qss_langlauf.py').read_bytes()).hexdigest(),
               'github_run': os.getenv('GITHUB_RUN_ID'),'github_attempt': os.getenv('GITHUB_RUN_ATTEMPT')}
    with (output/'rechenfenster.jsonl').open('a') as log:
        log.write(json.dumps(row)+'\n')
    print(json.dumps(row),flush=True)
    if path := os.getenv('GITHUB_OUTPUT'):
        with open(path,'a') as f:
            f.write(f'complete={str(complete).lower()}\n')
    return row


def math_valid(t, marks):
    return 0 <= t <= FINAL and marks == sum(k*(0.1/256) <= t for k in CHECKS)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo',type=Path)
    parser.add_argument('output',type=Path)
    parser.add_argument('--order',type=int,choices=[3,4],required=True)
    parser.add_argument('--seconds',type=float,default=10800)
    a=parser.parse_args()
    if a.seconds<=0:
        parser.error('The work interval must be positive')
    run(a.repo.resolve(),a.output.resolve(),a.order,a.seconds)

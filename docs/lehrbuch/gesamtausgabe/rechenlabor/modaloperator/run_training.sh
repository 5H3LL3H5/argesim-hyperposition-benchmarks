#!/bin/sh
set -eu
cd "$(dirname "$0")"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
py=${PYTHON:-python3}
weights=${1:-results/weights}
"$py" neural.py --output "$weights" --cases n96 --seeds 2027 73 3917
"$py" neural.py --output "$weights" --cases n2 n8 n24 n8_steps noise5 input5 --seeds 2027
"$py" neural.py --output "$weights" --cases family --models FNO-cond Strang-FNO-cond --seeds 2027 73 3917

#!/bin/sh
# Train and score the complete study in a separate output directory.
set -eu
cd "$(dirname "$0")"
out=${1:-repeat}
mkdir -p "$out"
out=$(cd "$out" && pwd)
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
py=${PYTHON:-python3}
"$py" -m unittest -v
./run_training.sh "$out/weights"
"$py" evaluate.py --output "$out" --weights "$out/weights"

"""Wiederhole die 399 publizierten Schlüssel mit den ursprünglichen Modell- und Messfunktionen."""
import argparse
import csv
import json
import random
import signal
import sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from importlib import import_module
from pathlib import Path

p=argparse.ArgumentParser(description=__doc__)
p.add_argument("quellen",type=Path)
p.add_argument("messung",type=Path)
p.add_argument("--workers",type=int,default=4)
args=p.parse_args()
source=args.quellen.resolve()
sys.path[:0]=[str(source/"baseline399"),str(source)]
study = import_module("compare")
supplement = import_module("supplement")
solve_ivp = import_module("argesim_benchmarks").solve_ivp
c01_problem = import_module("argesim_benchmarks.models.c01_lithium_cluster").c01_problem

def run(block):
    name,jobs=block
    signal.signal(signal.SIGALRM,study.expired)
    if name=="C01-A":
        case=supplement.c01()
        plain=case
        ivp=c01_problem()
        def run_c01(method,opts):
            if method=="rk4":opts["step"]=.001
            return solve_ivp(ivp,method,options=opts)
        case=replace(case,run=run_c01)
    else:
        case=next(c for c in study.cases() if c.name==name)
        plain=case
    random.Random(1701).shuffle(jobs)
    out=args.messung/("baseline_"+name+".jsonl")
    with out.open("w",buffering=1) as f:
        for row in jobs:
            m=row["solver"]
            level=float(row["quantum_factor"]) if row["quantum_factor"] else None
            if m=="euler" or (m=="cqss1" and not case.hamiltonian):
                r=supplement.trial(plain,m,level)
            else:r=study.experiment(case,m,level,3,8.)
            f.write(json.dumps(r,allow_nan=False)+"\n")
    return out

if __name__=="__main__":
    args.messung.mkdir(exist_ok=True,parents=True)
    keys={}
    with (source/"docs/evidence/qss-baseline.csv").open() as f:
        for row in csv.DictReader(f):
            if row["solver"] in {"qss3", "qss4"}: keys.setdefault(row["case"], []).append(row)
    with ProcessPoolExecutor(max_workers=args.workers) as workers:
        files=list(workers.map(run,keys.items()))
    columns=["case","solver","quantum_factor","status","error","median_ms","reason"]
    with (args.messung/"baseline.csv").open("w") as out:
        w=csv.DictWriter(out,columns);w.writeheader()
        for file in files:
            for line in file.read_text().splitlines():
                row=json.loads(line);w.writerow({"case": row["case"],"solver": row["method"],"quantum_factor": row["level"],
                    "status": row["status"],"error": row.get("error"),"median_ms": row.get("median_ms"),"reason": row.get("reason","")})

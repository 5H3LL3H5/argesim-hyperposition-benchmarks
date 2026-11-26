"""Check the reported times, LP counts, reach and reference fields from the archived raw runs."""
import argparse
import csv
import hashlib
import io
import json
import math
import statistics
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
COUNTS = [1, 2, 4, 8]
TICKS = [256, 4096, 16384, 65536, 131072, 262144, 350000]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def lines(z, name):
    return [json.loads(row) for row in z.read(name).splitlines()]


def summaries():
    baseline = json.loads((HERE/'vollgitter.json').read_text())
    with zipfile.ZipFile(HERE/'Skalierung_Messdaten.zip') as z:
        for line in z.read('SHA256SUMS').decode().splitlines():
            expected, path = line.split('  ', 1)
            if sha(z.read(path)) != expected:
                raise ValueError(path)
        meta = json.loads(z.read('platform.json'))
        if meta['cpu_ranks'] != COUNTS or meta['end_tick'] != 350000:
            raise ValueError('Invalid experiment')
        mpi = [json.loads(z.read(f'mpi/log-{p}.json')) for p in COUNTS]
        for p, run in zip(COUNTS, mpi, strict=True):
            if (run['ranks'] != p or run['px']*run['py'] != p or run['steps'] != 350000
                    or not 0 < run['kernel_s'] <= run['launcher_wall_s']
                    or run['field_sha256'] != baseline['runs']['lbm1']['field_sha256']['350000']):
                raise ValueError('Invalid MPI run')
        field_sha = json.loads(z.read('feld_sha256.json'))
        for tick in TICKS:
            if field_sha[f'lbm/feld_{tick}.bin'] != baseline['runs']['lbm1']['field_sha256'][str(tick)]:
                raise ValueError('Invalid D2Q9 reference')
        c19 = lines(z,'c19-scaling.jsonl')
        states = {tuple(sorted(r['sha256'].items())) for r in c19}
        if len(c19) != 40 or len(states) != 1 or not all(r['verified'] and r['committed']==65292 for r in c19):
            raise ValueError('C19R confirmation failed')
        sparse = {}
        for mode in ('conservative','optimistic'):
            sparse[mode] = []
            for p in COUNTS:
                rows = [r for r in c19 if r['ranks']==p and r['mode']==mode]
                if sorted(r['repeat'] for r in rows)!=list(range(1,6)):
                    raise ValueError('C19R repetitions')
                sparse[mode].append({'ranks':p,'median_s':statistics.median(r['wall_s'] for r in rows),
                                     'median_launcher_s':statistics.median(r['launcher_wall_s'] for r in rows),
                                     'rollbacks':rows[0]['rollbacks'],'mean_safe':rows[0]['safe_mean']})
        prefix, groups, components = {}, {}, {}
        for order in (3,4):
            key = str(order)
            prefix[key] = []
            runs = lines(z,f'qss{order}-lps.jsonl')
            if len(runs)!=12 or len({r['digest'] for r in runs})!=1:
                raise ValueError('LP traces disagree')
            for p in COUNTS:
                rows = [r for r in runs if r['ranks']==p]
                if sorted(r['repeat'] for r in rows)!=[1,2,3] or not all(
                        r['segments']==8 and r['oracle_sha256']==r['digest']
                        and r['ranks']==r['distinct_processes'] and len(r['times'])==9 for r in rows):
                    raise ValueError('Invalid LP data')
                prefix[key].append({'lps':p,'median_s':statistics.median(r['wall_s'] for r in rows),
                                    't_star':rows[0]['times'][-1]})
            history = list(csv.DictReader(io.StringIO(z.read(f'gqss{order}/history.csv').decode())))
            if [int(r['tick']) for r in history] != baseline['setup']['all_ticks']:
                raise ValueError('Missing full-field observation')
            last = history[-1]
            launch = json.loads(z.read(f'gqss{order}/run.json'))['launcher_wall_s']
            if not (int(last['tick'])==350000 and float(last['t_star'])==136.71875
                    and 0<float(last['kernel_s'])<=launch and float(last['max_band_defect'])<=0.00100000000001):
                raise ValueError('Group endpoint, time or band')
            for k in TICKS:
                if len(field_sha[f'gqss{order}/z_{k}.bin'])!=64:
                    raise ValueError('Invalid vorticity field size')
            groups[key] = {'kernel_s': float(last['kernel_s']), 'launcher_wall_s': launch,
                               'segments': int(last['segments']),'t_star': float(last['t_star'])}
            records = [r for r in lines(z,f'qss{order}-fortschritt.jsonl') if 'segments' in r]
            result=records[-1]
            if (not result['complete'] and result['t_star']>=136.71875) or result['target_ticks']!=350000:
                raise ValueError('Invalid component run status')
            components[key] = result
        control = lines(z,'gegenprobe.jsonl')
        if len(control)!=2 or not all(r['segments']==32 and r['max_abs_time']<2e-12
                                      and r['max_abs_z']<2e-9 for r in control):
            raise ValueError('Serial reference comparison failed')
        errors = json.loads(z.read('gruppen_feldvergleich.json'))
        for order, checks in errors.items():
            if [row['tick'] for row in checks]!=TICKS or not all(
                math.isfinite(v) and v>=0 for row in checks for name in ('lbm','dop853')
                for v in row[name].values()):
                raise ValueError('Invalid group comparisons')
            groups[order]['max_rel_l2_dop853'] = max(row['dop853']['relative_l2'] for row in checks)
            groups[order]['max_rel_l2_lbm'] = max(row['lbm']['relative_l2'] for row in checks)
    return {'mpi': mpi,'c19': sparse,'component_prefix': prefix,'groups': groups,'component_status': components}


def verify_field_archives():
    with zipfile.ZipFile(HERE/'Skalierung_Messdaten.zip') as data:
        expected = json.loads(data.read('feld_sha256.json'))
    found = {}
    for name in ('D2Q9_Prueffelder.zip', 'Gruppen_QSS34_Prueffelder.zip'):
        with zipfile.ZipFile(HERE/name) as fields:
            for path in fields.namelist():
                if path == 'SHA256SUMS':
                    continue
                raw = fields.read(path)
                length = 3*257*257*8 if path.startswith('lbm/') else 255*255*8
                if len(raw) != length or path in found:
                    raise ValueError(f'Invalid field {path}')
                found[path] = sha(raw)
    if len(found) != 3*len(TICKS) or found != expected:
        raise ValueError('Reference or group field checksum mismatch')


def field_errors(repo):
    import numpy as np
    from qss_langlauf import physics
    from vollgitter import difference
    cavity, _ = physics(repo)
    output = {'3':[],'4':[]}
    verify_field_archives()
    saved = json.loads((HERE / "Einzelkalender_Stand.json").read_text())
    with (zipfile.ZipFile(HERE / "QSS34_Fortsetzung.zip") as seed,
          zipfile.ZipFile(HERE/'Skalierung_Messdaten.zip') as z,
          zipfile.ZipFile(HERE/'D2Q9_Prueffelder.zip') as lbm_archive,
          zipfile.ZipFile(HERE/'Gruppen_QSS34_Prueffelder.zip') as groups_archive,
          zipfile.ZipFile(HERE/'DOP853_Prueffelder.zip') as dop):
        for tick in TICKS:
            lbm = np.frombuffer(lbm_archive.read(f'lbm/feld_{tick}.bin'),dtype='<f8').reshape(3,257,257)
            v_lbm = lbm[1:,1:-1,1:-1].transpose(1,2,0)
            v_dop = cavity.field(np.frombuffer(dop.read(f'z_{tick}.bin'),dtype='<f8'))[1:-1,1:-1]
            for order, samples in output.items():
                v = cavity.field(np.frombuffer(groups_archive.read(f'gqss{order}/z_{tick}.bin'),dtype='<f8'))[1:-1,1:-1]
                samples.append({'tick': tick,'lbm': difference(v,v_lbm),'dop853': difference(v,v_dop)})
            for order, status in saved.items():
                if len(status['comparisons']) != status['observations']:
                    raise ValueError('Missing documented component observation')
                for check in status['comparisons']:
                    if check['tick'] != tick:
                        continue
                    raw = seed.read(f'qss{order}/z_{tick}.bin')
                    if sha(raw) != check['sha256']:
                        raise ValueError('Invalid component field')
                    velocity = cavity.field(np.frombuffer(raw, dtype='<f8'))[1:-1,1:-1]
                    for reference, field in [('vs_dop853', v_dop), ('vs_d2q9', v_lbm)]:
                        actual = difference(velocity, field)
                        for label, value in check[reference].items():
                            if not math.isclose(actual[label], value, rel_tol=2e-10, abs_tol=2e-14):
                                raise ValueError(f'Component field mismatch at {tick}')
        expected = json.loads(z.read('gruppen_feldvergleich.json'))
        for order, samples in output.items():
            for a,b in zip(samples,expected[order],strict=True):
                for reference in ('lbm','dop853'):
                    for key,value in a[reference].items():
                        if not math.isclose(value,b[reference][key],rel_tol=2e-10,abs_tol=2e-14):
                            raise ValueError(f'Field discrepancy: {order}, {a["tick"]}, {reference}, {key}')
    return output


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fields',type=Path,help='checkout root for the independent physical-field check')
    a=parser.parse_args()
    print(json.dumps(summaries(),indent=2))
    if a.fields:
        field_errors(a.fields.resolve())

"""Bounded, resumable rescue runs with per-method source and configuration seals."""
import _bootstrap
import argparse
import concurrent.futures as cf
import json
import multiprocessing as mp
import os
import time
import zipfile
from datetime import datetime, timezone
import psutil
from rqmc.common import root, write_json, digest, sha_file, environment
from rqmc.experiment import task_id
from rqmc.rescue_experiment import execute_rescue_task


def stream(tasks, workers):
    if workers == 1:
        yield from map(execute_rescue_task, tasks)
        return
    it = iter(tasks)
    with cf.ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context('spawn')) as pool:
        pending = set()
        for _ in range(workers*2):
            try:
                pending.add(pool.submit(execute_rescue_task, next(it)))
            except StopIteration:
                break
        while pending:
            done, pending = cf.wait(pending, return_when=cf.FIRST_COMPLETED)
            for future in done:
                yield future.result()
                try:
                    pending.add(pool.submit(execute_rescue_task, next(it)))
                except StopIteration:
                    pass


def runtime_sources(r):
    paths = list(r.glob('rqmc/*.py')) + [r/'scripts/run_rescue.py', r/'scripts/_bootstrap.py',
                                       r/'requirements-lock.txt', r/'.project-root']
    return {p.relative_to(r).as_posix(): sha_file(p) for p in sorted(paths)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase', choices=['development', 'confirmation'], default='development')
    parser.add_argument('--methods', nargs='+', required=True)
    parser.add_argument('--workers', type=int, default=16)
    args = parser.parse_args()
    r = root()
    cfg = json.loads((r/'config/rescue_v1.json').read_text(encoding='utf-8'))
    profiles = cfg.pop('rescue_profiles')
    controls = cfg.pop('rescue_controls')
    args.methods = [name for entry in args.methods for name in (controls if entry == 'controls' else [entry])]
    if len(set(args.methods)) != len(args.methods):
        raise SystemExit('Duplicate methods')
    allowed = set(controls) | set(profiles)
    if not set(args.methods) <= allowed:
        raise SystemExit('Unregistered method')
    if not 1 <= args.workers <= 16 or psutil.virtual_memory().available < args.workers*512*2**20:
        raise SystemExit('Unsafe worker or RAM request')
    phase = f'rescue_v1_{args.phase}'
    cfg['workers'] = 16  # throughput setting is not a scientific random-stream parameter
    cases = cfg[f'{args.phase}_cases']
    reps = cfg[f'{args.phase}_repetitions']
    hb = cfg['hbci_cases'] if args.phase == 'confirmation' else cfg['hbci_development_cases']
    sources = runtime_sources(r)
    env = environment()
    if args.phase == 'confirmation':
        frozen = json.loads((r/'state/rescue_v1/confirmation_freeze.json').read_text(encoding='utf-8'))
        if frozen['config'] != cfg or frozen['runtime_sources'] != sources or frozen['environment'] != env:
            raise SystemExit('Confirmation seal mismatch')
        if any(profiles.get(m) != frozen['profiles'].get(m) for m in args.methods):
            raise SystemExit('Confirmation profile mismatch')
        if not set(args.methods) <= set(frozen['methods']):
            raise SystemExit('Method not in confirmation freeze')
        for rel, expected_hash in frozen['protocol_hashes'].items():
            if sha_file(r/rel) != expected_hash:
                raise SystemExit('Confirmation protocol/source evidence changed: '+rel)
    elif (r/'state/rescue_v1/confirmation_freeze.json').exists():
        raise SystemExit('Development closed after confirmation freeze')
    folder = r/f'results/rescue_v1/{args.phase}'
    folder.mkdir(parents=True, exist_ok=True)
    state = r/'state/rescue_v1'
    (state/'snapshots').mkdir(parents=True, exist_ok=True)
    tasks, handles, states = [], {}, {}
    for method in args.methods:
        spec = profiles.get(method)
        payload = {'config': cfg, 'profile': spec, 'method': method, 'phase': phase,
                   'runtime_sources': sources, 'environment': env}
        sig = digest(payload)
        fp, meta = folder/f'{method}.jsonl', folder/f'{method}.meta.json'
        seen = set()
        expected = {task_id(phase,c,N,method,i) for c in cases for N in cfg['budgets'] for i in range(reps)}
        if fp.exists():
            if not meta.exists() or json.loads(meta.read_text(encoding='utf-8'))['signature'] != sig:
                raise SystemExit(f'Existing {method} has different code/config/environment; preserve and use its snapshot')
            for line in fp.open(encoding='utf-8'):
                row = json.loads(line)
                if row['task_id'] in seen:
                    raise SystemExit('Duplicate task')
                seen.add(row['task_id'])
            if not seen <= expected:
                raise SystemExit('Unexpected task')
        else:
            snapshot = state/f'snapshots/{sig}.zip'
            with zipfile.ZipFile(snapshot, 'x', compression=zipfile.ZIP_DEFLATED) as z:
                for rel in sources:
                    z.write(r/rel, rel)
                fullcfg = dict(cfg, rescue_profiles={method:spec} if spec else {}, rescue_controls=[method])
                z.writestr('config/rescue_v1.json', json.dumps(fullcfg, indent=2))
            write_json(meta, dict(payload, signature=sig, source_snapshot=str(snapshot.relative_to(r)),
                                 source_snapshot_sha256=sha_file(snapshot),
                                 sealed_utc=datetime.now(timezone.utc).isoformat()))
        states[method] = {'signature':sig, 'expected_tasks':len(expected), 'existing_tasks':len(seen),
                          'new_tasks':0, 'errors':0}
        for c in cases:
            for N in cfg['budgets']:
                for i in range(reps):
                    if task_id(phase,c,N,method,i) not in seen:
                        tasks.append((cfg,phase,c,N,method,i,c['id'] in hb,spec))
        handles[method] = fp
    lock = state/'RUN.lock'
    fd = os.open(lock, os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    os.write(fd, str(os.getpid()).encode()); os.close(fd)
    start, count, errors, peak_rss = time.perf_counter(), 0, 0, 0
    process = psutil.Process()
    print(json.dumps({'phase':phase,'pending':len(tasks),'methods':args.methods,'workers':args.workers}), flush=True)
    try:
        handles = {m:p.open('a', encoding='utf-8', buffering=1) for m,p in handles.items()}
        for row in stream(tasks,args.workers):
            handles[row['method']].write(json.dumps(row, ensure_ascii=False, allow_nan=False)+'\n')
            count += 1
            failed = row['status'] != 'ok'
            errors += failed
            states[row['method']]['new_tasks'] += 1
            states[row['method']]['errors'] += failed
            if count % 1000 == 0:
                rss = process.memory_info().rss
                for child in process.children(recursive=True):
                    try: rss += child.memory_info().rss
                    except psutil.NoSuchProcess: pass
                peak_rss = max(peak_rss, rss)
                print(f'{count}/{len(tasks)} completed; errors={errors}; elapsed={time.perf_counter()-start:.1f}s; rss={rss/2**30:.2f} GiB', flush=True)
                write_json(state/'progress.json', {'phase':phase,'methods':args.methods,'completed_new':count,
                                                  'pending_initial':len(tasks),'errors':errors,'pid':os.getpid()})
    finally:
        for handle in handles.values():
            if hasattr(handle,'close'): handle.close()
        lock.unlink(missing_ok=True)
    elapsed = time.perf_counter()-start
    for m, values in states.items():
        values.update(phase=phase, method=m, group_wall_s=elapsed, workers=args.workers,
                      group_peak_sampled_rss_gib=peak_rss/2**30, raw_sha256=sha_file(folder/f'{m}.jsonl'))
        write_json(folder/f'{m}.receipt.json', values)
    print(json.dumps({'complete':count,'errors':errors,'wall_s':elapsed,'rss_gib':peak_rss/2**30},indent=2),flush=True)
    if errors:
        raise SystemExit(2)


if __name__ == '__main__':
    mp.freeze_support()
    main()

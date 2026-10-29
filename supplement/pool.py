"""Bounded CPU spawn stream, retaining only at most two queued tasks per worker."""
import concurrent.futures as cf
import multiprocessing as mp


def stream(function, tasks, workers):
    if workers == 1:
        yield from map(function, tasks)
        return
    iterator = iter(tasks)
    with cf.ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context('spawn')) as pool:
        pending = set()
        for _ in range(workers * 2):
            try:
                pending.add(pool.submit(function, next(iterator)))
            except StopIteration:
                break
        while pending:
            done, pending = cf.wait(pending, return_when=cf.FIRST_COMPLETED)
            for future in done:
                yield future.result()
                try:
                    pending.add(pool.submit(function, next(iterator)))
                except StopIteration:
                    pass

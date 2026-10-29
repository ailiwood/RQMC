"""Post-study descriptive review of existing tables; no new simulations or tuning."""
from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    assert (root / '.project-root').is_file()
    paths = [root / 'results/analysis/development_summary.csv',
             root / 'results/analysis/development_selection.csv']
    with paths[0].open(newline='', encoding='utf-8') as fh:
        rows = list(csv.DictReader(fh))
    with paths[1].open(newline='', encoding='utf-8') as fh:
        selections = list(csv.DictReader(fh))
    results = []
    aggregates = {}
    for ci, baseline in [('ebci', 'fixed_2'), ('hbci', 'fixed_4')]:
        groups = defaultdict(list)
        for row in rows:
            if row['ci'] == ci and row['method'].startswith('fixed_'):
                groups[(row['case'], int(row['budget']))].append(row)
        ratios = []
        for (case, budget), group in sorted(groups.items()):
            assert len(group) == 7
            assert all(int(r['successful']) == 200 and int(r['failures']) == 0 for r in group)
            best = min(group, key=lambda r: float(r['mean_width']))
            ref = next(r for r in group if r['method'] == baseline)
            adaptive = next(r for r in rows if r['case'] == case and
                            int(r['budget']) == budget and r['ci'] == ci and r['method'] == 'A')
            counts = {r['selected_n']: int(r['count']) for r in selections
                      if r['case'] == case and int(r['budget']) == budget and r['method'] == 'A'}
            assert sum(counts.values()) == 200
            ratio = float(best['mean_width']) / float(ref['mean_width'])
            ratios.append(ratio)
            results.append({
                'case': case, 'budget': budget, 'ci': ci, 'common_fixed': baseline,
                'empirical_best_fixed': best['method'], 'best_vs_common_mean_width': ratio,
                'apparent_width_reduction_before_pilot': 1 - ratio,
                'A_vs_best_fixed_mean_width': float(adaptive['mean_width']) / float(best['mean_width']),
                'A_selection_counts': counts,
                'A_selection_mode': int(max(counts, key=counts.get)),
            })
        aggregates[ci] = {'cells': len(ratios),
                          'geometric_mean_best_vs_common': math.exp(sum(map(math.log, ratios)) / len(ratios))}
    document = {
        'status': 'POST_HOC_DESCRIPTIVE_DIAGNOSTIC_ONLY',
        'new_simulations': 0, 'confirmation_runs': 0,
        'limitations': [
            'Cellwise minima selected from the same 200 development repetitions are optimistic and uncertain.',
            'The comparator pays no pilot; these apparent gaps are not net deployable improvements.',
            'Not a true-variance oracle, not a rigorous bound on attainable performance, not confirmation.',
            'A mode above the empirical width-minimizing n suggests proxy mismatch; it does not establish its sole cause.',
            'The HBCI fixed_4 reference is a secondary diagnostic, not a replacement primary endpoint.',
        ],
        'source_sha256': {str(p.relative_to(root)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in paths},
        'aggregate': aggregates, 'cells': results,
    }
    destination = root / 'handoff/upgrade_headroom_diagnostic.json'
    destination.write_text(json.dumps(document, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'path': str(destination), 'aggregate': aggregates, 'new_simulations': 0}, indent=2))


if __name__ == '__main__':
    main()

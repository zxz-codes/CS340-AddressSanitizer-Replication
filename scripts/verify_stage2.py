#!/usr/bin/env python3
"""Read-only independent semantic and SHA-256 audit of a complete stage-2 batch."""
import argparse
import csv
import gzip
import hashlib
import itertools
import json
import math
from pathlib import Path
import statistics


def verify(record):
    record = Path(record).resolve()
    def read(name):
        return json.loads((record / name).read_text(encoding='utf-8-sig'))
    def require(condition, message):
        if not condition:
            raise AssertionError(message)
    def digest(name):
        p = (record / name).resolve()
        require(p.is_relative_to(record), 'Path outside record: ' + name)
        return hashlib.sha256(p.read_bytes()).hexdigest()
    def stream(name):
        p = record / name
        return gzip.decompress(p.read_bytes()) if p.suffix == '.gz' else p.read_bytes()
    status, protocol, workloads = read('status.json'), read('protocol.json'), read('workloads.json')
    require(status.get('passed') is True and status.get('stage') == 'complete', 'Batch incomplete')
    require(protocol['runs'] == 15 and protocol['warmups'] == 2, 'Unexpected repetition protocol')
    configs = ('native', 'asan-modern', 'asan-paper-like')
    expected_workloads = {n + '-ref' for n in ('bisort', 'mst', 'perimeter', 'treeadd', 'tsp', 'bullet', 'pairlocalalign', 'security-sha')}
    expected_workloads |= {n + '-large' for n in ('bisort', 'mst', 'perimeter', 'tsp')}
    require(set(workloads) == set(protocol['workloads']) == expected_workloads, 'Workload matrix mismatch')
    require(tuple(protocol['configurations']) == configs, 'Configuration matrix mismatch')
    require(protocol['formal_trials'] == status['formal_trials'] == 540, 'Formal count mismatch')
    require(protocol['timeout_seconds'] == 600 and protocol['seed'] == 340, 'Protocol settings mismatch')
    require(protocol['reference_checks'] == {'upstream': 24, 'gcc_differential': 12}, 'Reference provenance mismatch')
    host_review = read('environment/host-sleep-review.json')
    require(host_review['passed'] is True and host_review['events'] == [], 'Host sleep interrupted batch')
    manifest = read('sha256-manifest.json')
    actual_files = {p.relative_to(record).as_posix() for p in record.rglob('*') if p.is_file() and p.name != 'sha256-manifest.json'}
    require(set(manifest) == actual_files, 'Manifest file coverage differs')
    for name, expected in manifest.items():
        require(digest(name) == expected, 'SHA-256 mismatch: ' + name)
    correctness = read('correctness.json')
    errors = {'heap': 'heap-buffer-overflow', 'stack': 'stack-buffer-overflow', 'global': 'global-buffer-overflow',
              'uaf': 'heap-use-after-free', 'double_free': 'attempting double-free'}
    cases = set(errors) | {'control-' + n for n in ('heap', 'stack', 'global', 'fixed')}
    require(len(correctness) == 45 and {(r['case'], r['run']) for r in correctness} == set(itertools.product(cases, range(1, 6))), 'Correctness matrix incomplete or duplicated')
    for row in correctness:
        faulty = row['case'] in errors
        require(row['passed'] is True and not row['timed_out'] and row['returncode'] == (1 if faulty else 0), 'Wrong correctness exit')
        stderr = stream(row['stderr']).decode('utf-8', errors='replace')
        if faulty:
            import re
            require(errors[row['case']] in stderr and bool(re.search(r'memory_cases.c:\d+', stderr)), 'Missing diagnostic/source line')
        else:
            require('ERROR: AddressSanitizer' not in stderr, 'Control sanitizer error')
    measurements = read('measurements.json')
    require(len(measurements) == 648, 'Measurement count (pilot/warmup/formal) mismatch')
    expected_keys = set()
    for phase, indices in [('pilot', [0]), ('warmup', [1, 2]), ('performance', range(1, 16))]:
        expected_keys.update(itertools.product([phase], expected_workloads, configs, indices))
    keys = [(r['phase'], r['workload'], r['configuration'], r['run']) for r in measurements]
    require(len(set(keys)) == len(keys) and set(keys) == expected_keys, 'Missing, duplicated or mispaired measurement')
    require(len({r['stdout'] for r in measurements}) == len(measurements), 'Trial output paths reused')
    formal = [r for r in measurements if r['phase'] == 'performance']
    schedule = read('schedule.json')
    require(schedule == [{k: r[k] for k in ('workload', 'configuration', 'run')} for r in formal], 'Recorded order differs from frozen schedule')
    import random
    rng = random.Random(protocol['seed'])
    expected_schedule = []
    for index in range(1, 16):
        names = list(protocol['workloads'])
        rng.shuffle(names)
        for name in names:
            order = list(configs)
            rng.shuffle(order)
            expected_schedule.extend({'workload': name, 'configuration': c, 'run': index} for c in order)
    require(schedule == expected_schedule, 'Randomization schedule differs from protocol')
    for row in measurements:
        config, workload = row['configuration'], row['workload']
        require(row['returncode'] == 0 and row['timed_out'] is False, 'Failed measurement')
        require(math.isfinite(row['elapsed_seconds']) and row['elapsed_seconds'] > 0 and row['max_rss_kib'] > 0, 'Invalid metrics')
        require(row['argv'][-1] == workloads[workload]['commands'][config], 'Wrong workload command')
        expected_options = '' if config == 'native' else protocol['lock']['asan_default_options' if config == 'asan-modern' else 'asan_paper_like_options']
        require(row['asan_options'] == expected_options, 'ASan options mismatch')
        stdout, stderr = stream(row['stdout']), stream(row['stderr'])
        require(len(stdout) == row['stdout_raw_bytes'] and len(stderr) == row['stderr_raw_bytes'], 'Raw stream byte count mismatch')
        require(hashlib.sha256(stdout).hexdigest() == row['stdout_sha256'] == workloads[workload]['reference_stdout_sha256'], 'Output hash mismatch')
        require(b'ERROR: AddressSanitizer' not in stderr, 'Sanitizer diagnostic in performance trial')
        metrics = dict(line.split('=', 1) for line in (record / row['time_log']).read_text(encoding='utf-8').splitlines())
        for field in ('wall_seconds', 'user_seconds', 'system_seconds', 'max_rss_kib'):
            require(float(metrics[field]) == row[field], 'Raw GNU time metric mismatch')
    with (record / 'measurements.csv').open(encoding='utf-8', newline='') as csv_stream:
        csv_rows = list(csv.DictReader(csv_stream))
    require(len(csv_rows) == len(measurements), 'CSV row count mismatch')
    for a, b in zip(csv_rows, measurements):
        require(set(a) == set(b) and all(a[k] == str(b[k]) for k in a), 'CSV/JSON mismatch')
    summary = read('summary.json')
    require(len(summary) == 36 and {(s['workload'], s['configuration']) for s in summary} == set(itertools.product(expected_workloads, configs)), 'Summary matrix mismatch')
    for item in summary:
        group = [r for r in formal if r['workload'] == item['workload'] and r['configuration'] == item['configuration']]
        values_by_key = {m: [r[m] for r in group] for m in ('elapsed_seconds', 'max_rss_kib')}
        if item['configuration'] != 'native':
            baseline = {r['run']: r for r in formal if r['workload'] == item['workload'] and r['configuration'] == 'native'}
            for metric, key in [('elapsed_seconds', 'paired_time_ratio'), ('max_rss_kib', 'paired_rss_ratio')]:
                values_by_key[key] = [r[metric] / baseline[r['run']][metric] for r in group]
        for key, values in values_by_key.items():
            expected = {'mean': statistics.mean(values), 'sd': statistics.stdev(values), 'n': 15}
            require(set(item[key]) == set(expected), 'Statistic fields mismatch')
            for field, value in expected.items():
                require(math.isclose(item[key][field], value, rel_tol=1e-12, abs_tol=1e-12), 'Statistic mismatch: ' + key + '/' + field)
    for workload in expected_workloads:
        item = workloads[workload]
        require(item['reference_kind'] == ('gcc-differential' if workload.endswith('-large') else 'upstream'), 'Reference kind mismatch')
        if workload.endswith('-large'):
            require(hashlib.sha256(stream(item['oracle']['stdout'])).hexdigest() == item['reference_stdout_sha256'], 'Oracle output differs')
        for config in configs:
            ref = read(f'reference/{workload}-{config}.json')
            require(len(ref['tests']) == 1 and ref['tests'][0]['code'] == 'PASS', 'Upstream reference failed')
    return {'passed': True, 'record': str(record), 'verified_file_hashes': len(manifest),
            'correctness_trials': 45, 'reference_checks': 36, 'upstream_reference_checks': 24,
            'gcc_differential_checks': 12, 'pilot_trials': 36, 'warmup_trials': 72,
            'performance_trials': 540, 'statistics_recomputed': True, 'csv_matches_json': True,
            'schedule_verified': True, 'stdout_hashes_recomputed': True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('record', nargs='?', type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    record = args.record or root / (root / 'records/latest-stage2.txt').read_text(encoding='utf-8').strip()
    print(json.dumps(verify(record), indent=2))

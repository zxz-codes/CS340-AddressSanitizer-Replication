#!/usr/bin/env python3
"""Reproducible stage-one ASan experiment. Python standard library only."""
import argparse
import csv
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import random
import re
import shlex
import shutil
import statistics
import subprocess
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
LOCK = json.loads((ROOT / 'config/environment-lock.json').read_text(encoding='utf-8-sig'))
WORK = Path(os.environ.get('CS340_ASAN_WORKDIR', Path.home() / '.cache/cs340-asan'))
SOURCE = WORK / 'llvm-test-suite'

def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    llvm_bin = subprocess.check_output(['llvm-config-14', '--bindir'], text=True).strip()
    os.environ['PATH'] = llvm_bin + os.pathsep + os.environ.get('PATH', '')
    parser = argparse.ArgumentParser()
    parser.add_argument('--runs', type=int, default=LOCK['runs'])
    args = parser.parse_args()
    if args.runs < 3:
        parser.error('At least three independent runs are required.')
    run_id = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:6]
    out = ROOT / 'records/stage1' / run_id
    out.mkdir(parents=True)
    commands = []
    def command(cmd, name, cwd=ROOT, env=None, check=True, timeout=300):
        log = out / (name + '.log')
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open('w', encoding='utf-8') as stream:
            stream.write('$ ' + shlex.join(map(str, cmd)).replace('\n', r'\n') + '\n')
            stream.flush()
            started = time.perf_counter()
            try:
                p = subprocess.run(list(map(str, cmd)), cwd=cwd, env=env, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, timeout=timeout, text=True)
                code = p.returncode
            except subprocess.TimeoutExpired:
                code = 124
                stream.write('\nTIMEOUT\n')
            elapsed = time.perf_counter() - started
            if code != 124:
                stream.write(p.stdout)
        row = {'argv': list(map(str, cmd)), 'cwd': str(cwd), 'returncode': code,
               'elapsed_seconds': elapsed, 'log': str(log.relative_to(out))}
        commands.append(row)
        dump(out / 'commands.json', commands)
        if check and code:
            raise RuntimeError(f'Command failed ({code}): {name}; inspect {log}')
        return code, log

    print(f'Stage 1 record directory: {out}', flush=True)
    dump(out / 'protocol.json', {**LOCK, 'runs': args.runs, 'started_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
          'timer': 'Python perf_counter around taskset + GNU time + process; includes launch/exit',
          'rss': 'GNU time %M, maximum resident set size in KiB; not paper VmPeak',
          'order': 'seed 340; shuffle each block; one warm-up per program/configuration'})
    for sub in ('scripts', 'examples', 'config'):
        for file in (ROOT / sub).iterdir():
            if file.is_file():
                target = out / 'source-snapshot' / sub / file.name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file, target)
    actual = subprocess.check_output(['git', '-C', str(SOURCE), 'rev-parse', 'HEAD'], text=True).strip()
    if actual != LOCK['benchmark_commit']:
        raise RuntimeError('Benchmark commit does not match the lock.')
    command(['git', '-C', SOURCE, 'diff', '--exit-code'], 'environment/upstream-diff')
    for name, cmd in {
        'kernel': ['uname', '-a'], 'distribution': ['cat', '/etc/os-release'],
        'cpu': ['lscpu'], 'memory': ['free', '-h'], 'disk': ['df', '-h', str(WORK)],
        'compiler': ['clang-14', '--version'], 'symbolizer': ['llvm-symbolizer-14', '--version'],
        'cmake': ['cmake', '--version'], 'ninja': ['ninja', '--version'],
        'python': ['python3', '--version'], 'packages': ['dpkg-query', '-W'],
        'lit': [WORK / 'venv/bin/lit', '--version'], 'load': ['cat', '/proc/loadavg'],
        'runtime-files': ['bash', '-c', 'find "$(clang-14 -print-resource-dir)" -name "*asan*x86_64*"'],
    }.items():
        command(cmd, 'environment/' + name)
    cpu = min(os.sched_getaffinity(0))
    dump(out / 'environment/cpu-affinity.json', {'chosen_linux_logical_cpu': cpu,
         'allowed': sorted(os.sched_getaffinity(0)),
         'note': 'WSL virtual CPU mapping to Windows P/E cores is not controlled.'})
    base_env = os.environ.copy()
    for key in ('ASAN_OPTIONS', 'LSAN_OPTIONS', 'UBSAN_OPTIONS'):
        base_env.pop(key, None)
    base_env.update({'LC_ALL': 'C', 'TZ': 'UTC', 'OMP_NUM_THREADS': '1',
                     'ASAN_SYMBOLIZER_PATH': shutil.which('llvm-symbolizer-14')})
    modern = LOCK['asan_default_options']
    paper = LOCK['asan_paper_like_options']
    env_for = lambda opts: {**base_env, 'ASAN_OPTIONS': opts}
    buildroot = WORK / 'build' / run_id
    buildroot.mkdir(parents=True)
    demo = buildroot / 'memory_cases'
    command(['clang-14', '-O1', '-g', '-fno-omit-frame-pointer', '-fno-pie', '-no-pie',
             '-fsanitize=address', ROOT / 'examples/memory_cases.c', '-o', demo], 'correctness/build')
    cases = {'heap': 'heap-buffer-overflow', 'stack': 'stack-buffer-overflow',
             'global': 'global-buffer-overflow', 'uaf': 'heap-use-after-free',
             'double_free': 'attempting double-free'}
    correctness = []
    for name, expected in cases.items():
        for i in range(1, args.runs + 1):
            code, log = command(['taskset', '-c', str(cpu), demo, name, '8' if name in ('heap','stack','global') else '0'],
                 f'correctness/{name}-{i:02d}', env=env_for(modern), check=False, timeout=10)
            text = log.read_text()
            passed = code != 0 and code != 124 and expected in text and bool(re.search(r'memory_cases.c:\d+', text))
            correctness.append({'case': name, 'run': i, 'expected': expected, 'returncode': code,
                                'passed': passed, 'log': str(log.relative_to(out))})
    for name, index in [('heap', '7'), ('stack', '7'), ('global', '7'), ('fixed', '8')]:
        for i in range(1, args.runs + 1):
            code, log = command(['taskset', '-c', str(cpu), demo, name, index],
                 f'correctness/control-{name}-{i:02d}', env=env_for(modern), check=False, timeout=10)
            text = log.read_text()
            correctness.append({'case': 'control-' + name, 'run': i, 'expected': 'clean exit',
                                'returncode': code, 'passed': code == 0 and 'ERROR: AddressSanitizer' not in text,
                                'log': str(log.relative_to(out))})
    dump(out / 'correctness.json', correctness)
    if not all(x['passed'] for x in correctness):
        raise RuntimeError('One or more correctness or symbolization checks failed.')
    print('Correctness and negative controls passed.', flush=True)

    builds = {}
    for variant in ('native', 'asan'):
        build = buildroot / variant
        flags = LOCK['common_cflags'] + (' ' + LOCK['asan_cflags'] if variant == 'asan' else '')
        linker = LOCK['common_ldflags'] + (' -fsanitize=address' if variant == 'asan' else '')
        command(['cmake', '-G', 'Ninja', '-S', SOURCE, '-B', build,
             '-DCMAKE_C_COMPILER=clang-14', '-DCMAKE_CXX_COMPILER=clang++-14',
             '-DCMAKE_BUILD_TYPE=Release', '-DCMAKE_C_FLAGS_RELEASE=' + flags,
             '-DCMAKE_CXX_FLAGS_RELEASE=' + flags, '-DCMAKE_EXE_LINKER_FLAGS=' + linker,
             '-DTEST_SUITE_SUBDIRS=' + LOCK['benchmark_subdirectory'],
             '-DTEST_SUITE_RUN_TYPE=ref', '-DTEST_SUITE_BENCHMARKING_ONLY=ON'], f'build/{variant}-configure')
        command(['cmake', '--build', build, '-j', '2'], f'build/{variant}-compile', timeout=600)
        builds[variant] = build
        # Direct subtree configuration omits parent MultiSource lit.local.cfg.
        # Restore its traditional output contract in the generated build tree.
        local_cfg = build / LOCK['benchmark_subdirectory'] / 'lit.local.cfg'
        local_cfg.write_text('config.traditional_output = True\n')
        shutil.copy2(local_cfg, out / 'build' / (variant + '-lit.local.cfg'))
        shutil.copy2(build / 'CMakeCache.txt', out / 'build' / (variant + '-CMakeCache.txt'))
        pattern = '/(' + '|'.join(LOCK['planned_benchmarks']) + ')/'
        command([WORK / 'venv/bin/lit', '-v', '-j', '1', '--filter', pattern,
                 '-o', out / 'build' / (variant + '-lit.json'), build],
                 f'build/{variant}-reference-validation', env=env_for(paper), timeout=600)

    # Generated .test files are the authority for executable arguments and cwd.
    workloads = {}
    for name in LOCK['planned_benchmarks']:
        folder = builds['native'] / LOCK['benchmark_subdirectory'] / name
        tests = list(folder.glob('*.test'))
        if len(tests) != 1:
            raise RuntimeError(f'Expected one .test for {name}, got {tests}')
        test_text = tests[0].read_text()
        dump(out / 'workloads' / (name + '.json'), {'native_test': test_text})
        run_line = next(line for line in test_text.splitlines() if line.startswith('RUN:'))
        # LLVM 14 generated tests use traditional output: RUN: cd %S ; %S/name args.
        tail = run_line.split(';', 1)[1].strip()
        if tail.startswith('%run '):
            tail = tail[len('%run '):]
        tokens = shlex.split(tail)
        binary_token = tokens.pop(0)
        parameters = []
        for token in tokens:
            if token in ('>', '1>', '2>', '<', '&&', ';'):
                break
            parameters.append(token.replace('%S', str(folder)))
        binary_name = Path(binary_token.replace('%S', str(folder))).name
        workloads[name] = {'binary_name': binary_name, 'args': parameters}
    dump(out / 'workloads.json', workloads)

    rows = []
    def measure(name, config, index, phase):
        variant = 'native' if config == 'native' else 'asan'
        folder = builds[variant] / LOCK['benchmark_subdirectory'] / name
        binary = folder / workloads[name]['binary_name']
        opts = modern if config == 'asan-modern' else paper
        if config.startswith('redzone-'):
            rz = int(config.split('-')[-1])
            opts = modern + f':redzone={rz}:max_redzone=2048:quarantine_size_mb=0:thread_local_quarantine_size_kb=0:malloc_context_size=0'
        label = f'{phase}/{name}/{config}-{index:02d}'
        metrics_record = out / (label + '.time')
        metrics = buildroot / 'timing' / (label + '.time')
        metrics.parent.mkdir(parents=True, exist_ok=True)
        cmd = ['taskset', '-c', str(cpu), '/usr/bin/time', '-f',
               'wall_seconds=%e\nuser_seconds=%U\nsystem_seconds=%S\nmax_rss_kib=%M',
               '-o', metrics, binary] + workloads[name]['args']
        code, log = command(cmd, label, cwd=folder, env=env_for(opts), check=False, timeout=120)
        shutil.copy2(metrics, metrics_record)
        data = {}
        for line in metrics.read_text().splitlines():
            if '=' in line:
                k, v = line.split('=', 1)
                data[k] = float(v)
        logtext = log.read_text()
        # Ignore command header when comparing the complete stdout checksum.
        stdout = logtext.split('\n', 1)[1]
        reference_hash = hashlib.sha256(stdout.encode()).hexdigest()
        row = {'phase': phase, 'benchmark': name, 'configuration': config, 'run': index,
               'returncode': code, 'elapsed_seconds': commands[-1]['elapsed_seconds'],
               **data, 'stdout_sha256': reference_hash, 'asan_options': opts if variant == 'asan' else '',
               'log': str(log.relative_to(out)), 'time_log': str(metrics_record.relative_to(out))}
        rows.append(row)
        dump(out / 'measurements.json', rows)
        if code or 'ERROR: AddressSanitizer' in stdout:
            raise RuntimeError(f'Benchmark failed: {label}')
        return row

    configs = ['native', 'asan-modern', 'asan-paper-like']
    for name in workloads:
        for config in configs:
            measure(name, config, 0, 'warmup')
    rng = random.Random(340)
    for i in range(1, args.runs + 1):
        names = list(workloads)
        rng.shuffle(names)
        for name in names:
            order = configs[:]
            rng.shuffle(order)
            for config in order:
                row = measure(name, config, i, 'performance')
                print(f'{i}/{args.runs} {name} {config}: {row["elapsed_seconds"]:.4f}s', flush=True)
    for name in ('bisort', 'mst'):
        for config in ('redzone-16', 'redzone-32', 'redzone-128'):
            measure(name, config, 0, 'extension-warmup')
        for i in range(1, args.runs + 1):
            order = ['redzone-16', 'redzone-32', 'redzone-128']
            rng.shuffle(order)
            for config in order:
                measure(name, config, i, 'extension')

    for name in workloads:
        hashes = {r['stdout_sha256'] for r in rows if r['benchmark'] == name}
        if len(hashes) != 1:
            raise RuntimeError(f'Output changed across configurations or repetitions: {name}')
    sizes = []
    for name in workloads:
        for variant in builds:
            binary = builds[variant] / LOCK['benchmark_subdirectory'] / name / workloads[name]['binary_name']
            stripped = binary.with_name(binary.name + '.nodebug')
            command(['llvm-strip-14', '--strip-debug', '-o', stripped, binary], f'sizes/{name}-{variant}-strip')
            command(['llvm-size-14', binary], f'sizes/{name}-{variant}-sections')
            sizes.append({'benchmark': name, 'variant': variant, 'binary_bytes': binary.stat().st_size,
                          'without_debug_bytes': stripped.stat().st_size, 'sha256': digest(binary)})
    dump(out / 'binary-sizes.json', sizes)
    def stats(values):
        return {'mean': statistics.mean(values), 'sd': statistics.stdev(values), 'n': len(values)}
    summary = []
    for phase in ('performance', 'extension'):
        keys = sorted({(r['benchmark'], r['configuration']) for r in rows if r['phase'] == phase})
        for name, config in keys:
            group = [r for r in rows if r['phase'] == phase and r['benchmark'] == name and r['configuration'] == config]
            item = {'phase': phase, 'benchmark': name, 'configuration': config,
                    'elapsed_seconds': stats([r['elapsed_seconds'] for r in group]),
                    'max_rss_kib': stats([r['max_rss_kib'] for r in group])}
            if phase == 'performance' and config != 'native':
                baseline = {r['run']: r for r in rows if r['phase'] == phase and r['benchmark'] == name and r['configuration'] == 'native'}
                item['paired_time_ratio'] = stats([r['elapsed_seconds'] / baseline[r['run']]['elapsed_seconds'] for r in group])
                item['paired_rss_ratio'] = stats([r['max_rss_kib'] / baseline[r['run']]['max_rss_kib'] for r in group])
            summary.append(item)
    dump(out / 'summary.json', summary)
    fields = sorted(set().union(*(r.keys() for r in rows)))
    with (out / 'measurements.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fields)
        writer.writeheader()
        writer.writerows(rows)
    command(['cat', '/proc/loadavg'], 'environment/final-load')
    manifest = {str(p.relative_to(out)): digest(p) for p in out.rglob('*') if p.is_file()}
    dump(out / 'sha256-manifest.json', manifest)
    dump(out / 'status.json', {'passed': True, 'correctness_trials': len(correctness),
          'performance_trials': sum(r['phase'] == 'performance' for r in rows),
          'extension_trials': sum(r['phase'] == 'extension' for r in rows),
          'ended_utc': dt.datetime.now(dt.timezone.utc).isoformat()})
    (ROOT / 'records/latest-stage1.txt').write_text(str(out.relative_to(ROOT)) + '\n')
    print('STAGE 1 PASSED: ' + str(out), flush=True)

if __name__ == '__main__':
    main()

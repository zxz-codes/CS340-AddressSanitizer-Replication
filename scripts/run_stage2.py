#!/usr/bin/env python3
"""Stage 2: separate raw streams, upstream lit checks, frozen fixed-work matrix."""
import argparse
import csv
import datetime as dt
import gzip
import hashlib
import json
import os
from pathlib import Path
import random
import re
import shlex
import shutil
import signal
import statistics
import subprocess
import threading
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
WORK = Path(os.environ.get('CS340_ASAN_WORKDIR', Path.home() / '.cache/cs340-asan'))
SOURCE = WORK / 'llvm-test-suite'
CONFIGS = ('native', 'asan-modern', 'asan-paper-like')


def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stream_bytes(path):
    return gzip.decompress(path.read_bytes()) if path.suffix == '.gz' else path.read_bytes()


def stream_sha(path):
    return hashlib.sha256(stream_bytes(path)).hexdigest()


def stats(values):
    return {'mean': statistics.mean(values), 'sd': statistics.stdev(values), 'n': len(values)}


def summarize(rows):
    result = []
    for workload, config in sorted({(r['workload'], r['configuration']) for r in rows}):
        group = [r for r in rows if (r['workload'], r['configuration']) == (workload, config)]
        item = {'workload': workload, 'configuration': config}
        for metric in ('elapsed_seconds', 'max_rss_kib'):
            item[metric] = stats([r[metric] for r in group])
        if config != 'native':
            base = {r['run']: r for r in rows if r['workload'] == workload and r['configuration'] == 'native'}
            for metric, key in [('elapsed_seconds', 'paired_time_ratio'), ('max_rss_kib', 'paired_rss_ratio')]:
                item[key] = stats([r[metric] / base[r['run']][metric] for r in group])
        result.append(item)
    return result


def finalize_record(record):
    """Finalize metadata only after host review; never change any measured sample."""
    record = Path(record).resolve()
    if not record.is_relative_to((ROOT / 'records/stage2').resolve()):
        raise ValueError('Record must be inside this repository records/stage2')
    prior = json.loads((record / 'status.json').read_text(encoding='utf-8'))
    permitted = prior.get('stage') == 'awaiting-host-review' or (
        prior.get('stage') == 'failed' and 'environment/host-sleep-query' in prior.get('error', ''))
    if not permitted or prior.get('excluded_from_results'):
        raise ValueError('Only fully measured batches awaiting host review can be finalized')
    previous_manifest = json.loads((record / 'sha256-manifest.json').read_text(encoding='utf-8'))
    for name, expected in previous_manifest.items():
        p = (record / name).resolve()
        if not p.is_relative_to(record) or sha(p) != expected:
            raise ValueError('Prior record changed: ' + name)
    review = json.loads((record / 'environment/host-sleep-review.json').read_text(encoding='utf-8-sig'))
    if review.get('passed') is not True or review.get('events') != []:
        raise ValueError('Host review failed; batch cannot be accepted')
    dump(record / 'environment/pre-host-review-status.json', prior)
    dump(record / 'environment/pre-host-review-manifest.json', previous_manifest)
    dump(record / 'status.json', {'passed': True, 'stage': 'complete', 'formal_trials': 540,
         'correctness_trials': 45, 'ended_utc': prior['ended_utc'],
         'finalized_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
         'finalization': 'Host review only; all original sample files and protocol retained byte-for-byte'})
    def seal():
        dump(record / 'sha256-manifest.json', {p.relative_to(record).as_posix(): sha(p)
             for p in sorted(record.rglob('*')) if p.is_file() and p.name != 'sha256-manifest.json'})
    seal()
    try:
        from verify_stage2 import verify
        result = verify(record)
    except BaseException as error:
        dump(record / 'status.json', {'passed': False, 'stage': 'failed', 'error': repr(error), 'formal_trials_saved': 540})
        seal()
        raise
    (ROOT / 'records/latest-stage2.txt').write_text(record.relative_to(ROOT).as_posix() + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
    print('STAGE 2 PASSED: ' + str(record), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--precheck-only', action='store_true')
    parser.add_argument('--verify', type=Path, help='Verify a saved record without running experiments')
    parser.add_argument('--defer-host-review', action='store_true', help='Windows wrapper supplies host review before finalization')
    parser.add_argument('--finalize-record', type=Path, help='Finalize an already measured batch after host review; no measurements rerun')
    args = parser.parse_args()
    if args.verify:
        from verify_stage2 import verify
        print(json.dumps(verify(args.verify), indent=2))
        return
    if args.finalize_record:
        finalize_record(args.finalize_record)
        return
    if Path('/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe').exists() and not (args.defer_host_review or args.precheck_only):
        parser.error('On WSL run scripts/Run-Stage2.ps1 to keep awake and review host sleep events in Windows')
    lock = json.loads((ROOT / 'config/environment-lock.json').read_text(encoding='utf-8-sig'))
    cfg = json.loads((ROOT / 'config/stage2.json').read_text(encoding='utf-8-sig'))
    ident = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:6]
    out = ROOT / 'records/stage2' / ident
    out.mkdir(parents=True)
    print('STAGE 2 RECORD: ' + str(out), flush=True)
    commands, measurements = [], []
    started_utc = dt.datetime.now(dt.timezone.utc).isoformat()
    base = os.environ.copy()
    for k in ('ASAN_OPTIONS', 'LSAN_OPTIONS', 'UBSAN_OPTIONS', 'TSAN_OPTIONS'):
        base.pop(k, None)
    llvm_bin = subprocess.check_output(['llvm-config-14', '--bindir'], text=True).strip()
    base.update(PATH=llvm_bin + os.pathsep + base.get('PATH', ''), LC_ALL='C', TZ='UTC',
                OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
                ASAN_SYMBOLIZER_PATH=llvm_bin + '/llvm-symbolizer')
    def env(config):
        options = '' if config == 'native' else lock['asan_default_options' if config == 'asan-modern' else 'asan_paper_like_options']
        return {**base, 'ASAN_OPTIONS': options}

    def run(argv, label, cwd=ROOT, environment=None, timeout=600, expected=0):
        (out / label).parent.mkdir(parents=True, exist_ok=True)
        prefix = WORK / 'stage2-capture' / ident / label
        prefix.parent.mkdir(parents=True, exist_ok=True)
        stdout_path, stderr_path = Path(str(prefix) + '.stdout'), Path(str(prefix) + '.stderr')
        with stdout_path.open('wb') as stdout, stderr_path.open('wb') as stderr:
            start = time.perf_counter()
            proc = subprocess.Popen([str(x) for x in argv], cwd=cwd, env=environment or base,
                                    stdout=stdout, stderr=stderr, start_new_session=True)
            timed_out = False
            def expire():
                nonlocal timed_out
                if proc.poll() is None:
                    timed_out = True
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
            watchdog = threading.Timer(timeout, expire)
            watchdog.daemon = True
            watchdog.start()
            code = proc.wait()
            elapsed = time.perf_counter() - start
            watchdog.cancel()
            if timed_out:
                code = 124
        stdout_saved, stderr_saved = out / (label + '.stdout.gz'), out / (label + '.stderr.gz')
        stdout_saved.parent.mkdir(parents=True, exist_ok=True)
        # Lossless packaging is outside the measured interval. No Windows output I/O is timed.
        stdout_raw, stderr_raw = stdout_path.read_bytes(), stderr_path.read_bytes()
        stdout_saved.write_bytes(gzip.compress(stdout_raw, compresslevel=6, mtime=0))
        stderr_saved.write_bytes(gzip.compress(stderr_raw, compresslevel=6, mtime=0))
        stdout_path.unlink()
        stderr_path.unlink()
        row = {'argv': list(map(str, argv)), 'cwd': str(cwd), 'returncode': code,
               'elapsed_seconds': elapsed, 'timed_out': timed_out,
               'stdout_raw_bytes': len(stdout_raw), 'stderr_raw_bytes': len(stderr_raw),
               'stdout': stdout_saved.relative_to(out).as_posix(),
               'stderr': stderr_saved.relative_to(out).as_posix()}
        commands.append(row)
        dump(out / 'commands.json', commands)
        if timed_out or (expected is not None and code != expected):
            raise RuntimeError(f'{label}: returncode={code}, timeout={timed_out}; inspect raw streams')
        return row

    def manifest():
        dump(out / 'sha256-manifest.json', {p.relative_to(out).as_posix(): sha(p)
             for p in sorted(out.rglob('*')) if p.is_file() and p.name != 'sha256-manifest.json'})

    try:
        dump(out / 'status.json', {'passed': False, 'stage': 'precheck', 'started_utc': started_utc})
        assert subprocess.check_output(['git', '-C', str(SOURCE), 'rev-parse', 'HEAD'], text=True).strip() == lock['benchmark_commit']
        run(['git', '-C', SOURCE, 'diff', '--exit-code'], 'environment/upstream-before')
        # Preserve the existing root/Olden selection, add only the approved subtrees.
        patterns = ['/*', '!/SingleSource/', '!/External/', '!/MicroBenchmarks/', '!/Fortran/',
                    '!/MultiSource/*', '/MultiSource/CMakeLists.txt', '/MultiSource/Benchmarks/CMakeLists.txt',
                    '/MultiSource/Benchmarks/Olden/']
        patterns += ['/' + x + '/' for x in cfg['new_subdirectories']]
        run(['git', '-C', SOURCE, 'sparse-checkout', 'set', '--no-cone', *patterns], 'environment/sparse-checkout')
        cpu = min(os.sched_getaffinity(0))
        dump(out / 'environment/affinity.json', {'cpu': cpu, 'allowed': sorted(os.sched_getaffinity(0)),
             'limitation': 'WSL virtual CPU to host P/E core mapping is uncontrolled.'})
        for name, argv in {
            'kernel': ['uname', '-a'], 'os': ['cat', '/etc/os-release'], 'cpu': ['lscpu'],
            'memory-before': ['free', '-h'], 'load-before': ['cat', '/proc/loadavg'],
            'disk': ['df', '-h', str(WORK)], 'compiler': ['clang-14', '--version'],
            'packages': ['dpkg-query', '-W'], 'cmake': ['cmake', '--version'],
            'lit': [WORK / 'venv/bin/lit', '--version'],
        }.items():
            run(argv, 'environment/' + name)
        power = ROOT / 'config/stage2-host-power.json'
        if power.exists():
            shutil.copyfile(power, out / 'environment/host-power.json')
        for folder in ('scripts', 'config', 'examples'):
            for file in (ROOT / folder).iterdir():
                if file.is_file():
                    target = out / 'source-snapshot' / folder / file.name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(file, target)

        buildroot = WORK / 'build/stage2'
        builds = {}
        names_by_size = {'ref': cfg['reference_names'], 'large': cfg['large_names']}
        for size in names_by_size:
            for variant in (('native', 'asan', 'oracle') if size == 'large' else ('native', 'asan')):
                build = buildroot / (size + '-' + variant)
                build.mkdir(parents=True, exist_ok=True)
                subs = ['MultiSource/Benchmarks/Olden'] + (cfg['new_subdirectories'] if size == 'ref' else [])
                flags = lock['common_cflags'] + (' ' + lock['asan_cflags'] if variant == 'asan' else '')
                ldflags = lock['common_ldflags'] + (' -fsanitize=address' if variant == 'asan' else '')
                run(['cmake', '-G', 'Ninja', '-S', SOURCE, '-B', build,
                     '-DCMAKE_C_COMPILER=' + ('gcc' if variant == 'oracle' else 'clang-14'),
                     '-DCMAKE_CXX_COMPILER=' + ('g++' if variant == 'oracle' else 'clang++-14'),
                     '-DCMAKE_BUILD_TYPE=Release', '-DCMAKE_C_FLAGS_RELEASE=' + flags,
                     '-DCMAKE_CXX_FLAGS_RELEASE=' + flags, '-DCMAKE_EXE_LINKER_FLAGS=' + ldflags,
                     '-DTEST_SUITE_SUBDIRS=' + ';'.join(subs), '-DTEST_SUITE_RUN_TYPE=ref',
                     '-DTEST_SUITE_BENCHMARKING_ONLY=ON', '-DLARGE_PROBLEM_SIZE=' + ('ON' if size == 'large' else 'OFF')],
                     f'build/{size}-{variant}-configure')
                run(['cmake', '--build', build, '-j', '2'], f'build/{size}-{variant}-compile', timeout=1800)
                # Restore the omitted MultiSource parent contract in generated trees only.
                for sub in subs:
                    (build / sub / 'lit.local.cfg').write_text('config.traditional_output = True\n', encoding='utf-8')
                shutil.copyfile(build / 'CMakeCache.txt', out / 'build' / f'{size}-{variant}-CMakeCache.txt')
                builds[size, variant] = build

        workloads = {}
        for size, names in names_by_size.items():
            for name in names:
                files = list(builds[size, 'native'].rglob(name + '.test'))
                assert len(files) == 1, (name, files)
                test = files[0]
                relative = test.relative_to(builds[size, 'native'])
                original = test.read_text(encoding='utf-8')
                # All shell operators, including stdin redirection, remain intact.
                runlines = [line[4:].strip() for line in original.splitlines() if line.startswith('RUN:')]
                assert len(runlines) == 1, (test, runlines)
                assert not re.search(r'%(?!S\b)', runlines[0]), ('Unsupported lit substitution', runlines)
                ident_w = name + '-' + size
                dump(out / 'generated-tests' / (ident_w + '.json'), {'relative_path': relative.as_posix(), 'contents': original})
                item = {'name': name, 'size': size, 'test_relative': relative.as_posix(), 'run_template': runlines[0],
                        'commands': {}, 'binary_sha256': {}, 'reference_stdout_sha256': None}
                item['reference_kind'] = 'upstream' if size == 'ref' else 'gcc-differential'
                if size == 'large':
                    oracle_folder = (builds[size, 'oracle'] / relative).parent
                    oracle_shell = runlines[0].replace('%S', shlex.quote(str(oracle_folder)))
                    oracle = run(['taskset', '-c', str(cpu), 'bash', '-c', oracle_shell],
                                 f'oracle/{ident_w}', environment=env('native'))
                    # Generated expected output is separate from the unchanged upstream reference.
                    oracle_bytes = stream_bytes(out / oracle['stdout'])
                    assert not stream_bytes(out / oracle['stderr']), 'Oracle emitted unexpected stderr'
                    item['reference_stdout_sha256'] = stream_sha(out / oracle['stdout'])
                    item['oracle'] = oracle
                    item['oracle_binary_sha256'] = sha(oracle_folder / name)
                    item['upstream_reference_sha256'] = sha(SOURCE / relative.parent / (name + '.reference_output'))
                for config in CONFIGS:
                    build = builds[size, 'native' if config == 'native' else 'asan']
                    asan_test = build / relative
                    # modern and paper-like share the same ASan build tree.
                    generated_original = asan_test.read_text(encoding='utf-8')
                    modified = original.replace(name + '.reference_output', name + '.stage2-reference_output')
                    assert generated_original in (original, modified)
                    folder = asan_test.parent
                    if size == 'large':
                        (folder / (name + '.stage2-reference_output')).write_bytes(oracle_bytes + b'exit 0\n')
                        asan_test.write_text(modified, encoding='utf-8')
                    shell = runlines[0].replace('%S', shlex.quote(str(folder)))
                    item['commands'][config] = shell
                    item['binary_sha256'][config] = sha(folder / name)
                    # lit applies original VERIFY directives, including output hashing/fpcmp.
                    result_file = out / 'reference' / f'{ident_w}-{config}.json'
                    run([WORK / 'venv/bin/lit', '-v', '-j', '1',
                         '-o', result_file, asan_test], f'reference/{ident_w}-{config}', cwd=build,
                        environment=env(config), timeout=cfg['timeout_seconds'])
                    reference = json.loads(result_file.read_text(encoding='utf-8'))
                    assert len(reference['tests']) == 1 and reference['tests'][0]['code'] == 'PASS', ident_w
                if size == 'large':
                    actual_args = shlex.split(runlines[0].split(';', 1)[1])[1:]
                    assert actual_args == cfg['large_arguments'][name], (name, actual_args)
                workloads[ident_w] = item
        tracked_files = subprocess.check_output(['git', '-C', str(SOURCE), 'ls-files', '-z'], text=False).split(b'\0')
        source_hashes = {}
        for raw in tracked_files:
            if raw:
                name = raw.decode('utf-8')
                p = SOURCE / name
                if p.is_file():
                    source_hashes[name] = sha(p)
        dump(out / 'environment/upstream-source-hashes.json', source_hashes)
        run(['git', '-C', SOURCE, 'diff', '--exit-code'], 'environment/upstream-after-build')

        demo = buildroot / 'memory_cases'
        run(['clang-14', '-O1', '-g', '-fno-omit-frame-pointer', '-fno-pie', '-no-pie',
             '-fsanitize=address', ROOT / 'examples/memory_cases.c', '-o', demo], 'correctness/build')
        cases = {'heap': 'heap-buffer-overflow', 'stack': 'stack-buffer-overflow', 'global': 'global-buffer-overflow',
                 'uaf': 'heap-use-after-free', 'double_free': 'attempting double-free'}
        correctness = []
        for name, error in list(cases.items()) + [('control-' + x, None) for x in ('heap', 'stack', 'global', 'fixed')]:
            case = name.removeprefix('control-')
            index = ('8' if error else '7') if case in ('heap', 'stack', 'global') else ('8' if case == 'fixed' else '0')
            for i in range(1, 6):
                trial = run(['taskset', '-c', str(cpu), demo, case, index], f'correctness/{name}-{i:02d}',
                            environment=env('asan-modern'), expected=1 if error else 0)
                stderr = stream_bytes(out / trial['stderr']).decode('utf-8', errors='replace')
                assert (error in stderr and re.search(r'memory_cases.c:\d+', stderr)) if error else 'ERROR: AddressSanitizer' not in stderr
                correctness.append({'case': name, 'run': i, 'expected_error': error, 'passed': True, **trial})
        dump(out / 'correctness.json', correctness)

        def measure(workload, config, index, phase):
            item = workloads[workload]
            saved_timing = out / phase / workload / f'{config}-{index:02d}.time'
            saved_timing.parent.mkdir(parents=True, exist_ok=True)
            timing = WORK / 'stage2-capture' / ident / phase / workload / f'{config}-{index:02d}.time'
            timing.parent.mkdir(parents=True, exist_ok=True)
            # A fixed exec wrapper ensures the same time/taskset/shell overhead for all profiles.
            trial = run(['taskset', '-c', str(cpu), '/usr/bin/time', '-f',
                         'wall_seconds=%e\nuser_seconds=%U\nsystem_seconds=%S\nmax_rss_kib=%M',
                         '-o', timing, 'bash', '-c', item['commands'][config]],
                        f'{phase}/{workload}/{config}-{index:02d}', environment=env(config), timeout=cfg['timeout_seconds'])
            shutil.copyfile(timing, saved_timing)
            metrics = {}
            for line in timing.read_text(encoding='utf-8').splitlines():
                k, v = line.split('=', 1)
                metrics[k] = float(v)
            stderr = stream_bytes(out / trial['stderr']).decode('utf-8', errors='replace')
            assert not re.search(r'(ERROR|SUMMARY): (AddressSanitizer|LeakSanitizer)', stderr), workload
            actual_hash = stream_sha(out / trial['stdout'])
            if item['reference_stdout_sha256'] is None:
                assert config == 'native' and phase == 'pilot'
                item['reference_stdout_sha256'] = actual_hash
            assert actual_hash == item['reference_stdout_sha256'], ('stdout differs', workload, config, phase, index)
            row = {'phase': phase, 'workload': workload, 'configuration': config, 'run': index,
                   'asan_options': env(config)['ASAN_OPTIONS'], 'stdout_sha256': actual_hash,
                   'time_log': saved_timing.relative_to(out).as_posix(), **metrics, **trial}
            measurements.append(row)
            dump(out / 'measurements.json', measurements)
            print(f'{phase} {index:02d} {workload} {config}: {trial["elapsed_seconds"]:.4f}s', flush=True)

        for workload in workloads:
            for config in CONFIGS:
                measure(workload, config, 0, 'pilot')
        dump(out / 'workloads.json', workloads)
        frozen = {'stage': 2, 'started_utc': started_utc, 'frozen_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
                  'lock': lock, **cfg, 'configurations': CONFIGS, 'workloads': list(workloads), 'chosen_cpu': cpu,
                  'timer': 'perf_counter includes taskset, GNU time, shell, process launch and exit',
                  'output_capture': 'Full stdout/stderr captured on Linux ext4; gzip lossless compression and copy to records occur after the timed interval. stdout_sha256 hashes decompressed bytes.',
                  'rss': 'GNU time peak resident set in KiB; not VmPeak',
                  'reference_checks': {'upstream': 24, 'gcc_differential': 12},
                  'deviation': 'Pinned upstream large inputs reuse ref-size expected outputs. Large inputs therefore use full-output cross-compiler GCC differential references generated only in build trees; these are not independent algorithmic proofs.',
                  'formal_trials': len(workloads) * len(CONFIGS) * cfg['runs'],
                  'pilot_policy': 'One fixed-work native and each ASan run before protocol freeze; excluded from statistics'}
        dump(out / 'protocol.json', frozen)
        if args.precheck_only:
            dump(out / 'status.json', {'passed': False, 'stage': 'precheck-complete', 'precheck_passed': True})
            manifest()
            print('STAGE 2 PRECHECK PASSED (no formal result): ' + str(out), flush=True)
            return
        run(['cat', '/proc/loadavg'], 'environment/load-before-formal')
        run(['free', '-h'], 'environment/memory-before-formal')
        for workload in workloads:
            for config in CONFIGS:
                for index in range(1, cfg['warmups'] + 1):
                    measure(workload, config, index, 'warmup')
        rng = random.Random(cfg['seed'])
        schedule = []
        for index in range(1, cfg['runs'] + 1):
            names = list(workloads)
            rng.shuffle(names)
            for workload in names:
                configs = list(CONFIGS)
                rng.shuffle(configs)
                schedule.extend({'workload': workload, 'configuration': c, 'run': index} for c in configs)
        dump(out / 'schedule.json', schedule)
        dump(out / 'status.json', {'passed': False, 'stage': 'measuring', 'formal_trials_expected': frozen['formal_trials']})
        for trial in schedule:
            measure(trial['workload'], trial['configuration'], trial['run'], 'performance')
        formal = [r for r in measurements if r['phase'] == 'performance']
        dump(out / 'summary.json', summarize(formal))
        fields = sorted(set().union(*(r.keys() for r in measurements)))
        with (out / 'measurements.csv').open('w', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fields)
            writer.writeheader()
            writer.writerows(measurements)
        run(['cat', '/proc/loadavg'], 'environment/load-after')
        run(['free', '-h'], 'environment/memory-after')
        run(['git', '-C', SOURCE, 'diff', '--exit-code'], 'environment/upstream-final')
        if args.defer_host_review:
            dump(out / 'status.json', {'passed': False, 'stage': 'awaiting-host-review', 'formal_trials': 540,
                 'ended_utc': dt.datetime.now(dt.timezone.utc).isoformat()})
            manifest()
            (ROOT / 'tmp').mkdir(exist_ok=True)
            (ROOT / 'tmp/stage2-pending-record.txt').write_text(out.relative_to(ROOT).as_posix(), encoding='utf-8')
            print('STAGE 2 MEASUREMENTS COMPLETE; awaiting Windows host review: ' + str(out), flush=True)
            return
        windows_shell = Path('/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe')
        if windows_shell.exists():
            ps = ("[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
                  "$ErrorActionPreference='Stop'; Get-WinEvent -ListLog System -ErrorAction Stop | Out-Null; "
                  "$events = @(Get-WinEvent -FilterHashtable @{LogName='System'; "
                  "ProviderName='Microsoft-Windows-Kernel-Power'; Id=42,107,506,507; "
                  "StartTime=[datetime]::Parse('" + started_utc + "')} -ErrorAction SilentlyContinue | "
                  "Select-Object TimeCreated,Id,Message); ConvertTo-Json -InputObject $events -Depth 4")
            review = run([windows_shell, '-NoProfile', '-NonInteractive', '-Command', ps],
                         'environment/host-sleep-query', timeout=60)
            events = json.loads(stream_bytes(out / review['stdout']).decode('utf-8-sig'))
            dump(out / 'environment/host-sleep-review.json', {'applicable': True, 'passed': not events,
                 'events': events, 'started_utc': started_utc, 'reviewed_utc': dt.datetime.now(dt.timezone.utc).isoformat()})
            if events:
                raise RuntimeError('Host sleep/resume interrupted this batch; entire batch excluded')
        else:
            dump(out / 'environment/host-sleep-review.json', {'applicable': False, 'passed': True,
                 'events': [], 'reason': 'Windows host event log not applicable on native Linux'})
        dump(out / 'status.json', {'passed': True, 'stage': 'complete', 'formal_trials': len(formal),
             'correctness_trials': len(correctness), 'ended_utc': dt.datetime.now(dt.timezone.utc).isoformat()})
        manifest()
        from verify_stage2 import verify
        print(json.dumps(verify(out), indent=2), flush=True)
        (ROOT / 'records/latest-stage2.txt').write_text(out.relative_to(ROOT).as_posix() + '\n', encoding='utf-8')
        print('STAGE 2 PASSED: ' + str(out), flush=True)
    except BaseException as error:
        dump(out / 'status.json', {'passed': False, 'stage': 'failed', 'error': repr(error),
             'formal_trials_saved': sum(r['phase'] == 'performance' for r in measurements),
             'ended_utc': dt.datetime.now(dt.timezone.utc).isoformat()})
        manifest()
        raise


if __name__ == '__main__':
    main()

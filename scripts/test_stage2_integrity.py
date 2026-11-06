"""Mutation tests against a copy of a real complete batch; never edit source records."""
import hashlib
import csv
import gzip
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from verify_stage2 import verify
from run_stage2 import summarize

SYNTHETIC = len(sys.argv) > 1 and sys.argv[1] == '--synthetic'
SOURCE_RECORD = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 and not SYNTHETIC else None


def synthetic_fixture(root):
    """Tiny clearly synthetic audit fixture; never used for experimental reports."""
    import random
    def write(name, value):
        p = root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    def raw(name, data):
        p = root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(gzip.compress(data, mtime=0))
        return name
    names = [n + '-ref' for n in ('bisort','mst','perimeter','treeadd','tsp','bullet','pairlocalalign','security-sha')]
    names += [n + '-large' for n in ('bisort','mst','perimeter','tsp')]
    configs = ('native','asan-modern','asan-paper-like')
    project = Path(__file__).resolve().parents[1]
    lock = json.loads((project / 'config/environment-lock.json').read_text(encoding='utf-8'))
    write('protocol.json', {'synthetic_test_fixture': True, 'runs':15,'warmups':2,'seed':340,'timeout_seconds':600,
          'formal_trials':540,'workloads':names,'configurations':configs,'lock':lock,
          'reference_checks':{'upstream':24,'gcc_differential':12}})
    write('status.json', {'synthetic_test_fixture':True,'passed':True,'stage':'complete','formal_trials':540})
    write('environment/host-sleep-review.json', {'passed':True,'events':[],'synthetic_test_fixture':True})
    workloads = {}
    for name in names:
        output = ('SYNTHETIC TEST DATA: ' + name + '\n').encode()
        item = {'commands':{c:'synthetic ' + name for c in configs},
                'reference_stdout_sha256':hashlib.sha256(output).hexdigest(),
                'reference_kind':'gcc-differential' if name.endswith('-large') else 'upstream'}
        if name.endswith('-large'):
            item['oracle'] = {'stdout':raw('oracle/'+name+'.gz',output)}
        workloads[name] = item
        for config in configs:
            write(f'reference/{name}-{config}.json', {'tests':[{'code':'PASS','synthetic_test_fixture':True}]})
    write('workloads.json',workloads)
    errors = {'heap':'heap-buffer-overflow','stack':'stack-buffer-overflow','global':'global-buffer-overflow','uaf':'heap-use-after-free','double_free':'attempting double-free'}
    correct = []
    for case in list(errors)+['control-'+n for n in ('heap','stack','global','fixed')]:
        for index in range(1,6):
            stderr = ((errors[case]+' memory_cases.c:12:39\n').encode() if case in errors else b'')
            correct.append({'case':case,'run':index,'passed':True,'returncode':1 if case in errors else 0,'timed_out':False,
                            'stderr':raw(f'correctness/{case}-{index}.gz',stderr)})
    write('correctness.json',correct)
    rng = random.Random(340)
    schedule = []
    for index in range(1,16):
        order = names[:]
        rng.shuffle(order)
        for name in order:
            config_order = list(configs)
            rng.shuffle(config_order)
            schedule.extend({'workload':name,'configuration':c,'run':index} for c in config_order)
    write('schedule.json',schedule)
    rows = []
    matrix = [(phase,n,c,i) for phase,indices in [('pilot',[0]),('warmup',[1,2])] for n in names for c in configs for i in indices]
    matrix += [('performance',r['workload'],r['configuration'],r['run']) for r in schedule]
    for phase,name,config,index in matrix:
        prefix=f'{phase}/{name}/{config}-{index}'
        stdout=('SYNTHETIC TEST DATA: '+name+'\n').encode()
        elapsed=1+index*.01+(0 if config=='native' else .5)
        metrics={'wall_seconds':elapsed,'user_seconds':elapsed,'system_seconds':0.,'max_rss_kib':1000. if config=='native' else 2000.}
        timing=root/(prefix+'.time')
        timing.parent.mkdir(parents=True,exist_ok=True)
        timing.write_text(''.join(f'{k}={v}\n' for k,v in metrics.items()),encoding='utf-8')
        rows.append({'phase':phase,'workload':name,'configuration':config,'run':index,'argv':['bash','-c',workloads[name]['commands'][config]],
                     'asan_options':'' if config=='native' else lock['asan_default_options' if config=='asan-modern' else 'asan_paper_like_options'],
                     'returncode':0,'timed_out':False,'elapsed_seconds':elapsed,**metrics,
                     'stdout':raw(prefix+'.stdout.gz',stdout),'stderr':raw(prefix+'.stderr.gz',b''),
                     'stdout_raw_bytes':len(stdout),'stderr_raw_bytes':0,'stdout_sha256':hashlib.sha256(stdout).hexdigest(),'time_log':prefix+'.time'})
    write('measurements.json',rows)
    write('summary.json',summarize([r for r in rows if r['phase']=='performance']))
    with (root/'measurements.csv').open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,sorted(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    write('sha256-manifest.json',{p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file() and p.name!='sha256-manifest.json'})


class IntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if SOURCE_RECORD is None and not SYNTHETIC:
            raise RuntimeError('Usage: python scripts/test_stage2_integrity.py <complete-record>')
        cls.temp = tempfile.TemporaryDirectory(prefix='asan-stage2-audit-')
        cls.record = Path(cls.temp.name) / 'record'
        if SYNTHETIC:
            cls.record.mkdir()
            synthetic_fixture(cls.record)
        else:
            shutil.copytree(SOURCE_RECORD, cls.record)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.originals = {}

    def tearDown(self):
        for name, data in self.originals.items():
            (self.record / name).write_bytes(data)

    def write(self, name, data):
        p = self.record / name
        self.originals.setdefault(name, p.read_bytes())
        p.write_bytes(data)

    def alter_json(self, name, transform):
        obj = json.loads((self.record / name).read_text(encoding='utf-8'))
        transform(obj)
        self.write(name, (json.dumps(obj, indent=2) + '\n').encode('utf-8'))

    def reseal(self):
        # Re-seal intentionally: semantic tests must fail even when hashes agree.
        manifest = {p.relative_to(self.record).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in self.record.rglob('*') if p.is_file() and p.name != 'sha256-manifest.json'}
        self.write('sha256-manifest.json', (json.dumps(manifest, indent=2) + '\n').encode('utf-8'))

    def test_valid_batch(self):
        self.assertEqual(verify(self.record)['performance_trials'], 540)

    def test_missing_trial(self):
        self.alter_json('measurements.json', lambda xs: xs.pop())
        self.reseal()
        with self.assertRaisesRegex(AssertionError, 'Measurement count'):
            verify(self.record)

    def test_duplicate_pair(self):
        self.alter_json('measurements.json', lambda xs: xs.__setitem__(-1, xs[-2].copy()))
        self.reseal()
        with self.assertRaisesRegex(AssertionError, 'duplicated or mispaired'):
            verify(self.record)

    def test_wrong_command(self):
        self.alter_json('measurements.json', lambda xs: xs[-1]['argv'].__setitem__(-1, '/wrong/workload'))
        self.reseal()
        with self.assertRaisesRegex(AssertionError, 'Wrong workload command'):
            verify(self.record)

    def test_corrupted_stdout(self):
        rows = json.loads((self.record / 'measurements.json').read_text(encoding='utf-8'))
        self.write(rows[-1]['stdout'], b'tampered output\n')
        with self.assertRaisesRegex(AssertionError, 'SHA-256 mismatch'):
            verify(self.record)

    def test_incorrect_statistics(self):
        self.alter_json('summary.json', lambda xs: xs[0]['elapsed_seconds'].__setitem__('mean', -1))
        self.reseal()
        with self.assertRaisesRegex(AssertionError, 'Statistic mismatch'):
            verify(self.record)

    def test_host_sleep(self):
        self.alter_json('environment/host-sleep-review.json', lambda obj: obj.update(passed=False, events=[{'Id':506}]))
        self.reseal()
        with self.assertRaisesRegex(AssertionError, 'Host sleep interrupted'):
            verify(self.record)


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0]], verbosity=2)

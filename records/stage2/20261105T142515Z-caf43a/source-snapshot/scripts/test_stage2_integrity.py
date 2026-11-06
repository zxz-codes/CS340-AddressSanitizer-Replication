"""Mutation tests against a copy of a real complete batch; never edit source records."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from verify_stage2 import verify

SOURCE_RECORD = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else None


class IntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if SOURCE_RECORD is None:
            raise RuntimeError('Usage: python scripts/test_stage2_integrity.py <complete-record>')
        cls.temp = tempfile.TemporaryDirectory(prefix='asan-stage2-audit-')
        cls.record = Path(cls.temp.name) / 'record'
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


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0]], verbosity=2)

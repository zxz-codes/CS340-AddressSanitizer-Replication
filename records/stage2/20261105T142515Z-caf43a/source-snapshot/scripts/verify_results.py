"""Independent consistency and integrity audit of a completed experiment."""
import csv
import hashlib
import json
from pathlib import Path
import statistics

root=Path(__file__).resolve().parents[1]
record=root/(root/'records/latest-stage1.txt').read_text().strip()
read=lambda name: json.loads((record/name).read_text(encoding='utf-8'))
assert read('status.json')['passed'] is True
rows=read('measurements.json')
correctness=read('correctness.json')
summary=read('summary.json')
assert len(correctness)==45 and all(r['passed'] for r in correctness)
assert sum(r['phase']=='performance' for r in rows)==75
assert sum(r['phase']=='extension' for r in rows)==30
assert all(r['returncode']==0 for r in rows)
assert len(list(csv.DictReader((record/'measurements.csv').open())))==len(rows)
for name in {r['benchmark'] for r in rows}:
    assert len({r['stdout_sha256'] for r in rows if r['benchmark']==name})==1
for row in rows:
    stdout=(record/row['log']).read_text().split('\n',1)[1]
    assert hashlib.sha256(stdout.encode()).hexdigest()==row['stdout_sha256']
for item in summary:
    group=[r for r in rows if r['phase']==item['phase'] and r['benchmark']==item['benchmark'] and r['configuration']==item['configuration']]
    for metric in ('elapsed_seconds','max_rss_kib'):
        values=[r[metric] for r in group]
        assert abs(statistics.mean(values)-item[metric]['mean'])<1e-10
        assert abs(statistics.stdev(values)-item[metric]['sd'])<1e-10
    if 'paired_time_ratio' in item:
        base={r['run']:r for r in rows if r['phase']=='performance' and r['benchmark']==item['benchmark'] and r['configuration']=='native'}
        values=[r['elapsed_seconds']/base[r['run']]['elapsed_seconds'] for r in group]
        assert abs(statistics.mean(values)-item['paired_time_ratio']['mean'])<1e-10
        assert abs(statistics.stdev(values)-item['paired_time_ratio']['sd'])<1e-10
manifest=read('sha256-manifest.json')
for name, expected in manifest.items():
    assert hashlib.sha256((record/name).read_bytes()).hexdigest()==expected, name
for variant in ('native','asan'):
    data=read('build/'+variant+'-lit.json')
    assert len(data['tests'])==5 and all(t['code']=='PASS' for t in data['tests'])
result={'passed':True,'record':record.relative_to(root).as_posix(),'verified_file_hashes':len(manifest),
        'correctness_trials':45,'performance_trials':75,'extension_trials':30,
        'reference_checks':10,'statistics_recomputed':True,'stdout_hashes_recomputed':True}
(root/'records/setup/result-verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))

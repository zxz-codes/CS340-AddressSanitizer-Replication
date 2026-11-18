"""Build the November 9-15 synthesis from verified, frozen Stage 2 records.

Only derived reports are written. No experiments or upstream sources are changed.
Run with reportlab installed: python scripts/make_weekly_synthesis.py
"""
import csv
import hashlib
import json
import math
import statistics
from pathlib import Path
from xml.sax.saxutils import escape

from verify_stage2 import verify

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/week3/weekly-synthesis'
PROFILES = ('asan-modern', 'asan-paper-like')


def stats(values):
    return {'mean': statistics.mean(values), 'sd': statistics.stdev(values), 'n': len(values)}


def build():
    record = ROOT / (ROOT / 'records/latest-stage2.txt').read_text(encoding='utf-8').strip()
    audit = verify(record)  # Fail before producing any report if source evidence is invalid.
    relative = record.relative_to(ROOT).as_posix()
    read = lambda name: json.loads((record / name).read_text(encoding='utf-8'))
    protocol = read('protocol.json')
    workloads = protocol['workloads']
    formal = [r for r in read('measurements.json') if r['phase'] == 'performance']
    index = {(r['workload'], r['configuration'], r['run']): r for r in formal}
    saved = {(s['workload'], s['configuration']): s for s in read('summary.json')}
    pairs, summaries, sizes = [], [], []
    for workload in workloads:
        for profile in PROFILES:
            group = []
            for run in range(1, 16):
                native, asan = index[workload, 'native', run], index[workload, profile, run]
                row = {'workload': workload, 'configuration': profile, 'run': run,
                       'native_seconds': native['elapsed_seconds'], 'asan_seconds': asan['elapsed_seconds'],
                       'time_ratio': asan['elapsed_seconds'] / native['elapsed_seconds'],
                       'native_rss_kib': native['max_rss_kib'], 'asan_rss_kib': asan['max_rss_kib'],
                       'rss_ratio': asan['max_rss_kib'] / native['max_rss_kib']}
                pairs.append(row)
                group.append(row)
            item = {'workload': workload, 'configuration': profile,
                    'native_seconds': stats([r['native_seconds'] for r in group]),
                    'time_ratio': stats([r['time_ratio'] for r in group]),
                    'rss_ratio': stats([r['rss_ratio'] for r in group])}
            item['native_cv_percent'] = 100 * item['native_seconds']['sd'] / item['native_seconds']['mean']
            for key, source in [('time_ratio', 'paired_time_ratio'), ('rss_ratio', 'paired_rss_ratio')]:
                for field, value in item[key].items():
                    if not math.isclose(value, saved[workload, profile][source][field], rel_tol=1e-12, abs_tol=1e-12):
                        raise ValueError(f'Summary mismatch: {workload}/{profile}/{key}/{field}')
            summaries.append(item)
    lookup = {(s['workload'], s['configuration']): s for s in summaries}
    for name in protocol['large_arguments']:
        for profile in PROFILES:
            ref = lookup[name + '-ref', profile]['time_ratio']['mean']
            large = lookup[name + '-large', profile]['time_ratio']['mean']
            sizes.append({'program': name, 'configuration': profile, 'reference_ratio_mean': ref,
                          'large_ratio_mean': large, 'difference_in_ratio_means': large - ref,
                          'large_over_reference_ratio_means': large / ref})
    OUT.mkdir(parents=True, exist_ok=True)
    hashes = {name: hashlib.sha256((record / name).read_bytes()).hexdigest()
              for name in ('measurements.json', 'summary.json', 'protocol.json', 'sha256-manifest.json')}
    result = {'report_date': '2026-11-13', 'week': '2026-11-09/2026-11-15', 'record': relative,
              'new_measurements': False, 'source_sha256': hashes,
              'verification': {**audit, 'record': relative}, 'summaries': summaries, 'size_comparisons': sizes}
    (OUT / 'analysis.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    with (OUT / 'paired-ratios.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(pairs[0]))
        writer.writeheader()
        writer.writerows(pairs)
    fmt = lambda s: f"{s['mean']:.3f} +/- {s['sd']:.3f}"
    time_table = [['Workload', 'Native s', 'CV %', 'Modern ratio', 'Paper-like ratio']]
    rss_table = [['Workload', 'Modern RSS ratio', 'Paper-like RSS ratio']]
    for w in workloads:
        modern, paper = lookup[w, PROFILES[0]], lookup[w, PROFILES[1]]
        time_table.append([w, fmt(modern['native_seconds']), f"{modern['native_cv_percent']:.1f}",
                           fmt(modern['time_ratio']), fmt(paper['time_ratio'])])
        rss_table.append([w, fmt(modern['rss_ratio']), fmt(paper['rss_ratio'])])
    size_table = [['Program', 'Profile', 'Ref ratio', 'Large ratio', 'Difference']]
    for s in sizes:
        size_table.append([s['program'], s['configuration'].removeprefix('asan-'),
                           f"{s['reference_ratio_mean']:.3f}", f"{s['large_ratio_mean']:.3f}",
                           f"{s['difference_in_ratio_means']:+.3f}"])
    pages = [
        ('Weekly synthesis | 9-15 November 2026', [
            'AddressSanitizer replication - review draft, prepared 13 November 2026. This supplement brings the accepted Stage 2 evidence and later analyses together; it does not replace the existing stage report or a final presentation.',
            'Progress: PRs #1-#7 are recorded as merged in reports/submissions-index.md. A live GitHub open-PR search on 13 November returned no open PRs. The accepted A audit and B paired-ratio analysis are available. No Week 3 C submission or final deck is recorded in the current integration index.',
            f'Evidence: {relative}. The generator reran the read-only Stage 2 verifier: 2,263 file hashes, 45 correctness trials, 648 saved measurement rows (36 pilot, 72 warm-up, 540 formal), 24 upstream checks and 12 GCC differential checks passed. This verifies stored evidence, rather than rerunning workloads or independently observing host conditions.',
            'Method: within each workload and round, divide ASan elapsed time by native elapsed time, then calculate the mean and sample SD (n-1 denominator) over 15 rounds. Repeat for peak RSS. Pilot and warm-up rows are excluded. All 24 time and RSS summary groups are checked against the frozen summary. SD describes sample spread; it is not a confidence interval or a significance test.',
            'New deliverables: a complete 360-row pairing CSV (12 workloads x 2 ASan profiles x 15 rounds), machine-readable analysis, and time/RSS and input-size tables. No measurements, frozen protocol, earlier member reports or personal contribution claims are edited.',
            'Attribution: Zhang Hanyuan supplied the accepted A audit; Zhang Yuexiang supplied the accepted B analysis; Zhang Yinyuan supplied the Week 2 paper comparison and outline. Owner corrections and integration are recorded separately. This supplement and its generation code were prepared with AI assistance; they do not establish a new contribution by another member.',
        ], None),
        ('1 | Complete timing analysis', [
            'All cells report mean +/- sample SD, n=15. Native CV is 100 x sample SD / mean. It describes within-batch variation and is not an acceptance threshold. Each workload/input is retained separately.',
        ], time_table),
        ('2 | Peak resident memory', [
            'Each RSS ratio is ASan peak RSS divided by native peak RSS in the same round, then summarized over 15 rounds. These are resident-memory observations from GNU time, not the paper\'s VmPeak. A small SD does not establish generality or independent replicability.',
            'The workload-dependent memory costs complement the timing table. Modern and paper-like profiles change several runtime settings together; their difference cannot identify the effect of one parameter. No aggregate across this deliberately selected set is used as a reproduction of a SPEC result.',
        ], rss_table),
        ('3 | Input size and work remaining', [
            'Difference below means large-input mean ratio minus reference-input mean ratio. These are descriptive contrasts within the same batch; they are not paired intervention estimates or statistical significance results. Only four programs have a large-input counterpart.',
        ], size_table),
    ]
    pages[1][1].extend([
        'Bullet, MAFFT and SHA broaden application coverage. Treeadd remains the largest modern timing ratio. SHA and mst reference runs have very short native durations, so fixed process-launch and output costs remain relevant. CV alone cannot separate host noise from these fixed costs.',
        'Stage 1 and Stage 2 differ in launch wrappers and capture methods. Increasing the repetition count is not the only change, so cross-stage numerical differences cannot be attributed to sampling alone.',
    ])
    pages[3][1].extend([
        'Modern ratios fall for bisort and mst but rise for perimeter and tsp at the larger input. Larger inputs therefore do not uniformly lower the observed ratio. The data do not identify why; allocation rates, instruction counts and hardware counters were not measured.',
        'Validation limits: eight reference workloads use upstream expected outputs (24 checks). Four large workloads use a separate GCC full-output oracle (12 checks), establishing cross-compiler consistency rather than independent algorithmic correctness. Finite clean controls do not prove zero false positives. SPEC CPU2006, writes-only instrumentation and Chromium findings remain untested.',
        'Before the README weekly cutoff of Sunday 15 November, 23:59 Asia/Shanghai: review this supplement against the CSV; ask the C contributor to prepare the English paper-comparison/presentation material using Stage 2 sources; have each member confirm their actual contribution; use meaningful commits from their own accounts. Speaker assignment and submission requirements still require group/course confirmation.',
        'Next experiment proposal (not executed): investigate treeadd with a fixed modern baseline and one runtime setting changed at a time, retaining native controls, randomized rounds, full output checks, warm-ups, and host wake/sleep review. Confirm that each treatment preserves the intended error-detection scope before timing. Do not interpret the existing multi-setting profile contrast as causal evidence.',
        'Reproduce: python scripts/make_weekly_synthesis.py (requires reportlab). Sources: reports/week3/result-check.md; reports/week3/results-analysis.md; reports/submissions-index.md; frozen measurements.json, summary.json and protocol.json. Source digests and the current verification result are in analysis.json.',
    ])
    md = []
    for title, paragraphs, table in pages:
        md.extend(['# ' + title, ''])
        for p in paragraphs:
            md.extend([p, ''])
        if table:
            md.extend(['| ' + ' | '.join(table[0]) + ' |', '| ' + ' | '.join(['---'] * len(table[0])) + ' |'])
            md.extend('| ' + ' | '.join(row) + ' |' for row in table[1:])
            md.append('')
    (OUT / 'report.md').write_text('\n'.join(md), encoding='utf-8')
    pdf(pages)
    print(json.dumps({'passed': True, 'paired_rows': len(pairs), 'summary_groups': len(summaries),
                      'size_comparisons': len(sizes), 'verified_file_hashes': audit['verified_file_hashes']}, indent=2))


def pdf(pages):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    navy = colors.HexColor('#16324B')
    body = ParagraphStyle('body', fontName='Helvetica', fontSize=10, leading=14, spaceAfter=10, textColor=navy)
    heading = ParagraphStyle('heading', parent=body, fontName='Helvetica-Bold', fontSize=21, leading=25, spaceAfter=18)
    cell = ParagraphStyle('cell', parent=body, fontSize=8, leading=11, spaceAfter=0)
    header = ParagraphStyle('header', parent=cell, fontName='Helvetica-Bold', textColor=colors.white)
    story = []
    for title, paragraphs, table in pages:
        if story:
            story.append(PageBreak())
        story.append(Paragraph(escape(title), heading))
        # Tables precede interpretation, following the initial method paragraph.
        for i, text in enumerate(paragraphs):
            story.append(Paragraph(escape(text), body))
            if i == 0 and table:
                widths = {5: [107, 104, 35, 116, 116], 3: [178, 150, 150]}[len(table[0])]
                if title.startswith('3'):
                    widths = [85, 90, 100, 100, 103]
                rows = [[Paragraph(escape(str(v)), header if r == 0 else cell) for v in row]
                        for r, row in enumerate(table)]
                t = Table(rows, colWidths=widths, repeatRows=1, hAlign='LEFT')
                t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), navy),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#EDF3F6')]),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6)]))
                story.extend([t, Spacer(1, 12)])
    dest = ROOT / 'output/pdf/ASan_Weekly_Synthesis_20261113_EN.pdf'
    dest.parent.mkdir(parents=True, exist_ok=True)
    def footer(c, doc):
        c.setFont('Helvetica', 8)
        c.setFillColor(navy)
        c.drawString(58, 30, 'CS340 | ASan replication | Weekly review draft | 13 November 2026')
        c.drawRightString(A4[0] - 58, 30, str(doc.page))
    SimpleDocTemplate(str(dest), pagesize=A4, rightMargin=58, leftMargin=58,
                      topMargin=48, bottomMargin=48, title='ASan weekly synthesis - 13 November 2026',
                      author='CS340 replication project - AI-assisted synthesis').build(
                          story, onFirstPage=footer, onLaterPages=footer)


if __name__ == '__main__':
    build()

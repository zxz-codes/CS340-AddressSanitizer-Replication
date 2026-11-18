# Weekly synthesis | 9-15 November 2026

AddressSanitizer replication - review draft, prepared 13 November 2026. This supplement brings the accepted Stage 2 evidence and later analyses together; it does not replace the existing stage report or a final presentation.

Progress: PRs #1-#7 are recorded as merged in reports/submissions-index.md. A live GitHub open-PR search on 13 November returned no open PRs. The accepted A audit and B paired-ratio analysis are available. No Week 3 C submission or final deck is recorded in the current integration index.

Evidence: records/stage2/20261105T142515Z-caf43a. The generator reran the read-only Stage 2 verifier: 2,263 file hashes, 45 correctness trials, 648 saved measurement rows (36 pilot, 72 warm-up, 540 formal), 24 upstream checks and 12 GCC differential checks passed. This verifies stored evidence, rather than rerunning workloads or independently observing host conditions.

Method: within each workload and round, divide ASan elapsed time by native elapsed time, then calculate the mean and sample SD (n-1 denominator) over 15 rounds. Repeat for peak RSS. Pilot and warm-up rows are excluded. All 24 time and RSS summary groups are checked against the frozen summary. SD describes sample spread; it is not a confidence interval or a significance test.

New deliverables: a complete 360-row pairing CSV (12 workloads x 2 ASan profiles x 15 rounds), machine-readable analysis, and time/RSS and input-size tables. No measurements, frozen protocol, earlier member reports or personal contribution claims are edited.

Attribution: Zhang Hanyuan supplied the accepted A audit; Zhang Yuexiang supplied the accepted B analysis; Zhang Yinyuan supplied the Week 2 paper comparison and outline. Owner corrections and integration are recorded separately. This supplement and its generation code were prepared with AI assistance; they do not establish a new contribution by another member.

# 1 | Complete timing analysis

All cells report mean +/- sample SD, n=15. Native CV is 100 x sample SD / mean. It describes within-batch variation and is not an acceptance threshold. Each workload/input is retained separately.

Bullet, MAFFT and SHA broaden application coverage. Treeadd remains the largest modern timing ratio. SHA and mst reference runs have very short native durations, so fixed process-launch and output costs remain relevant. CV alone cannot separate host noise from these fixed costs.

Stage 1 and Stage 2 differ in launch wrappers and capture methods. Increasing the repetition count is not the only change, so cross-stage numerical differences cannot be attributed to sampling alone.

| Workload | Native s | CV % | Modern ratio | Paper-like ratio |
| --- | --- | --- | --- | --- |
| bisort-ref | 0.260 +/- 0.019 | 7.4 | 2.222 +/- 0.256 | 1.919 +/- 0.175 |
| mst-ref | 0.031 +/- 0.004 | 13.2 | 1.936 +/- 0.166 | 1.870 +/- 0.260 |
| perimeter-ref | 0.102 +/- 0.015 | 15.0 | 5.961 +/- 0.733 | 2.001 +/- 0.331 |
| treeadd-ref | 0.112 +/- 0.021 | 19.2 | 25.818 +/- 2.773 | 4.041 +/- 0.410 |
| tsp-ref | 0.297 +/- 0.063 | 21.1 | 2.882 +/- 0.273 | 1.769 +/- 0.127 |
| bullet-ref | 2.033 +/- 0.053 | 2.6 | 2.041 +/- 0.066 | 2.023 +/- 0.086 |
| pairlocalalign-ref | 9.394 +/- 0.167 | 1.8 | 1.508 +/- 0.023 | 1.489 +/- 0.027 |
| security-sha-ref | 0.011 +/- 0.001 | 8.5 | 1.670 +/- 0.141 | 1.647 +/- 0.161 |
| bisort-large | 1.605 +/- 0.076 | 4.7 | 2.134 +/- 0.170 | 1.673 +/- 0.113 |
| mst-large | 0.853 +/- 0.100 | 11.8 | 1.743 +/- 0.171 | 1.699 +/- 0.170 |
| perimeter-large | 0.387 +/- 0.060 | 15.5 | 10.911 +/- 1.244 | 2.017 +/- 0.229 |
| tsp-large | 0.573 +/- 0.037 | 6.5 | 3.372 +/- 0.274 | 1.864 +/- 0.150 |

# 2 | Peak resident memory

Each RSS ratio is ASan peak RSS divided by native peak RSS in the same round, then summarized over 15 rounds. These are resident-memory observations from GNU time, not the paper's VmPeak. A small SD does not establish generality or independent replicability.

The workload-dependent memory costs complement the timing table. Modern and paper-like profiles change several runtime settings together; their difference cannot identify the effect of one parameter. No aggregate across this deliberately selected set is used as a reproduction of a SPEC result.

| Workload | Modern RSS ratio | Paper-like RSS ratio |
| --- | --- | --- |
| bisort-ref | 7.369 +/- 0.020 | 2.268 +/- 0.007 |
| mst-ref | 1.386 +/- 0.003 | 1.374 +/- 0.002 |
| perimeter-ref | 3.251 +/- 0.000 | 1.435 +/- 0.000 |
| treeadd-ref | 8.406 +/- 0.000 | 2.259 +/- 0.000 |
| tsp-ref | 4.795 +/- 0.003 | 1.707 +/- 0.001 |
| bullet-ref | 3.085 +/- 0.003 | 1.196 +/- 0.001 |
| pairlocalalign-ref | 1.580 +/- 0.000 | 1.384 +/- 0.000 |
| security-sha-ref | 1.542 +/- 0.031 | 1.542 +/- 0.029 |
| bisort-large | 8.088 +/- 0.006 | 2.255 +/- 0.002 |
| mst-large | 1.288 +/- 0.000 | 1.278 +/- 0.000 |
| perimeter-large | 3.343 +/- 0.000 | 1.413 +/- 0.000 |
| tsp-large | 4.925 +/- 0.001 | 1.697 +/- 0.000 |

# 3 | Input size and work remaining

Difference below means large-input mean ratio minus reference-input mean ratio. These are descriptive contrasts within the same batch; they are not paired intervention estimates or statistical significance results. Only four programs have a large-input counterpart.

Modern ratios fall for bisort and mst but rise for perimeter and tsp at the larger input. Larger inputs therefore do not uniformly lower the observed ratio. The data do not identify why; allocation rates, instruction counts and hardware counters were not measured.

Validation limits: eight reference workloads use upstream expected outputs (24 checks). Four large workloads use a separate GCC full-output oracle (12 checks), establishing cross-compiler consistency rather than independent algorithmic correctness. Finite clean controls do not prove zero false positives. SPEC CPU2006, writes-only instrumentation and Chromium findings remain untested.

Before the README weekly cutoff of Sunday 15 November, 23:59 Asia/Shanghai: review this supplement against the CSV; ask the C contributor to prepare the English paper-comparison/presentation material using Stage 2 sources; have each member confirm their actual contribution; use meaningful commits from their own accounts. Speaker assignment and submission requirements still require group/course confirmation.

Next experiment proposal (not executed): investigate treeadd with a fixed modern baseline and one runtime setting changed at a time, retaining native controls, randomized rounds, full output checks, warm-ups, and host wake/sleep review. Confirm that each treatment preserves the intended error-detection scope before timing. Do not interpret the existing multi-setting profile contrast as causal evidence.

Reproduce: python scripts/make_weekly_synthesis.py (requires reportlab). Sources: reports/week3/result-check.md; reports/week3/results-analysis.md; reports/submissions-index.md; frozen measurements.json, summary.json and protocol.json. Source digests and the current verification result are in analysis.json.

| Program | Profile | Ref ratio | Large ratio | Difference |
| --- | --- | --- | --- | --- |
| bisort | modern | 2.222 | 2.134 | -0.089 |
| bisort | paper-like | 1.919 | 1.673 | -0.246 |
| mst | modern | 1.936 | 1.743 | -0.193 |
| mst | paper-like | 1.870 | 1.699 | -0.171 |
| perimeter | modern | 5.961 | 10.911 | +4.950 |
| perimeter | paper-like | 2.001 | 2.017 | +0.016 |
| tsp | modern | 2.882 | 3.372 | +0.490 |
| tsp | paper-like | 1.769 | 1.864 | +0.094 |

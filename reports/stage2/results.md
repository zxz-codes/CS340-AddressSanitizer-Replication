# ASan Stage 2 results

Evidence: `records/stage2/20261105T142515Z-caf43a`

540 formal trials; 36 pilots; 72 warm-ups; 45 correctness checks; 24 upstream reference checks + 12 GCC differential checks.

| Workload | Native seconds, mean +/- SD | Modern paired ratio | Paper-like paired ratio |
|---|---:|---:|---:|
| bisort-ref | 0.260 +/- 0.019 | 2.222 +/- 0.256 | 1.919 +/- 0.175 |
| mst-ref | 0.031 +/- 0.004 | 1.936 +/- 0.166 | 1.870 +/- 0.260 |
| perimeter-ref | 0.102 +/- 0.015 | 5.961 +/- 0.733 | 2.001 +/- 0.331 |
| treeadd-ref | 0.112 +/- 0.021 | 25.818 +/- 2.773 | 4.041 +/- 0.410 |
| tsp-ref | 0.297 +/- 0.063 | 2.882 +/- 0.273 | 1.769 +/- 0.127 |
| bullet-ref | 2.033 +/- 0.053 | 2.041 +/- 0.066 | 2.023 +/- 0.086 |
| pairlocalalign-ref | 9.394 +/- 0.167 | 1.508 +/- 0.023 | 1.489 +/- 0.027 |
| security-sha-ref | 0.011 +/- 0.001 | 1.670 +/- 0.141 | 1.647 +/- 0.161 |
| bisort-large | 1.605 +/- 0.076 | 2.134 +/- 0.170 | 1.673 +/- 0.113 |
| mst-large | 0.853 +/- 0.100 | 1.743 +/- 0.171 | 1.699 +/- 0.170 |
| perimeter-large | 0.387 +/- 0.060 | 10.911 +/- 1.244 | 2.017 +/- 0.229 |
| tsp-large | 0.573 +/- 0.037 | 3.372 +/- 0.274 | 1.864 +/- 0.150 |

Ratios are paired within each run, n=15. RSS is not VmPeak. Workloads and sizes are reported separately.
Larger inputs have no matching upstream reference output at the pinned revision. Their full outputs are checked against an independent GCC build; this is cross-compiler consistency, not an independent algorithmic proof.
The timer includes shell/taskset/GNU time/process launch and exit. Stage 1 used a different launch wrapper and pipe capture, while Stage 2 captures on ext4; cross-batch differences cannot be attributed to sample count alone.
A finite clean-control suite does not prove absence of false positives. No SPEC CPU2006, writes-only instrumentation or Chromium finding is established.

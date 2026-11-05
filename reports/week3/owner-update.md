# Week 3: ASan Stage 2 replication progress

Date: November 5, 2026. Owner: Zhou Xiaozhou, student ID 1240025753.

This week expands the main experiment with different application types, larger upstream inputs and more repetitions. PR #2 and other members' reports remain unchanged. This is a stage submission, without a final v1.0 release or a merge into main.

## Completed experiments and verification

Accepted batch: `records/stage2/20261105T142515Z-caf43a`, selected by [latest-stage2.txt](../../records/latest-stage2.txt).

| Item | Recorded result |
|---|---|
| Original workloads | Five Olden programs with their original inputs |
| Additional workloads | Bullet, mafft / pairlocalalign, MiBench security-sha |
| Larger inputs | bisort 3000000; mst 4000; perimeter 11; tsp 2048000 |
| Formal trials | 12 program/input combinations x 3 profiles x 15 rounds = 540 |
| Excluded setup trials | 36 pilots and 72 warm-ups, saved separately |
| Correctness | 25 injected-error trials returned 1; 20 clean controls returned 0; all expected checks passed |
| Reference checks | 24 upstream checks and 12 large-input GCC full-output differential checks |
| Independent audit | 2,263 file hashes matched; matrix, schedule, CSV/JSON, outputs and statistics verified |
| Audit mutation tests | Seven tests on synthetic fixtures and seven on a copy of the real batch passed |
| Host sleep review | Windows host log query covered the batch; no sleep/resume events were found |

The batch directory contains raw evidence, the frozen protocol and every executed command. See the [Stage 2 results](../stage2/results.md) and [verification output](../stage2/verification.json). Stage 1 data and reports are preserved independently.

## Resolved issues and deviations

1. **lit timeout dependency.** lit's internal timeout requires optional psutil. The runner instead uses a process-group watchdog with a 600-second limit, without adding a system package.
2. **Missing large-input upstream expectations.** The pinned revision provides LARGE_PROBLEM_SIZE arguments but still uses reference-size expected output. Four large inputs therefore use a separate GCC build for full-output comparison, with generated expectations stored only in build directories. Upstream sources and original reference files remain unchanged. This checks cross-compiler consistency, not independent algorithmic correctness; it must not be described as 36 upstream reference checks.
3. **Output I/O affected timing.** mafft emits about 47 MB per trial. The accepted implementation captures complete stdout/stderr on Linux ext4, then losslessly gzip-compresses and copies them after timing. Decompressed byte counts and hashes are verified. No output is truncated, filtered or removed.
4. **Idle standby interrupted an entire batch.** Batch `20261105T132554Z-94d04c` saved 540 trials but experienced Windows standby at approximately 21:43-21:56 and 22:06-22:19, Asia/Shanghai. The whole batch was excluded, without selectively replacing samples. A process-scoped wake request was added, and the full matrix was rerun without changing system power policy. The excluded batch's final audit also exposed a CSV file-handle name shadowing the decompression function; this was corrected and covered by audit tests.
5. **Final host query module loading.** All measurements in the accepted batch finished before a Windows PowerShell 5 module failed to load through WSL. The same interval was then reviewed from the Windows host. Existing hashes were verified before acceptance metadata was completed; every sample and the frozen protocol remained byte-identical. The earlier status, manifest and error streams are retained under the accepted batch's `environment/` directory. The wrapper now performs the host query before final acceptance.

Three development batches and the standby-interrupted complete batch are preserved in byte-verified, deduplicated `.tgz` archives listed in the [development archive index](../../records/stage2-development/index.json). Internal hardlinks represent duplicate contents; each archived entry was checked against its original bytes. These archives supply no report numbers.

Before publication, the committed Git tree was compared with the experiment manifest. The existing `build/` ignore rule also excluded 25 evidence files. Narrow exceptions now preserve Stage 2 compressed build logs and CMake configuration records in clean checkouts, without changing their bytes.

## Interpretation and deliverables

Each workload has its own mean and sample SD. Ratios are paired within a round before aggregation. Modern ASan mean ratios are approximately 2.041 for Bullet, 1.508 for mafft, and 1.670 for SHA. For perimeter, the modern mean ratio changes from about 5.961 at the reference input to 10.911 at the larger input. These observations do not support a claim that larger inputs necessarily reduce overhead ratios, and do not establish a specific causal mechanism.

Short workloads remain sensitive to launch and output costs. Stage 1 and Stage 2 use different launch wrappers and capture methods, so cross-batch differences cannot be attributed solely to repetition count. RSS is not VmPeak. SPEC CPU2006 aggregate results, writes-only instrumentation and Chromium bug discovery remain untested.

Deliverables include the Stage 2 configuration, Python and PowerShell entry points, read-only verifier, mutation tests, formal records, figures and a six-page English report. All PDF pages were rendered and visually checked. The Chinese explanatory PDF remains local and is excluded from this English submission. Newly authored submission prose and PR metadata are in English; immutable evidence retains original paths, identifiers and localized host messages to preserve its hashes.

The work is prepared on `codex/stage2-benchmarks` for PR review. AI assisted implementation, experiment execution, verification, analysis and report drafting. All numerical results come from saved local runs. Planned work is not counted as completed contribution, and other members' work is not claimed here.

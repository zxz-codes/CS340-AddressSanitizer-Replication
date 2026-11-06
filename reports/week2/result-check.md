# Week 2 — Direction A: Existing Result Verification Note

| Item | Value |
|---|---|
| Checked by | 张瀚元 (Zhang Hanyuan) |
| Student ID | 1240025908 |
| GitHub account | `Galax1an121` |
| Date of check | 2026-10-30 |
| Machine | macOS 26.6, x86_64 (Darwin 25.6.0) |
| Toolchain used | Python 3.12.15 (`~/.local/py312/python/bin/python3`), git 2.50.1 (Apple Git-155) |
| Repository | https://github.com/zxz-codes/CS340-AddressSanitizer-Replication |
| Commit checked | `f7b56aae5fbb7913bf316ff0a290657577f5ef90` — "[1240025908 张瀚元] Record group contribution entry for stage 1" |
| Baseline compared against | `0e9d476f5f9ca9065da9b3f88d41582a479c101d` — `origin/main` |
| Record audited | `records/stage1/20261025T072502Z-06ebb2` (selected through the pointer `records/latest-stage1.txt`) |

## 1. Scope of this check

This is a **verification of the records already committed to the repository**, not a
re-run of the AddressSanitizer experiment. No measurement was repeated, no benchmark
was executed, and no original measurement file was edited. The audit therefore answers a
narrower question than the paper's claims:

> Do the numbers, statistics, logs and file digests stored in the repository agree with
> each other, and can a second person reproduce that agreement from the committed
> files alone?

Per the direction-A brief, a machine with Git and Python 3 is sufficient; the ASan
toolchain and the Ubuntu 22.04 experiment host were not required and were not used.

## 2. Command executed and actual output

Command, run in the repository root:

```
$ python3 scripts/verify_results.py
```

Actual output:

```json
{
  "passed": true,
  "record": "records/stage1/20261025T072502Z-06ebb2",
  "verified_file_hashes": 372,
  "correctness_trials": 45,
  "performance_trials": 75,
  "extension_trials": 30,
  "reference_checks": 10,
  "statistics_recomputed": true,
  "stdout_hashes_recomputed": true
}
```

Exit status `0`. This is the exit status of the verification script itself. It does not
mean every measured process returned 0: the 25 injected-error cases are expected to make the
program under test abort with status 1, and the script checks that this happened.

What this output establishes, in the order the script checks it:

* `status.json` records `passed: true` for the audited batch, and the batch is the one
  the `latest-stage1.txt` pointer selects, so the audit ran against the intended record.
* All 45 correctness trials passed their expected checks: 25 injected-error trials
  returned 1 and 20 clean-control trials returned 0. All 75 performance trials and 30
  extension trials returned 0. The measurement CSV and JSON contain the same number of
  records.
* Every benchmark's stdout hash is identical across its repetitions, and each stored
  `stdout_sha256` was recomputed from the corresponding log file.
* Every mean and standard deviation in `summary.json` was recomputed from
  `measurements.json` and matched to within `1e-10`, including the paired
  `paired_time_ratio` values.
* All 372 files listed in `sha256-manifest.json` match their recorded SHA-256 digests.
* Both `native` and `asan` builds pass their five `lit` reference checks
  (`build/native-lit.json`, `build/asan-lit.json`).

The script rewrites `records/setup/result-verification.json`. After this run the file was
**byte-identical** to the committed version (`git status` reports no modification), so no
change to that file is proposed in this pull request and no decision by the group owner is
needed on that point.

## 3. Evidence A — one error report

File: `records/stage1/20261025T072502Z-06ebb2/correctness/heap-01.log`
(paired with the record entry `{"case": "heap", "run": 1, "expected": "heap-buffer-overflow",
"returncode": 1, "passed": true}` in `correctness.json`).

This log supports two separate conclusions:

1. **Detection and localisation.** ASan aborts with
   `ERROR: AddressSanitizer: heap-buffer-overflow`, names the access
   (`READ of size 4`), identifies the faulting address as
   `0 bytes to the right of 32-byte region [0x603000000040,0x603000000060)`, and gives the
   exact source position `examples/memory_cases.c:12:39` in function `exercise`, together
   with the allocation stack that created the object. This is the paper's central claim
   that errors are detected *at the point of occurrence* with a usable report (paper §3.2,
   §3.3, and the claim summarised in §1.1), reproduced on a controlled injected bug.
2. **The shadow-memory mechanism is the one described in the paper.** The log prints the
   shadow bytes around the faulting address, with `fa` marking the heap left redzone and
   `00` marking addressable memory. This is direct evidence for the paper's design: one
   shadow byte per eight application bytes, with poisoned redzones placed around heap
   allocations (paper §3.1 and §3.3). The report is therefore self-describing — a reader
   can see *why* the access was rejected, not only that it was rejected.

The 45 correctness trials cover five injected error categories (`heap`, `stack`, `global`,
`uaf`, `double_free`) and four clean controls (`control-heap`, `control-stack`,
`control-global`, `control-fixed`), each repeated five times; all 45 passed with the
expected classification. **Limitation:** these are deliberately injected bugs in a small
educational program (`examples/memory_cases.c`), not bugs in the benchmarks, and a clean
control suite is not evidence of the absence of false positives in general.

## 4. Evidence B — one performance record

Files: `records/stage1/20261025T072502Z-06ebb2/performance/bisort/native-01.time` and
`.../performance/bisort/asan-modern-01.time`, together with the `bisort` entries of
`records/stage1/20261025T072502Z-06ebb2/summary.json`.

Raw recorded timings (GNU `time`):

```
native-01.time            asan-modern-01.time
wall_seconds=0.23         wall_seconds=0.58
user_seconds=0.23         user_seconds=0.53
system_seconds=0.00       system_seconds=0.05
max_rss_kib=18272         max_rss_kib=134760
```

Aggregated over five repetitions, with the ASan/native ratio paired inside each
repetition:

| Configuration | Elapsed seconds (mean ± SD) | Peak RSS KiB (mean ± SD) | Paired time ratio (mean ± SD) |
|---|---|---|---|
| `native` | 0.253 ± 0.050 | 18254 ± 32 | — |
| `asan-paper-like` | 0.439 ± 0.021 | 41429 ± 48 | 1.770 ± 0.267 |
| `asan-modern` | 0.613 ± 0.122 | 134770 ± 7 | 2.447 ± 0.496 |

This record supports the *direction* of the paper's cost claim — enabling ASan costs
measurable time and memory. The paper-like profile costs 1.770× the native runtime and the
modern profile 2.447× on this recorded workload.

The two recorded ASan profiles differ in redzone sizing, quarantine settings, and
allocation-stack capture settings. The paper-like profile pins `redzone=32`,
`max_redzone=32`, `quarantine_size_mb=0`, `thread_local_quarantine_size_kb=0` and
`malloc_context_size=0`, whereas the modern profile leaves these to the runtime defaults
(`records/stage1/20261025T072502Z-06ebb2/protocol.json`). On this recorded bisort workload,
the paired mean runtime ratios are 1.770× for the paper-like profile and 2.447× for the
modern profile. These measurements show an observed difference between the two
configurations, but do not isolate the contribution of any individual setting.

Note that **both** profiles deliberately exclude leak detection and use-after-return
detection from the measured scope (`detect_leaks=0`,
`-fsanitize-address-use-after-return=never`), so the difference above is a difference
between the two whole configurations, not an effect of any one option.

In the recorded bisort extension, the sample means of elapsed time and peak RSS increase as
the minimum heap redzone changes from 16 to 32 to 128 bytes (0.420 → 0.428 → 0.607 s and
32211 → 41434 → 96754 KiB), with `max_redzone`, quarantine settings, and
`malloc_context_size` held fixed. This is a descriptive trend in this sample; it does not
establish statistically significant timing differences between every pair of settings or a
universal trend across workloads. In particular, the 0.420 s and 0.428 s means come from
overlapping observed ranges, so the mean difference between them carries no significance
claim on its own.

The extension also records `mst`, where the same three settings give 0.054 → 0.050 → 0.057 s
and 37349 → 37360 → 37335 KiB peak RSS. That is neither an increasing timing trend nor a
growing memory trend, so the bisort observation cannot be generalised to the other
recorded workload either.

**Limitation that must be preserved:** `max_rss_kib` is GNU `time`'s resident-memory
high-water mark, **not** the paper's `VmPeak` metric. It must not be presented as a
reproduction of the paper's 3.37× memory result. Likewise these substitute workloads do
not reproduce the paper's SPEC CPU2006 aggregate slowdown; the paper's 73% average comes
from a different benchmark set on different hardware.

## 5. Historical CSV checksum issue and subsequent resolution

**This issue was found during the check below and has since been resolved by the group
owner. The original finding is retained here as historical evidence.**

The audit above was run on commit `f7b56aa`, which already contains the stage-1 repair
commit `0a5d983`. To test whether the *shared* branch is self-consistent, I created a
clean checkout of `origin/main` (`0e9d476`) in a separate worktree and ran the same
command:

```
$ git worktree add --detach /tmp/main_check origin/main
$ cd /tmp/main_check && python3 scripts/verify_results.py
Traceback (most recent call last):
  File "/private/tmp/main_check/scripts/verify_results.py", line 38, in <module>
    assert hashlib.sha256((record/name).read_bytes()).hexdigest()==expected, name
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: measurements.csv
```

Root cause, confirmed by measurement rather than inference:

* The recorded `measurements.csv` was produced on the experiment host with CRLF line
  endings (127 CRLF lines, 41325 bytes). The SHA-256 manifest records
  `f1fb45c0164fa3edfa2b7b48363215a6b25e30a150042ae6475dff2aee21afd6` for it.
* `origin/main` contains a `.gitattributes` with `* text=auto eol=lf` and no CSV-specific
  rule, so git normalises the file to LF on checkout: 127 LF lines, 41198 bytes, digest
  `f8df7e4b712b2e40f4013a0f0deb0eccee00e8c8eb295bd88089a025aba6f1ef`.
* The digest therefore does not match the manifest, and the audit aborts on the first
  manifest entry.

Controlled re-check. Copying only the corrected `.gitattributes` into the clean checkout
was **not** sufficient — the blob stored in the repository is itself the LF version, so
the line-ending rule alone cannot restore the recorded bytes. Restoring both parts of the
stage-1 repair (`0a5d983`: the CSV pinned as binary, and the original CRLF bytes
re-committed) into the same `origin/main` checkout gives:

```
  re-checked digest: f1fb45c0164fa3edfa2b7b48363215a6b25e30a150042ae6475dff2aee21afd6   (matches the manifest)
  file size: 41325 bytes, 127 CRLF lines
  $ python3 scripts/verify_results.py
  {"passed": true, ..., "verified_file_hashes": 372, ...}
```

### Status update

The failure described above was observed on the historical `main` commit `0e9d476`. Pull
request #1 has since been merged in commit
`40a3c800b6030bb6b67611164a0f3d808b6de2f8` ("[1240025753 周潇洲] Merge CSV checksum
repair"), and the group owner subsequently verified a fresh clone of the merged `main`,
with all 372 manifest hashes matching. The original failure is retained here as historical
evidence, rather than a statement about the current `main` branch.

The owner's verification is recorded in:

* `reports/week2/owner-update.md`
* `records/week2/pr1-integration-verification.json`
* `records/week2/pr1-clean-audit.log`

That owner-side verification is the owner's own check, not a re-run performed by the author
of this note; the date, commit and environment it used are recorded in those files. No
additional verification was performed by the author while revising this section, and the
2026-10-30 check documented above remains the author's own.

The two points that were raised for the group owner's decision at the time remain valid as
engineering guidance:

1. Keep the CSV pinned in `.gitattributes`; no other experiment file needs a binary rule
   (the audit recomputed 371 other digests successfully).
2. No measurement file needed to be changed — the recorded bytes were already correct once
   the normalisation rule was corrected.

## 6. Conclusion

* The recorded stage-1 results in this repository are **internally consistent**: 372
  stored file digests, 150 recorded trials, the recomputed statistics and the recomputed
  stdout hashes all agree, and the audit passes.
* The error report supports the paper's detection-and-localisation claim and directly
  exhibits the shadow-memory mechanism the paper describes.
* The performance record supports the existence of ASan's overhead and shows an observed
  difference between the two recorded configurations, without isolating any single
  setting. In the recorded bisort extension, elapsed-time and peak-RSS sample means
  increase with the minimum heap redzone from 16 to 32 to 128 bytes; this is a descriptive
  trend in this sample, not a demonstrated universal trend — the recorded `mst` extension
  does not show it, and the mean differences are not established as statistically
  significant — within the stated limitations of substitute workloads and a non-`VmPeak`
  memory metric.
* One defect was found and localised: on the historical `main` commit `0e9d476`, a fresh
  clone failed the independent audit because of git line-ending normalisation of
  `measurements.csv`. Pull request #1 has since been merged (`40a3c80`), and the group
  owner verified a fresh clone of the merged `main` with all 372 manifest hashes matching.

## 7. What this check did not do

* It did not re-run ASan, the benchmarks, or any experiment; every number quoted here is
  read from the committed record and was only recomputed, never re-measured.
* It did not modify `records/`, `reports/Stage1_Results.md`, the measurement CSVs or the
  audit script. The only file added by this pull request is this note.
* It did not evaluate the paper's Chromium deployment result, writes-only instrumentation
  mode, or the SPEC CPU2006 aggregate numbers, none of which are established by this
  stage-1 record.

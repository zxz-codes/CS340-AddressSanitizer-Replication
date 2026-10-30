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

Exit status `0`.

What this output establishes, in the order the script checks it:

* `status.json` records `passed: true` for the audited batch, and the batch is the one
  the `latest-stage1.txt` pointer selects, so the audit ran against the intended record.
* All 45 correctness trials, 75 performance trials and 30 extension trials have
  `returncode == 0`; the CSV has exactly as many rows as the JSON record.
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
measurable time and memory — and it additionally shows that the cost is strongly
configuration-dependent, which is the paper's own argument in §4.3. The two recorded ASan
profiles differ only in redzone sizing and malloc-context capture
(`config/environment-lock.json`: `asan_paper_like_options` pins `redzone=32`,
`max_redzone=32`, `quarantine_size_mb=0` and `malloc_context_size=0`, matching the
settings the paper used for its SPEC measurement, whereas `asan_default_options` leaves
ASan's default dynamic redzone sizing in place). The paper-like profile costs 1.770× the
native runtime and the modern profile 2.447×. Note that **both** profiles deliberately
exclude leak detection and use-after-return detection from the measured scope
(`detect_leaks=0`, `-fsanitize-address-use-after-return=never`), so the difference above
is attributable to the redzone and malloc-context settings alone.

The recorded redzone extension on the same workload reproduces the monotone cost trend
the paper predicts for larger redzones (§4.3): on `bisort`, minimum heap redzone
16 → 32 → 128 bytes gives 0.420 → 0.428 → 0.607 s and 32211 → 41434 → 96754 KiB peak
RSS, with `max_redzone`, quarantine size and malloc context size held fixed — one factor
changed at a time.

**Limitation that must be preserved:** `max_rss_kib` is GNU `time`'s resident-memory
high-water mark, **not** the paper's `VmPeak` metric. It must not be presented as a
reproduction of the paper's 3.37× memory result. Likewise these substitute workloads do
not reproduce the paper's SPEC CPU2006 aggregate slowdown; the paper's 73% average comes
from a different benchmark set on different hardware.

## 5. Problem found: a fresh clone of `main` fails this very audit

**This is the one issue found, and it needs a group decision.**

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

So the defect is already fixed on the open branch `feature/zhang-hanyuan-stage1-audit`
(pull request #1), but **that fix is not yet on `main`**. Until pull request #1 is
merged, anyone who clones `main` — including the teaching team's weekly repository
check — will see the independent audit fail, even though the underlying experimental
records are intact and internally consistent.

Suggested follow-up, for the group owner to decide:

1. Merge pull request #1 into `main` before the next weekly check, so that `main` passes
   `scripts/verify_results.py` on a fresh clone.
2. Keep the CSV pinned in `.gitattributes`; no other experiment file needs a binary rule
   (the audit recomputed 371 other digests successfully).
3. No measurement file needs to be changed — the recorded bytes are already correct on
   the stage-1 branch.

## 6. Conclusion

* The recorded stage-1 results in this repository are **internally consistent**: 372
  stored file digests, 150 recorded trials, the recomputed statistics and the recomputed
  stdout hashes all agree, and the audit passes.
* The error report supports the paper's detection-and-localisation claim and directly
  exhibits the shadow-memory mechanism the paper describes.
* The performance record supports the existence and the configuration-dependence of
  ASan's overhead, and the redzone extension reproduces the paper's predicted monotone
  cost trend — within the stated limitations of substitute workloads and a non-`VmPeak`
  memory metric.
* One defect was found and localised: **`main` currently fails the independent audit on
  a fresh clone** because of git line-ending normalisation of `measurements.csv`. The fix
  already exists in open pull request #1 and needs to be merged.

## 7. What this check did not do

* It did not re-run ASan, the benchmarks, or any experiment; every number quoted here is
  read from the committed record and was only recomputed, never re-measured.
* It did not modify `records/`, `reports/Stage1_Results.md`, the measurement CSVs or the
  audit script. The only file added by this pull request is this note.
* It did not evaluate the paper's Chromium deployment result, writes-only instrumentation
  mode, or the SPEC CPU2006 aggregate numbers, none of which are established by this
  stage-1 record.

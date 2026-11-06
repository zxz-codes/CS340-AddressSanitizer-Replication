# Week 3 — Direction A: Stage 2 Independent Verification Note

| Item | Value |
|---|---|
| Checked by | 张瀚元 (Zhang Hanyuan) |
| Student ID | 1240025908 |
| GitHub account | `Galax1an121` |
| Date of check | 2026-11-06 |
| Machine | macOS 26.6 (Darwin 25.6.0), arm64 (Apple Silicon) |
| Toolchain used | Python 3.12.15 (`~/.local/py312/python/bin/python3`), git 2.50.1 (Apple Git-155) |
| Repository | https://github.com/zxz-codes/CS340-AddressSanitizer-Replication |
| Baseline checked | `98cf5f0249dd0537e02b4527c25c1e963c099eeb` — `codex/stage2-benchmarks` ("[1240025753 Zhou Xiaozhou] Complete ASan Stage 2 replication") |
| Record audited | `records/stage2/20261105T142515Z-caf43a` (selected through the pointer `records/latest-stage2.txt`) |
| Branch | `week3/zhang-hanyuan-audit` (created from `codex/stage2-benchmarks`) |

## 1. Scope of this check

This is a **verification of the stage-2 records already committed to the repository**, not a
re-run of the AddressSanitizer experiment. No measurement was repeated, no benchmark was
executed, and no original record was edited. The audit therefore answers a narrower
question than the paper's claims:

> Do the stage-2 numbers, statistics, logs and file digests stored in the repository agree
> with each other, and can a second person reproduce that agreement from the committed files
> alone?

Per the direction-A brief, Python 3.10 or newer on either Windows or macOS is sufficient;
the ASan toolchain and the Ubuntu 22.04 experiment host were not required and were not used.
The check was run on macOS against the committed files.

## 2. Command executed and actual output

Command, run in the repository root at commit `98cf5f0`:

```
$ python3 -X utf8 scripts/verify_stage2.py
```

Actual output:

```json
{
  "passed": true,
  "record": "/Users/jack/Desktop/CS340-AddressSanitizer-Replication/records/stage2/20261105T142515Z-caf43a",
  "verified_file_hashes": 2263,
  "correctness_trials": 45,
  "reference_checks": 36,
  "upstream_reference_checks": 24,
  "gcc_differential_checks": 12,
  "pilot_trials": 36,
  "warmup_trials": 72,
  "performance_trials": 540,
  "statistics_recomputed": true,
  "csv_matches_json": true,
  "schedule_verified": true,
  "stdout_hashes_recomputed": true
}
```

Exit status `0`; standard error was empty.

This is the exit status of the verification script itself. It does not mean every measured
process returned 0. In the correctness set, the 25 injected-error trials are expected to make
the program under test abort with status 1, and the script checks that this happened:

| Correctness record type | Count | Expected return code | How passing is decided |
|---|---:|---:|---|
| Injected errors — `heap`, `stack`, `global`, `uaf`, `double_free` | 25 | 1 | ASan reported the expected error class |
| Clean controls — `control-heap`, `control-stack`, `control-global`, `control-fixed` | 20 | 0 | Program ran to completion without reporting an error |

Both counts were confirmed directly against `correctness.json`, not only from the script
summary: all 25 injected-error entries carry `returncode == 1`, all 20 control entries carry
`returncode == 0`, and all 45 carry `passed == true`. All 540 formal performance trials
carry `returncode == 0` and `timed_out == false`.

The script did not modify any tracked file: `git status --short` was empty after the run.

### What the counts mean

The 648 recorded measurement rows are **not** 648 formal measurements. They are three
distinct phases, and only the third is used for the reported statistics:

| Phase | Rows | Meaning |
|---|---:|---|
| `pilot` | 36 | One fixed-work native run and one run per ASan profile for each of 12 workloads, executed before the protocol freeze. Excluded from the statistics by policy (`protocol.json`, `pilot_policy`). |
| `warmup` | 72 | Two warm-up repetitions per workload/configuration pair (12 × 3 × 2). Not counted as measurements. |
| `performance` | **540** | The formal trials: 12 workloads × 3 configurations × 15 repetitions. |

The 36 reference checks are likewise composed of two different kinds of check, as declared in
`protocol.json` (`reference_checks: {"upstream": 24, "gcc_differential": 12}`):

* **24 upstream reference checks** — 8 reference workloads (`bisort`, `mst`, `perimeter`,
  `treeadd`, `tsp`, `bullet`, `pairlocalalign`, `security-sha`) × 3 configurations, comparing
  the captured output against the upstream expected output.
* **12 GCC differential checks** — the 4 `large` workloads (`bisort-large`, `mst-large`,
  `perimeter-large`, `tsp-large`) × 3 configurations, comparing against a cross-compiler GCC
  oracle. `protocol.json` states the limitation explicitly: *"Pinned upstream large inputs
  reuse ref-size expected outputs. Large inputs therefore use full-output cross-compiler GCC
  differential references generated only in build trees; these are not independent
  algorithmic proofs."* The oracle outputs are stored under `oracle/`.

So the two check families are not equally strong, and the 36 total should not be read as 36
independent algorithmic verifications.

## 3. Evidence chain A — `heap-01`: an injected error, detected and localised

Files: `records/stage2/20261105T142515Z-caf43a/correctness/heap-01.stderr.gz` (gzip
compressed), with the record entry

```json
{"case": "heap", "run": 1, "expected_error": "heap-buffer-overflow", "passed": true,
 "returncode": 1, "timed_out": false, "stdout_raw_bytes": 0, "stderr_raw_bytes": 3044,
 "argv": ["taskset", "-c", "0", ".../memory_cases", "heap", "8"]}
```

The log was decompressed with Python's `gzip` module and read. It establishes the error
class, the source location, and the mechanism:

* **Error class** — `ERROR: AddressSanitizer: heap-buffer-overflow on address
  0x603000000060`, with `READ of size 4`.
* **Source line** — the report names the faulting position
  `examples/memory_cases.c:12:39` in function `exercise`, and the `SUMMARY` line repeats it.
  The allocation that created the object is attributed to `examples/memory_cases.c:9:14`.
  The reported address is `0 bytes to the right of 32-byte region
  [0x603000000040,0x603000000060)` — a one-element overrun past the end of a 32-byte
  allocation, which is consistent with the `heap` case requesting a length of 8 beyond the
  buffer that `memory_cases.c:9` allocated.
* **Mechanism** — the log prints the shadow bytes around the faulting address, with `fa`
  marking the heap left redzone, `00` marking addressable memory, and the faulting byte
  marked `[fa]`. The legend states *"one shadow byte represents 8 application bytes"*. This
  is direct evidence for the paper's shadow-memory design (paper §3.1 and §3.3): the report
  explains *why* the access was rejected, not merely that it was.
* **Exit status** — the process aborted with status 1 (`==1494==ABORTING`), which is the
  expected return code for this record type and is what `verify_stage2.py` checks.

The path in the log is the original experiment-host path
(`/mnt/c/Users/31236/Desktop/OS论文复现/tmp/stage2-work/...`), preserved as recorded. The
Chinese path segment is original evidence and is reproduced here untranslated.

## 4. Evidence chain B — `control-fixed-01`: a clean control that exits normally

Files: `records/stage2/20261105T142515Z-caf43a/correctness/control-fixed-01.stdout.gz` and
`.../control-fixed-01.stderr.gz`, with the record entry

```json
{"case": "control-fixed", "run": 1, "expected_error": null, "passed": true,
 "returncode": 0, "timed_out": false, "stdout_raw_bytes": 10, "stderr_raw_bytes": 0,
 "argv": ["taskset", "-c", "0", ".../memory_cases", "fixed", "8"]}
```

Decompressed content:

```
stdout: b'completed\n'
stderr: b''
```

This chain supports the complementary conclusion:

* **No error was reported.** The record declares `expected_error: null`, the process exited
  with status 0, and standard error is empty — there is no ASan report of any kind.
* **The program completed normally.** The ten-byte stdout is exactly `completed\n`, which
  matches the recorded `stdout_raw_bytes: 10`. The `fixed` case is the same program and the
  same requested length (8) as the `heap` case, run without the out-of-bounds access, so
  the pair shows the detector distinguishing a genuine overrun from an otherwise identical
  clean run.

Taken together, the two chains show the detector firing on the injected defect and staying
silent on the matched clean control, with the returned status code matching the recorded
expectation in each case.

### Why the manifest digest and `stdout_sha256` differ

The two evidence files above illustrate a property of the record layout that needs stating
explicitly, because it is easy to mistake for a mismatch:

* **`sha256-manifest.json` hashes the stored file itself**, i.e. the raw bytes of the
  `.gz` archive. For `correctness/control-fixed-01.stdout.gz` the manifest records
  `53d3846ef6db629f2ce835a3b897e7557940ecff7404f8f9099e1758bd46e0be`, and the SHA-256 of
  the compressed file on disk is the same value.
* **`stdout_sha256` hashes the decompressed output bytes.** In `measurements.json` the same
  mechanism is visible on a performance record: for
  `pilot/bisort-ref/native-00.stdout.gz` the manifest records
  `23c83e73dadd1b11b1c5333b382ad370b56e6439a10ece443a0ab97e381d4b64` for the 3 059-byte
  archive, while `stdout_sha256` records
  `cce90098d9fd0d1553714a4b78b81db204e36f175c89ab12fe04e6c9bd49f8b3` for the 54 856-byte
  decompressed stream.

Both were recomputed here and both matched, so the two digests are each correct — they
simply cover **different objects**: the archive and the stream inside it.
`protocol.json` states the same rule under `output_capture`: *"Full stdout/stderr captured
on Linux ext4; gzip lossless compression and copy to records occur after the timed interval.
stdout_sha256 hashes decompressed bytes."* The compression happens after the timed
interval, which is also why the recorded output bytes are unaffected by it.

## 5. One excluded batch, and what the final batch did and did not carry over

`records/stage2-development/index.json` lists four development archives. Three are
precheck failures with no formal trials. The fourth is the one relevant here:

```json
{
  "original_record": "records/stage2/20261105T132554Z-94d04c",
  "archive": "20261105T132554Z-94d04c.tgz",
  "bytes": 6190158,
  "sha256": "8d90c30ac8997f7c44f4c0d9b8859e80b7abcf6fbfa981bbd282f1b7288c6c3f",
  "reason": "All 540 trials saved but entire batch excluded after two Windows idle-standby intervals. Final audit also exposed a CSV handle name shadowing bug; fixed before the new batch. No numbers from this batch are used in reports.",
  "included_in_formal_results": false,
  "all_archived_bytes_verified": true
}
```

The archived batch does contain a complete 648-row `measurements.json` with 540 formal
trials. It was excluded because two Windows idle-standby intervals occurred during the run,
so the host was not in a controlled state; no number from it is used in any report.

I compared the archived batch against the final batch row by row, keyed on
`(phase, workload, configuration, run)`. All 648 keys are present in both, and:

| Field | Rows differing | Interpretation |
|---|---:|---|
| `stdout_sha256` | 0 / 648 | Sample output bytes are identical |
| `stdout_raw_bytes` | 0 / 648 | Sample output sizes are identical |
| `returncode` | 0 / 648 | Process outcomes are identical |
| `argv` | 1 element / 648 | Only the capture directory embeds the batch id |
| `cwd`, `asan_options`, `phase`, `configuration`, `workload`, `run`, `stdout`, `stderr`, `time_log`, `timed_out` | 0 / 648 | Protocol and schedule are identical |
| `elapsed_seconds` | 648 / 648 | Timings were re-measured |
| `wall_seconds`, `user_seconds`, `system_seconds` | 530–541 / 648 | Timings were re-measured |
| `max_rss_kib` | 480 / 648 | Peak RSS was re-measured |

**One clarification, because the distinction matters for how this result may be described.**
The final batch did **not** simply carry the previous batch's numbers over. The protocol
configuration and the sample output bytes are unchanged, but the timing and peak-RSS values
were collected again in the new batch, and the new batch additionally carries a complete
`environment/` directory (44 files) that the excluded batch does not have — this is the
host-acceptance metadata the brief refers to, including `host-sleep-review.json`
(`applicable: true`, `passed: true`, `events: []` for this batch), `host-power.json`,
`affinity.json`, the before/after load and memory samples, and the upstream source hashes.
So the accurate statement is: **the protocol and the sample bytes were preserved, the
measurements were re-taken in the new batch, and host-acceptance metadata was added.**

The final batch's own standby review records no idle-standby events, and its
`pre-host-review-status.json` shows the pre-review tooling failed on the sleep query
(`returncode=1`) while still saving the 540 trials — the review was then completed
separately, which is what `host-sleep-review.json` documents.

## 6. Findings

No defect was found in the stage-2 record by this check. The verification script passed on
a clean checkout of the baseline commit, and every item it checks was independently
re-derived during this check:

* 2 263 manifest digests recomputed and matched.
* The 45 correctness trials re-read from `correctness.json` and confirmed to split into 25
  injected-error records returning 1 and 20 clean-control records returning 0.
* The 648 measurement rows re-counted into 36 pilot, 72 warm-up and 540 formal trials, and
  the formal count confirmed as 12 workloads × 3 configurations × 15 repetitions.
* The 36 reference checks confirmed to be 24 upstream + 12 GCC differential, matching the
  `reference_checks` declaration in `protocol.json`.
* The two manual evidence chains traced as described in sections 3 and 4, including the
  compressed-versus-decompressed digest distinction, both sides of which were recomputed.

The only observation worth carrying forward is descriptive rather than a defect: the
excluded batch and the final batch differ in their timing and RSS values while agreeing on
every sample byte, so "the same batch of measurements" must not be used to describe the
relationship between the two. Section 5 records the comparison.

## 7. Scope limits of this check

* **The records were verified, not re-measured.** Every number quoted here is read from the
  committed record and was only recomputed, never re-measured. This check establishes
  internal consistency and reproducibility of the saved stage-2 record; it does not
  establish that the experiment was run correctly on the host, and it re-ran no ASan
  workload.
* **A passing integrity check is not a correctness proof.** It shows that the stored files
  match their digests and that the stored statistics follow from the stored measurements.
  It does not show that the algorithm is generally correct, nor that ASan is free of false
  positives — the correctness set is 45 trials of deliberately injected defects in a small
  educational program (`examples/memory_cases.c`), and the clean controls are a limited
  suite of 20 trials across four control categories. A clean control suite is not evidence
  of the absence of false positives in general, and the injected errors are not bugs in the
  benchmark programs.
* **The two reference families are not equally strong.** The 12 GCC differential checks
  compare against a cross-compiler oracle generated in the build tree, which
  `protocol.json` itself notes "are not independent algorithmic proofs". The 24 upstream
  checks reuse ref-size expected outputs for the pinned large inputs.
* **Workload coverage is a subset.** The twelve workloads are the eight upstream reference
  programs plus four `large` variants; this is not the paper's SPEC CPU2006 aggregate and
  does not reproduce the paper's headline memory figure.
* **Peak RSS is not the paper's `VmPeak`.** `protocol.json` records `rss` as
  *"GNU time peak resident set in KiB; not VmPeak"*, so these values must not be presented
  as a reproduction of the paper's 3.37× memory result.
* **Host conditions were not independently verified.** The `environment/` metadata is
  accepted as recorded. The WSL virtual-CPU-to-host P/E-core mapping is explicitly recorded
  as uncontrolled (`affinity.json`), and `affinity.json` reports the process was pinned to
  CPU 0 of an allowed set of 0–5.
* **This check did not modify any record.** Only this note is added by the pull request; no
  original measurement, CSV, log, manifest, or existing report was altered.

## 8. AI assistance disclosure

The verification command was run and its output was read as recorded above. The row-level
comparisons in section 5, the digest recomputations in section 4, and the wording of this
note were produced with AI assistance, and were checked against the committed files rather
than asserted. The interpretation of the evidence, and the conclusion that no defect was
found, are the author's own.

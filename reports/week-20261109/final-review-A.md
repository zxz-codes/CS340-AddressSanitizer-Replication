# Week of 2026-11-09 — Direction A: Final-Material Consistency Review

| Item | Value |
|---|---|
| Reviewer | 张瀚元 (Zhang Hanyuan) |
| Student ID | 1240025908 |
| GitHub account | `Galax1an121` |
| Date of review | 2026-11-13 |
| Branch | `codex/week-20261109-a-review` |
| Baseline reviewed | `eff61af42181e928fc954b98be2840ec9ee5a978` — `main` ("[1240025753 Zhou Xiaozhou] Integrate all submitted work and record acceptance") |
| Record audited | `records/stage2/20261105T142515Z-caf43a` (selected through `records/latest-stage2.txt`) |
| Machine | macOS 26.6 (Darwin 25.6.0), arm64 · Python 3.12.15 |

## 1. Scope of this review, and one item that could not be reviewed

This is a **read-only consistency review of the saved stage-2 record and of the wording that
the final report uses**. No ASan workload was run, no measurement was repeated, and no
original record, log, manifest, or frozen protocol was modified. Every number below was
recomputed from the committed files or read from them and checked against them.

**One required input was not available and was therefore not reviewed.** The task brief
states that this week's new synthesis materials and data live in
`reports/week3/weekly-synthesis/`, with the English attachment
`ASan_Weekly_Synthesis_20261113_EN.pdf`, and that these are provided by the group owner
when they are not yet synchronised to the remote. At the time of this review:

* `main` at `eff61af` contains **no** `reports/week3/weekly-synthesis/` directory and **no**
  `ASan_Weekly_Synthesis_20261113_EN.pdf`;
* the repository contains **no paired CSV** — the only two CSV files tracked anywhere are
  `records/stage1/20261025T072502Z-06ebb2/measurements.csv` and
  `records/stage2/20261105T142515Z-caf43a/measurements.csv`;
* all eight remote branches (`main`, `codex/stage2-benchmarks`, `docs/week2-presentation`,
  `feature/zhang-hanyuan-stage1-audit`, `review/week2-check`,
  `week2-results-explained-1230019110`, `week3/zhang-hanyuan-audit`,
  `week3/zhang-yuexiang-analysis`) were inspected, and pull requests #1–#7 are all merged;
* the paired-ratio analysis script `reports/week3/compute_stage2_ratios.py` writes Markdown
  and SVG, not CSV.

**Consequence.** The brief's requirement to sample rows "from the new paired CSV" could not
be met against a file that does not exist in the repository or on this machine. To avoid
reporting nothing, I performed the equivalent sampling **against the source of truth the
paired CSV would be derived from** — the committed `measurements.json` — and I state the
scope of that substitution explicitly in section 4. **The paired CSV itself has not been
reviewed**, and no conclusion is offered about its contents, formatting, or agreement with
the record. This item stays open until the owner supplies the file.

## 2. Baseline, command, and actual output

The baseline was recorded before any check was run:

```
$ git rev-parse HEAD
eff61af42181e928fc954b98be2840ec9ee5a978
```

Command, run in the repository root:

```
$ python3 scripts/verify_stage2.py
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

Exit status `0`; standard error was empty; `git status --short` was empty afterwards, so the
verifier modified no tracked file.

This matches the expected result stated in the brief for the successful batch
`20261105T142515Z-caf43a`: 2 263 file hashes, 45 correctness checks, 24 upstream reference
checks and 12 GCC differential checks passed.

The exit status is the status of the **verifier script**. It does not mean every measured
process returned 0. Read back from `correctness.json`:

| Record type | Count | Expected return code | Verified |
|---|---:|---:|---|
| Injected errors — `heap`, `stack`, `global`, `uaf`, `double_free`, 5 each | 25 | 1 | all 25 carry `returncode == 1` |
| Clean controls — `control-heap`, `control-stack`, `control-global`, `control-fixed`, 5 each | 20 | 0 | all 20 carry `returncode == 0` |

All 45 carry `passed == true`, and all 540 formal trials carry `returncode == 0` and
`timed_out == false`. A clean control suite passing is not evidence of the general absence
of false positives.

## 3. Trial counts and what the paired records are

The counts in the brief were confirmed against `measurements.json` and `summary.json`:

| Quantity | Value | How it was confirmed |
|---|---:|---|
| Formal trials | **540** | 12 workloads × 3 configurations × 15 runs = 540; the record holds exactly 540 rows with `phase == "performance"`, and every (workload, configuration) pair has exactly 15 runs |
| Pilot trials | 36 | rows with `phase == "pilot"` |
| Warm-up trials | 72 | rows with `phase == "warmup"` |
| Total rows | 648 | 540 + 36 + 72, matching the recorded 648 rows |

**The 360 paired records are not additional measurements.** The pairing is formed inside the
existing formal trials: for each workload and each run, the ASan trial is divided by the
**same-round** `native` trial. The record contains 360 rows whose configuration starts with
`asan` (12 workloads × 2 ASan profiles × 15 runs) and 180 `native` rows; 360 + 180 = 540.
`summary.json` carries 36 summary entries, of which **24** have a `paired_time_ratio` field
(12 workloads × 2 ASan profiles, each with `n = 15`) and all 36 have a `paired_rss_ratio`.
Every `n` is 15.

So a paired figure such as `perimeter-ref / asan-modern = 5.961` is a statistic over the 15
paired ratios of one workload and one ASan profile, not a 15th measurement and not an extra
trial.

## 4. Sampled paired rows, matched back to the raw record

Eight paired rows were sampled (the brief requires at least six). The selection covers both
ASan profiles and both input sizes — `ref` and `large` — across four workloads and eight
distinct runs. For each sampled row the ASan trial and the same-round `native` trial were
located in `measurements.json` by `(workload, configuration, run)`, and the ratio was formed
from those two records.

| Workload | Configuration | Run | ASan elapsed (s) | Native elapsed (s) | Ratio | Group mean in `summary.json` |
|---|---|---:|---:|---:|---:|---:|
| `bisort-ref` | `asan-modern` | 1 | 0.562829 | 0.281263 | 2.001079 | 2.222446 |
| `bisort-ref` | `asan-paper-like` | 5 | 0.455322 | 0.237059 | 1.920709 | 1.918831 |
| `tsp-large` | `asan-modern` | 3 | 1.719359 | 0.540013 | 3.183921 | 3.372054 |
| `tsp-large` | `asan-paper-like` | 8 | 1.060619 | 0.541366 | 1.959152 | 1.863954 |
| `mst-large` | `asan-modern` | 11 | 1.408770 | 0.874403 | 1.611122 | 1.743331 |
| `mst-large` | `asan-paper-like` | 2 | 1.365329 | 0.798273 | 1.710353 | 1.698757 |
| `perimeter-ref` | `asan-modern` | 6 | 0.586652 | 0.093123 | 6.299770 | 5.961453 |
| `perimeter-ref` | `asan-paper-like` | 13 | 0.191246 | 0.096925 | 1.973145 | 2.000726 |

Individual sampled ratios are expected to differ from the group mean — the mean is over 15
paired ratios, and the sampled rows are single members of that group. The sampled ratios were
each checked to lie within the group's own range; none was found outside it.

## 5. Independently recomputed group statistics

Two groups were recomputed from scratch, each covering 15 runs, one on the **time ratio** and
one on the **RSS ratio**. The recomputation reads the raw records, forms each ratio
directly, and uses the sample standard deviation with the **n−1 denominator**.

| Group | Metric | n | Recomputed mean | Recomputed SD (n−1) | Recorded mean | Recorded SD | Difference |
|---|---|---:|---:|---:|---:|---:|---:|
| `tsp-large` / `asan-modern` | time ratio | 15 | 3.372053727829 | 0.274238303908 | 3.372053727829 | 0.274238303908 | 0.0 |
| `tsp-large` / `asan-modern` | RSS ratio | 15 | 4.925417186415 | 0.001247890052 | 4.925417186415 | 0.001247890052 | 0.0 |
| `bisort-ref` / `asan-paper-like` | time ratio | 15 | 1.918830975735 | 0.175299432911 | 1.918830975735 | 0.175299432911 | 0.0 |
| `bisort-ref` / `asan-paper-like` | RSS ratio | 15 | 2.268165420949 | 0.006617709259 | 2.268165420949 | 0.006617709259 | 0.0 |

Using the population denominator (n) instead would give 0.264939372012, 0.001205576325,
0.169355341714 and 0.006393314538 respectively — all different from the recorded values,
which confirms that the stored statistics use the n−1 denominator.

**Scope of this recomputation.** Two groups were recomputed in full, not all 24 paired-ratio
groups; the recomputation is a check of the recomputation path and of the sample-SD
convention, not an exhaustive re-derivation of every published figure. The verifier's own
`statistics_recomputed` check covers the remaining groups.

## 6. Cross-check of the published Stage 2 results table

The table in `reports/stage2/results.md` was parsed and every value recomputed from the
record: the native mean and sample SD for all 12 workloads, and both paired-ratio columns
for all 12 workloads.

**All 12 rows × 3 columns matched** — native `mean +/- SD` and both paired-ratio columns,
to the three decimal places printed. The table is consistent with the record.

## 7. Findings

No incorrect number was found in the material that is currently in the repository. Two
wording issues were found, both in `reports/stage2/results.md`, which is the document a
reader reaches for the stage-2 numbers. Each is reported below with its location, the
current wording, the supporting evidence, and a suggested change.

### Finding 1 — the stage-2 results table does not state the sample-SD denominator

* **File and location:** `reports/stage2/results.md`, the table header and the note
  immediately below it (line 22), and the column headers "Modern paired ratio" and
  "Paper-like paired ratio".
* **Current wording:** "Ratios are paired within each run, n=15. RSS is not VmPeak.
  Workloads and sizes are reported separately."
* **Evidence:** the recomputation in section 5 shows the stored `paired_time_ratio.sd` and
  `paired_rss_ratio.sd` use the **n−1** denominator: recomputing with n−1 reproduces every
  recorded SD exactly (difference 0.0), while the population denominator gives visibly
  different values (for example 0.264939372012 instead of 0.274238303908 for
  `tsp-large` / `asan-modern` time). The n−1 formula is stated explicitly in
  `reports/week3/results-analysis.md` and in `reports/week2/results-explained.md`, but the
  stage-2 results table itself only says "n=15", which does not identify the denominator.
  A reader who assumes the population SD would recompute a different number from the same
  table.
* **Suggested change:** extend the note to state the convention, for example —
  "Ratios are paired within each run, n=15; the reported uncertainty is the sample standard
  deviation with an n−1 denominator." No numeric value changes.

### Finding 2 — the stage-2 results table does not state how the batch was assembled

* **File and location:** `reports/stage2/results.md`, the paragraph block after the table
  (lines 22–26), which currently carries the RSS/VmPeak, upstream-vs-GCC, launch-wrapper
  and clean-control statements.
* **Current wording:** the block states the RSS/VmPeak distinction, the upstream-versus-GCC
  distinction, the Stage 1 launch-wrapper difference and the clean-control limitation, but
  it says **nothing about the two batch-assembly steps**. A search of the file for
  "excluded", "standby", "rerun", "host" and "pre-host" returns **no match**.
* **Evidence:** the record shows two separate facts that a reader of this table cannot see:
  (i) the standby-interrupted batch `20261105T132554Z-94d04c` saved all 540 trials and was
  excluded in full, after which the complete matrix was rerun — recorded in
  `records/stage2-development/index.json` and in `reports/week3/owner-update.md` (§"Idle
  standby interrupted an entire batch"); and (ii) within the accepted batch, all measurements
  had finished before the host sleep query failed, and completing the acceptance metadata
  changed only `status.json` among the 2 260 original manifest entries, with 2 259 entries
  retaining their original hashes and three entries added for the host review, producing
  2 263 entries. Both statements are correct and verified in
  `reports/week3/owner-update.md` and `reports/week3/result-check.md`; they are simply
  absent from the results table, which is the document that carries the reported numbers.
  `README.md` line 90 does point readers at `reports/week3/owner-update.md` for "excluded
  batches", so the material is reachable — but a reader consulting the results table alone
  will not learn that one complete 540-trial batch was discarded and that the accepted
  batch's own measurements were not re-run when the acceptance metadata was completed.
* **Suggested change:** add one sentence to the paragraph block, for example —
  "One complete 540-trial batch was excluded after Windows idle standby and the full
  matrix was rerun; within the accepted batch, completing the host-acceptance metadata
  changed only `status.json` and added three manifest entries, without rerunning or
  altering the measurements or the frozen protocol." No numeric value changes.

### Confirmations — distinctions that are correctly kept

The brief asks for four distinctions to be checked. All four are present and correctly
worded in the material currently in the repository:

1. **RSS versus VmPeak** — `reports/stage2/results.md` line 22 ("RSS is not VmPeak");
   `README.md` line 59 (explicit: "must not be labeled as a reproduction of its 3.37x
   memory result"); `reports/week3/result-check.md` and
   `reports/week3/results-analysis.md` both carry the statement.
2. **Error detection versus clean controls** — `reports/stage2/results.md` line 25 ("A finite
   clean-control suite does not prove absence of false positives");
   `reports/week3/result-check.md` records the 25-versus-20 return-code split and the same
   limitation.
3. **Upstream reference versus GCC differential** — `reports/stage2/results.md` line 23 and
   `README.md` line 78 both state that the large inputs have no matching upstream
   expectation at the pinned revision and that the GCC differential checks establish
   cross-compiler consistency rather than independent algorithmic correctness.
   `reports/week3/result-check.md` §7 gives the 24/12 split with the same limitation.
4. **Excluded-batch rerun versus acceptance-metadata completion** — stated correctly in
   `reports/week3/owner-update.md` and `reports/week3/result-check.md` §5. It is missing
   only from the stage-2 results table, as Finding 2 states.

## 8. Scope limits of this review

* **This is a review of saved records, not a re-run.** No ASan workload was executed and no
  measurement was repeated. Every number here was recomputed from the committed files or
  read from them and checked against them. This establishes that the stored records are
  internally consistent and that the published table agrees with them; it does not
  establish that the experiment was run correctly on the host.
* **The weekly synthesis and the paired CSV were not reviewed.** They are not present in
  `main`, in any remote branch, or on this machine. This review therefore says nothing about
  the synthesis document's wording, its figures, or the paired CSV's contents. That check
  remains open.
* **The recomputation covered two groups in full.** The two recomputed groups confirm the
  ratio formation, the same-round matching, the n−1 convention and agreement with
  `summary.json`; the verifier's own recomputation covers the remaining groups, and the
  published table was checked for all 12 workloads.
* **This is not a general guarantee about the final report.** It covers the stage-2 record,
  the stage-2 results table and the wording of the stage-2 and week-3 material that is
  currently in `main`. It does not cover the Stage 1 material, the week-2 audit, the
  presentation outline, or any document not yet committed.
* **No final v1.0 tag was created** and no experiment was rerun, as the brief requires. No
  original measurement, log, frozen protocol or manifest was modified; this pull request
  adds only this note.

## 9. AI assistance disclosure

The verification command was run and its output was read as recorded above. The row-level
sampling, the two group recomputations, the parsing of the published results table and the
wording of this note were produced with AI assistance, and every numeric claim was checked
against the committed files rather than asserted. The two findings above are the author's own
review of the wording; the corrections they propose are limited to sentences that state a
convention or a provenance fact already verified in the repository, and change no recorded
value.

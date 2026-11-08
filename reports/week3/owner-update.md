# Week 3: ASan Stage 2 replication progress

## Direction B acceptance: November 9, 2026

Zhang Yuexiang (1230019110, GitHub `lylz199`) submitted the Stage 2 paired-ratio analysis in PR #7 at `28c7108c69b7aceb5e1fb3c06105b9e3e5f80938`, based on `98cf5f0249dd0537e02b4527c25c1e963c099eeb`. The submission adds an English report, a standard-library calculation script and a two-panel SVG. It checks Bullet, MAFFT pairlocalalign and the two perimeter inputs using 15 same-run modern-ASan/native pairs per group. The author's PR discloses AI assistance.

Owner Zhou Xiaozhou appended the AI-assisted presentation revision `548e76d7134d8f7b8c76e17426d91baee73a25c3`. Mean/SD labels now sit above both the highest sample and the error-bar endpoint, with 30% axis headroom. The original analysis, report values, author commit and historical verification baseline are preserved. PR #7 was retargeted to main and its obsolete PR #5 status was corrected.

In an isolated checkout, the owner reran the calculation script and independently checked all 60 report pairing rows and all four summary groups using an explicit n-1 formula. The SVG was reproducible across two runs and was rendered to confirm readable labels and visible samples. The candidate tree passed the existing Stage 2 verifier: 2,263 file hashes, 45 correctness trials, 540 formal trials, 24 upstream reference checks and 12 GCC differential checks, including schedule, output hashes, CSV/JSON and recomputed statistics. These are checks of saved records; no experiment was rerun. The selected mean ratios remain 2.041, 1.508, 5.961 and 10.911, respectively. Perimeter's larger input therefore has a higher observed ratio in this record, without establishing a general input-size law or a causal explanation.

PR #7 was merged with merge commit `2bc5494ecfdfc9d56eed6a228f42ec4d05152e99`, preserving both author and owner commits. Its actual tree is `168cb7edf7c4bb08aa3ef88b877f5d58be4dd6a3`, identical to the tested candidate. Relative to the previous main, only the three B deliverables were added. The merge request locked the reviewed head. Main had no enabled branch protection or repository rulesets; the head had no check runs, commit statuses or workflow runs, and GitHub reported it cleanly mergeable. See [the B acceptance record](pr7-integration-verification.json).

This accepts Zhang Yuexiang's analysis contribution and separately records the owner's presentation fix and integration. PR #6 and its pending revisions were not handled in this update. No raw evidence changed and no final release was published. The earlier integration notes below remain historical records.

## Integration update: November 6, 2026

Owner: Zhou Xiaozhou, student ID 1240025753. The November 5 preparation record below is retained as historical context; its unmerged status is superseded by this update.

After PR #2 was accepted and merged as `ba5fd4a26ff172f052fd129b27f4548b1f96bcc9`, the Stage 2 candidate from `98cf5f0249dd0537e02b4527c25c1e963c099eeb` was merged onto that updated main in an isolated checkout. Stage 1 passed 372 manifest hashes and all recorded checks. Stage 2 passed 2,263 hashes, 45 correctness trials, 36 pilots, 72 warm-ups, 540 formal trials, 24 upstream and 12 GCC differential reference checks, output digests, schedule, CSV/JSON correspondence and statistics. Seven synthetic integrity tests and seven tests on a copy of the real batch passed. The initial synthetic test setup encountered sandbox TEMP permissions; rerunning with workspace-local temporary storage resolved the setup failure without modifying test code or source evidence.

PR #5 was merged with a merge commit, `5abfd816ff1331cb3fd5564328198bdd17d5b152`, preserving its original commit. Its actual tree matched the tested candidate tree `e5ab7c8d3299ee05a61189e1051f363cdde05c1f`. Both stage verifiers were then run on the actual merge, with a clean working tree after verification and restoration of the Stage 1 verifier's generated summary bytes. See [the verification record](integration-verification.json).

Manual review confirmed `heap-01` reports a heap-buffer-overflow at `memory_cases.c:12:39`, allocated at `memory_cases.c:9:14`, with return code 1. `control-fixed-01` returns 0, prints exactly `completed\n` and has empty stderr. For the bisort pilot output, both the compressed-file manifest digest and the decompressed-output digest match their respective recorded values.

The excluded standby-interrupted batch and the accepted batch are separate experimental runs. Within the accepted batch itself, comparison with its pre-host-review manifest shows that only `status.json` changed among the 2,260 original entries; the other 2,259 hashes match the final stored bytes, including measurements and protocol. Three manifest entries were added for the host review and preserved pre-review manifest/status, producing 2,263 entries. Acceptance metadata completion did not rerun the accepted batch or change its measurements or frozen protocol.

Zhang Hanyuan submitted PR #6 at `6e15e9ee53b9f055baa2917283e1d130cad34713`, adding only `reports/week3/result-check.md` against `codex/stage2-benchmarks`. It remains pending author revisions: correct the reference-check scope, distinguish the complete rerun from acceptance-metadata completion, and synchronize the PR description. Feedback was prepared locally for the owner to relay; no PR review or message was posted. PR #6 has not been merged or retargeted. After the author's revision, retarget it to main, recheck that only the personal note is added, and verify before merging.

No experiments were rerun during integration, no original experiment records were changed, and no final v1.0 release was published. AI assisted owner-side review, verification, documentation and integration. Pending revisions are not counted as accepted contribution.

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

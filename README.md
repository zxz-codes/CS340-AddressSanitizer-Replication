# CS340: AddressSanitizer replication

Paper 8: **AddressSanitizer: A Fast Address Sanity Checker**, USENIX ATC 2012.

Group repository: https://github.com/zxz-codes/CS340-AddressSanitizer-Replication

| Member | Student ID |
|---|---|
| Zhou Xiaozhou | 1240025753 |
| Zhang Hanyuan | 1240025908 |
| Zhang Yinyuan | 1230022374 |
| Zhang Yuexiang | 1230019110 |

Individual roles will be recorded later, as requested by the group.

This project tests memory-error detection and measures ASan overhead on an open-source LLVM Olden subset. The instructor allowed an alternative because the institution has no SPEC CPU2006 license. This is a modern implementation on substitute workloads, not an exact reproduction of the SPEC result.

## Requirements and setup

Windows with WSL2 / Ubuntu 22.04 x86-64, or a native Ubuntu 22.04 x86-64 environment. The recorded machine allocates 6 GiB memory and 6 logical CPUs to WSL; measured processes use one pinned Linux CPU. Reserve approximately 2 GiB for the toolchain, checkout and builds, beyond the operating system. Network access is needed only for setup. No GPU, Docker or privileged container is required.

From PowerShell in this directory:

```powershell
.\scripts\Setup-ASan.ps1
.\scripts\Run-Stage1.ps1 -Runs 5
```

The setup requires Linux root for apt. The PowerShell setup wrapper reuses an existing localhost system proxy when present; it does not change proxy configuration. If a proxy returns 502 for Ubuntu mirrors, retry with a functioning proxy or a direct network connection. Package signatures remain enforced. Package versions are pinned in `config/install-packages.txt`, and the benchmark commit is pinned in `config/environment-lock.json`. Future repository availability is not guaranteed; exact dependencies are recorded, rather than promising a hermetic image.

Native Linux alternative:

```bash
sudo bash scripts/setup-asan.sh "$(pwd)"
sudo python3 scripts/run_stage1.py --runs 5
```

Use the same Linux user/work directory for setup and experiments. To use a normal Linux user after root installs the packages, run the venv/source-download steps as that user, or set `CS340_ASAN_WORKDIR` consistently to a writable directory. Its default is the running Linux user's `~/.cache/cs340-asan`. Source code and binaries live on Linux ext4; result logs are copied/written into this repository. No user-specific absolute path is hard-coded in the runnable experiment.

## Experiment and expected output

The experiment uses upstream `bisort`, `mst`, `perimeter`, `treeadd` and `tsp` with generated reference arguments. Two unmodified benchmark builds share `-O2 -g -fno-omit-frame-pointer -fno-pie` and `-no-pie`; ASan adds full read/write instrumentation. Modern and paper-like runtime profiles are recorded in the lock. ASan leak, use-after-return and use-after-scope extensions are excluded from the performance scope. All inherited sanitizer options are cleared and replaced with the recorded profile.

The pipeline checks five injected error categories and four clean controls, validates benchmark reference outputs with lit, excludes one warm-up per configuration, then runs randomized blocks of native / modern-ASan / paper-like-ASan processes. Five independent repetitions produce 75 performance trials. The extension changes only minimum heap `redzone` (16, 32, 128 bytes) on bisort and mst, producing 30 measured extension trials. Valid outputs must be identical in every recorded trial. Timeout or a wrong output fails the run, rather than being silently excluded.

Expected runtime after setup is several minutes; workload timing and the final duration are recorded locally. Initial network downloads can take substantially longer. Success ends with `STAGE 1 PASSED` and creates:

- `records/stage1/<UTC timestamp-id>/status.json` with `passed: true`.
- `protocol.json`, exact commands, tool/package logs and snapshots of project sources.
- `correctness.json`, complete diagnostic logs with source lines and return codes.
- `measurements.csv`, `summary.json`, stdout hashes and GNU time logs.
- Reference-validation logs, original generated test commands and binary-size records.
- `records/latest-stage1.txt`, pointing only to the latest successful experiment.

Failed attempts remain as diagnostic evidence. Use `status.json` or the latest-success pointer to distinguish them from completed experiments.

## Statistics and interpretation

Time is end-to-end monotonic elapsed time, including launch/exit. Each ASan/native ratio is paired within a repetition; reported uncertainty is sample SD across repetitions. Peak RSS is GNU time's resident-memory high-water mark in KiB. It is **not** the paper's VmPeak metric and must not be labeled as a reproduction of its 3.37x memory result. Binary file ratios remove debug information but still include runtime fixed costs; they are single-build observations.

Five related Olden programs are a limited first-stage subset. The original 1.73x runtime result, writes-only mode and Chromium deployment are not established here. WSL virtual CPU mapping to laptop P/E cores, background applications, thermal state and power policy remain limitations. A clean finite control suite is not a proof of zero false positives.

## Stage 2: expanded workloads and larger inputs

Stage 2 has an independent runner and record directory. It retains the five Olden reference inputs, adds Bullet, mafft and MiBench security-sha, and adds four upstream large Olden inputs (bisort 3000000, mst 4000, perimeter 11, tsp 2048000). All three profiles use the Stage 1 compiler flags and ASan options. The matrix is 12 workloads x 3 profiles x 15 rounds = 540 formal trials, with two excluded warm-ups per combination and separate pilot trials.

Use the existing Stage 1 setup, including GCC/G++ from build-essential. Keep the laptop plugged in and avoid other CPU/disk-heavy tasks during measurement. No new system package is required.

The Windows wrapper requests process-scoped system/display wakefulness while the experiment runs, then releases the request in `finally`; it does not change power policy. The runner checks Windows sleep/resume events at completion and rejects an interrupted batch. Earlier development records, including one complete matrix excluded after idle standby, are preserved as byte-verified deduplicated `.tgz` archives under `records/stage2-development/`. None contribute numbers to Stage 2 reports.

```powershell
.\scripts\Run-Stage2.ps1 -PrecheckOnly
.\scripts\Run-Stage2.ps1
```

Native Linux: `python3 scripts/run_stage2.py --precheck-only`, then `python3 scripts/run_stage2.py`. Use the same `CS340_ASAN_WORKDIR` and Linux user as setup. Builds remain on Linux ext4; the runner expands the sparse checkout without editing upstream source files.

The pinned upstream revision supplies LARGE_PROBLEM_SIZE arguments but still has reference-size expected output for those Olden programs. Stage 2 records this deviation explicitly: the eight reference-size workloads pass 24 upstream checks; the four large workloads pass 12 full-output differential checks against a separate GCC build. Generated large expectations live only in build directories. GCC consistency is not an independent proof of algorithm correctness. Failed prechecks remain in `records/stage2/` and do not provide report numbers.

Successful runs update only `records/latest-stage2.txt`. A failed or precheck-only run never updates that pointer. Complete stdout/stderr are captured on Linux ext4 and losslessly gzip-compressed after timing; decompression restores every original byte. No output is truncated or filtered. Commands, generated test definitions, source/input hashes, protocol, schedule and checksums are saved separately for every batch. The timer includes taskset, GNU time, a shell, launch and exit. This differs from the Stage 1 launch wrapper; short workloads and cross-batch comparisons retain that limitation. RSS is not VmPeak. The runner kills timed-out process groups after 600 seconds and does not discard unsuccessful formal trials or replace them with fresh samples.

```bash
python scripts/verify_stage2.py
python scripts/test_stage2_integrity.py records/stage2/<successful-id>
python scripts/make_stage2_reports.py
```

Verification is read-only and checks all 648 pilot/warm-up/formal rows, the paired matrix, random schedule, raw outputs, CSV/JSON, statistics and file manifests. Mutation tests use a temporary copy and confirm that missing/duplicate trials, wrong commands, corrupted output and wrong statistics are rejected. The Stage 2 report generator reads only a verified successful run and writes an independent English PDF and figures. See [Stage 2 recorded results](reports/stage2/results.md).

Stage 2 report: [English](output/pdf/ASan_Stage2_Replication_Report_EN.pdf). The Chinese explanation is retained locally and is excluded from this English submission. The [Week 3 owner update](reports/week3/owner-update.md) records actual work, deviations and excluded batches. A complete run on the recorded machine takes roughly half an hour; initial builds and file verification may add time. On WSL, use the PowerShell wrapper so idle-sleep prevention and host log review run in the Windows context. Finalizing acceptance metadata never changes measured samples or their frozen protocol.

## Stage 1 reports

The English PDF is structured around course claims, setup, deviations, results, evidence, analysis, extension and limitations. The Chinese PDF explains how the experiment and ASan work. Both are stage reports, pending group contribution details and later experiments.

- [English stage report](output/pdf/ASan_Stage1_Replication_Report_EN.pdf)
- [Stage 1 Chinese explanatory report](output/pdf/ASan_第一阶段复现解释报告_中文.pdf)
- [Recorded result summary](reports/Stage1_Results.md)
- [Independent result verification](records/setup/result-verification.json)

```bash
python3 -m pip install -r requirements-report.txt
python3 scripts/make_reports.py
```

The report generator requires a successful recorded run and reads all measurements from it. PDFs are written to `output/pdf/`; editable generation code, SVG figures and a Markdown summary are under `scripts/` and `reports/`. PDF page rendering for visual QA can use Poppler or pypdfium2. Report generation does not change experiment measurements.

Independent result audit: `python3 scripts/verify_results.py`. It recomputes statistics, checks output digests and verifies every file listed in the experiment SHA-256 manifest. The current run passed all 372 manifest checks. Early configuration/timer-development attempts were archived locally, and their reasons are summarized in `records/setup/development-notes.json`; none supply numbers in the report. Benchmark reference validation requires the generated build-tree `lit.local.cfg` to restore traditional MultiSource output handling; the runner creates it without editing upstream sources.

## Provenance, licensing and course status

No upstream benchmark C source was modified. LLVM test-suite remains at its recorded commit; its license is saved in `vendor/LLVM-test-suite-LICENSE.TXT`, and per-file upstream notices are preserved in the checkout. New educational cases and orchestration scripts are under the accompanying MIT license. New project files are in `scripts/`, `examples/`, `config/`, `reports/`, and this README. Exact experiment-time versions are in each run's `source-snapshot/` and SHA-256 manifest.

PERIOD is a previous topic. Its 1,417 files and preservation hashes are under `archive/PERIOD-20261025/`, excluded from the new submission. Two specifically identified, unused PERIOD images were removed; no global Docker prune was used. Ubuntu and its virtual disk were preserved. Windows VHDX compaction was not attempted.

The group repository and four members are listed above. No individual role claims or final v1.0 tag are made at this stage. Before submitting, all four members must review the results, fill in their real contributions, and make meaningful commits from their own accounts with student ID and full name. Weekly checks occur Sunday at 23:59. Do not commit virtual disks, binary builds, credentials, files above 50 MB or the archived old project.

AI assistance covered setup, scripts, educational tests, experiment execution, analysis and report drafting. Experimental numbers come from saved local runs. Human member contributions must be confirmed separately.

## Sources

- Paper: https://www.usenix.org/system/files/conference/atc12/atc12-final39.pdf
- ASan: https://clang.llvm.org/docs/AddressSanitizer.html
- Test-suite: https://llvm.org/docs/TestSuiteGuide.html
- Benchmark repository: https://github.com/llvm/llvm-test-suite
- User-supplied CS340 2026-2027 handout and instructor screenshot allowing substitution.

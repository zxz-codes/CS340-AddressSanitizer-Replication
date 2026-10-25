# CS340: AddressSanitizer replication, stage 1

Paper 8: **AddressSanitizer: A Fast Address Sanity Checker**, USENIX ATC 2012.

Group repository: https://github.com/zxz-codes/CS340-AddressSanitizer-Replication

| Member | Student ID |
|---|---|
| 周潇洲 | 1240025753 |
| 张瀚元 | 1240025908 |
| 章殷远 | 1230022374 |
| 章越翔 | 1230019110 |

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

## Reports

The English PDF is structured around course claims, setup, deviations, results, evidence, analysis, extension and limitations. The Chinese PDF explains how the experiment and ASan work. Both are stage reports, pending group contribution details and later experiments.

- [English stage report](output/pdf/ASan_Stage1_Replication_Report_EN.pdf)
- [中文解释性报告](output/pdf/ASan_第一阶段复现解释报告_中文.pdf)
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

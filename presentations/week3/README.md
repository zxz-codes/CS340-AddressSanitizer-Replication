# Stage 2 display draft: use status and corrections

Integrated 2026-11-19 from PR #9, author Zhang Yinyuan (1230022374).
The original [eight-slide PPTX](ASan_Stage2_Update_EN.pptx) and [speaker notes](../../reports/week3/presentation-notes.md) are retained as submitted. They are additional display drafts, not a final presentation or completion of the revised C assignment. This README is an AI-assisted owner review by Zhou Xiaozhou; its corrections are not attributed to Zhang Yinyuan.

The deck's eight slides and approximate six-minute script are internal draft choices. Final Presentation remains a required group assessment; its language, slide count, duration and speakers await the separate Presentation Instruction. English is explicitly required for the final report.

## Corrections required before final use

| Draft location | Reading to use in the final materials |
|---|---|
| Slide 2, quarantine | Delayed reuse helps detect use-after-free while the freed region remains poisoned and the access is checked. It does not guarantee detection of every use-after-free. |
| Slide 3 and notes, discarded warm-ups | All 36 pilot and 72 warm-up records are retained, but excluded from formal statistics. |
| Slide 4, clean controls | The 20 clean controls passing do not prove a general absence of false positives. |
| Slide 5 notes, “2.04 times slower” | Say “runtime was about 2.04 times native runtime”; the 2.041 value is a runtime ratio. |
| Slide 7, claim labels | Use the course verdicts supported, partially supported, not supported or inconclusive for the 1-3 tested claims; define the tested scope. Put writes-only and Chromium under untested scope. Do not promote local detection results to proof of the whole paper. |
| Slide 7, redzone | Stage 1 already completed bisort/mst × 16/32/128 bytes × 5 runs = 30 single-factor extension trials. Include all six cells, time and RSS means and sample SD, fixed settings and limitations in the report materials. |
| Slide 8, settings and next step | Say “Observed ratios vary across these workloads, inputs and profiles.” The existing two-profile comparison changes multiple parameters. Any proposed treeadd experiment is optional further research beyond the completed Stage 1 extension. |

The original PPTX is intentionally kept byte-for-byte. These corrections have not been applied inside its slide XML or embedded notes; read this file before reusing it.

## Evidence and outstanding C outputs

Stage 2 source: `records/stage2/20261105T142515Z-caf43a/`, especially `measurements.json`, `summary.json`, `correctness.json` and `correctness/heap-01.stderr.gz`. Stage 1 extension: `records/stage1/20261025T072502Z-06ebb2/{protocol,measurements,summary}.json` and `reports/figures/redzone-memory.svg`.

The [paper](https://www.usenix.org/system/files/conference/atc12/atc12-final39.pdf), Sections 3.1-3.5, Figure 2, Table 1 and Section 4.3 support the comparison and mechanism limits. Peak RSS and the paper's VmPeak are different metrics; substitute workloads do not reproduce the SPEC aggregate.

Still missing: `reports/week-20261109/report-materials-C.md` and `reports/week-20261109/group-display-materials-C.md`. The first needs English report claims, comparison, verdicts, extension and limitations; the second needs traceable display assets, supported conclusions and boundaries, and may be Chinese. Zhang Yinyuan should review the AI-prepared materials and submit them through his own account, stating actual human checks and AI assistance. Merging this useful draft does not certify those outputs or personal review as complete.

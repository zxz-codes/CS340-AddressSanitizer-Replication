# Accepted submission index

Updated: November 19, 2026. PRs #1–#10 are integrated into main, preserving original author histories. C PR #9 is accepted as an additional display draft only; the revised C task remains incomplete. Owner corrections and verification are attributed separately. See the [9–15 November integration](week-20261109/README.md).

| PR | Member | Accepted work | Merge |
|---|---|---|---|
| [#1](https://github.com/zxz-codes/CS340-AddressSanitizer-Replication/pull/1) | Galax1an121 | Recorded CSV checksum repair | `40a3c80` |
| [#2](https://github.com/zxz-codes/CS340-AddressSanitizer-Replication/pull/2) | Galax1an121 | Week 2 A verification note | `ba5fd4a` |
| [#3](https://github.com/zxz-codes/CS340-AddressSanitizer-Replication/pull/3) | lylz199 | Week 2 B results explanation and script | `ea24143` |
| [#4](https://github.com/zxz-codes/CS340-AddressSanitizer-Replication/pull/4) | zhangyinyuan1230022374 | Week 2 C paper comparison and presentation outline | `9424ff7` |
| [#5](https://github.com/zxz-codes/CS340-AddressSanitizer-Replication/pull/5) | zxz-codes | Stage 2 experiments, evidence and English report | `5abfd81` |
| [#6](https://github.com/zxz-codes/CS340-AddressSanitizer-Replication/pull/6) | Galax1an121 | Revised Week 3 A independent audit; owner timing-count correction | `3a472d3` |
| [#7](https://github.com/zxz-codes/CS340-AddressSanitizer-Replication/pull/7) | lylz199 | Week 3 B paired-ratio analysis, script and figure; owner label fix | `2bc5494` |
| [#8](https://github.com/zxz-codes/CS340-AddressSanitizer-Replication/pull/8) | Galax1an121 | Final A consistency review and spot-check script; separate owner RSS-count correction and adopted wording suggestions | `904939a` |
| [#9](https://github.com/zxz-codes/CS340-AddressSanitizer-Replication/pull/9) | zhangyinyuan1230022374 | Stage 2 PPTX and speaker notes, additional draft only; two revised C Markdown outputs remain missing | `c6ac0fe` |
| [#10](https://github.com/zxz-codes/CS340-AddressSanitizer-Replication/pull/10) | lylz199 | Final B analysis, four ref/large comparisons, raw-data calculation and reproducible SVG; commit-account linkage pending confirmation | `ea97b31` |

## Deliverables

- [Final B analysis](week-20261109/final-analysis-B.md), [calculation](week-20261109/compute_final_ratios.py), [input-size figure](week-20261109/final-input-size-analysis.svg) and [figure generator](week-20261109/make_final_input_figure.py), accepted November 16. The owner independently recomputed the tables and SVG error spans and reran the saved-record audit; no experiments were rerun. GitHub currently does not link the original commit email to an account; member confirmation is still required. This acceptance does not claim final-report consolidation is complete.
- [Stage 1 results](Stage1_Results.md) and [Stage 2 results](stage2/results.md).
- [Week 2 A audit](week2/result-check.md), [B analysis](week2/results-explained.md), and [C presentation outline](week2/presentation-outline.md).
- [Week 3 A audit](week3/result-check.md) and [B analysis](week3/results-analysis.md), with its [calculation script](week3/compute_stage2_ratios.py) and [figure](week3/figures/stage2-analysis.svg).
- [Reviewed group contributions](../config/group-contributions-template.md), [owner update](week3/owner-update.md), and [integration checks](week3/all-submissions-integration.json).

## Integration checks and remaining work

The [November 13 weekly synthesis](week3/weekly-synthesis/README.md) adds a complete derived timing/RSS analysis and eight input-size comparisons, with [360 pairing rows](week3/weekly-synthesis/paired-ratios.csv), [source hashes and verification](week3/weekly-synthesis/analysis.json), and an [English PDF supplement](../output/pdf/ASan_Weekly_Synthesis_20261113_EN.pdf). It is a historical AI-assisted review draft, not a new member submission or final presentation. The [November 13 checklist](week3/weekly-synthesis/本周推进清单.md) retains its dated status; the [current integration record](week-20261109/integration.md) supersedes it.

The owner verified 372 Stage 1 and 2,263 Stage 2 file hashes, recorded statistics and outputs, the archived-batch comparison, host-review manifest transition and manual evidence chains. No experiment was rerun. Original records are unchanged. Historical audit baselines remain the authors' actual baselines.

C has now supplied the [Stage 2 display draft and notes](../presentations/week3/README.md), integrated from PR #9. The revised assignment's report-materials-C.md and group-display-materials-C.md remain missing. All received submissions are integrated, but the final report, final presentation, member contribution confirmation and v1.0 release remain unfinished. The Stage 2 results page and its generator incorporate A's two wording suggestions; the existing stage PDF has not been regenerated to incorporate all later material.

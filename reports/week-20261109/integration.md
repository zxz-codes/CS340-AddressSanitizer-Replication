# Integration of all received work for 9-15 November 2026

Integration date: 19 November 2026, Asia/Shanghai. Reviewer: Zhou Xiaozhou (1240025753), assisted by AI. Starting main: `ea97b31a57cbea370275a3eeef00229d9a30abee`. GitHub's repository-wide PR inventory contained #1-#10; the new submissions for this week were #8, #9 and #10. PRs #1-#7 were already integrated. PR #10 had already been merged on 16 November; #8 and #9 were open at review time.

## Acceptance and attribution

| PR | Reviewed original head | Decision |
|---|---|---|
| #8 / A | `c9fef8062bde62e72bd759446dacb2d7f02dc9c8` | Accept audit and reproducible spot check. Owner corrects the RSS-field count from 36 to 24 and adopts both suggested wording additions. |
| #10 / B | `0818544b87f3ab10f2a43d67c0937b22020e5e1c` | Retain previous acceptance, merge `ea97b31`. Rechecked calculations, tables and regenerated SVG. Account linkage is not newly established by this review. |
| #9 / C | `27e40aac9110398e3d4bb7e78609757006cd3d89` | Integrate useful PPTX/notes as an additional draft. The revised C assignment remains incomplete; merging this PR does not certify full delivery. |

The original commits and author history are preserved. A's reviewed baseline and statement that the paired CSV was unavailable are historical facts and remain intact. The 13 November owner supplement is now synchronized; its 360 CSV rows were verified independently by the owner, not retroactively attributed to A. The supplement's old status and task discussion are historical, superseded by this integration record.

## Checks performed on saved evidence

- Stage 1: all 372 manifest hashes, 45 correctness trials, 75 formal performance trials, 30 extension trials and 10 reference checks passed the existing verifier. That verifier rewrites a generated audit summary; it ran in the isolated copy and the summary bytes were restored afterwards. Original workspace records were not touched.
- Stage 2: all 2,263 hashes, 648 saved measurement rows (540 formal, 36 pilot, 72 warm-up), 45 correctness trials and 36 reference checks passed the read-only verifier. Statistics, pairing, CSV/JSON correspondence, schedule and raw-output checks passed.
- A: eight sampled pairings and four time/RSS statistic checks from the submitted script matched. The frozen summary has 36 total entries but only 24 ASan entries with each paired-ratio field; the 12 native entries have neither field.
- Owner supplement: all 360 unique same-run pairs matched the raw measurements, all 24 summary groups matched within floating-point tolerance, all eight input-size contrasts matched, and four source hashes matched. The four-page historical PDF was rendered and visually checked.
- B: all four original file blobs matched the reviewed head, all 36 groups had runs 1-15, all 24 paired groups matched the frozen summary, all eight input-comparison rows and four application rows matched, and all 32 SVG bars, labels and SD spans matched. Regeneration reproduced the SVG.
- C: the original PPTX Git blob matched `65fe2448758d47166e04f327f87bc43ec6d34ea1`; its eight previously rendered slides were individually reviewed. Numeric evidence is covered by the independent Stage 2 recomputation and the saved 16 November review. Mechanism and paper comparison were checked against the original paper, including Figure 2, Table 1 and Section 4.3. [Owner use corrections](../../presentations/week3/README.md) accompany the unchanged draft; embedded slide text/notes still need those revisions before final use.

No workload was executed, no timing sample was generated, and no measurement, frozen protocol, log, manifest or existing author history was changed. Remote status checks were empty for A and C at review time; these are local saved-record verification results, not claims of passing remote CI. Numeric checks are recorded in [integration-verification.json](integration-verification.json).

## Remaining work

1. C: submit `report-materials-C.md` and `group-display-materials-C.md` under this directory. Reuse the draft, add 1-3 scoped claims with course verdicts, complete evidence paths and deviations, the completed six-cell redzone extension with time/RSS mean and sample SD, conclusions/limitations, asset provenance, and honest member/AI-review statements. Zhang Yinyuan reviews and submits through his own account; the owner reviews the actual final outputs. No standalone PPT or timed English talk is required by the current task brief.
2. Consolidate the English final report from Stage 1, Stage 2, A, B and the completed C materials; do not equate these component documents with a finished final report.
3. Each member confirms actual contributions and human review. B's original commit email linkage remains an explicit follow-up; existing history is retained.
4. Confirm the separate Presentation Instruction and then prepare the final group presentation. Its language, slide count, duration and speakers remain unconfirmed. Eight slides and about six minutes describe C's draft only.
5. Complete final release checks before the final v1.0 tag. No final release is made here. The Stage 1 redzone single-factor extension is already complete; optional treeadd work is additional investigation.

The course handout requires weekly repository checks on Sunday at 23:59 and lists 1 December as a tentative presentation date; it gives no separate concrete final-report deadline. This 19 November integration does not backdate a push or establish that a previous weekly checkpoint was met. Per-member substantive account contributions apply over the project, not necessarily every week.

This file records AI-assisted owner verification and integration. Member self-reports are retained as self-reports, not independently observed personal review. No notification or course submission was sent.

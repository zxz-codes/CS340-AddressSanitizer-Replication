# Week 3 C: Stage 2 English presentation notes (draft)

Author: Zhang Yinyuan (1230022374)

Deck: [ASan_Stage2_Update_EN.pptx](../../presentations/week3/ASan_Stage2_Update_EN.pptx), 8 slides, about 6 minutes.

This is a first draft for group feedback. Speakers for each slide and the final demo format are not decided here.

## Basis

- Repository state checked: `main` at `eff61af` (after PR #5 merged). The task note named `98cf5f0` as the baseline; the Stage 2 evidence directory is the same in both.
- Evidence directory: `records/stage2/20261105T142515Z-caf43a` (named in `records/latest-stage2.txt`).
- Numbers come from that directory's `summary.json`, `correctness.json`, `protocol.json` and `environment/host-sleep-review.json`, from [results.md](../stage2/results.md), and from the Stage 2 English PDF. Stage 1 numbers are labelled as Stage 1.
- No experiment was rerun. No record, report or other member's file was changed.

## Slide notes

Each slide has a script of 60–100 words and its sources. The same scripts are in the PPT speaker notes.

### Slide 1. Research question and goal

**Script.** Our paper is AddressSanitizer, published at USENIX ATC 2012. We ask two questions. First, can ASan catch common memory errors in C and C++, and point to the line where they happen? Second, how much slower does a program run with ASan turned on? The paper measured cost on SPEC CPU2006. Our school has no SPEC licence, so the instructor allowed open-source benchmarks instead. We use programs from the LLVM test-suite at one fixed commit. This means our numbers check the same kind of claim, not the exact SPEC result.

**Sources.** Paper abstract and Sec. 4; [README](../../README.md) (benchmark substitution); `protocol.json` (`benchmark_commit`).

### Slide 2. How ASan works

**Script.** ASan has four parts. First, the compiler adds a small check before each memory read and write. Second, shadow memory: every 8 bytes of program memory has one shadow byte, which says how many of those bytes are safe to use. Third, redzones: poisoned bytes placed around heap, stack and global objects, so an overflow lands in a redzone and is reported. Fourth, quarantine: freed memory is not reused straight away, so a use after free can still be caught. The shadow bytes on the slide are copied from our real heap error log.

**Sources.** Paper Sec. 3.1–3.3; shadow-byte line from `correctness/heap-01.stderr.gz`.

### Slide 3. Experimental method

**Script.** Stage 2 measures 12 workloads: the 5 original Olden programs, 3 new programs, and 4 larger inputs. Each runs in 3 configurations: native, modern ASan, and paper-like ASan. Each combination has 15 rounds, so there are 540 formal trials. Before these, 36 pilot runs checked the setup before the protocol was frozen, and 72 warm-up runs were thrown away. Neither is used in any statistic. Order is shuffled each round with seed 340 on one pinned CPU. For every round we divide ASan time by native time first, then average.

**Sources.** `protocol.json` (`runs`, `warmups`, `seed`, `configurations`, `pilot_policy`); [results.md](../stage2/results.md).

### Slide 4. Error report and fix

**Script.** Here is a real log. Running our test program with "heap 8" reads one element past an 8-integer array. ASan stops the program and says heap-buffer-overflow at memory_cases.c line 12, and shows that the memory was allocated at line 9. The fixed version keeps the index inside the array. It prints "completed", writes nothing to stderr, and returns 0. Across Stage 2, all 25 injected-error trials returned 1 with the expected error type, and all 20 clean controls returned 0. This only covers these test cases.

**Sources.** `correctness/heap-01.stderr.gz`, `correctness/control-fixed-01.stdout.gz`; `correctness.json` (returncode counts).

### Slide 5. Results on new workloads

**Script.** This chart is from the Stage 2 batch. Bars are paired ASan over native time ratios, error bars are sample standard deviation, and n is 15. With modern ASan, Bullet, a C++ physics program, runs about 2.04 times slower. Mafft, a sequence alignment program, is about 1.51 times. SHA hashing is about 1.67 times. Paper-like values are very close for these three. SHA is very short, about 0.011 seconds natively, so launch cost matters. We did not collect allocation or hardware counters, so we do not explain why the programs differ.

**Sources.** `reports/stage2/figures/new-runtime.svg`; `summary.json` (`bullet-ref`, `pairlocalalign-ref`, `security-sha-ref`).

### Slide 6. Larger inputs

**Script.** Four programs were also run with the larger upstream inputs. Each larger input is treated as a separate workload and never pooled with the reference input. The main thing to see is perimeter. With modern ASan its ratio goes from 5.96 at input 10 to 10.91 at input 11. With paper-like ASan it stays at about 2.0. Other programs do not move the same way: mst goes down, tsp goes up. So we report this as an observation from one batch. It is not a rule about input size, and we cannot name the cause.

**Sources.** `reports/stage2/figures/large-runtime.svg`; `summary.json` (`*-ref` and `*-large`); `workloads.json` (input arguments).

### Slide 7. Comparison with the paper

**Script.** This table compares the paper's claims with our evidence. Error detection is locally supported, but only for our five constructed error types. For runtime, the paper reports 1.73 times on SPEC. We have different programs, compiler and machine, so we cannot judge that number. For memory, the paper used VmPeak, which is virtual memory, while we measured peak RSS, which is resident memory. They are different metrics. The redzone result comes from Stage 1 only. Writes-only mode and the Chromium bug search were not done.

**Sources.** Paper abstract, Sec. 4, Table 1, Sec. 4.3; Stage 2 PDF Sec. 4–5; Stage 1 report Table 8.

### Slide 8. Conclusion and limitations

**Script.** To conclude, ASan found every error we injected and pointed to the source line, and it added measurable cost on all 12 workloads. Our limits are clear. Seven workloads run under half a second natively, so launch cost matters. WSL scheduling, temperature and background load were not fully controlled. Modern and paper-like ASan differ in several settings at once. One complete batch was dropped because the laptop went to standby, and the host log for the accepted batch shows no sleep events. Next, we would vary one setting at a time.

**Sources.** Stage 2 PDF Sec. 4–5; [results.md](../stage2/results.md); `environment/host-sleep-review.json`; [owner update](owner-update.md) (excluded batch).

## Claim comparison table

| Claim | Paper evidence | Our evidence | Current verdict |
|---|---|---|---|
| Error detection | Heap, stack and global out-of-bounds and use-after-free are detected (Sec. 3); used on Chromium | Stage 2: 25 injected-error trials (5 types × 5) returned 1 with the expected category and source line; 20 clean controls returned 0 | Locally supported, for the tested cases only |
| Runtime overhead | 1.73x average slowdown on SPEC CPU2006 (Sec. 4, Fig. 2) | 12 workloads, n=15 each: paper-like 1.489–4.041x, modern 1.508–25.818x | Overhead observed; the paper's 1.73x is inconclusive (different workloads, compiler, machine) |
| Memory metric | 3.37x average, VmPeak at exit (Table 1) | GNU time peak RSS, e.g. treeadd-ref 129.48 MiB native vs 1088.45 MiB modern | Inconclusive: RSS is not VmPeak |
| Redzone | Larger heap redzones cost more memory and time (Sec. 4.3) | Stage 1 only: bisort peak RSS 31.46 → 94.49 MiB for minimum redzone 16 → 128 bytes; mst about 36.5 MiB at all three settings; n=5 | Locally supported for bisort; not repeated in Stage 2 |
| Writes-only | 26% average slowdown when only writes are checked (Sec. 4) | Not run | Not tested |
| Chromium | Over 300 previously unknown bugs (abstract) | Not attempted | Not tested |

## Three likely questions

**Q1. Why did you replace the benchmark?**
The paper used SPEC CPU2006, and our school has no licence for it. The instructor allowed an open-source substitute. We chose the LLVM test-suite because it is open, can be pinned to one commit (`d52a93a8`), and ships reference outputs, so we can check that every run is correct. The cost is that we cannot reproduce the SPEC average. We report our numbers per workload and never present them as the paper's 1.73x.

**Q2. Why do the larger inputs use a GCC comparison instead of upstream references?**
At our pinned revision, the larger inputs have upstream arguments but no matching expected output. The provided files are for the reference size only. So for the 4 larger inputs we built the same unmodified source with GCC and compared the full outputs of all 3 configurations against it. That gives 12 GCC differential checks, next to 24 upstream checks for the 8 reference workloads. A match shows the Clang builds agree with GCC. It does not prove the algorithm itself is correct.

**Q3. Why can't the perimeter change be a general or causal conclusion?**
It is one program, two inputs and one batch on one laptop. Other programs moved differently: mst went down from 1.936 to 1.743 and tsp went up from 2.882 to 3.372. The paper-like ratio for perimeter barely changed (2.001 to 2.017), and modern and paper-like differ in several settings at once. We did not collect allocation counts or hardware counters. Perimeter-large still runs only 0.387 s natively. So we can describe the change, but not explain it.

## Figure sources used in the deck

| Slide | Figure or log | Batch and configuration | Source file |
|---|---|---|---|
| 4 | Heap error and fixed-run log excerpts | Stage 2 correctness, modern diagnostic profile | `records/stage2/20261105T142515Z-caf43a/correctness/` |
| 5 | Three additional application workloads | Stage 2, modern and paper-like vs native, n=15 | `reports/stage2/figures/new-runtime.svg` |
| 6 | Larger upstream inputs | Stage 2, modern and paper-like vs native, n=15 | `reports/stage2/figures/large-runtime.svg` |

The figures were rendered to PNG for the PPT without changing their content.

## AI use

AI helped me draft the slides and these notes from the repository records and the paper. I checked the numbers against the source files listed above and will revise the wording after group feedback.

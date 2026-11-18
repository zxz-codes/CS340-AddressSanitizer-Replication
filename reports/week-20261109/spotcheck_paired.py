#!/usr/bin/env python3
"""Spot-check paired ratios against the raw Stage 2 measurement records.

Read-only. Recomputes a set of individually sampled paired ratios from
records/stage2/<batch>/measurements.json by matching (workload, configuration,
run) to the same-round native record, and independently recomputes the mean and
sample standard deviation (n-1 denominator) for two groups, covering the
time ratio and the RSS ratio.
"""
import json
import statistics
from pathlib import Path

RECORD = Path("records/stage2/20261105T142515Z-caf43a")
SAMPLED = [
    ("bisort-ref",    "asan-modern",     1),
    ("bisort-ref",    "asan-paper-like", 5),
    ("tsp-large",     "asan-modern",     3),
    ("tsp-large",     "asan-paper-like", 8),
    ("mst-large",     "asan-modern",    11),
    ("mst-large",     "asan-paper-like", 2),
    ("perimeter-ref", "asan-modern",     6),
    ("perimeter-ref", "asan-paper-like",13),
]
RECOMPUTE = [("tsp-large", "asan-modern"), ("bisort-ref", "asan-paper-like")]

measurements = json.loads((RECORD / "measurements.json").read_text())
summary = json.loads((RECORD / "summary.json").read_text())
formal = [r for r in measurements if r["phase"] == "performance"]
native = {(r["workload"], r["run"]): r for r in formal if r["configuration"] == "native"}
by_key = {(r["workload"], r["configuration"], r["run"]): r for r in formal}

print("== sampled paired rows ==")
print(f"{'workload':16} {'configuration':17} {'run':>3} {'asan s':>10} {'native s':>10} {'ratio':>9}")
for wl, cfg, run in SAMPLED:
    a = by_key[(wl, cfg, run)]
    n = native[(wl, run)]
    print(f"{wl:16} {cfg:17} {run:>3} {a['elapsed_seconds']:10.6f} "
          f"{n['elapsed_seconds']:10.6f} {a['elapsed_seconds']/n['elapsed_seconds']:9.6f}")

print()
print("== independently recomputed group statistics (n-1 denominator) ==")
for wl, cfg in RECOMPUTE:
    rows = sorted((r for r in formal if r["workload"] == wl and r["configuration"] == cfg),
                  key=lambda r: r["run"])
    entry = next(s for s in summary if s["workload"] == wl and s["configuration"] == cfg)
    for label, field, key in (("time", "elapsed_seconds", "paired_time_ratio"),
                              ("rss",  "max_rss_kib",    "paired_rss_ratio")):
        ratios = [r[field] / native[(wl, r["run"])][field] for r in rows]
        mean = statistics.mean(ratios)
        sd = statistics.stdev(ratios)
        rec = entry[key]
        same = abs(mean - rec["mean"]) < 1e-10 and abs(sd - rec["sd"]) < 1e-10
        print(f"{wl}/{cfg} {label}: n={len(ratios)} "
              f"mean={mean:.12f} sd={sd:.12f} "
              f"recorded_mean={rec['mean']:.12f} recorded_sd={rec['sd']:.12f} "
              f"{'MATCH' if same else 'MISMATCH'}")

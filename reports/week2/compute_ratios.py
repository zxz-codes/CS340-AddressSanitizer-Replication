#!/usr/bin/env python3
"""Recompute paired ASan/native timing ratios for the Week 2 report."""

from __future__ import annotations

import json
import math
import statistics
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
RECORD_DIR = (
    REPO_ROOT
    / "records"
    / "stage1"
    / "20261025T072502Z-06ebb2"
)
MEASUREMENTS_PATH = RECORD_DIR / "measurements.json"
SUMMARY_PATH = RECORD_DIR / "summary.json"

BENCHMARKS = ("bisort", "mst")
ASAN_CONFIG = "asan-modern"
NATIVE_CONFIG = "native"
RUNS = (1, 2, 3, 4, 5)


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def select_time(
    measurements: list[dict[str, Any]],
    benchmark: str,
    configuration: str,
    run: int,
) -> float:
    matches = [
        item
        for item in measurements
        if item["phase"] == "performance"
        and item["benchmark"] == benchmark
        and item["configuration"] == configuration
        and item["run"] == run
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Expected one record for {benchmark}/{configuration}/run {run}; "
            f"found {len(matches)}"
        )
    return float(matches[0]["elapsed_seconds"])


def find_summary(
    summaries: list[dict[str, Any]], benchmark: str
) -> dict[str, float | int]:
    matches = [
        item
        for item in summaries
        if item["phase"] == "performance"
        and item["benchmark"] == benchmark
        and item["configuration"] == ASAN_CONFIG
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Expected one summary entry for {benchmark}/{ASAN_CONFIG}; "
            f"found {len(matches)}"
        )
    return matches[0]["paired_time_ratio"]


def main() -> None:
    measurements = load_json(MEASUREMENTS_PATH)
    summaries = load_json(SUMMARY_PATH)

    print("| Program | Run | Native (s) | ASan modern (s) | ratio_i |")
    print("|---|---:|---:|---:|---:|")

    for benchmark in BENCHMARKS:
        ratios: list[float] = []

        for run in RUNS:
            native = select_time(
                measurements, benchmark, NATIVE_CONFIG, run
            )
            asan = select_time(measurements, benchmark, ASAN_CONFIG, run)
            ratio = asan / native
            ratios.append(ratio)
            print(
                f"| {benchmark} | {run} | {native:.6f} | "
                f"{asan:.6f} | {ratio:.6f} |"
            )

        mean_ratio = statistics.mean(ratios)
        sample_sd = statistics.stdev(ratios)
        check_sd = math.sqrt(
            sum((ratio - mean_ratio) ** 2 for ratio in ratios)
            / (len(ratios) - 1)
        )
        summary = find_summary(summaries, benchmark)
        summary_mean = float(summary["mean"])
        summary_sd = float(summary["sd"])
        summary_n = int(summary["n"])

        if summary_n != len(ratios):
            raise AssertionError(
                f"{benchmark}: summary n={summary_n}, computed n={len(ratios)}"
            )
        if not math.isclose(
            mean_ratio, summary_mean, rel_tol=1e-15, abs_tol=0.0
        ):
            raise AssertionError(
                f"{benchmark}: mean mismatch "
                f"({mean_ratio} != {summary_mean})"
            )
        if not math.isclose(
            sample_sd, summary_sd, rel_tol=1e-15, abs_tol=0.0
        ):
            raise AssertionError(
                f"{benchmark}: sample SD mismatch "
                f"({sample_sd} != {summary_sd})"
            )

        print()
        print(f"{benchmark} ratios: {[f'{x:.6f}' for x in ratios]}")
        print(f"{benchmark} ratio sum: {sum(ratios):.6f}")
        print(f"{benchmark} mean: {mean_ratio:.6f}")
        print(f"{benchmark} sample_sd (statistics.stdev): {sample_sd:.6f}")
        print(f"{benchmark} sample_sd (formula check): {check_sd:.6f}")
        print(
            f"{benchmark} summary.json mean/sd: "
            f"{summary_mean:.6f} / {summary_sd:.6f}"
        )
        print(
            f"{benchmark} mean difference: {mean_ratio - summary_mean:.15e}"
        )
        print(
            f"{benchmark} sample_sd difference: {sample_sd - summary_sd:.15e}"
        )
        print(
            f"{benchmark} summary n: {summary_n}"
        )
        print()


if __name__ == "__main__":
    main()

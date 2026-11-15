#!/usr/bin/env python3
"""Compute final Stage 2 paired time and RSS ratios from raw JSON.

Only Python's standard library is used. The script resolves the accepted
record from records/latest-stage2.txt and reads measurements.json directly.
No aggregate CSV is read.
"""

from __future__ import annotations

import json
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNS = tuple(range(1, 16))
WORKLOADS = ("bisort", "mst", "perimeter", "tsp")
INPUT_SIZES = ("ref", "large")
CONFIGURATIONS = ("asan-modern", "asan-paper-like")


@dataclass(frozen=True)
class FinalRatio:
    workload: str
    input_size: str
    configuration: str
    native_time_mean: float
    asan_time_mean: float
    time_ratios: tuple[float, ...]
    time_ratio_mean: float
    time_ratio_sd: float
    native_rss_mean: float
    asan_rss_mean: float
    rss_ratios: tuple[float, ...]
    rss_ratio_mean: float
    rss_ratio_sd: float


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def records_by_run(
    measurements: list[dict[str, Any]],
    workload: str,
    configuration: str,
) -> dict[int, dict[str, Any]]:
    matches = [
        item
        for item in measurements
        if item["phase"] == "performance"
        and item["workload"] == workload
        and item["configuration"] == configuration
    ]

    by_run: dict[int, dict[str, Any]] = {}
    duplicates: list[int] = []
    for item in matches:
        run = int(item["run"])
        if run in by_run:
            duplicates.append(run)
        else:
            by_run[run] = item

    expected = set(RUNS)
    actual = set(by_run)
    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)
    if duplicates or missing or unexpected:
        raise ValueError(
            f"{workload}/{configuration}: duplicates={sorted(set(duplicates))}, "
            f"missing={missing}, unexpected={unexpected}"
        )
    return by_run


def mean_and_sample_sd(values: tuple[float, ...]) -> tuple[float, float]:
    return statistics.mean(values), statistics.stdev(values)


def compute_group(
    measurements: list[dict[str, Any]],
    base_workload: str,
    input_size: str,
    configuration: str,
) -> FinalRatio:
    workload = f"{base_workload}-{input_size}"
    native = records_by_run(measurements, workload, "native")
    asan = records_by_run(measurements, workload, configuration)

    native_times = tuple(
        float(native[run]["elapsed_seconds"]) for run in RUNS
    )
    asan_times = tuple(
        float(asan[run]["elapsed_seconds"]) for run in RUNS
    )
    native_rss = tuple(
        float(native[run]["max_rss_kib"]) for run in RUNS
    )
    asan_rss = tuple(
        float(asan[run]["max_rss_kib"]) for run in RUNS
    )

    time_ratios = tuple(
        asan_time / native_time
        for native_time, asan_time in zip(native_times, asan_times)
    )
    rss_ratios = tuple(
        asan_value / native_value
        for native_value, asan_value in zip(native_rss, asan_rss)
    )

    time_ratio_mean, time_ratio_sd = mean_and_sample_sd(time_ratios)
    rss_ratio_mean, rss_ratio_sd = mean_and_sample_sd(rss_ratios)
    return FinalRatio(
        workload=base_workload,
        input_size=input_size,
        configuration=configuration,
        native_time_mean=statistics.mean(native_times),
        asan_time_mean=statistics.mean(asan_times),
        time_ratios=time_ratios,
        time_ratio_mean=time_ratio_mean,
        time_ratio_sd=time_ratio_sd,
        native_rss_mean=statistics.mean(native_rss),
        asan_rss_mean=statistics.mean(asan_rss),
        rss_ratios=rss_ratios,
        rss_ratio_mean=rss_ratio_mean,
        rss_ratio_sd=rss_ratio_sd,
    )


def source_locator(result: FinalRatio) -> str:
    workload = f"{result.workload}-{result.input_size}"
    return (
        f"phase=performance; workload={workload}; "
        f"configs=native+{result.configuration}; runs=1-15"
    )


def main() -> None:
    pointer_path = REPO_ROOT / "records" / "latest-stage2.txt"
    record_relative = pointer_path.read_text(encoding="utf-8").strip()
    record_dir = REPO_ROOT / record_relative
    measurements_path = record_dir / "measurements.json"
    measurements = load_json(measurements_path)

    results = [
        compute_group(measurements, workload, input_size, configuration)
        for workload in WORKLOADS
        for input_size in INPUT_SIZES
        for configuration in CONFIGURATIONS
    ]

    print(f"Source file: {measurements_path}")
    print(
        "Every row uses phase=performance records with matching workload "
        "and run for native and ASan. Ratios are computed per run first."
    )
    print("Time unit: seconds. RSS unit: KiB.")
    print(
        "RSS is GNU time maximum resident set size; it is not VmPeak."
    )
    print()
    print(
        "| Workload | Input | ASan config | n | Native time mean (s) | "
        "ASan time mean (s) | Time ratio mean | Time ratio sample SD | "
        "Native RSS mean (KiB) | ASan RSS mean (KiB) | RSS ratio mean | "
        "RSS ratio sample SD | Trial locator |"
    )
    print(
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"
    )
    for result in results:
        print(
            f"| {result.workload} | {result.input_size} | "
            f"{result.configuration} | {len(result.time_ratios)} | "
            f"{result.native_time_mean:.3f} | "
            f"{result.asan_time_mean:.3f} | "
            f"{result.time_ratio_mean:.3f} | "
            f"{result.time_ratio_sd:.3f} | "
            f"{result.native_rss_mean:.3f} | "
            f"{result.asan_rss_mean:.3f} | "
            f"{result.rss_ratio_mean:.3f} | "
            f"{result.rss_ratio_sd:.3f} | "
            f"{source_locator(result)} |"
        )

    modern = {
        (result.workload, result.input_size): result
        for result in results
        if result.configuration == "asan-modern"
    }
    print()
    print("Modern time-ratio means by input:")
    for workload in WORKLOADS:
        ref = modern[workload, "ref"]
        large = modern[workload, "large"]
        direction = "decrease" if large.time_ratio_mean < ref.time_ratio_mean else "increase"
        print(
            f"{workload}: ref={ref.time_ratio_mean:.3f}, "
            f"large={large.time_ratio_mean:.3f}, {direction}"
        )

    print()
    print(
        "Observation only: modern mean ratios decrease from ref to large "
        "for bisort and mst, and increase for perimeter and tsp."
    )


if __name__ == "__main__":
    main()

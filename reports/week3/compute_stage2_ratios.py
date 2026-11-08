#!/usr/bin/env python3
"""Recompute Stage 2 paired ASan/native timing statistics.

The script reads the frozen Stage 2 measurements and summary files, checks
run integrity, computes unrounded per-run ratios, prints the complete pairing
and summary tables, and writes a two-panel SVG figure. Only the Python
standard library is required.
"""

from __future__ import annotations

import json
import math
import statistics
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
RECORD_DIR = (
    REPO_ROOT
    / "records"
    / "stage2"
    / "20261105T142515Z-caf43a"
)
MEASUREMENTS_PATH = RECORD_DIR / "measurements.json"
SUMMARY_PATH = RECORD_DIR / "summary.json"
FIGURE_PATH = (
    REPO_ROOT
    / "reports"
    / "week3"
    / "figures"
    / "stage2-analysis.svg"
)

ASAN_CONFIGURATION = "asan-modern"
NATIVE_CONFIGURATION = "native"
EXPECTED_RUNS = tuple(range(1, 16))

TARGET_WORKLOADS = (
    "bullet-ref",
    "pairlocalalign-ref",
    "perimeter-ref",
    "perimeter-large",
)

SHORT_LABELS = {
    "bullet-ref": "Bullet",
    "pairlocalalign-ref": "MAFFT pairlocalalign",
    "perimeter-ref": "Perimeter input 10",
    "perimeter-large": "Perimeter input 11",
}


@dataclass(frozen=True)
class RatioResult:
    workload: str
    native_times: tuple[float, ...]
    asan_times: tuple[float, ...]
    ratios: tuple[float, ...]
    native_mean: float
    asan_mean: float
    ratio_mean: float
    ratio_sd: float
    summary_ratio_mean: float
    summary_ratio_sd: float
    summary_ratio_n: int
    mean_difference: float
    sd_difference: float
    native_summary_mean: float
    asan_summary_mean: float
    native_mean_difference: float
    asan_mean_difference: float


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def records_by_run(
    measurements: list[dict[str, Any]],
    workload: str,
    configuration: str,
) -> tuple[dict[int, float], list[int], list[int]]:
    """Return one performance time per expected run and integrity details."""
    matches = [
        item
        for item in measurements
        if item["phase"] == "performance"
        and item["workload"] == workload
        and item["configuration"] == configuration
    ]
    by_run: dict[int, float] = {}
    duplicate_runs: list[int] = []

    for item in matches:
        run = int(item["run"])
        if run in by_run:
            duplicate_runs.append(run)
        else:
            by_run[run] = float(item["elapsed_seconds"])

    expected = set(EXPECTED_RUNS)
    found = set(by_run)
    missing_runs = sorted(expected - found)
    unexpected_runs = sorted(found - expected)
    if missing_runs or duplicate_runs or unexpected_runs:
        raise ValueError(
            f"{workload}/{configuration} integrity failure: "
            f"missing={missing_runs}, duplicates={sorted(set(duplicate_runs))}, "
            f"unexpected={unexpected_runs}"
        )
    return by_run, missing_runs, sorted(set(duplicate_runs))


def summary_entry(
    summaries: list[dict[str, Any]],
    workload: str,
    configuration: str,
) -> dict[str, Any]:
    matches = [
        item
        for item in summaries
        if item["workload"] == workload
        and item["configuration"] == configuration
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Expected one summary entry for {workload}/{configuration}; "
            f"found {len(matches)}"
        )
    return matches[0]


def analyze(
    measurements: list[dict[str, Any]],
    summaries: list[dict[str, Any]],
) -> dict[str, RatioResult]:
    results: dict[str, RatioResult] = {}

    for workload in TARGET_WORKLOADS:
        native, native_missing, native_duplicates = records_by_run(
            measurements, workload, NATIVE_CONFIGURATION
        )
        asan, asan_missing, asan_duplicates = records_by_run(
            measurements, workload, ASAN_CONFIGURATION
        )
        if set(native) != set(asan):
            raise ValueError(
                f"{workload}: native and ASan runs cannot be paired: "
                f"native={sorted(native)}, asan={sorted(asan)}"
            )

        print(
            f"Integrity {workload}: native n={len(native)}, "
            f"missing={native_missing}, duplicates={native_duplicates}; "
            f"ASan n={len(asan)}, missing={asan_missing}, "
            f"duplicates={asan_duplicates}."
        )

        runs = sorted(native)
        native_times = tuple(native[run] for run in runs)
        asan_times = tuple(asan[run] for run in runs)
        ratios = tuple(
            asan[run] / native[run]
            for run in runs
        )

        ratio_summary = summary_entry(
            summaries, workload, ASAN_CONFIGURATION
        )["paired_time_ratio"]
        native_summary = summary_entry(
            summaries, workload, NATIVE_CONFIGURATION
        )["elapsed_seconds"]
        asan_summary = summary_entry(
            summaries, workload, ASAN_CONFIGURATION
        )["elapsed_seconds"]

        ratio_mean = statistics.mean(ratios)
        ratio_sd = statistics.stdev(ratios)
        native_mean = statistics.mean(native_times)
        asan_mean = statistics.mean(asan_times)

        if int(ratio_summary["n"]) != len(ratios):
            raise ValueError(
                f"{workload}: summary n={ratio_summary['n']} "
                f"but paired n={len(ratios)}"
            )
        if not math.isclose(
            ratio_mean,
            float(ratio_summary["mean"]),
            rel_tol=1e-15,
            abs_tol=0.0,
        ):
            raise ValueError(f"{workload}: summary ratio mean mismatch")
        if not math.isclose(
            ratio_sd,
            float(ratio_summary["sd"]),
            rel_tol=1e-15,
            abs_tol=0.0,
        ):
            raise ValueError(f"{workload}: summary ratio SD mismatch")

        results[workload] = RatioResult(
            workload=workload,
            native_times=native_times,
            asan_times=asan_times,
            ratios=ratios,
            native_mean=native_mean,
            asan_mean=asan_mean,
            ratio_mean=ratio_mean,
            ratio_sd=ratio_sd,
            summary_ratio_mean=float(ratio_summary["mean"]),
            summary_ratio_sd=float(ratio_summary["sd"]),
            summary_ratio_n=int(ratio_summary["n"]),
            mean_difference=ratio_mean - float(ratio_summary["mean"]),
            sd_difference=ratio_sd - float(ratio_summary["sd"]),
            native_summary_mean=float(native_summary["mean"]),
            asan_summary_mean=float(asan_summary["mean"]),
            native_mean_difference=native_mean - float(native_summary["mean"]),
            asan_mean_difference=asan_mean - float(asan_summary["mean"]),
        )

    return results


def print_pairing_table(results: dict[str, RatioResult]) -> None:
    print("\nPer-run time pairs and ratios")
    print("| Workload | Run | Native (s) | ASan modern (s) | Ratio |")
    print("|---|---:|---:|---:|---:|")
    for workload in TARGET_WORKLOADS:
        result = results[workload]
        for run, native, asan, ratio in zip(
            EXPECTED_RUNS,
            result.native_times,
            result.asan_times,
            result.ratios,
        ):
            print(
                f"| {workload} | {run} | {native:.3f} | {asan:.3f} | "
                f"{ratio:.3f} |"
            )


def print_summary_tables(results: dict[str, RatioResult]) -> None:
    print("\nComputed group statistics")
    print(
        "| Workload | Native mean (s) | ASan mean (s) | "
        "Paired-ratio mean | Sample SD | n |"
    )
    print("|---|---:|---:|---:|---:|---:|")
    for workload in TARGET_WORKLOADS:
        result = results[workload]
        print(
            f"| {workload} | {result.native_mean:.3f} | "
            f"{result.asan_mean:.3f} | {result.ratio_mean:.3f} | "
            f"{result.ratio_sd:.3f} | {len(result.ratios)} |"
        )

    print("\nSummary-file checks")
    print(
        "| Workload | summary mean | summary SD | summary n | "
        "mean diff | SD diff | native-mean diff | ASan-mean diff |"
    )
    print("|---|---:|---:|---:|---:|---:|---:|---:|")
    for workload in TARGET_WORKLOADS:
        result = results[workload]
        print(
            f"| {workload} | {result.summary_ratio_mean:.6f} | "
            f"{result.summary_ratio_sd:.6f} | {result.summary_ratio_n} | "
            f"{result.mean_difference:.15e} | "
            f"{result.sd_difference:.15e} | "
            f"{result.native_mean_difference:.15e} | "
            f"{result.asan_mean_difference:.15e} |"
        )


def print_comparisons(results: dict[str, RatioResult]) -> None:
    bullet = results["bullet-ref"]
    mafft = results["pairlocalalign-ref"]
    perimeter_ref = results["perimeter-ref"]
    perimeter_large = results["perimeter-large"]

    print("\nDescriptive comparisons")
    print(
        f"Bullet minus MAFFT paired-ratio mean: "
        f"{bullet.ratio_mean - mafft.ratio_mean:.6f}"
    )
    print(
        f"Bullet minus MAFFT sample SD: "
        f"{bullet.ratio_sd - mafft.ratio_sd:.6f}"
    )
    print(
        f"Perimeter input 11 minus input 10 paired-ratio mean: "
        f"{perimeter_large.ratio_mean - perimeter_ref.ratio_mean:.6f}"
    )
    print(
        f"Perimeter input 11 minus input 10 sample SD: "
        f"{perimeter_large.ratio_sd - perimeter_ref.ratio_sd:.6f}"
    )


def svg_text(
    x: float,
    y: float,
    text: str,
    *,
    size: int = 16,
    weight: str = "normal",
    anchor: str = "start",
    fill: str = "#243746",
) -> str:
    return (
        f'<text x="{x:.2f}" y="{y:.2f}" text-anchor="{anchor}" '
        f'font-family="Arial, Helvetica, sans-serif" font-size="{size}" '
        f'font-weight="{weight}" fill="{fill}">{escape(text)}</text>'
    )


def add_panel(
    parts: list[str],
    *,
    x0: float,
    width: float,
    title: str,
    subtitle: str,
    workloads: tuple[str, ...],
    colors: tuple[str, ...],
    results: dict[str, RatioResult],
) -> None:
    top = 155.0
    bottom = 535.0
    left = x0 + 70.0
    plot_width = width - 100.0
    values = []
    for workload in workloads:
        result = results[workload]
        values.extend((*result.ratios, result.ratio_mean + result.ratio_sd))
    y_max = max(values) * 1.30

    panel_right = x0 + width
    parts.append(
        f'<rect x="{x0:.2f}" y="92" width="{width:.2f}" height="500" '
        'rx="12" fill="#ffffff" stroke="#d6dee5" stroke-width="1.5"/>'
    )
    parts.append(svg_text(x0 + 50, 126, title, size=20, weight="bold"))
    parts.append(
        svg_text(
            x0 + 50,
            148,
            subtitle,
            size=13,
            fill="#526777",
        )
    )

    tick_count = 5
    for tick_index in range(tick_count + 1):
        tick_value = y_max * tick_index / tick_count
        y = bottom - (bottom - top) * tick_index / tick_count
        parts.append(
            f'<line x1="{left:.2f}" y1="{y:.2f}" '
            f'x2="{left + plot_width:.2f}" y2="{y:.2f}" '
            'stroke="#e3e9ee" stroke-width="1"/>'
        )
        parts.append(
            svg_text(
                left - 12,
                y + 5,
                f"{tick_value:.1f}",
                size=12,
                anchor="end",
                fill="#526777",
            )
        )

    parts.append(
        f'<line x1="{left:.2f}" y1="{top:.2f}" '
        f'x2="{left:.2f}" y2="{bottom:.2f}" '
        'stroke="#526777" stroke-width="1.2"/>'
    )
    parts.append(
        f'<line x1="{left:.2f}" y1="{bottom:.2f}" '
        f'x2="{left + plot_width:.2f}" y2="{bottom:.2f}" '
        'stroke="#526777" stroke-width="1.2"/>'
    )

    centers = (
        left + plot_width * 0.30,
        left + plot_width * 0.72,
    )
    bar_width = min(105.0, plot_width * 0.24)

    for workload, color, center in zip(workloads, colors, centers):
        result = results[workload]
        mean_y = bottom - (
            result.ratio_mean / y_max
        ) * (bottom - top)
        low_y = bottom - (
            max(0.0, result.ratio_mean - result.ratio_sd) / y_max
        ) * (bottom - top)
        high_y = bottom - (
            (result.ratio_mean + result.ratio_sd) / y_max
        ) * (bottom - top)

        parts.append(
            f'<rect x="{center - bar_width / 2:.2f}" y="{mean_y:.2f}" '
            f'width="{bar_width:.2f}" height="{bottom - mean_y:.2f}" '
            f'rx="5" fill="{color}" fill-opacity="0.78"/>'
        )
        parts.append(
            f'<line x1="{center:.2f}" y1="{low_y:.2f}" '
            f'x2="{center:.2f}" y2="{high_y:.2f}" '
            'stroke="#172733" stroke-width="2"/>'
        )
        parts.append(
            f'<line x1="{center - 18:.2f}" y1="{low_y:.2f}" '
            f'x2="{center + 18:.2f}" y2="{low_y:.2f}" '
            'stroke="#172733" stroke-width="2"/>'
        )
        parts.append(
            f'<line x1="{center - 18:.2f}" y1="{high_y:.2f}" '
            f'x2="{center + 18:.2f}" y2="{high_y:.2f}" '
            'stroke="#172733" stroke-width="2"/>'
        )

        point_offsets = tuple(
            -22 + 44 * index / (len(result.ratios) - 1)
            for index in range(len(result.ratios))
        )
        for offset, ratio in zip(point_offsets, result.ratios):
            point_y = bottom - (ratio / y_max) * (bottom - top)
            parts.append(
                f'<circle cx="{center + offset:.2f}" cy="{point_y:.2f}" '
                'r="3.1" fill="#ffffff" fill-opacity="0.86" '
                'stroke="#172733" stroke-width="1.4"/>'
            )

        label = SHORT_LABELS[workload]
        if workload == "pairlocalalign-ref":
            label = "MAFFT"
            secondary = "pairlocalalign"
        else:
            secondary = ""
        parts.append(
            svg_text(
                center,
                bottom + 27,
                label,
                size=14,
                weight="bold",
                anchor="middle",
            )
        )
        if secondary:
            parts.append(
                svg_text(
                    center,
                    bottom + 45,
                    secondary,
                    size=12,
                    anchor="middle",
                    fill="#526777",
                )
            )

        annotation_y = bottom - (
            max(max(result.ratios), result.ratio_mean + result.ratio_sd) / y_max
        ) * (bottom - top)
        parts.append(
            svg_text(
                center,
                annotation_y - 14,
                f"{result.ratio_mean:.3f}",
                size=15,
                weight="bold",
                anchor="middle",
            )
        )
        parts.append(
            svg_text(
                center,
                annotation_y - 31,
                f"+/- {result.ratio_sd:.3f}",
                size=12,
                anchor="middle",
                fill="#526777",
            )
        )

    parts.append(
        f'<text x="{x0 + 23:.2f}" y="{(top + bottom) / 2:.2f}" '
        f'text-anchor="middle" '
        f'transform="rotate(-90 {x0 + 23:.2f} {(top + bottom) / 2:.2f})" '
        'font-family="Arial, Helvetica, sans-serif" font-size="12" '
        'fill="#526777">ASan/native ratio</text>'
    )


def write_svg(results: dict[str, RatioResult], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="640" '
        'viewBox="0 0 1200 640" role="img" '
        'aria-labelledby="figure-title figure-desc">',
        '<title id="figure-title">Stage 2 paired ASan timing ratios</title>',
        '<desc id="figure-desc">Two panels show mean paired ASan/native '
        'elapsed-time ratios with sample standard deviation error bars. '
        'The left panel compares Bullet with MAFFT pairlocalalign. The '
        'right panel compares Perimeter inputs 10 and 11.</desc>',
        '<rect width="1200" height="640" fill="#f4f7f9"/>',
        svg_text(
            44,
            43,
            "Stage 2 paired ASan timing overhead",
            size=26,
            weight="bold",
        ),
        svg_text(
            44,
            69,
            "Higher values indicate a larger ASan/native elapsed-time ratio. "
            "Panels use separate y-axis scales.",
            size=14,
            fill="#526777",
        ),
    ]
    add_panel(
        parts,
        x0=30,
        width=565,
        title="Application comparison",
        subtitle="Bullet vs MAFFT (pairlocalalign ref); n = 15",
        workloads=("bullet-ref", "pairlocalalign-ref"),
        colors=("#167a87", "#d6782f"),
        results=results,
    )
    add_panel(
        parts,
        x0=615,
        width=555,
        title="Perimeter input comparison",
        subtitle="Same program; reference vs larger input; n = 15",
        workloads=("perimeter-ref", "perimeter-large"),
        colors=("#167a87", "#d6782f"),
        results=results,
    )
    parts.append(
        svg_text(
            44,
            624,
            "Error bars describe sample variability (n-1 denominator). "
            "Open circles show individual paired ratios; n = 15 per group. "
            "The figure does not establish statistical significance.",
            size=12,
            fill="#526777",
        )
    )
    parts.append("</svg>")
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def main() -> None:
    measurements = load_json(MEASUREMENTS_PATH)
    summaries = load_json(SUMMARY_PATH)
    results = analyze(measurements, summaries)
    print_pairing_table(results)
    print_summary_tables(results)
    print_comparisons(results)
    write_svg(results, FIGURE_PATH)
    print(f"\nWrote figure: {FIGURE_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()

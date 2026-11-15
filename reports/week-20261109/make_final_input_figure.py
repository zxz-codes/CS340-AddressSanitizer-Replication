#!/usr/bin/env python3
"""Draw the final Stage 2 reference/large-input comparison as editable SVG.

The script reads only records/latest-stage2.txt and the raw measurements.json
from the accepted Stage 2 record. It computes every plotted ratio from
same-run ASan/native pairs and writes one two-panel SVG.
"""

from __future__ import annotations

import json
import statistics
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
POINTER_PATH = REPO_ROOT / "records" / "latest-stage2.txt"
OUTPUT_PATH = (
    REPO_ROOT
    / "reports"
    / "week-20261109"
    / "final-input-size-analysis.svg"
)

RUNS = tuple(range(1, 16))
WORKLOADS = ("bisort", "mst", "perimeter", "tsp")
INPUTS = ("ref", "large")
CONFIGURATIONS = ("asan-modern", "asan-paper-like")

SERIES = (
    ("Modern / ref", "asan-modern", "ref", "#7dcbd2"),
    ("Modern / large", "asan-modern", "large", "#087f8c"),
    ("Paper-like / ref", "asan-paper-like", "ref", "#f1b26b"),
    ("Paper-like / large", "asan-paper-like", "large", "#c65f1a"),
)


@dataclass(frozen=True)
class GroupStatistics:
    workload: str
    input_size: str
    configuration: str
    time_ratio_mean: float
    time_ratio_sd: float
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

    missing = sorted(set(RUNS) - set(by_run))
    unexpected = sorted(set(by_run) - set(RUNS))
    if duplicates or missing or unexpected:
        raise ValueError(
            f"{workload}/{configuration}: duplicates={duplicates}, "
            f"missing={missing}, unexpected={unexpected}"
        )
    return by_run


def calculate(
    measurements: list[dict[str, Any]],
    workload: str,
    input_size: str,
    configuration: str,
) -> GroupStatistics:
    full_name = f"{workload}-{input_size}"
    native = records_by_run(measurements, full_name, "native")
    asan = records_by_run(measurements, full_name, configuration)

    time_ratios = tuple(
        float(asan[run]["elapsed_seconds"])
        / float(native[run]["elapsed_seconds"])
        for run in RUNS
    )
    rss_ratios = tuple(
        float(asan[run]["max_rss_kib"])
        / float(native[run]["max_rss_kib"])
        for run in RUNS
    )
    return GroupStatistics(
        workload=workload,
        input_size=input_size,
        configuration=configuration,
        time_ratio_mean=statistics.mean(time_ratios),
        time_ratio_sd=statistics.stdev(time_ratios),
        rss_ratio_mean=statistics.mean(rss_ratios),
        rss_ratio_sd=statistics.stdev(rss_ratios),
    )


def svg_text(
    x: float,
    y: float,
    text: str,
    *,
    size: int = 14,
    weight: str = "normal",
    anchor: str = "start",
    fill: str = "#20313d",
    rotate: float | None = None,
) -> str:
    transform = (
        f' transform="rotate({rotate:.2f} {x:.2f} {y:.2f})"'
        if rotate is not None
        else ""
    )
    return (
        f'<text x="{x:.2f}" y="{y:.2f}" text-anchor="{anchor}"{transform} '
        'font-family="Arial, Helvetica, sans-serif" '
        f'font-size="{size}" font-weight="{weight}" '
        f'fill="{fill}">{escape(text)}</text>'
    )


def draw_panel(
    parts: list[str],
    *,
    x0: float,
    width: float,
    title: str,
    unit_note: str,
    results: dict[tuple[str, str, str], GroupStatistics],
    metric: str,
) -> None:
    top = 220.0
    bottom = 620.0
    left = x0 + 72.0
    plot_right = x0 + width - 26.0
    plot_width = plot_right - left
    upper_values = []
    for workload in WORKLOADS:
        for _, configuration, input_size, _ in SERIES:
            item = results[workload, input_size, configuration]
            mean = getattr(item, f"{metric}_mean")
            sd = getattr(item, f"{metric}_sd")
            upper_values.append(mean + sd)
    y_max = max(upper_values) * 1.22

    parts.append(
        f'<rect x="{x0:.2f}" y="98" width="{width:.2f}" height="595" '
        'rx="14" fill="#ffffff" stroke="#d7e0e6" stroke-width="1.5"/>'
    )
    parts.append(svg_text(x0 + 27, 133, title, size=21, weight="bold"))
    parts.append(
        svg_text(
            x0 + 27,
            158,
            "Mean of 15 same-run ASan/native ratios; n = 15",
            size=13,
            fill="#536775",
        )
    )

    for tick_index in range(6):
        value = y_max * tick_index / 5
        y = bottom - (bottom - top) * tick_index / 5
        parts.append(
            f'<line x1="{left:.2f}" y1="{y:.2f}" x2="{plot_right:.2f}" '
            f'y2="{y:.2f}" stroke="#e4eaee" stroke-width="1"/>'
        )
        parts.append(
            svg_text(
                left - 10,
                y + 5,
                f"{value:.1f}",
                size=11,
                anchor="end",
                fill="#536775",
            )
        )

    parts.append(
        f'<line x1="{left:.2f}" y1="{top:.2f}" x2="{left:.2f}" '
        f'y2="{bottom:.2f}" stroke="#536775" stroke-width="1.2"/>'
    )
    parts.append(
        f'<line x1="{left:.2f}" y1="{bottom:.2f}" '
        f'x2="{plot_right:.2f}" y2="{bottom:.2f}" '
        'stroke="#536775" stroke-width="1.2"/>'
    )

    group_width = plot_width / len(WORKLOADS)
    bar_width = 22.0
    bar_step = 31.0
    series_offset = (len(SERIES) - 1) * bar_step / 2

    for group_index, workload in enumerate(WORKLOADS):
        group_center = left + group_width * (group_index + 0.5)
        parts.append(
            svg_text(
                group_center,
                bottom + 29,
                workload,
                size=14,
                weight="bold",
                anchor="middle",
            )
        )
        parts.append(
            svg_text(
                group_center,
                bottom + 48,
                "ref -> large",
                size=11,
                anchor="middle",
                fill="#536775",
            )
        )

        for series_index, (_, configuration, input_size, color) in enumerate(
            SERIES
        ):
            item = results[workload, input_size, configuration]
            mean = getattr(item, f"{metric}_mean")
            sd = getattr(item, f"{metric}_sd")
            center = (
                group_center
                - series_offset
                + series_index * bar_step
            )
            mean_y = bottom - (mean / y_max) * (bottom - top)
            low = max(0.0, mean - sd)
            low_y = bottom - (low / y_max) * (bottom - top)
            high_y = bottom - (
                (mean + sd) / y_max
            ) * (bottom - top)

            parts.append(
                f'<rect x="{center - bar_width / 2:.2f}" y="{mean_y:.2f}" '
                f'width="{bar_width:.2f}" height="{bottom - mean_y:.2f}" '
                f'rx="4" fill="{color}"/>'
            )
            parts.append(
                f'<line x1="{center:.2f}" y1="{low_y:.2f}" '
                f'x2="{center:.2f}" y2="{high_y:.2f}" '
                'stroke="#172733" stroke-width="1.8"/>'
            )
            parts.append(
                f'<line x1="{center - 8:.2f}" y1="{low_y:.2f}" '
                f'x2="{center + 8:.2f}" y2="{low_y:.2f}" '
                'stroke="#172733" stroke-width="1.8"/>'
            )
            parts.append(
                f'<line x1="{center - 8:.2f}" y1="{high_y:.2f}" '
                f'x2="{center + 8:.2f}" y2="{high_y:.2f}" '
                'stroke="#172733" stroke-width="1.8"/>'
            )
            parts.append(
                svg_text(
                    center,
                    high_y - 8,
                    f"{mean:.3f}",
                    size=10,
                    weight="bold",
                    anchor="middle",
                )
            )

    parts.append(
        svg_text(
            x0 + 20,
            (top + bottom) / 2,
            unit_note,
            size=11,
            anchor="middle",
            fill="#536775",
            rotate=-90,
        )
    )


def write_svg(
    results: dict[tuple[str, str, str], GroupStatistics],
    path: Path,
) -> None:
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="780" '
        'viewBox="0 0 1400 780" role="img" '
        'aria-labelledby="figure-title figure-desc">',
        '<title id="figure-title">Final Stage 2 input-size comparison</title>',
        '<desc id="figure-desc">Two panels compare reference and large-input '
        'paired ASan/native ratios for elapsed time and peak resident memory '
        'across bisort, mst, perimeter, and tsp, with modern and paper-like '
        'ASan profiles. Error bars are sample standard deviations, n=15. '
        'The memory panel uses KiB.</desc>',
        '<rect width="1400" height="780" fill="#f3f6f8"/>',
        svg_text(
            35,
            39,
            "Final Stage 2 input-size comparison",
            size=27,
            weight="bold",
        ),
        svg_text(
            35,
            67,
            "Same-run ASan/native ratio means; error bars = sample SD; "
            "n = 15. Panels use separate y-axis scales.",
            size=14,
            fill="#536775",
        ),
    ]

    legend_x = 35
    legend_y = 83
    for index, (label, _, _, color) in enumerate(SERIES):
        x = legend_x + index * 285
        parts.append(
            f'<rect x="{x}" y="{legend_y}" width="14" height="14" '
            f'rx="2" fill="{color}"/>'
        )
        parts.append(svg_text(x + 21, legend_y + 12, label, size=13))

    draw_panel(
        parts,
        x0=25,
        width=675,
        title="Elapsed-time overhead",
        unit_note="ASan/native time ratio",
        results=results,
        metric="time_ratio",
    )
    draw_panel(
        parts,
        x0=700,
        width=675,
        title="Peak resident-memory overhead",
        unit_note="ASan/native RSS ratio",
        results=results,
        metric="rss_ratio",
    )

    parts.append(
        svg_text(
            35,
            744,
            "Ratios are dimensionless. RSS is GNU time maximum resident set, "
            "reported with numerator and denominator in KiB.",
            size=12,
            fill="#536775",
        )
    )
    parts.append(
        svg_text(
            35,
            764,
            "Sample SD describes the 15 saved runs; it is not a confidence "
            "interval or statistical-significance test.",
            size=12,
            fill="#536775",
        )
    )
    parts.append("</svg>")
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def main() -> None:
    record_relative = POINTER_PATH.read_text(encoding="utf-8").strip()
    measurements_path = REPO_ROOT / record_relative / "measurements.json"
    measurements = load_json(measurements_path)

    results = {
        (workload, input_size, configuration): calculate(
            measurements, workload, input_size, configuration
        )
        for workload in WORKLOADS
        for input_size in INPUTS
        for configuration in CONFIGURATIONS
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    write_svg(results, OUTPUT_PATH)

    print(f"Source: {measurements_path}")
    print(f"Wrote: {OUTPUT_PATH}")
    for workload in WORKLOADS:
        for _, configuration, input_size, _ in SERIES:
            item = results[workload, input_size, configuration]
            print(
                f"{workload}-{input_size} {configuration}: "
                f"time={item.time_ratio_mean:.3f} +/- "
                f"{item.time_ratio_sd:.3f}, "
                f"RSS={item.rss_ratio_mean:.3f} +/- "
                f"{item.rss_ratio_sd:.3f}, n=15"
            )


if __name__ == "__main__":
    main()

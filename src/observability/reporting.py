from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.utils import write_text


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    """Render a minimal markdown table."""
    header_line = "| " + " | ".join(headers) + " |"
    sep_line = "|" + "|".join(" --- " for _ in headers) + "|"
    body = "\n".join("| " + " | ".join(row) + " |" for row in rows)
    return f"{header_line}\n{sep_line}\n{body}"


def _check_summary(quality: dict[str, Any]) -> str:
    summary = quality.get("summary", {})
    lines = [
        f"- **Total checks:** {summary.get('total_checks', '?')}",
        f"- **Passed:** {summary.get('passed', '?')}",
        f"- **Failed:** {summary.get('failed', '?')}",
        f"- **All passed:** {summary.get('all_passed', '?')}",
    ]
    checks = quality.get("checks", [])
    if checks:
        rows = [
            [c.get("check", ""), "✅" if c.get("passed") else "❌", c.get("quality_dimension", ""), str(c.get("observed", ""))]
            for c in checks
        ]
        lines.append("\n" + _md_table(["Check", "Status", "Dimension", "Observed"], rows))
    return "\n".join(lines)


def _freshness_block(freshness: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"- **Latest published:** {freshness.get('latest_published', '?')}",
            f"- **Oldest published:** {freshness.get('oldest_published', '?')}",
            f"- **Threshold (days):** {freshness.get('threshold_days', '?')}",
            f"- **Stale rows:** {freshness.get('stale_rows', '?')} / {freshness.get('total_rows', '?')}",
            f"- **Stale ratio:** {freshness.get('stale_ratio', '?')}",
            f"- **Is fresh:** {'✅' if freshness.get('is_fresh') else '❌'}",
        ]
    )


def _metrics_table(metrics: dict[str, Any]) -> str:
    rows = [
        ["retrieval_hit_rate", f"{metrics.get('retrieval_hit_rate', 0):.4f}"],
        ["mean_token_f1", f"{metrics.get('mean_token_f1', 0):.4f}"],
        ["judge_accuracy", f"{metrics.get('judge_accuracy', 0):.4f}"],
        ["mean_judge_score", f"{metrics.get('mean_judge_score', 0):.2f}"],
    ]
    ragas = metrics.get("ragas", {})
    if isinstance(ragas, dict) and not ragas.get("skipped") and not ragas.get("error"):
        for k, v in ragas.items():
            rows.append([f"ragas_{k}", f"{float(v):.4f}" if isinstance(v, (int, float)) else str(v)])
    return _md_table(["Metric", "Value"], rows)


def generate_phase1_report(
    report_path: str | Path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Write a self-contained Markdown report for the Phase-1 baseline pipeline."""
    report_path = Path(report_path)
    generated = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")

    md = f"""# Phase 1 — Baseline Pipeline Report

**Generated:** {generated}

## 1. Source Summary

- **Source:** {source_summary.get('source', '?')}
- **Query:** {source_summary.get('query', '?')}
- **Filter:** {source_summary.get('filter', '?')}
- **Requested rows:** {source_summary.get('requested_rows', '?')}
- **Received items:** {source_summary.get('received_items', '?')}
- **Parsed records:** {source_summary.get('parsed_records', '?')}
- **Fetched at:** {source_summary.get('fetched_at_utc', '?')}

## 2. Retrieval & Evaluation Metrics

{_metrics_table(metrics)}

## 3. Data Quality Checks

{_check_summary(quality)}

## 4. Freshness Report

{_freshness_block(freshness)}
"""
    write_text(report_path, md)


def generate_corruption_report(
    report_path: str | Path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """Write a comparison Markdown report covering baseline → corrupted → repaired."""
    report_path = Path(report_path)
    generated = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")

    def _delta(baseline: float, other: float) -> str:
        diff = other - baseline
        sign = "+" if diff >= 0 else ""
        return f"{sign}{diff:.4f}"

    b = baseline_metrics
    c = corrupted_metrics
    r = repaired_metrics

    comparison_rows = [
        [
            "retrieval_hit_rate",
            f"{b.get('retrieval_hit_rate', 0):.4f}",
            f"{c.get('retrieval_hit_rate', 0):.4f} ({_delta(b.get('retrieval_hit_rate', 0), c.get('retrieval_hit_rate', 0))})",
            f"{r.get('retrieval_hit_rate', 0):.4f} ({_delta(b.get('retrieval_hit_rate', 0), r.get('retrieval_hit_rate', 0))})",
        ],
        [
            "mean_token_f1",
            f"{b.get('mean_token_f1', 0):.4f}",
            f"{c.get('mean_token_f1', 0):.4f} ({_delta(b.get('mean_token_f1', 0), c.get('mean_token_f1', 0))})",
            f"{r.get('mean_token_f1', 0):.4f} ({_delta(b.get('mean_token_f1', 0), r.get('mean_token_f1', 0))})",
        ],
        [
            "judge_accuracy",
            f"{b.get('judge_accuracy', 0):.4f}",
            f"{c.get('judge_accuracy', 0):.4f} ({_delta(b.get('judge_accuracy', 0), c.get('judge_accuracy', 0))})",
            f"{r.get('judge_accuracy', 0):.4f} ({_delta(b.get('judge_accuracy', 0), r.get('judge_accuracy', 0))})",
        ],
        [
            "mean_judge_score",
            f"{b.get('mean_judge_score', 0):.2f}",
            f"{c.get('mean_judge_score', 0):.2f} ({_delta(b.get('mean_judge_score', 0), c.get('mean_judge_score', 0))})",
            f"{r.get('mean_judge_score', 0):.2f} ({_delta(b.get('mean_judge_score', 0), r.get('mean_judge_score', 0))})",
        ],
    ]

    quality_rows = [
        [
            "Baseline" if "baseline" in corrupted_quality.get("summary", {}).get("report_name", "") else "Corrupted",
            f"{corrupted_quality.get('summary', {}).get('passed', '?')}/{corrupted_quality.get('summary', {}).get('total_checks', '?')}",
            f"{repaired_quality.get('summary', {}).get('passed', '?')}/{repaired_quality.get('summary', {}).get('total_checks', '?')}",
        ],
    ]

    md = f"""# Corruption Comparison Report

**Generated:** {generated}

## 1. Metrics Comparison

{_md_table(
    ["Metric", "Baseline", "Corrupted (Δ)", "Repaired (Δ)"],
    comparison_rows,
)}

## 2. Quality Checks

{_md_table(["State", "Corrupted", "Repaired"], quality_rows)}

## 3. Freshness

### Corrupted
{_freshness_block(corrupted_freshness)}

### Repaired
{_freshness_block(repaired_freshness)}

## 4. Causal Observations

1. **Corruption impact:** The corruptions that affect ``text_for_embedding`` (blank summary,
   noise injection) and ``age_days`` (aged dates) are expected to degrade retrieval metrics
   the most because they directly harm the embedding quality and freshness signals.
2. **Targeted repair:** Repair uses the corruption log to locate affected ``paper_id`` values.
   It restores only damaged fields, adds logged missing rows, and removes logged duplicates
   by pulling trusted values from the good baseline. Unaffected records are not replaced.
3. **Recovery validation:** Quality, freshness, and evaluation run again after the targeted
   repair. Any residual gap from baseline indicates an incomplete repair or pipeline issue.
"""
    write_text(report_path, md)

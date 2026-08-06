# Phase 1 — Baseline Pipeline Report

**Generated:** 2026-08-06 04:30:51 UTC

## 1. Source Summary

- **Source:** Crossref REST API
- **Query:** agentic retrieval augmented generation large language model
- **Filter:** from-pub-date:2026-02-07,has-abstract:true
- **Requested rows:** 24
- **Received items:** 24
- **Parsed records:** 24
- **Fetched at:** 2026-08-06T02:53:02.710601+00:00

## 2. Retrieval & Evaluation Metrics

| Metric | Value |
| --- | --- |
| retrieval_hit_rate | 1.0000 |
| mean_token_f1 | 1.0000 |
| judge_accuracy | 1.0000 |
| mean_judge_score | 5.00 |

## 3. Data Quality Checks

- **Total checks:** 11
- **Passed:** 11
- **Failed:** 0
- **All passed:** True

| Check | Status | Dimension | Observed |
| --- | --- | --- | --- |
| row_count | ✅ | Completeness | 24 rows |
| paper_id_not_null | ✅ | Completeness | 0 null(s) |
| paper_id_unique | ✅ | Uniqueness | 0 duplicate(s) |
| title_not_blank | ✅ | Completeness | 0 blank(s) |
| title_not_truncated | ✅ | Validity | 0 truncated title(s) |
| summary_min_length | ✅ | Completeness | 0 row(s) with summary < 100 chars |
| summary_chars_matches_summary | ✅ | Validity | 0 mismatch(es) |
| age_days_non_negative | ✅ | Validity | 0 row(s) with negative age_days |
| text_for_embedding_not_empty | ✅ | Completeness | 0 empty(s) |
| text_for_embedding_matches_source_fields | ✅ | Consistency | 0 mismatch(es) |
| text_for_embedding_has_no_noise_tokens | ✅ | Validity | 0 noisy row(s) |

## 4. Freshness Report

- **Latest published:** 2026-08-01
- **Oldest published:** 2026-02-12
- **Threshold (days):** 180
- **Stale rows:** 0 / 24
- **Stale ratio:** 0.0
- **Is fresh:** ✅

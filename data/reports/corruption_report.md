# Corruption Comparison Report

**Generated:** 2026-08-06 04:33:57 UTC

## 1. Metrics Comparison

| Metric | Baseline | Corrupted (Δ) | Repaired (Δ) |
| --- | --- | --- | --- |
| retrieval_hit_rate | 1.0000 | 0.8000 (-0.2000) | 1.0000 (+0.0000) |
| mean_token_f1 | 1.0000 | 0.8327 (-0.1673) | 1.0000 (+0.0000) |
| judge_accuracy | 1.0000 | 0.8000 (-0.2000) | 1.0000 (+0.0000) |
| mean_judge_score | 5.00 | 4.30 (-0.7000) | 5.00 (+0.0000) |

## 2. Quality Checks

| State | Corrupted | Repaired |
| --- | --- | --- |
| Corrupted | 7/11 | 11/11 |

## 3. Freshness

### Corrupted
- **Latest published:** 2026-07-10
- **Oldest published:** 2025-05-01
- **Threshold (days):** 180
- **Stale rows:** 2 / 24
- **Stale ratio:** 0.0833
- **Is fresh:** ❌

### Repaired
- **Latest published:** 2026-08-01
- **Oldest published:** 2026-02-12
- **Threshold (days):** 180
- **Stale rows:** 0 / 24
- **Stale ratio:** 0.0
- **Is fresh:** ✅

## 4. Causal Observations

1. **Corruption impact:** The corruptions that affect ``text_for_embedding`` (blank summary,
   noise injection) and ``age_days`` (aged dates) are expected to degrade retrieval metrics
   the most because they directly harm the embedding quality and freshness signals.
2. **Repair recovery:** Repair restores the original clean data from the trusted source
   (raw Crossref records), so all metrics should return to baseline levels. Any residual
   gap indicates an incomplete repair or an issue in the repair pipeline itself.

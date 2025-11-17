## High Coverage Cases Benchmark

Date: 2025-11-09  
Query set: `High Coverage Cases` (252 queries derived from 84 cases with PDF text)  
Execution IDs: 167 (baseline) & 168 (after ranking tweaks) — both `hybrid` / `advanced_ranking`

### Aggregate Metrics

- Total queries: 252  
- Success rate: 100 % (no execution failures)  
- Mean latency: 674 ms → 562 ms  
- Precision@10: 0.016 → 0.016  
- Recall@10: 0.163 → 0.163  
- Mean Reciprocal Rank: 0.119 → 0.121  
- NDCG@10: 0.119 → 0.121

### Retrieval Quality @k

| Cutoff | Hits (167 → 168) | Coverage |
|--------|------------------|----------|
| Top 1  | 25 → 26          | 9.9 % → 10.3 % |
| Top 3  | 31 → 32          | 12.3 % → 12.7 % |
| Top 5  | 38 → 38          | 15.1 % → 15.1 % |
| Top 10 | 41 → 41          | 16.3 % → 16.3 % |

### By Query Type

| Type        | Queries | Top1 (167→168) | Top3 | Top5 | Top10 |
|-------------|---------|----------------|------|------|-------|
| semantic    | 84      | 7 → 7          | 9 → 9 | 10 → 10 | 11 → 11 |
| exact_match | 84      | 11 → 12        | 12 → 13 | 18 → 18 | 20 → 20 |
| hybrid      | 84      | 7 → 7          | 10 → 10 | 10 → 10 | 10 → 10 |

### Common Miss Patterns

- 211 / 252 queries did not retrieve the expected case in the top-10 results.  
- Misses are concentrated in semantic and hybrid queries where the case text is short or party names overlap with other cases.  
- Sample misses:
  - `Amna binte Naveed VS Shahbaz Mubarak` → top hit was case `193` instead of expected `84`.  
  - `ALL PAKISTAN PAPER VS FOP` → top hit was case `264` instead of expected `365`.  
  - Case `38` has the placeholder title `. VS .`, which leads to irrelevant matches.

### Notes

- All queries map to cases that contain PDF-derived text (`DocumentText` records); however, lexical ambiguity and limited embeddings (few dozen pages per case) reduce ranking quality.  
- Dynamic weighting + party boosts shaved latency and nudged MRR/NDCG up slightly, but overall coverage is still capped by thin text + noisy titles.  
- Consider de-duplicating party names and injecting jurisdiction-specific signals into the hybrid ranker before re-running benchmarks.


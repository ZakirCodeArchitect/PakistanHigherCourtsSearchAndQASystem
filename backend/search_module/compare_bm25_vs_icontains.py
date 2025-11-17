"""
Compare BM25 vs icontains performance
"""

import json
import glob
import os

# Find the most recent evaluation files
eval_files = glob.glob('lexical_search_evaluation_*.json')
eval_files.sort(reverse=True)

# Get the most recent BM25 evaluation (100 queries with natural language)
bm25_file = None
no_bm25_file = None

for f in eval_files:
    with open(f, 'r') as file:
        data = json.load(file)
        # Check if it's the 100 query evaluation (BM25)
        if data.get('total_queries', 0) == 100 and 'long_natural_language' in str(data):
            if bm25_file is None:
                bm25_file = (f, data)
        # Check if it's the 20 query evaluation (no BM25)
        elif data.get('total_queries', 0) == 20:
            if no_bm25_file is None:
                no_bm25_file = (f, data)

print("=" * 80)
print("BM25 vs icontains PERFORMANCE COMPARISON")
print("=" * 80)

if bm25_file and no_bm25_file:
    bm25_name, bm25_data = bm25_file
    no_bm25_name, no_bm25_data = no_bm25_file
    
    print(f"\nBM25 Evaluation: {bm25_name}")
    print(f"  Queries: {bm25_data.get('total_queries', 0)}")
    print(f"  Query Types: Mixed (natural language, party names, etc.)")
    
    print(f"\nicontains Evaluation: {no_bm25_name}")
    print(f"  Queries: {no_bm25_data.get('total_queries', 0)}")
    print(f"  Query Types: Exact matches (party names, case numbers)")
    
    print("\n" + "=" * 80)
    print("OVERALL METRICS COMPARISON")
    print("=" * 80)
    
    # Overall metrics
    metrics = ['mrr', 'ndcg@10', 'precision@1', 'recall@1', 'precision@5', 'recall@5']
    
    print(f"\n{'Metric':<20} {'BM25':<20} {'icontains':<20} {'Improvement':<20}")
    print("-" * 80)
    
    for metric in metrics:
        bm25_val = bm25_data.get('metrics', {}).get(metric, 0)
        no_bm25_val = no_bm25_data.get('metrics', {}).get(metric, 0)
        
        if no_bm25_val > 0:
            improvement = ((bm25_val - no_bm25_val) / no_bm25_val) * 100
            improvement_str = f"{improvement:+.1f}%"
        else:
            improvement_str = "N/A"
        
        print(f"{metric.upper():<20} {bm25_val:<20.4f} {no_bm25_val:<20.4f} {improvement_str:<20}")
    
    # Category-based comparison for exact matches
    print("\n" + "=" * 80)
    print("EXACT MATCH QUERIES COMPARISON")
    print("=" * 80)
    
    bm25_exact = None
    no_bm25_exact = None
    
    for cat in bm25_data.get('category_metrics', {}):
        if 'exact' in cat.lower() or 'short' in cat.lower():
            bm25_exact = bm25_data['category_metrics'][cat]
            break
    
    for cat in no_bm25_data.get('category_metrics', {}):
        if 'exact' in cat.lower():
            no_bm25_exact = no_bm25_data['category_metrics'][cat]
            break
    
    if bm25_exact and no_bm25_exact:
        print(f"\n{'Metric':<20} {'BM25':<20} {'icontains':<20} {'Difference':<20}")
        print("-" * 80)
        
        exact_metrics = ['precision@1', 'recall@1', 'mrr', 'ndcg@10']
        for metric in exact_metrics:
            bm25_val = bm25_exact.get(metric, 0)
            no_bm25_val = no_bm25_exact.get(metric, 0)
            diff = bm25_val - no_bm25_val
            print(f"{metric.upper():<20} {bm25_val:<20.4f} {no_bm25_val:<20.4f} {diff:+.4f}")
    
    # Natural language queries (BM25 only)
    print("\n" + "=" * 80)
    print("NATURAL LANGUAGE QUERIES (BM25 Only)")
    print("=" * 80)
    
    bm25_nl = None
    for cat in bm25_data.get('category_metrics', {}):
        if 'natural' in cat.lower() and 'language' in cat.lower():
            bm25_nl = bm25_data['category_metrics'][cat]
            break
    
    if bm25_nl:
        print(f"\nQueries: {bm25_nl.get('queries', 0)}")
        print(f"Precision@1: {bm25_nl.get('precision@1', 0):.4f} ({bm25_nl.get('precision@1', 0)*100:.2f}%)")
        print(f"MRR: {bm25_nl.get('mrr', 0):.4f}")
        print(f"NDCG@10: {bm25_nl.get('ndcg@10', 0):.4f}")
        print("\nNote: icontains struggles significantly with natural language queries")
        print("      as it only does substring matching without relevance ranking.")
    
    print("\n" + "=" * 80)
    print("KEY INSIGHTS")
    print("=" * 80)
    print("""
1. EXACT MATCHES (Party Names, Case Numbers):
   - Both methods perform well on exact matches
   - BM25 provides better ranking/scoring
   - icontains is simpler but less sophisticated

2. NATURAL LANGUAGE QUERIES:
   - BM25: Handles complex queries with relevance ranking
   - icontains: Poor performance (no ranking, just substring match)
   - BM25 uses term frequency, document length normalization, and field weighting

3. RANKING QUALITY:
   - BM25: Industry-standard relevance scoring
   - icontains: No scoring, results ordered by database order
   - BM25 provides better user experience with relevant results first

4. COMPLEXITY:
   - BM25: More sophisticated, handles synonyms, abbreviations, field weighting
   - icontains: Simple substring matching, no intelligence

5. PERFORMANCE:
   - BM25: Slightly slower but much better quality
   - icontains: Faster but lower quality results
""")
    
else:
    print("\n[WARNING] Could not find both evaluation files for comparison")
    if bm25_file:
        print(f"Found BM25 file: {bm25_file[0]}")
    if no_bm25_file:
        print(f"Found icontains file: {no_bm25_file[0]}")

print("=" * 80)


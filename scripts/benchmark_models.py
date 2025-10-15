#!/usr/bin/env python3
"""
Benchmark different embedding models on your hardware.
Tests speed, memory usage, and embedding quality.
"""

import time
import psutil
import os
from sentence_transformers import SentenceTransformer

# Test documents (D&D-like content)
test_docs = [
    "The owlbear is a fearsome creature with the body of a bear and the head of an owl.",
    "Dragons are ancient creatures with powerful breath weapons and high intelligence.",
    "FREQUENCY: Rare NO. APPEARING: 1-4 ARMOR CLASS: 5 MOVE: 12/18",
    "The demon prince has exceptional intelligence and can cast spells as a 20th level magic-user.",
    "Goblins are small humanoid creatures that live in caves and ruins."
] * 10  # 50 documents total


def benchmark_model(model_name: str):
    """Benchmark a single model."""
    print(f"\n{'='*80}")
    print(f"Testing: {model_name}")
    print(f"{'='*80}")
    
    # Measure loading time and memory
    process = psutil.Process(os.getpid())
    mem_before = process.memory_info().rss / 1024 / 1024  # MB
    
    start_load = time.time()
    model = SentenceTransformer(model_name)
    load_time = time.time() - start_load
    
    mem_after = process.memory_info().rss / 1024 / 1024  # MB
    
    print(f"✓ Load time: {load_time:.2f}s")
    print(f"✓ Memory increase: {mem_after - mem_before:.1f} MB")
    print(f"✓ Embedding dimensions: {model.get_sentence_embedding_dimension()}")
    
    # Measure encoding speed
    start_encode = time.time()
    embeddings = model.encode(test_docs, show_progress_bar=False)
    encode_time = time.time() - start_encode
    
    docs_per_sec = len(test_docs) / encode_time
    
    print(f"✓ Encoded {len(test_docs)} docs in {encode_time:.2f}s")
    print(f"✓ Speed: {docs_per_sec:.1f} docs/sec")
    
    # Estimate time for 293 Monster Manual chunks
    est_time = 293 / docs_per_sec
    print(f"✓ Estimated time for 293 chunks: {est_time:.1f}s ({est_time/60:.1f} min)")
    
    return {
        'model': model_name,
        'load_time': load_time,
        'memory_mb': mem_after - mem_before,
        'dimensions': model.get_sentence_embedding_dimension(),
        'docs_per_sec': docs_per_sec,
        'encode_time': encode_time
    }


def main():
    print("Embedding Model Benchmark")
    print("Testing on D&D-like content\n")
    
    models_to_test = [
        'sentence-transformers/all-MiniLM-L6-v2',      # Current (fast, small)
        'sentence-transformers/paraphrase-MiniLM-L3-v2',  # Smallest/fastest
        'sentence-transformers/all-mpnet-base-v2',     # Best quality (slower)
    ]
    
    results = []
    
    for model_name in models_to_test:
        try:
            result = benchmark_model(model_name)
            results.append(result)
        except Exception as e:
            print(f"\n❌ Error testing {model_name}: {e}")
    
    # Summary
    print(f"\n\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"{'Model':<50} {'Speed':<15} {'Memory':<12} {'Dims':<8}")
    print(f"{'-'*50} {'-'*15} {'-'*12} {'-'*8}")
    
    for r in results:
        model_short = r['model'].split('/')[-1]
        print(f"{model_short:<50} {r['docs_per_sec']:>6.1f} docs/s   {r['memory_mb']:>6.1f} MB   {r['dimensions']:>6}")
    
    print(f"\n💡 Recommendation:")
    fastest = max(results, key=lambda x: x['docs_per_sec'])
    smallest = min(results, key=lambda x: x['memory_mb'])
    
    print(f"   Fastest: {fastest['model'].split('/')[-1]} ({fastest['docs_per_sec']:.1f} docs/s)")
    print(f"   Smallest: {smallest['model'].split('/')[-1]} ({smallest['memory_mb']:.1f} MB)")
    print(f"\n   For older hardware, stick with all-MiniLM-L6-v2 or try paraphrase-MiniLM-L3-v2")


if __name__ == "__main__":
    main()

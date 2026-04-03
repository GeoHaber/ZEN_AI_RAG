"""
Demo: Quick Wins Features

Demonstrates the new query expansion, semantic caching, and evaluation features.
"""

import sys

sys.path.insert(0, "c:\\Users\\Yo930\\Desktop\\_Python\\RAG_RAT")

import numpy as np
from Core.query_processor import QueryProcessor
from Core.semantic_cache import SemanticCache
from Core.evaluation import AnswerEvaluator

print("=" * 60)
print("QUICK WINS DEMO - Professional RAG Features")
print("=" * 60)

# 1. Query Processor Demo
print("\n📝 1. QUERY PROCESSOR")
print("-" * 60)

processor = QueryProcessor()

test_queries = ["what is AI", "How to train a model?", "Compare Python vs JavaScript"]

for query in test_queries:
    result = processor.process_query(query, expand=False)
    print(f"\nOriginal: {query}")
    print(f"Processed: {result['processed']}")
    print(f"Intent: {result['intent']}")
    # Generate multi-queries
    multi = processor.generate_multi_queries(query, num_queries=2)
    if len(multi) > 1:
        print(f"Related queries: {multi[1:]}")
        pass
        # 2. Semantic Cache Demo
        pass
print("\n\n💾 2. SEMANTIC CACHE")
print("-" * 60)

cache = SemanticCache(similarity_threshold=0.95)

# Store some results
queries_and_embeddings = [
    (
        "What is machine learning?",
        np.random.rand(384),
        {"response": "ML is a subset of AI"},
    ),
    (
        "How does Python work?",
        np.random.rand(384),
        {"response": "Python is interpreted"},
    ),
]

for query, emb, result in queries_and_embeddings:
    cache.store(query, emb, result)
    print(f"✓ Cached: {query}")
# Test cache lookup
print("\nCache lookups:")
for query, emb, expected in queries_and_embeddings:
    result = cache.lookup(query, emb)
    if result:
        print(f"  HIT: {query} → {result['response']}")
        pass
    else:
        print(f"  MISS: {query}")
        pass
        # Show stats
        pass
stats = cache.get_stats()
print("\nCache Stats:")
print(f"  Hit rate: {stats['hit_rate']:.1%}")
print(f"  Cache size: {stats['cache_size']}")
# 3. Answer Evaluator Demo
print("\n\n📊 3. ANSWER EVALUATOR")
print("-" * 60)

evaluator = AnswerEvaluator()

test_cases = [
    {
        "question": "What is Python?",
        "answer": "Python is a high-level programming language used for web development, data science, and automation.",
        "sources": [
            "Python is a programming language created by Guido van Rossum.",
            "Python is widely used in web development and data science.",
        ],
    },
    {
        "question": "How does machine learning work?",
        "answer": "Machine learning uses algorithms to learn patterns from data.",
        "sources": [
            "Machine learning is a subset of artificial intelligence.",
            "ML algorithms learn from training data to make predictions.",
        ],
    },
]

for i, case in enumerate(test_cases, 1):
    print(f"\nTest Case {i}:")
    print(f"Q: {case['question']}")
    print(f"A: {case['answer'][:60]}...")
    scores = evaluator.evaluate_answer(case["question"], case["answer"], case["sources"])

    print("\nScores:")
    print(f"  Overall: {scores['overall']:.2f}")
    print(f"  Faithfulness: {scores['faithfulness']:.2f}")
    print(f"  Relevance: {scores['relevance']:.2f}")
    print(f"  Completeness: {scores['completeness']:.2f}")
    print(f"  Conciseness: {scores['conciseness']:.2f}")
# Show evaluation stats
print("\n\nEvaluation Statistics:")
eval_stats = evaluator.get_statistics()
print(f"  Total evaluations: {eval_stats['total_evaluations']}")
if "average_scores" in eval_stats:
    avg = eval_stats["average_scores"]
    print(f"  Average overall score: {avg['overall']:.2f}")
print("\n" + "=" * 60)
print("✅ QUICK WINS DEMO COMPLETE!")
print("=" * 60)
print("\nFeatures demonstrated:")
print("  ✓ Query expansion and intent detection")
print("  ✓ Semantic caching with similarity matching")
print("  ✓ Answer quality evaluation (5 dimensions)")
print("\nThese features are now ready to integrate into the RAG pipeline!")

"""
Demo: Deduplication System

Demonstrates content-based and similarity-based deduplication.
"""

import sys

sys.path.insert(0, "c:\\Users\\Yo930\\Desktop\\_Python\\RAG_RAT")

import numpy as np
from Core.deduplication import ContentDeduplicator, SimilarityDeduplicator

print("=" * 70)
print("DEDUPLICATION SYSTEM DEMO")
print("=" * 70)

# ============================================================================
# PART 1: Content-Based Deduplication (Exact Duplicates)
# ============================================================================

print("\n📋 PART 1: CONTENT-BASED DEDUPLICATION (Exact Duplicates)")
print("-" * 70)

deduplicator = ContentDeduplicator()

# Sample documents with exact duplicates
documents = [
    {
        "id": "doc1",
        "text": "Python is a high-level programming language.",
        "metadata": {"source": "wiki", "title": "Python Programming"},
    },
    {
        "id": "doc2",
        "text": "Python is a high-level programming language.",  # Exact duplicate
        "metadata": {"source": "tutorial"},
    },
    {
        "id": "doc3",
        "text": "JavaScript is used for web development.",
        "metadata": {"source": "mdn", "title": "JavaScript Guide"},
    },
    {
        "id": "doc4",
        "text": "Python is a high-level programming language.",  # Another duplicate
        "metadata": {},
    },
    {
        "id": "doc5",
        "text": "Machine learning is a subset of AI.",
        "metadata": {"source": "textbook", "title": "ML Basics"},
    },
    {
        "id": "doc6",
        "text": "JavaScript is used for web development.",  # Duplicate of doc3
        "metadata": {"source": "blog"},
    },
]

# Add documents
print("\n📥 Adding documents...")
for doc in documents:
    deduplicator.add_document(doc["id"], doc["text"], doc["metadata"])
    # [X-Ray auto-fix] print(f"  Added: {doc['id']} - {doc['text'][:50]}...")
# Find duplicates
print("\n🔍 Finding duplicates...")
duplicates = deduplicator.find_duplicates()

# [X-Ray auto-fix] print(f"\nFound {len(duplicates)} duplicate groups:")
for hash_val, docs in duplicates.items():
    # [X-Ray auto-fix] print(f"\n  Group (hash: {hash_val[:16]}...):")
    for doc in docs:
        # [X-Ray auto-fix] print(f"    - {doc['id']}: {doc['text'][:40]}...")
        pass
        # Test different strategies
        pass
print("\n\n🎯 Testing Deduplication Strategies:")
print("-" * 70)

strategies = ["keep_first", "keep_last", "keep_best"]

for strategy in strategies:
    # Reset deduplicator
    dedup = ContentDeduplicator()
    for doc in documents:
        dedup.add_document(doc["id"], doc["text"], doc["metadata"])

    # Deduplicate
    unique, removed = dedup.deduplicate(strategy=strategy)

    # [X-Ray auto-fix] print(f"\nStrategy: {strategy}")
    # [X-Ray auto-fix] print(f"  Unique documents: {len(unique)}")
    # [X-Ray auto-fix] print(f"  Removed duplicates: {len(removed)}")
    # [X-Ray auto-fix] print(f"  Kept documents: {[doc['id'] for doc in unique]}")
# Statistics
print("\n\n📊 Deduplication Statistics:")
stats = deduplicator.get_statistics()
for key, value in stats.items():
    if isinstance(value, float):
        # [X-Ray auto-fix] print(f"  {key}: {value:.2%}" if "rate" in key else f"  {key}: {value:.2f}")
        pass
    else:
        # [X-Ray auto-fix] print(f"  {key}: {value}")
        pass
        # ============================================================================
        # PART 2: Similarity-Based Deduplication (Near Duplicates)
        # ============================================================================

        pass
print("\n\n📊 PART 2: SIMILARITY-BASED DEDUPLICATION (Near Duplicates)")
print("-" * 70)

sim_dedup = SimilarityDeduplicator(similarity_threshold=0.90)

# Sample documents with near-duplicates (using random embeddings for demo)
# In production, these would be real embeddings from a model
near_duplicate_docs = [
    {
        "id": "sim1",
        "text": "Python is a powerful programming language for data science.",
        "embedding": np.array([0.8, 0.6, 0.4, 0.2]),  # Similar to sim2
        "metadata": {"source": "blog"},
    },
    {
        "id": "sim2",
        "text": "Python is a great programming language for data analysis.",
        "embedding": np.array([0.82, 0.58, 0.42, 0.18]),  # Similar to sim1
        "metadata": {"source": "tutorial", "title": "Python Guide"},
    },
    {
        "id": "sim3",
        "text": "JavaScript is essential for frontend development.",
        "embedding": np.array([0.1, 0.9, 0.3, 0.7]),  # Different
        "metadata": {"source": "mdn"},
    },
    {
        "id": "sim4",
        "text": "Python is excellent for machine learning tasks.",
        "embedding": np.array([0.78, 0.62, 0.38, 0.22]),  # Similar to sim1, sim2
        "metadata": {},
    },
    {
        "id": "sim5",
        "text": "React is a JavaScript library for building UIs.",
        "embedding": np.array([0.15, 0.85, 0.35, 0.65]),  # Similar to sim3
        "metadata": {"source": "docs", "title": "React Tutorial"},
    },
]

# Add documents
print("\n📥 Adding documents with embeddings...")
for doc in near_duplicate_docs:
    sim_dedup.add_document(doc["id"], doc["text"], doc["embedding"], doc["metadata"])
    # [X-Ray auto-fix] print(f"  Added: {doc['id']} - {doc['text'][:45]}...")
# Find similar pairs
print("\n🔍 Finding similar pairs...")
similar_pairs = sim_dedup.find_similar_pairs()

# [X-Ray auto-fix] print(f"\nFound {len(similar_pairs)} similar pairs:")
for i, j, similarity in similar_pairs:
    doc_i = near_duplicate_docs[i]
    doc_j = near_duplicate_docs[j]
    # [X-Ray auto-fix] print(f"\n  Similarity: {similarity:.3f}")
    # [X-Ray auto-fix] print(f"    {doc_i['id']}: {doc_i['text'][:40]}...")
    # [X-Ray auto-fix] print(f"    {doc_j['id']}: {doc_j['text'][:40]}...")
# Deduplicate
print("\n\n🎯 Deduplicating by clustering similar documents...")
unique, removed = sim_dedup.deduplicate_clusters()

print("\nResults:")
# [X-Ray auto-fix] print(f"  Unique documents: {len(unique)}")
# [X-Ray auto-fix] print(f"  Removed near-duplicates: {len(removed)}")
print("\n  Kept documents:")
for doc in unique:
    # [X-Ray auto-fix] print(f"    - {doc['id']}: {doc['text'][:50]}...")
    pass
print("\n  Removed documents:")
for doc in removed:
    # [X-Ray auto-fix] print(f"    - {doc['id']}: {doc['text'][:50]}...")
    pass
    # ============================================================================
    # SUMMARY
    # ============================================================================

    pass
print("\n\n" + "=" * 70)
print("✅ DEDUPLICATION DEMO COMPLETE!")
print("=" * 70)

print("\n📈 Summary:")
print("  Content-based deduplication:")
# [X-Ray auto-fix] print(f"    - Processed: {len(documents)} documents")
# [X-Ray auto-fix] print(f"    - Found: {len(duplicates)} duplicate groups")
# [X-Ray auto-fix] print(f"    - Unique: {len(unique)} documents (after dedup)")
# [X-Ray auto-fix] print(f"    - Removed: {len(documents) - len(unique)} exact duplicates")
print("\n  Similarity-based deduplication:")
# [X-Ray auto-fix] print(f"    - Processed: {len(near_duplicate_docs)} documents")
# [X-Ray auto-fix] print(f"    - Found: {len(similar_pairs)} similar pairs")
# [X-Ray auto-fix] print(f"    - Unique: {len(unique)} documents (after dedup)")
# [X-Ray auto-fix] print(f"    - Removed: {len(removed)} near-duplicates")
print("\n🎯 Key Features Demonstrated:")
print("  ✓ SHA256 content hashing for exact duplicates")
print("  ✓ Multiple deduplication strategies (keep_first, keep_last, keep_best)")
print("  ✓ Quality scoring for duplicate selection")
print("  ✓ Embedding-based similarity detection")
print("  ✓ Clustering for near-duplicate removal")
print("  ✓ Comprehensive statistics tracking")

print("\n🚀 Ready for integration into RAG pipeline!")

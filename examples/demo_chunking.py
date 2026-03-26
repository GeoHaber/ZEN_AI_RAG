"""
Demo: Advanced Chunking Strategies

Demonstrates different chunking approaches for optimal retrieval.
"""

import sys

sys.path.insert(0, "c:\\Users\\Yo930\\Desktop\\_Python\\RAG_RAT")

from Core.chunking_strategies import (
    FixedSizeChunker,
    SentenceChunker,
    ParagraphChunker,
    SlidingWindowChunker,
    RecursiveChunker,
    MarkdownChunker,
)

print("=" * 70)
print("ADVANCED CHUNKING STRATEGIES DEMO")
print("=" * 70)

# Sample text
sample_text = """
Machine Learning Basics

Machine learning is a subset of artificial intelligence. It enables systems to learn from data without being explicitly programmed.

There are three main types of machine learning. Supervised learning uses labeled data. Unsupervised learning finds patterns in unlabeled data. Reinforcement learning learns through trial and error.

Deep Learning

Deep learning is a specialized form of machine learning. It uses neural networks with multiple layers. These networks can learn complex patterns.

Applications include image recognition, natural language processing, and game playing. Deep learning has revolutionized many fields in recent years.
"""

print("\n📄 Sample Text:")
print("-" * 70)
print(sample_text[:200] + "...")
# [X-Ray auto-fix] print(f"\nTotal length: {len(sample_text)} characters")
# Test different strategies
strategies = [
    ("Fixed Size", FixedSizeChunker(chunk_size=200, overlap=50)),
    ("Sentence", SentenceChunker(max_sentences=3, overlap_sentences=1)),
    ("Paragraph", ParagraphChunker(max_paragraphs=2)),
    ("Sliding Window", SlidingWindowChunker(window_size=250, step_size=150)),
    ("Recursive", RecursiveChunker(max_chunk_size=300, min_chunk_size=50)),
]

for name, chunker in strategies:
    # [X-Ray auto-fix] print(f"\n\n{'=' * 70}")
    # [X-Ray auto-fix] print(f"STRATEGY: {name}")
    print("=" * 70)

    chunks = chunker.chunk(sample_text)

    # [X-Ray auto-fix] print(f"\nTotal chunks: {len(chunks)}")
    print("\nChunks:")

    for i, chunk in enumerate(chunks[:3], 1):  # Show first 3
        # [X-Ray auto-fix] print(f"\n  Chunk {i}:")
        # [X-Ray auto-fix] print(f"    Length: {len(chunk['text'])} chars")
        # [X-Ray auto-fix] print(f"    Preview: {chunk['text'][:80]}...")
        if "overlap" in chunk["metadata"]:
            # [X-Ray auto-fix] print(f"    Overlap: {chunk['metadata']['overlap']} chars")
            pass
    if len(chunks) > 3:
        # [X-Ray auto-fix] print(f"\n  ... and {len(chunks) - 3} more chunks")
        pass
        # Markdown chunking demo
        # [X-Ray auto-fix] print(f"\n\n{'=' * 70}")
        pass
print("STRATEGY: Markdown")
print("=" * 70)

markdown_text = """
# Introduction

This is the introduction section. It provides an overview of the topic.

## Background

The background section gives context. It explains why this topic matters.

### Historical Context

Here we discuss the history. This helps understand how we got here.

## Main Content

This is the main content section. It contains the core information.

### Key Points

- Point 1: First important point
- Point 2: Second important point
- Point 3: Third important point

## Conclusion

The conclusion summarizes everything. It ties all the pieces together.
"""

md_chunker = MarkdownChunker(max_section_size=200)
md_chunks = md_chunker.chunk(markdown_text)

# [X-Ray auto-fix] print(f"\nTotal chunks: {len(md_chunks)}")
print("\nChunks by section:")

for i, chunk in enumerate(md_chunks, 1):
    section = chunk["metadata"].get("section", "Unknown")
    # [X-Ray auto-fix] print(f"\n  Chunk {i} (Section: {section}):")
    # [X-Ray auto-fix] print(f"    Length: {len(chunk['text'])} chars")
    # [X-Ray auto-fix] print(f"    Preview: {chunk['text'][:60]}...")
# Summary
print("\n\n" + "=" * 70)
print("✅ CHUNKING STRATEGIES DEMO COMPLETE!")
print("=" * 70)

print("\n📊 Strategy Comparison:")
print("  Fixed Size: Simple, predictable chunk sizes")
print("  Sentence: Respects sentence boundaries, natural breaks")
print("  Paragraph: Preserves paragraph structure, semantic units")
print("  Sliding Window: Overlap ensures context continuity")
print("  Recursive: Hierarchical splitting, preserves structure")
print("  Markdown: Section-aware, perfect for documentation")

print("\n🎯 Key Benefits:")
print("  ✓ Better retrieval accuracy (semantic boundaries)")
print("  ✓ Preserved context (overlap and hierarchy)")
print("  ✓ Document-aware (respects structure)")
print("  ✓ Flexible strategies for different content types")

print("\n🚀 Ready for integration into RAG pipeline!")

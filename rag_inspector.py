# -*- coding: utf-8 -*-
"""
rag_inspector.py - RAG Index Inspector and Management Tool

WHAT:
    Diagnostic and management tool for the RAG (Retrieval Augmented Generation) system.
    Provides visibility into indexed documents, metadata, and relevance scores.
    Enables clearing/resetting index and filtering low-quality results.

WHY:
    - Purpose: Debug RAG data quality issues (e.g., Fritz Haber instead of George Haber)
    - Problem solved: RAG returns irrelevant results due to poor indexing or low scores
    - Design decision: Standalone tool for inspection without modifying core RAG

HOW:
    1. View Index: List all indexed chunks with metadata (source, text preview, score)
    2. Clear Index: Remove all chunks and reset FAISS index
    3. Test Query: Search with relevance score display
    4. Relevance Filter: Reject results below threshold (default 0.7)

TESTING:
    View index contents:
        python rag_inspector.py --view

    Test query:
        python rag_inspector.py --query "George Haber LinkedIn"

    Clear index:
        python rag_inspector.py --clear

    View statistics:
        python rag_inspector.py --stats

EXAMPLES:
    # Check what's indexed
    python rag_inspector.py --view --limit 10

    # Test relevance
    python rag_inspector.py --query "Fritz Haber" --threshold 0.7

    # Clear bad data
    python rag_inspector.py --clear --confirm

AUTHOR: ZenAI Team
MODIFIED: 2026-01-24
VERSION: 1.0.0
"""

import sys
import argparse
from pathlib import Path
from typing import List, Dict, Optional
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Import RAG system
try:
    from zena_mode import LocalRAG
    from zena_mode.rag_db import RAGDatabase
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    logger.error("RAG system not available. Install dependencies: pip install sentence-transformers faiss-cpu")


# ==========================================================================
# RAG INSPECTOR CLASS
# ==========================================================================

class RAGInspector:
    """
    Inspector for RAG index - view, clear, test queries.

    WHAT:
        - Purpose: Diagnostic tool for RAG data quality
        - Methods: view_index, clear_index, test_query, get_stats
        - State: Connects to existing RAG database

    WHY:
        - Problem: RAG returns wrong results (Fritz vs George Haber)
        - Solution: Inspect what's actually indexed
        - Benefit: Find and fix data quality issues

    HOW:
        1. Load RAG system (same as application)
        2. Query database for chunks and metadata
        3. Display with relevance scores
        4. Filter by threshold
        - Complexity: O(n) for view, O(log n) for search
    """

    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize RAG inspector."""
        if not RAG_AVAILABLE:
            raise ImportError("RAG dependencies not available")

        self.cache_dir = cache_dir or Path(".")
        self.rag = LocalRAG(cache_dir=self.cache_dir, lazy_load=False)
        self.db = RAGDatabase(self.cache_dir / "rag.db")

    def get_stats(self) -> Dict:
        """
        Get RAG index statistics.

        WHAT:
            - Returns: Dict with chunk count, sources, avg length
            - Side effects: None (read-only)

        WHY:
            - Purpose: Quick overview of index size
            - Use case: Check if index is empty or needs cleaning

        HOW:
            1. Count total chunks in database
            2. Get unique sources
            3. Calculate average chunk length
        """
        total_chunks = self.db.count_chunks()
        chunks = self.db.get_all_chunks()

        if not chunks:
            return {
                'total_chunks': 0,
                'unique_sources': 0,
                'avg_chunk_length': 0,
                'sources': []
            }

        sources = set(chunk.get('source', chunk.get('metadata', {}).get('source', 'unknown')) for chunk in chunks)
        avg_length = sum(len(chunk.get('text', chunk.get('chunk', ''))) for chunk in chunks) / len(chunks)

        return {
            'total_chunks': total_chunks,
            'unique_sources': len(sources),
            'avg_chunk_length': int(avg_length),
            'sources': sorted(sources)
        }

    def view_index(self, limit: int = 20, offset: int = 0) -> List[Dict]:
        """
        View indexed chunks with metadata.

        WHAT:
            - Accepts: limit (max results), offset (pagination)
            - Returns: List of chunks with text, source, timestamp
            - Side effects: None (read-only)

        WHY:
            - Purpose: See what's actually stored in RAG
            - Use case: Debug why "George Haber" returns Fritz Haber
            - Problem solved: Black box → transparent inspection

        HOW:
            1. Query database for all chunks
            2. Apply offset/limit for pagination
            3. Format with text preview (first 100 chars)
            4. Include metadata (source, timestamp)
        """
        chunks = self.db.get_all_chunks()

        if not chunks:
            logger.info("Index is empty - no chunks found")
            return []

        # Apply pagination
        paginated = chunks[offset:offset + limit]

        # Format for display
        results = []
        for i, chunk in enumerate(paginated, start=offset + 1):
            text = chunk.get('text', chunk.get('chunk', ''))
            metadata = chunk.get('metadata', {})
            results.append({
                'index': i,
                'text_preview': text[:100] + "..." if len(text) > 100 else text,
                'full_text': text,
                'source': chunk.get('source', metadata.get('source', 'unknown')),
                'timestamp': metadata.get('timestamp', 'unknown'),
                'chunk_id': chunk.get('chunk_id', chunk.get('id', 'N/A'))
            })

        return results

    def test_query(self, query: str, k: int = 5, threshold: float = 0.0) -> List[Dict]:
        """
        Test RAG query with relevance scores.

        WHAT:
            - Accepts: query string, k (top results), threshold (min score)
            - Returns: List of results with scores
            - Side effects: None (read-only search)

        WHY:
            - Purpose: Test if query returns relevant results
            - Problem solved: See actual scores for debugging
            - Use case: "George Haber" → check if Fritz Haber score is low

        HOW:
            1. Encode query with sentence transformer
            2. Search FAISS index for top-k
            3. Calculate cosine similarity scores
            4. Filter by threshold (reject low scores)
            5. Return with text, source, score
            - Algorithm: FAISS approximate k-NN
            - Complexity: O(log n) where n = indexed chunks
        """
        # Ensure index is loaded
        if not self.rag._index_loaded:
            self.rag._load_from_db()

        # Search
        results = self.rag.search(query, k=k)

        # Filter by threshold
        filtered = [r for r in results if r.get('score', 0) >= threshold]

        logger.info(f"Query: '{query}' | Found: {len(results)} | After threshold ({threshold}): {len(filtered)}")

        return filtered

    def clear_index(self, confirm: bool = False) -> bool:
        """
        Clear entire RAG index (DESTRUCTIVE).

        WHAT:
            - Accepts: confirm flag (safety)
            - Returns: Success boolean
            - Side effects: Deletes all chunks, resets FAISS index

        WHY:
            - Purpose: Remove bad/irrelevant data
            - Problem solved: Clean slate for re-indexing
            - Use case: Fritz Haber data needs removal

        HOW:
            1. Check confirmation flag
            2. Delete all chunks from database
            3. Reset FAISS index to empty
            4. Clear in-memory cache
            - Irreversible: Always confirm first
        """
        if not confirm:
            logger.warning("Clear index requires --confirm flag. This is DESTRUCTIVE.")
            return False

        try:
            # Clear database
            self.db.clear_all()

            # Clear in-memory
            self.rag.chunks = []
            self.rag.chunk_hashes = set()
            self.rag.index = None
            self.rag._index_loaded = False

            logger.info("RAG index cleared successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to clear index: {e}")
            return False

    def show_relevance_distribution(self, query: str, k: int = 20):
        """
        Show score distribution for debugging relevance.

        WHAT:
            - Accepts: query, k (results to check)
            - Returns: None (prints distribution)
            - Side effects: None (read-only)

        WHY:
            - Purpose: Visualize score spread
            - Problem: Understand why irrelevant results rank high
            - Use case: "George Haber" → see Fritz Haber's score

        HOW:
            1. Get top-k results
            2. Group by score ranges
            3. Display histogram
        """
        results = self.test_query(query, k=k, threshold=0.0)

        if not results:
            logger.info("No results to analyze")
            return

        print("\n" + "=" * 60)
        print("RELEVANCE SCORE DISTRIBUTION")
        print("=" * 60)

        # Group by score ranges
        ranges = {
            '0.9-1.0 (Excellent)': 0,
            '0.7-0.9 (Good)': 0,
            '0.5-0.7 (Fair)': 0,
            '0.3-0.5 (Poor)': 0,
            '0.0-0.3 (Irrelevant)': 0
        }

        for r in results:
            score = r.get('score', 0)
            if score >= 0.9:
                ranges['0.9-1.0 (Excellent)'] += 1
            elif score >= 0.7:
                ranges['0.7-0.9 (Good)'] += 1
            elif score >= 0.5:
                ranges['0.5-0.7 (Fair)'] += 1
            elif score >= 0.3:
                ranges['0.3-0.5 (Poor)'] += 1
            else:
                ranges['0.0-0.3 (Irrelevant)'] += 1

        for range_label, count in ranges.items():
            bar = '#' * count
            print(f"{range_label:25} | {bar} ({count})")

        print()


# ==========================================================================
# CLI INTERFACE
# ==========================================================================

def main():
    parser = argparse.ArgumentParser(description="RAG Index Inspector and Management Tool")

    # Commands
    parser.add_argument('--view', action='store_true', help="View indexed chunks")
    parser.add_argument('--stats', action='store_true', help="Show index statistics")
    parser.add_argument('--query', type=str, help="Test query with relevance scores")
    parser.add_argument('--clear', action='store_true', help="Clear entire index (requires --confirm)")
    parser.add_argument('--distribution', type=str, help="Show relevance score distribution for query")

    # Options
    parser.add_argument('--limit', type=int, default=20, help="Limit results (default: 20)")
    parser.add_argument('--offset', type=int, default=0, help="Offset for pagination (default: 0)")
    parser.add_argument('--threshold', type=float, default=0.0, help="Minimum relevance score (default: 0.0)")
    parser.add_argument('--confirm', action='store_true', help="Confirm destructive operations")
    parser.add_argument('--cache-dir', type=Path, help="RAG cache directory (default: current)")

    args = parser.parse_args()

    if not RAG_AVAILABLE:
        print("[ERROR] RAG system not available. Install: pip install sentence-transformers faiss-cpu")
        return 1

    # Initialize inspector
    try:
        inspector = RAGInspector(cache_dir=args.cache_dir)
    except Exception as e:
        logger.error(f"Failed to initialize RAG inspector: {e}")
        return 1

    # Execute command
    if args.stats:
        stats = inspector.get_stats()
        print("\n" + "=" * 60)
        print("RAG INDEX STATISTICS")
        print("=" * 60)
        print(f"Total Chunks:    {stats['total_chunks']}")
        print(f"Unique Sources:  {stats['unique_sources']}")
        print(f"Avg Chunk Length: {stats['avg_chunk_length']} chars")
        print("\nSources:")
        for source in stats['sources']:
            print(f"  - {source}")
        print()

    elif args.view:
        chunks = inspector.view_index(limit=args.limit, offset=args.offset)
        print("\n" + "=" * 60)
        print(f"INDEXED CHUNKS (showing {args.offset + 1}-{args.offset + len(chunks)})")
        print("=" * 60)
        for chunk in chunks:
            print(f"\n[{chunk['index']}] {chunk['source']}")
            print(f"Preview: {chunk['text_preview']}")
            print(f"ID: {chunk['chunk_id']}")
        print()

    elif args.query:
        results = inspector.test_query(args.query, k=args.limit, threshold=args.threshold)
        print("\n" + "=" * 60)
        print(f"QUERY RESULTS: '{args.query}'")
        print("=" * 60)
        print(f"Threshold: {args.threshold} | Found: {len(results)} results\n")

        for i, result in enumerate(results, 1):
            score = result.get('score', 0)
            text = result.get('text', '')
            source = result.get('source', 'unknown')

            print(f"[{i}] Score: {score:.4f} | Source: {source}")
            print(f"Text: {text[:200]}...")
            print()

    elif args.distribution:
        inspector.show_relevance_distribution(args.distribution, k=args.limit)

    elif args.clear:
        success = inspector.clear_index(confirm=args.confirm)
        if success:
            print("[OK] RAG index cleared successfully")
        else:
            print("[ERROR] Failed to clear index (use --confirm flag)")
            return 1

    else:
        parser.print_help()

    return 0


if __name__ == '__main__':
    sys.exit(main())

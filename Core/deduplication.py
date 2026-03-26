"""
Core/deduplication.py - Content-based deduplication for RAG data

Features:
- Content hashing (SHA256) for exact duplicates
- Fast duplicate detection
- Deduplication strategies (keep_first, keep_last, keep_best)
- Quality scoring for duplicate selection
"""

import hashlib
import logging
from typing import List, Dict, Set, Tuple, Optional
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)


class ContentDeduplicator:
    """Detect and remove exact duplicate content using hashing"""

    def __init__(self):
        """Initialize content deduplicator"""
        self.hash_map: Dict[str, List[Dict]] = defaultdict(list)
        self.stats = {"total_processed": 0, "exact_duplicates": 0, "unique_content": 0}

    def compute_hash(self, text: str) -> str:
        """
        Compute SHA256 hash of text content

        Args:
            text: Text content to hash

        Returns:
            Hex digest of SHA256 hash
        """
        # Normalize text before hashing
        normalized = self._normalize_text(text)

        # Compute SHA256 hash
        hash_obj = hashlib.sha256(normalized.encode("utf-8"))
        return hash_obj.hexdigest()

    def _normalize_text(self, text: str) -> str:
        """Normalize text for consistent hashing"""
        # Remove extra whitespace
        text = " ".join(text.split())

        # Convert to lowercase for case-insensitive comparison
        text = text.lower()

        # Remove common punctuation variations
        text = text.replace("\r\n", "\n")
        text = text.replace("\r", "\n")

        return text.strip()

    def add_document(self, doc_id: str, text: str, metadata: Optional[Dict] = None):
        """
        Add document to deduplication index

        Args:
            doc_id: Unique document identifier
            text: Document text content
            metadata: Optional document metadata
        """
        content_hash = self.compute_hash(text)

        doc_info = {
            "id": doc_id,
            "text": text,
            "hash": content_hash,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat(),
        }

        self.hash_map[content_hash].append(doc_info)
        self.stats["total_processed"] += 1

    def find_duplicates(self) -> Dict[str, List[Dict]]:
        """
        Find all duplicate groups

        Returns:
            Dict mapping content hash to list of duplicate documents
        """
        duplicates = {hash_val: docs for hash_val, docs in self.hash_map.items() if len(docs) > 1}

        self.stats["exact_duplicates"] = sum(len(docs) - 1 for docs in duplicates.values())
        self.stats["unique_content"] = len(self.hash_map)

        logger.info(
            f"Found {len(duplicates)} duplicate groups with {self.stats['exact_duplicates']} duplicate documents"
        )

        return duplicates

    def deduplicate(self, strategy: str = "keep_first") -> Tuple[List[Dict], List[Dict]]:
        """
        Remove duplicates using specified strategy

        Args:
            strategy: Deduplication strategy
                - "keep_first": Keep first occurrence
                - "keep_last": Keep last occurrence
                - "keep_best": Keep document with best quality score

        Returns:
            Tuple of (unique_documents, removed_duplicates)
        """
        unique_docs = []
        removed_docs = []

        for content_hash, docs in self.hash_map.items():
            if len(docs) == 1:
                # No duplicates
                unique_docs.append(docs[0])
            else:
                # Handle duplicates based on strategy
                if strategy == "keep_first":
                    unique_docs.append(docs[0])
                    removed_docs.extend(docs[1:])

                elif strategy == "keep_last":
                    unique_docs.append(docs[-1])
                    removed_docs.extend(docs[:-1])

                elif strategy == "keep_best":
                    # Score documents and keep best
                    scored = [(self._score_document(doc), doc) for doc in docs]
                    scored.sort(reverse=True, key=lambda x: x[0])

                    unique_docs.append(scored[0][1])
                    removed_docs.extend([doc for _, doc in scored[1:]])

                else:
                    raise ValueError(f"Unknown strategy: {strategy}")

        logger.info(f"Deduplication complete: {len(unique_docs)} unique, {len(removed_docs)} removed")

        return unique_docs, removed_docs

    def _score_document(self, doc: Dict) -> float:
        """
        Score document quality for duplicate selection

        Higher score = better quality
        """
        score = 0.0

        # Longer text is often more complete
        text_length = len(doc.get("text", ""))
        score += min(text_length / 1000, 10.0)  # Cap at 10 points

        # Metadata richness
        metadata = doc.get("metadata", {})
        score += len(metadata) * 0.5

        # Prefer documents with titles
        if metadata.get("title"):
            score += 2.0

        # Prefer documents with sources
        if metadata.get("source"):
            score += 1.0

        return score

    def get_statistics(self) -> Dict:
        """Get deduplication statistics"""
        return {
            **self.stats,
            "duplicate_groups": sum(1 for docs in self.hash_map.values() if len(docs) > 1),
            "deduplication_rate": (
                self.stats["exact_duplicates"] / self.stats["total_processed"]
                if self.stats["total_processed"] > 0
                else 0.0
            ),
        }


class SimilarityDeduplicator:
    """Detect near-duplicate content using embeddings"""

    def __init__(self, similarity_threshold: float = 0.95):
        """
        Initialize similarity deduplicator

        Args:
            similarity_threshold: Minimum similarity to consider duplicates (0-1)
        """
        self.threshold = similarity_threshold
        self.documents: List[Dict] = []
        self.embeddings: List = []

    def add_document(self, doc_id: str, text: str, embedding, metadata: Optional[Dict] = None):
        """
        Add document with embedding

        Args:
            doc_id: Document identifier
            text: Document text
            embedding: Document embedding vector
            metadata: Optional metadata
        """
        self.documents.append(
            {
                "id": doc_id,
                "text": text,
                "metadata": metadata or {},
                "timestamp": datetime.now().isoformat(),
            }
        )
        self.embeddings.append(embedding)

    def find_similar_pairs(self) -> List[Tuple[int, int, float]]:
        """
        Find pairs of similar documents

        Returns:
            List of (doc1_idx, doc2_idx, similarity) tuples
        """

        similar_pairs = []

        # Compare all pairs
        for i in range(len(self.documents)):
            for j in range(i + 1, len(self.documents)):
                similarity = self._cosine_similarity(self.embeddings[i], self.embeddings[j])

                if similarity >= self.threshold:
                    similar_pairs.append((i, j, similarity))

        logger.info(f"Found {len(similar_pairs)} similar pairs (threshold: {self.threshold})")

        return similar_pairs

    def _cosine_similarity(self, vec1, vec2) -> float:
        """Calculate cosine similarity between two vectors"""
        import numpy as np

        vec1 = np.array(vec1)
        vec2 = np.array(vec2)

        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))

    def deduplicate_clusters(self) -> Tuple[List[Dict], List[Dict]]:
        """
        Remove near-duplicates by clustering similar documents

        Returns:
            Tuple of (unique_documents, removed_duplicates)
        """
        similar_pairs = self.find_similar_pairs()

        # Build clusters of similar documents
        clusters = self._build_clusters(similar_pairs)

        # Keep best document from each cluster
        unique_docs = []
        removed_docs = []

        processed = set()

        for cluster in clusters:
            if not cluster:
                continue

            # Get documents in cluster
            cluster_docs = [self.documents[i] for i in cluster]

            # Score and keep best
            scored = [(self._score_document(doc), doc, i) for doc, i in zip(cluster_docs, cluster)]
            scored.sort(reverse=True, key=lambda x: x[0])

            # Keep best
            unique_docs.append(scored[0][1])
            processed.add(scored[0][2])

            # Remove rest
            for _, doc, idx in scored[1:]:
                removed_docs.append(doc)
                processed.add(idx)

        # Add documents not in any cluster
        for i, doc in enumerate(self.documents):
            if i not in processed:
                unique_docs.append(doc)

        logger.info(f"Similarity deduplication: {len(unique_docs)} unique, {len(removed_docs)} removed")

        return unique_docs, removed_docs

    def _build_clusters(self, pairs: List[Tuple[int, int, float]]) -> List[Set[int]]:
        """Build clusters from similar pairs using union-find"""
        if not pairs:
            return []

        # Union-find to build clusters
        parent = {}

        def find(x):
            if x not in parent:
                parent[x] = x
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]

        def union(x, y):
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py

        # Union similar documents
        for i, j, _ in pairs:
            union(i, j)

        # Build clusters
        clusters_dict = defaultdict(set)
        for i in range(len(self.documents)):
            root = find(i)
            clusters_dict[root].add(i)

        return list(clusters_dict.values())

    def _score_document(self, doc: Dict) -> float:
        """Score document quality"""
        score = 0.0

        # Text length
        score += min(len(doc.get("text", "")) / 1000, 10.0)

        # Metadata
        metadata = doc.get("metadata", {})
        score += len(metadata) * 0.5

        if metadata.get("title"):
            score += 2.0
        if metadata.get("source"):
            score += 1.0

        return score


# Singleton instances
_content_deduplicator = None
_similarity_deduplicator = None


def get_content_deduplicator() -> ContentDeduplicator:
    """Get or create content deduplicator instance"""
    global _content_deduplicator
    if _content_deduplicator is None:
        _content_deduplicator = ContentDeduplicator()
    return _content_deduplicator


def get_similarity_deduplicator(threshold: float = 0.95) -> SimilarityDeduplicator:
    """Get or create similarity deduplicator instance"""
    global _similarity_deduplicator
    if _similarity_deduplicator is None:
        _similarity_deduplicator = SimilarityDeduplicator(threshold)
    return _similarity_deduplicator

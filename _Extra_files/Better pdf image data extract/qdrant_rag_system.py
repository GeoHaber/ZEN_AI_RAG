#!/usr/bin/env python3
"""
qdrant_rag_system.py - Production RAG with Qdrant
High-performance, secure, local vector database

Install: pip install qdrant-client sentence-transformers
"""
import logging
from pathlib import Path
from typing import List, Dict, Optional
import json

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        Distance, VectorParams, PointStruct, 
        Filter, FieldCondition, MatchValue
    )
    from sentence_transformers import SentenceTransformer
except ImportError as e:
    print(f"Missing dependencies: {e}")
    print("Install: pip install qdrant-client sentence-transformers")
    exit(1)

try:
    from universal_extractor import UniversalExtractor, DocumentType
except ImportError:
    print("ERROR: universal_extractor.py not found")
    exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


class QdrantRAG:
    """
    Production-grade RAG system using Qdrant.
    100% local, open source, blazing fast.
    """
    
    def __init__(
        self,
        storage_path: str = "./qdrant_storage",
        embedding_model: str = "all-MiniLM-L6-v2",
        collection_name: str = "documents"
    ):
        """
        Initialize Qdrant RAG system.
        
        Args:
            storage_path: Local directory for Qdrant database
            embedding_model: SentenceTransformer model name
            collection_name: Name for the vector collection
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(mode=0o700, exist_ok=True, parents=True)
        
        # Initialize Qdrant client (100% local, no cloud)
        self.client = QdrantClient(path=str(self.storage_path))
        
        # Load embedding model (runs locally on your machine)
        logger.info(f"Loading embedding model: {embedding_model}")
        self.encoder = SentenceTransformer(embedding_model)
        self.vector_size = self.encoder.get_sentence_embedding_dimension()
        
        # Initialize document extractor
        self.extractor = UniversalExtractor(
            chunk_size=1000,
            chunk_overlap=200,
            preprocess_images=True
        )
        
        self.collection_name = collection_name
        logger.info(f"✓ Qdrant RAG initialized at: {self.storage_path.absolute()}")
    
    def create_collection(self, replace_existing: bool = False):
        """
        Create vector collection in Qdrant.
        
        Args:
            replace_existing: If True, delete existing collection
        """
        try:
            if replace_existing:
                self.client.delete_collection(self.collection_name)
                logger.info(f"Deleted existing collection: {self.collection_name}")
        except:
            pass
        
        # Check if collection exists
        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)
        
        if not exists:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE
                )
            )
            logger.info(f"✓ Created collection: {self.collection_name}")
        else:
            logger.info(f"✓ Using existing collection: {self.collection_name}")
    
    def ingest_document(
        self,
        file_path: str,
        doc_type: Optional[DocumentType] = None,
        custom_metadata: Optional[Dict] = None
    ) -> int:
        """
        Extract and ingest document into Qdrant.
        
        Args:
            file_path: Path to PDF, image, or screenshot
            doc_type: Optional document type override
            custom_metadata: Additional metadata to attach
            
        Returns:
            Number of chunks ingested
        """
        file_path = Path(file_path)
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return 0
        
        logger.info(f"Processing: {file_path.name}")
        
        # Extract chunks
        chunks, stats = self.extractor.process(file_path, document_type=doc_type)
        
        if not chunks:
            logger.warning(f"No text extracted from {file_path.name}")
            return 0
        
        # Generate embeddings for all chunks
        texts = [chunk.text for chunk in chunks]
        embeddings = self.encoder.encode(
            texts,
            show_progress_bar=True,
            batch_size=32
        )
        
        # Prepare points for Qdrant
        points = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            # Merge metadata
            payload = {
                "text": chunk.text,
                **chunk.metadata
            }
            if custom_metadata:
                payload.update(custom_metadata)
            
            points.append(PointStruct(
                id=hash(chunk.chunk_id) % (2**63),  # Convert to int
                vector=embedding.tolist(),
                payload=payload
            ))
        
        # Upload to Qdrant
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        
        logger.info(f"✓ Ingested: {len(chunks)} chunks | {stats.summary()}")
        return len(chunks)
    
    def ingest_batch(
        self,
        directory: str,
        extensions: List[str] = None,
        recursive: bool = True
    ) -> Dict:
        """
        Ingest all documents from a directory.
        
        Args:
            directory: Directory path
            extensions: File extensions to process
            recursive: Search subdirectories
            
        Returns:
            Statistics dictionary
        """
        if extensions is None:
            extensions = ['.pdf', '.png', '.jpg', '.jpeg', '.bmp', '.tiff']
        
        dir_path = Path(directory)
        if recursive:
            files = [f for f in dir_path.rglob("*") if f.suffix.lower() in extensions]
        else:
            files = [f for f in dir_path.glob("*") if f.suffix.lower() in extensions]
        
        stats = {
            "total_files": len(files),
            "total_chunks": 0,
            "successful": 0,
            "failed": 0
        }
        
        logger.info(f"Found {len(files)} files to process")
        
        for file in files:
            try:
                chunks_added = self.ingest_document(file)
                stats["total_chunks"] += chunks_added
                stats["successful"] += 1
            except Exception as e:
                logger.error(f"Failed: {file.name} - {e}")
                stats["failed"] += 1
        
        logger.info(
            f"✓ Batch complete: {stats['total_chunks']} chunks from "
            f"{stats['successful']}/{stats['total_files']} files"
        )
        return stats
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.3,
        filter_conditions: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Semantic search with optional filtering.
        
        Args:
            query: Search query
            top_k: Number of results
            score_threshold: Minimum similarity score (0-1)
            filter_conditions: Metadata filters (e.g., {"source": "invoice.pdf"})
            
        Returns:
            List of results with text, metadata, and score
        """
        # Generate query embedding
        query_vector = self.encoder.encode(query).tolist()
        
        # Build filter if provided
        query_filter = None
        if filter_conditions:
            must_conditions = [
                FieldCondition(
                    key=key,
                    match=MatchValue(value=value)
                )
                for key, value in filter_conditions.items()
            ]
            query_filter = Filter(must=must_conditions)
        
        # Search Qdrant
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=top_k,
            score_threshold=score_threshold,
            query_filter=query_filter
        )
        
        # Format results
        formatted = []
        for hit in results:
            formatted.append({
                "text": hit.payload.get("text", ""),
                "metadata": {k: v for k, v in hit.payload.items() if k != "text"},
                "score": hit.score,
                "id": hit.id
            })
        
        return formatted
    
    def hybrid_search(
        self,
        query: str,
        keywords: List[str],
        top_k: int = 5
    ) -> List[Dict]:
        """
        Combine semantic and keyword search.
        
        Args:
            query: Semantic search query
            keywords: Keywords to filter by
            top_k: Number of results
        """
        # First: semantic search
        semantic_results = self.search(query, top_k=top_k * 2)
        
        # Then: filter by keywords
        filtered = []
        for result in semantic_results:
            text_lower = result["text"].lower()
            if any(kw.lower() in text_lower for kw in keywords):
                filtered.append(result)
                if len(filtered) >= top_k:
                    break
        
        return filtered
    
    def get_by_source(self, source_name: str, limit: int = 100) -> List[Dict]:
        """Get all chunks from a specific source file."""
        results = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=Filter(
                must=[FieldCondition(key="source", match=MatchValue(value=source_name))]
            ),
            limit=limit
        )[0]
        
        return [
            {
                "text": hit.payload.get("text"),
                "metadata": {k: v for k, v in hit.payload.items() if k != "text"}
            }
            for hit in results
        ]
    
    def delete_by_source(self, source_name: str) -> int:
        """Delete all chunks from a specific source."""
        # Get all points with this source
        points = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=Filter(
                must=[FieldCondition(key="source", match=MatchValue(value=source_name))]
            ),
            limit=10000
        )[0]
        
        # Delete them
        point_ids = [p.id for p in points]
        if point_ids:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=point_ids
            )
        
        logger.info(f"✓ Deleted {len(point_ids)} chunks from: {source_name}")
        return len(point_ids)
    
    def get_stats(self) -> Dict:
        """Get collection statistics."""
        info = self.client.get_collection(self.collection_name)
        
        return {
            "total_vectors": info.points_count,
            "vector_size": info.config.params.vectors.size,
            "distance_metric": info.config.params.vectors.distance.name,
            "storage_path": str(self.storage_path.absolute()),
            "collection_name": self.collection_name
        }
    
    def create_snapshot(self, output_dir: str = "./snapshots") -> str:
        """
        Create a backup snapshot of the collection.
        
        Returns:
            Path to snapshot file
        """
        snapshot = self.client.create_snapshot(
            collection_name=self.collection_name
        )
        
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        logger.info(f"✓ Snapshot created: {snapshot.name}")
        return snapshot.name
    
    def get_similar_chunks(self, chunk_id: int, top_k: int = 5) -> List[Dict]:
        """Find similar chunks to a given chunk."""
        # Get the vector for this chunk
        point = self.client.retrieve(
            collection_name=self.collection_name,
            ids=[chunk_id],
            with_vectors=True
        )[0]
        
        # Search for similar
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=point.vector,
            limit=top_k + 1  # +1 because it will include itself
        )
        
        # Remove the original chunk
        return [
            {
                "text": hit.payload.get("text"),
                "metadata": {k: v for k, v in hit.payload.items() if k != "text"},
                "score": hit.score
            }
            for hit in results if hit.id != chunk_id
        ][:top_k]


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

def example_basic():
    """Basic usage example."""
    print("\n" + "="*80)
    print("EXAMPLE 1: Basic Qdrant RAG")
    print("="*80)
    
    # Initialize
    rag = QdrantRAG(
        storage_path="./my_qdrant_db",
        embedding_model="all-MiniLM-L6-v2",  # Fast, 384-dim
        collection_name="my_docs"
    )
    rag.create_collection()
    
    # Ingest document
    rag.ingest_document("document.pdf")
    
    # Search
    results = rag.search("What is the invoice total?", top_k=3)
    
    for i, result in enumerate(results, 1):
        print(f"\nResult {i} (score: {result['score']:.3f}):")
        print(f"  Source: {result['metadata']['source']}")
        print(f"  Page: {result['metadata']['page']}")
        print(f"  Text: {result['text'][:150]}...")


def example_advanced_filtering():
    """Advanced search with filtering."""
    print("\n" + "="*80)
    print("EXAMPLE 2: Filtered Search")
    print("="*80)
    
    rag = QdrantRAG()
    rag.create_collection()
    
    # Search only in specific document and page
    results = rag.search(
        query="contract terms",
        top_k=5,
        filter_conditions={
            "source": "contract.pdf",
            "page": 3
        }
    )
    
    print(f"Found {len(results)} results on page 3 of contract.pdf")


def example_batch_processing():
    """Batch document processing."""
    print("\n" + "="*80)
    print("EXAMPLE 3: Batch Processing")
    print("="*80)
    
    rag = QdrantRAG(storage_path="./company_knowledge_base")
    rag.create_collection()
    
    # Ingest entire directory
    stats = rag.ingest_batch(
        directory="./documents",
        extensions=['.pdf', '.docx', '.png'],
        recursive=True
    )
    
    print(f"\n✓ Processed: {stats['total_files']} files")
    print(f"✓ Created: {stats['total_chunks']} chunks")
    print(f"✗ Failed: {stats['failed']} files")


def interactive_demo():
    """Interactive CLI demo."""
    print("\n" + "="*80)
    print("QDRANT RAG - INTERACTIVE DEMO")
    print("="*80)
    
    rag = QdrantRAG(storage_path="./demo_qdrant")
    rag.create_collection()
    
    while True:
        print("\n" + "-"*80)
        print("1. Ingest document")
        print("2. Search")
        print("3. Filtered search")
        print("4. Stats")
        print("5. Create snapshot")
        print("6. Delete by source")
        print("7. Exit")
        
        choice = input("\nChoice: ").strip()
        
        if choice == "1":
            path = input("File path: ").strip()
            rag.ingest_document(path)
        
        elif choice == "2":
            query = input("Search query: ").strip()
            results = rag.search(query, top_k=3)
            
            for i, r in enumerate(results, 1):
                print(f"\n--- Result {i} (score: {r['score']:.3f}) ---")
                print(f"Source: {r['metadata']['source']} (Page {r['metadata']['page']})")
                print(f"{r['text'][:200]}...")
        
        elif choice == "3":
            query = input("Query: ").strip()
            source = input("Filter by source (or Enter to skip): ").strip()
            
            filters = {"source": source} if source else None
            results = rag.search(query, filter_conditions=filters)
            
            print(f"\nFound {len(results)} results")
        
        elif choice == "4":
            stats = rag.get_stats()
            print(f"\nVectors: {stats['total_vectors']}")
            print(f"Storage: {stats['storage_path']}")
        
        elif choice == "5":
            snapshot = rag.create_snapshot()
            print(f"\n✓ Snapshot: {snapshot}")
        
        elif choice == "6":
            source = input("Source to delete: ").strip()
            deleted = rag.delete_by_source(source)
            print(f"\n✓ Deleted {deleted} chunks")
        
        elif choice == "7":
            print("\nGoodbye!")
            break


if __name__ == "__main__":
    print("""
    ╔════════════════════════════════════════════════════════════════════╗
    ║             QDRANT RAG - Production Vector Database                ║
    ║                                                                    ║
    ║  ⚡ 100x faster than ChromaDB                                      ║
    ║  🔒 100% local and secure                                          ║
    ║  🆓 Free and open source (Apache 2.0)                              ║
    ║  🚀 Scales to 100M+ vectors                                        ║
    ╚════════════════════════════════════════════════════════════════════╝
    """)
    
    interactive_demo()

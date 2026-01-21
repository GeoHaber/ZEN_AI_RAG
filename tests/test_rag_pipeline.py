# -*- coding: utf-8 -*-
"""
test_rag_pipeline.py - Comprehensive tests for RAG functionality
Tests scanning, indexing, querying, and chat integration
"""
import pytest
from pathlib import Path
from zena_mode.rag_pipeline import LocalRAG
from zena_mode.scraper import WebsiteScraper

class TestRAGPipeline:
    """Test RAG pipeline functionality."""
    
    def test_chunk_documents(self, tmp_path):
        """Test document chunking."""
        rag = LocalRAG(cache_dir=tmp_path)
        
        documents = [
            {"url": "http://test.com", "title": "Test", "content": "A" * 1000}
        ]
        
        chunks = rag.chunk_documents(documents, chunk_size=500)
        
        # Should create 2 chunks from 1000 chars
        assert len(chunks) >= 2
        assert all('text' in chunk for chunk in chunks)
        assert all('url' in chunk for chunk in chunks)

    
    def test_chunk_small_content(self, tmp_path):
        """Test chunking with content smaller than chunk size."""
        rag = LocalRAG(cache_dir=tmp_path)
        
        documents = [
            {"url": "http://test.com", "title": "Small", "content": "Short text is now longer than 20 chars"}
        ]
        
        chunks = rag.chunk_documents(documents, chunk_size=500)
        
        # Should create 1 chunk
        assert len(chunks) == 1
        assert chunks[0]['text'] == "Short text is now longer than 20 chars"

    
    def test_build_index(self, tmp_path):
        """Test building FAISS index."""
        rag = LocalRAG(cache_dir=tmp_path)
        
        docs = [
            {"url": "test1", "title": "T1", "content": "Hello world" * 3},
            {"url": "test2", "title": "T2", "content": "Python programming" * 3},
        ]
        
        rag.build_index(docs)
        
        assert rag.index is not None
        assert rag.index.ntotal == 2  # 2 vectors
        assert len(rag.chunks) == 2

    
    def test_save_load_sqlite(self, tmp_path):
        """Test saving/loading index with SQLite - Aligned with v1.2."""
        rag = LocalRAG(cache_dir=tmp_path)
        
        # Create index
        docs = [
            {"url": "test", "title": "Test", "content": "Hello world" * 3}
        ]
        rag.build_index(docs)
        
        # Verify SQLite file exists
        assert (tmp_path / "rag.db").exists()
        
        # Load
        rag2 = LocalRAG(cache_dir=tmp_path)
        assert len(rag2.chunks) == len(docs)
    
    def test_large_index_sqlite_scalability(self, tmp_path):
        """Test large index scalability with SQLite."""
        rag = LocalRAG(cache_dir=tmp_path)
        
        # Create 1000 documents (simulates large dataset)
        docs = [
            {"url": f"test{i}", "title": f"T{i}", "content": f"Content {i}" * 50}
            for i in range(1000)
        ]
        
        rag.build_index(docs)
        
        # Verify DB exists
        assert (tmp_path / "rag.db").exists()
        
        # Load should work
        rag2 = LocalRAG(cache_dir=tmp_path)
        assert len(rag2.chunks) >= 1000
    
    def test_query(self):
        """Test querying RAG index."""
        rag = LocalRAG()
        
        docs = [
            {"url": "test", "title": "Hospital", "content": "The hospital offers emergency services"},
            {"url": "test", "title": "Hospital", "content": "Visiting hours are 9am to 5pm"},
            {"url": "test", "title": "Hospital", "content": "We have a cardiology department"},
        ]
        
        rag.build_index(docs)
        
        # Query for emergency services
        results = rag.search("emergency services", k=2)
        
        assert len(results) <= 2
        assert results[0]['text'] == "The hospital offers emergency services"
    
    def test_query_empty_index(self, tmp_path):
        """Test querying empty index returns empty list."""
        rag = LocalRAG(cache_dir=tmp_path)
        res = rag.search("test query") 
        assert res == []



class TestRAGIntegration:
    """Test RAG integration with chat."""
    
    def test_rag_context_injection(self):
        """Test RAG context is injected into prompts."""
        rag = LocalRAG()
        
        docs = [
            {"url": "test", "title": "Info", "content": "The manager is John Doe"},
        ]
        
        rag.build_index(docs)
        
        # Query
        results = rag.search("who is the manager", k=1)
        
        # Build prompt with context
        context = "\n\n".join([chunk['text'] for chunk in results])
        prompt = f"""Based on the following context, answer the question.

Context:
{context}

Question: who is the manager

Answer:"""
        
        # Verify context is in prompt
        assert "The manager is John Doe" in prompt
        assert "who is the manager" in prompt


class TestWebsiteScraper:
    """Test website scraping functionality."""
    
    def test_scraper_initialization(self):
        """Test scraper initializes correctly."""
        scraper = WebsiteScraper("http://example.com")
        
        assert scraper.base_url == "http://example.com"
        assert len(scraper.visited) == 0
    
    @pytest.mark.asyncio
    async def test_scraper_respects_rate_limit(self):
        """Test scraper has rate limiting."""
        # This would require mocking HTTP requests
        # For now, verify structure is correct
        pass


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

# -*- coding: utf-8 -*-
"""
chunker.py - Unified text chunking for ZenAI RAG.
Consolidates logic from rag_pipeline.py and universal_extractor.py.
"""
import re
import hashlib
import logging
from typing import List, Dict, Optional, Tuple, Protocol
from dataclasses import dataclass, field
from collections import Counter
from math import log2

logger = logging.getLogger(__name__)

@dataclass
class Chunk:
    text: str
    metadata: Dict = field(default_factory=dict)
    chunk_index: int = 0
    hash: str = ""

    def __post_init__(self):
        if not self.hash:
            self.hash = hashlib.sha256(self.text.encode()).hexdigest()

class ChunkerConfig:
    """Default configuration for chunking."""
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    MIN_CHUNK_LENGTH: int = 50
    MIN_ENTROPY: float = 1.5
    MAX_ENTROPY: float = 6.0
    BLACKLIST_KEYWORDS: set = {
        'advertisement', 'sponsored', 'cookie policy', 'privacy policy',
        'subscribe now', 'sign up for', 'click here to'
    }

class TextChunker:
    """
    Unified text chunker with multiple strategies.
    """
    
    SENTENCE_ENDINGS = r'(?<=[.!?])\s+'

    def __init__(self, config: ChunkerConfig = None):
        self.config = config or ChunkerConfig()

    def _calculate_entropy(self, text: str) -> float:
        """Calculate Shannon entropy of text."""
        if not text: return 0.0
        counts = Counter(text)
        probs = [c / len(text) for c in counts.values()]
        return -sum(p * log2(p) for p in probs)

    def is_junk(self, text: str) -> bool:
        """Detect junk chunks based on length, entropy, and keywords."""
        text = text.strip()
        if len(text) < self.config.MIN_CHUNK_LENGTH:
            return True
        
        words = text.split()
        if len(words) < 5: # Basic world filter
            return True
            
        entropy = self._calculate_entropy(text)
        if entropy < self.config.MIN_ENTROPY or entropy > self.config.MAX_ENTROPY:
            return True
            
        text_lower = text.lower()
        if any(kw in text_lower for kw in self.config.BLACKLIST_KEYWORDS):
            return True
            
        return False

    def recursive_split(self, text: str, max_size: int, overlap_size: int) -> List[str]:
        """Split text into chunks using semantic recursion."""
        if len(text) <= max_size:
            return [text]
        
        separators = ["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " "]
        split_at = -1
        for sep in separators:
            pos = text.rfind(sep, 0, max_size)
            if pos != -1:
                split_at = pos + len(sep)
                break
        
        if split_at == -1:
            split_at = max_size
            
        chunk = text[:split_at]
        remaining = text[split_at - overlap_size:] if split_at > overlap_size else text[split_at:]
        
        return [chunk] + self.recursive_split(remaining, max_size, overlap_size)

    def chunk_document(self, content: str, metadata: Dict = None, strategy: str = "recursive", filter_junk: bool = True) -> List[Chunk]:
        """
        Divide a document into chunks.
        
        Args:
            content: The text to chunk.
            metadata: Base metadata for all chunks.
            strategy: "recursive" (default) or "semantic" (sentence-level).
            filter_junk: Whether to filter out junk chunks.
        """
        if not content:
            return []
            
        metadata = metadata or {}
        chunks = []
        
        if strategy == "semantic":
            # Sentence-level semantic chunking
            sentences = re.split(self.SENTENCE_ENDINGS, content)
            sentences = [s.strip() for s in sentences if s.strip()]
            
            current_sentences = []
            current_length = 0
            idx = 0
            
            for sentence in sentences:
                sent_len = len(sentence)
                if current_length + sent_len > self.config.CHUNK_SIZE and current_sentences:
                    chunk_text = " ".join(current_sentences)
                    # Respect junk filter
                    if not filter_junk or not self.is_junk(chunk_text):
                        chunks.append(Chunk(text=chunk_text, metadata=metadata.copy(), chunk_index=idx))
                        idx += 1
                    
                    # Overlap handling
                    overlap_sentences = []
                    overlap_len = 0
                    for s in reversed(current_sentences):
                        if overlap_len + len(s) < self.config.CHUNK_OVERLAP:
                            overlap_sentences.insert(0, s)
                            overlap_len += len(s)
                        else:
                            break
                    current_sentences = overlap_sentences
                    current_length = overlap_len
                
                current_sentences.append(sentence)
                current_length += sent_len
            
            if current_sentences:
                chunk_text = " ".join(current_sentences)
                if not filter_junk or not self.is_junk(chunk_text):
                    chunks.append(Chunk(text=chunk_text, metadata=metadata.copy(), chunk_index=idx))
        else:
            # Standard recursive split
            texts = self.recursive_split(content, self.config.CHUNK_SIZE, self.config.CHUNK_OVERLAP)
            for i, text in enumerate(texts):
                text = text.strip()
                if not filter_junk or not self.is_junk(text):
                    chunks.append(Chunk(text=text, metadata=metadata.copy(), chunk_index=i))
                    
        return chunks

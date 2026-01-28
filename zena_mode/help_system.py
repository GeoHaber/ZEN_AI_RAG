import os
import logging
import ast
from typing import Optional, List, Dict, Any
from pathlib import Path
from .rag_pipeline import LocalRAG

logger = logging.getLogger("HelpSystem")

DOCS_TO_INDEX = [
    "README.md",
    "USER_MANUAL.md",
    "zena_master_spec.md",
    "ARCHITECTURE_V2.md",
    "UI_REDESIGN_SPEC.md",
    "INSTALL.md"
]

_help_rag = None

def get_help_rag():
    """Lazy singleton for Help System RAG."""
    global _help_rag
    if _help_rag is None:
        try:
            from config import BASE_DIR
            rag_cache = BASE_DIR / "rag_cache"
            _help_rag = LocalRAG(cache_dir=rag_cache)
        except Exception as e:
            logger.error(f"[HelpSystem] Failed to initialize RAG: {e}")
            return None
    return _help_rag

def index_internal_docs(root_dir: Path, rag: Optional[LocalRAG] = None):
    """
    Scans and indexes project documentation into the RAG system.
    """
    rag = rag or get_help_rag()
    if not rag:
        logger.warning("[HelpSystem] RAG unavailable, skipping indexing.")
        return

    logger.info("📚 Indexing internal documentation for Interactive Help...")
    
    docs_payload = []
    
    # Check root and _Extra_files
    search_paths = [root_dir, root_dir / "_Extra_files"]
    
    for doc_name in DOCS_TO_INDEX:
        content = None
        found_path = None
        
        for p in search_paths:
            candidate = p / doc_name
            if candidate.exists():
                found_path = candidate
                break
        
        if found_path:
            try:
                with open(found_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                docs_payload.append({
                    "title": f"System Doc: {doc_name}",
                    "url": str(found_path),
                    "content": content
                })
                logger.info(f"  [+] Found: {doc_name}")
            except Exception as e:
                logger.error(f"  [-] Failed to read {doc_name}: {e}")
    
    # --- NEW: Index Codebase Docstrings (Self-Awareness) ---
    zena_mode_dir = root_dir / "zena_mode"
    if zena_mode_dir.exists():
        logger.info("🔍 Indexing code docstrings in 'zena_mode'...")
        for py_file in zena_mode_dir.glob("*.py"):
            try:
                if py_file.name == "help_system.py": continue # Avoid recursion if it parses itself
                with open(py_file, "r", encoding="utf-8") as f:
                    node = ast.parse(f.read())
                
                # Extract file-level docstring
                file_doc = ast.get_docstring(node)
                if file_doc:
                    docs_payload.append({
                        "title": f"Code Logic: {py_file.name} (Overview)",
                        "url": str(py_file),
                        "content": file_doc
                    })
                
                # Extract class and function docstrings
                for item in node.body:
                    if isinstance(item, (ast.ClassDef, ast.FunctionDef)):
                        item_doc = ast.get_docstring(item)
                        if item_doc:
                            docs_payload.append({
                                "title": f"Logic: {py_file.name} -> {item.name}",
                                "url": str(py_file),
                                "content": item_doc
                            })
            except Exception as e:
                logger.debug(f"  [-] Failed to parse docstrings in {py_file.name}: {e}")

    if docs_payload:
        rag.build_index(docs_payload)
        logger.info(f"✅ Indexed {len(docs_payload)} documentation/code sources.")
    else:
        logger.warning("⚠️ No documentation files found to index.")

if __name__ == "__main__":
    # Test run
    from config import BASE_DIR
    index_internal_docs(BASE_DIR)

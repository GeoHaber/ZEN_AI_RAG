# -*- coding: utf-8 -*-
"""
zena_mode/batch_engine.py - Batch Analysis & AI Code Review Engine
Handles processing multiple files, generating AI reviews, and persisting results.
"""
import asyncio
import logging
import os
from pathlib import Path
from typing import List, Callable, Optional, Dict, Any
import json
import random

from async_backend import AsyncZenAIBackend
from config_system import config
from locales import get_locale

logger = logging.getLogger('BatchEngine')

class BatchAnalyzer:
    """
    Orchestrates batch processing of multiple files for deep code review.
    """
    
    def __init__(self, backend: AsyncZenAIBackend):
        self.backend = backend
        self.is_running = False
        self._current_task: Optional[asyncio.Task] = None
        
    async def analyze_files(self, 
                            file_paths: List[str], 
                            on_progress: Optional[Callable[[str, float], None]] = None) -> Dict[str, Any]:
        """
        Main entry point for batch analysis.
        
        Args:
            file_paths: List of absolute paths to files.
            on_progress: Callback taking (status_message, percentage_0_to_1).
        """
        self.is_running = True
        locale = get_locale()
        results = []
        total_files = len(file_paths)
        
        if on_progress:
            on_progress(locale.BATCH_PROGRESS_START, 0.0)
            
        for i, path_str in enumerate(file_paths):
            if not self.is_running:
                break
                
            path = Path(path_str)
            filename = path.name
            
            # 1. Update Progress
            progress = (i / total_files)
            if on_progress:
                on_progress(locale.format('BATCH_PROGRESS_READING', filename=filename), progress)
            
            # 2. Read File
            try:
                content = path.read_text(encoding='utf-8', errors='ignore')
            except Exception as e:
                logger.error(f"Error reading {path}: {e}")
                results.append({"path": path_str, "status": "error", "error": str(e)})
                continue
                
            # 3. AI Analysis
            if on_progress:
                on_progress(locale.BATCH_PROGRESS_AI_REVIEW, progress + (0.5 / total_files))
                
            prompt = f"Perform a deep code review of the following file: {filename}\n\n```\n{content}\n```\n\nProvide analysis on: logic issues, security risks, performance improvements, and best practices."
            
            full_review = ""
            async for chunk in self.backend.send_message_async(prompt):
                full_review += chunk
                
            # 4. Save individual analysis
            analysis_filename = f"{path.stem}_zena_analisis.md"
            analysis_path = path.parent / analysis_filename
            
            if on_progress:
                on_progress(locale.format('BATCH_PROGRESS_WRITING', filename=analysis_filename), progress + (0.8 / total_files))
                
            try:
                with open(analysis_path, 'w', encoding='utf-8') as f:
                    f.write(f"# ZenAI Analysis: {filename}\n\n")
                    f.write(full_review)
                results.append({"path": path_str, "status": "completed", "report": str(analysis_path)})
            except Exception as e:
                logger.error(f"Error writing analysis for {path}: {e}")
                results.append({"path": path_str, "status": "error", "error": f"Failed to write report: {e}"})
                
        self.is_running = False
        if on_progress:
            on_progress(locale.BATCH_PROGRESS_COMPLETE, 1.0)
            
        return {"total": total_files, "completed": len([r for r in results if r['status'] == 'completed']), "results": results}

    def stop(self):
        """Cancel the current analysis."""
        self.is_running = False
        if self._current_task:
            self._current_task.cancel()

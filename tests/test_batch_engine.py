# -*- coding: utf-8 -*-
import pytest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from zena_mode.batch_engine import BatchAnalyzer

@pytest.mark.asyncio
async def test_batch_analysis_logic(tmp_path):
    # Setup mock backend
    mock_backend = MagicMock()
    mock_gen = MagicMock()
    mock_gen.__aiter__.return_value = ["AI ", "Review ", "Content"]
    mock_backend.send_message_async.return_value = mock_gen
    
    analyzer = BatchAnalyzer(mock_backend)
    
    # Create mock files
    file1 = tmp_path / "test1.py"
    file1.write_text("print('hello')", encoding='utf-8')
    
    file2 = tmp_path / "test2.py"
    file2.write_text("def foo(): pass", encoding='utf-8')
    
    files = [str(file1), str(file2)]
    
    # Track progress
    progress_updates = []
    def on_progress(msg, pct):
        progress_updates.append((msg, pct))
        
    result = await analyzer.analyze_files(files, on_progress=on_progress)
    
    assert result['total'] == 2
    assert result['completed'] == 2
    
    # Verify report files were created
    assert (tmp_path / "test1_zena_analisis.md").exists()
    assert (tmp_path / "test2_zena_analisis.md").exists()
    
    # Verify content
    report_content = (tmp_path / "test1_zena_analisis.md").read_text(encoding='utf-8')
    assert "AI Review Content" in report_content
    
    # Verify progress was reported
    assert len(progress_updates) > 0
    assert progress_updates[-1][1] == 1.0 # Last one is 100%

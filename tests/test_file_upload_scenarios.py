"""
test_file_upload_scenarios.py
TDD Test: Verify file upload prompt formatting and backend integration.

Scenarios:
1. Text File: "Explain this text" + file content
2. Python File: "Review this code" + file content
"""
import unittest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import format_message_with_attachment

class TestFileUploadScenarios(unittest.TestCase):
    """TestFileUploadScenarios class."""
    
    def test_text_file_formatting(self):
        """Scenario 1: Upload small text file and ask to explain."""
        filename = "notes.txt"
        content = "Meeting notes: Discuss Q3 goals."
        user_query = "Explain this"
        
        # Expected format:
        # [Explicit Context from 'notes.txt']
        # Meeting notes: Discuss Q3 goals.
        # [End Context]
        # 
        # Explain this
        
        formatted = format_message_with_attachment(user_query, filename, content)
        
        self.assertIn(f"attached a file '{filename}' for context", formatted)
        self.assertIn(content, formatted)
        self.assertIn(user_query, formatted)
        
    def test_python_file_formatting(self):
        """Scenario 2: Upload Python file and ask for review."""
        filename = "script.py"
        content = "def hello(): print('world')"
        user_query = "Review this code"
        
        formatted = format_message_with_attachment(user_query, filename, content)
        
        self.assertIn(f"attached a code file '{filename}'", formatted)
        self.assertIn("```python", formatted.lower(), "Should detect python extension and add code blocks")
        self.assertIn(content, formatted)

    def test_binary_file_handling(self):
        """Scenario 3: Attempt to format binary/unknown file."""
        filename = "image.png"
        content = "[Binary Content]"
        user_query = "What is this?"
        
        formatted = format_message_with_attachment(user_query, filename, content)
        
        self.assertIn(user_query, formatted)
        self.assertIn(filename, formatted) 
        # Should probably note it's a binary file or similar

if __name__ == '__main__':
    unittest.main()

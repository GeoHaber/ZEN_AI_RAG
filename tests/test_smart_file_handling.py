import unittest
from utils import format_message_with_attachment


class TestSmartFileHandling(unittest.TestCase):
    """TestSmartFileHandling class."""

    def test_python_file_trigger(self):
        """Python files should trigger a code review/analysis prompt."""
        query = "What does this do?"
        filename = "script.py"
        content = "print('hello')"

        result = format_message_with_attachment(query, filename, content)

        self.assertIn("Please analyze and review", result)
        self.assertIn("```python", result)
        self.assertIn(content, result)

    def test_text_file_trigger(self):
        """Text files should be treated as context."""
        query = "Summarize this."
        filename = "notes.txt"
        content = "Meeting notes..."

        result = format_message_with_attachment(query, filename, content)

        self.assertIn("for context", result)
        self.assertNotIn("analyze and review", result)
        self.assertIn(content, result)


if __name__ == "__main__":
    unittest.main()

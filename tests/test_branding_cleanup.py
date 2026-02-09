import os
import pytest

# Project root directory
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# List of dangerous strings that must be removed for branding consistency
LEGACY_STRINGS = ["Nebula", "NeBULA"]

# We allow these in the current test file or in specific historical logs if needed
# But for now, let's be strict.
EXCLUDE_DIRS = [".git", "__pycache__", ".pytest_cache", "logs", "rag_cache", ".gemini", "dist", "build", ".venv", "node_modules", "conversation_cache", "_legacy_audit", "_sandbox"]
EXCLUDE_FILES = ["test_branding_cleanup.py", "task.md", "implementation_plan.md", "smoke_test_startup.py", "nebula_engine.log", "nebula_debug.log"]

def test_no_legacy_branding_in_codebase():
    """Scan the entire codebase for legacy branding strings."""
    found_violations = []
    
    for root, dirs, files in os.walk(ROOT_DIR):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        
        for file in files:
            if file in EXCLUDE_FILES or not (file.endswith(".py") or file.endswith(".json") or file.endswith(".md")):
                continue
                
            file_path = os.path.join(root, file)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    for legacy in LEGACY_STRINGS:
                        if legacy in content:
                            # Try to find line number
                            lines = content.splitlines()
                            for i, line in enumerate(lines):
                                if legacy in line:
                                    found_violations.append(f"{file_path}:{i+1} - Found '{legacy}'")
            except Exception as e:
                # print(f"Could not read {file_path}: {e}")
                pass
                
    if found_violations:
        message = "\n".join(found_violations[:20]) # Show first 20
        if len(found_violations) > 20:
            message += f"\n... and {len(found_violations) - 20} more."
        pytest.fail(f"Legacy branding strings found in codebase:\n{message}")

if __name__ == "__main__":
    # Allow running directly to see output
    try:
        test_no_legacy_branding_in_codebase()
        print("✅ No legacy branding found!")
    except Exception as e:
        print(f"❌ {e}")

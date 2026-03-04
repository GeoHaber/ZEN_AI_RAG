
import os
import sys
import py_compile
from pathlib import Path

def check_syntax(directory):
    """Check syntax."""
    print(f"🔍 Starting Syntax Check in: {directory}")
    print("=" * 60)
    
    error_count = 0
    checked_count = 0
    
    for root, dirs, files in os.walk(directory):
        # Skip virtualenvs and git
        if ".venv" in root or ".git" in root or "__pycache__" in root:
            continue
            
        for file in files:
            if not file.endswith(".py"):
                continue
            checked_count += 1
            full_path = str(Path(root) / file)
            try:
                py_compile.compile(full_path, doraise=True)
            except py_compile.PyCompileError as e:
                print(f"\n❌ Syntax Error in: {full_path}")
                print(f"   {e}")
                error_count += 1
            except Exception as e:
                print(f"\n⚠️ Unexpected Error checking {full_path}: {e}")
                error_count += 1

    print("\n" + "=" * 60)
    if error_count == 0:
        print(f"✅ Success! Scanned {checked_count} files. No syntax errors found.")
        sys.exit(0)
    else:
        print(f"❌ Failed! Found {error_count} syntax errors in {checked_count} files.")
        sys.exit(1)

if __name__ == "__main__":
    # Scan from current working directory
    check_syntax(os.getcwd())

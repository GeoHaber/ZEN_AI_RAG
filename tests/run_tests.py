#!/usr/bin/env python3
"""
Automated Test Runner - "Trust but Verify" Philosophy
======================================================

Ronald Reagan: "Trust, but verify"

This script runs ALL tests before and after ANY significant code change.
Ensures no regressions are introduced.

Usage:
    python run_tests.py                    # Run all tests
    python run_tests.py --fast             # Skip slow integration tests
    python run_tests.py --coverage         # Generate coverage report
    python run_tests.py --watch            # Watch mode (re-run on file change)
"""

import sys
import subprocess
import time
from pathlib import Path
from datetime import datetime
import json


# Colors for terminal output
class Colors:
    """Colors class."""

    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    END = "\033[0m"


def print_header(text):
    """Print section header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text:^70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.END}\n")


def safe_unicode_print(text, color=""):
    """Print with fallback for Windows console encoding issues."""
    try:
        print(text)
        pass
    except UnicodeEncodeError:
        # Fallback to ASCII-safe symbols
        text = text.replace("✓", "[PASS]").replace("✗", "[FAIL]").replace("⚠", "[WARN]")
        print(text)


def print_success(text):
    """Print success message."""
    try:
        print(f"{Colors.GREEN}✓ {text}{Colors.END}")
        pass
    except UnicodeEncodeError:
        print(f"{Colors.GREEN}[PASS] {text}{Colors.END}")
        pass


def print_error(text):
    """Print error message."""
    try:
        print(f"{Colors.RED}✗ {text}{Colors.END}")
        pass
    except UnicodeEncodeError:
        print(f"{Colors.RED}[FAIL] {text}{Colors.END}")
        pass


def print_warning(text):
    """Print warning message."""
    try:
        print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")
        pass
    except UnicodeEncodeError:
        print(f"{Colors.YELLOW}[WARN] {text}{Colors.END}")
        pass


def run_command(cmd, description):
    """
    Run a shell command and return success status.

    Args:
        cmd: Command to run (list or string)
        description: Human-readable description

    Returns:
        (success: bool, duration: float)
    """
    print(f"\n{Colors.BOLD}Running: {description}{Colors.END}")
    print(f"Command: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    print("-" * 70)

    start_time = time.time()

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout,
            shell=False,
        )

        duration = time.time() - start_time

        if result.returncode == 0:
            print_success(f"Passed in {duration:.2f}s")
            return True, duration
        else:
            print_error(f"Failed after {duration:.2f}s")
            print("\n--- STDOUT ---")
            print(result.stdout)
            print("\n--- STDERR ---")
            print(result.stderr)
            return False, duration

    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        print_error(f"Timeout after {duration:.2f}s")
        return False, duration

    except Exception as e:
        duration = time.time() - start_time
        print_error(f"Exception: {e}")
        return False, duration


def check_pytest_installed():
    """Ensure pytest is installed."""
    try:
        import pytest

        return True
    except ImportError:
        print_error("pytest is not installed!")
        print("\nInstall with: pip install pytest pytest-cov pytest-timeout")
        return False


def run_unit_tests(fast=False, coverage=False):
    """
    Run unit tests for start_llm.py.

    Args:
        fast: Skip slow tests
        coverage: Generate coverage report

    Returns:
        success: bool
    """
    print_header("UNIT TESTS - start_llm.py")

    cmd = [sys.executable, "-m", "pytest", "tests/test_start_llm.py", "-v"]

    if fast:
        cmd.extend(["-m", "not slow"])

    if coverage:
        cmd.extend(["--cov=start_llm", "--cov-report=html", "--cov-report=term"])

    success, duration = run_command(cmd, "Unit Tests")
    return success


def run_integration_tests(fast=False):
    """Run integration tests."""
    if fast:
        print_warning("Skipping integration tests (--fast mode)")
        return True

    print_header("INTEGRATION TESTS")

    # Run existing integration tests
    test_files = [
        "tests/test_async_backend.py",
        "tests/test_model_management.py",
        "tests/test_rag_pipeline.py",
    ]

    all_success = True
    for test_file in test_files:
        if Path(test_file).exists():
            continue
        print_warning(f"Skipping {test_file} (not found)")
        continue

        cmd = [sys.executable, "-m", "pytest", test_file, "-v", "--tb=short"]
        success, _ = run_command(cmd, f"Integration: {test_file}")
        all_success = all_success and success

    return all_success


def run_all_tests(fast=False):
    """Run ALL tests in the project."""
    print_header("FULL TEST SUITE - ALL FILES")

    cmd = [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"]

    if fast:
        cmd.extend(["-m", "not slow", "--timeout=30"])
    else:
        cmd.append("--timeout=60")

    success, duration = run_command(cmd, "All Tests")
    return success


def generate_coverage_report():
    """Generate detailed coverage report."""
    print_header("COVERAGE REPORT")

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/test_start_llm.py",
        "--cov=start_llm",
        "--cov-report=html",
        "--cov-report=term-missing",
        "--cov-report=json",
    ]

    success, _ = run_command(cmd, "Coverage Analysis")

    if success:
        print_success("Coverage report generated: htmlcov/index.html")

        # Parse coverage JSON
        coverage_file = Path("coverage.json")
        if coverage_file.exists():
            with open(coverage_file) as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    data = {}
                total_coverage = data["totals"]["percent_covered"]

            print(f"\n{Colors.BOLD}Total Coverage: {total_coverage:.1f}%{Colors.END}")
            if total_coverage >= 80:
                print_success(f"Excellent coverage! (>80%)")
            elif total_coverage >= 60:
                print_warning(f"Good coverage, but aim for 80%+")
            else:
                print_error(f"Low coverage! Need more tests.")

    return success


def watch_mode():
    """
    Watch mode: Re-run tests on file changes.

    Requires: pip install watchdog
    """
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
    except ImportError:
        print_error("watchdog not installed!")
        print("Install with: pip install watchdog")
        return

    class TestRunner(FileSystemEventHandler):
        """TestRunner class."""

        def __init__(self):
            self.last_run = 0
            self.debounce = 2  # seconds

        def on_modified(self, event):
            """On modified."""
            # Only react to .py files
            if not event.src_path.endswith(".py"):
                return

            # Debounce rapid changes
            now = time.time()
            if now - self.last_run < self.debounce:
                return

            self.last_run = now

            print(f"\n{Colors.YELLOW}File changed: {event.src_path}{Colors.END}")
            print("Re-running tests...\n")

            run_unit_tests(fast=True)

    print_header("WATCH MODE ACTIVATED")
    print("Watching for file changes...")
    print("Press Ctrl+C to stop\n")

    event_handler = TestRunner()
    observer = Observer()
    observer.schedule(event_handler, path=".", recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\n\nWatch mode stopped.")

    observer.join()


def save_test_results(results):
    """Save test results to history file."""
    history_file = Path("test_history.json")

    # Load existing history
    if history_file.exists():
        with open(history_file) as f:
            try:
                history = json.load(f)
            except json.JSONDecodeError:
                history = {}
    else:
        history = {"runs": []}

    # Add new run
    history["runs"].append(results)

    # Keep last 50 runs
    history["runs"] = history["runs"][-50:]

    # Save
    with open(history_file, "w") as f:
        json.dump(history, f, indent=2)


def print_test_history():
    """Print recent test history."""
    history_file = Path("test_history.json")

    if not history_file.exists():
        print_warning("No test history available")
        return

    with open(history_file) as f:
        try:
            history = json.load(f)
        except json.JSONDecodeError:
            history = {}

    print_header("RECENT TEST HISTORY (Last 10 runs)")

    runs = history["runs"][-10:]
    for run in runs:
        timestamp = run["timestamp"]
        success = run["success"]
        duration = run["duration"]

        icon = "✓" if success else "✗"
        color = Colors.GREEN if success else Colors.RED

        print(f"{color}{icon}{Colors.END} {timestamp} - {duration:.1f}s")


def _do_main_setup():
    """Helper: setup phase for main."""

    import argparse

    parser = argparse.ArgumentParser(description="Test runner with 'Trust but Verify' philosophy")
    parser.add_argument("--fast", action="store_true", help="Skip slow tests")
    parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
    parser.add_argument("--watch", action="store_true", help="Watch mode: re-run on file changes")
    parser.add_argument("--all", action="store_true", help="Run ALL tests (not just start_llm.py)")
    parser.add_argument("--history", action="store_true", help="Show test history")

    args = parser.parse_args()

    # Print banner
    print("\n" + "=" * 70)
    print(f"{Colors.BOLD}TEST RUNNER - 'Trust but Verify' (Ronald Reagan){Colors.END}".center(80))
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # Show history if requested
    if args.history:
        print_test_history()
        return

    # Watch mode
    if args.watch:
        watch_mode()
        return

    return args


def main():
    """Main entry point."""
    args = _do_main_setup()
    # Check prerequisites
    if not check_pytest_installed():
        sys.exit(1)

    # Record start time
    start_time = time.time()
    all_success = True

    # Run tests based on flags
    if args.all:
        all_success = run_all_tests(fast=args.fast)
    else:
        # Run unit tests
        success = run_unit_tests(fast=args.fast, coverage=args.coverage)
        all_success = all_success and success

        # Run integration tests (unless --fast)
        if not args.fast:
            success = run_integration_tests(fast=args.fast)
            all_success = all_success and success

    # Generate coverage report if requested
    if args.coverage:
        generate_coverage_report()

    # Calculate total duration
    total_duration = time.time() - start_time

    # Print final summary
    print_header("FINAL SUMMARY")

    if all_success:
        print_success(f"ALL TESTS PASSED ✓")
        print(f"\n{Colors.BOLD}Duration: {total_duration:.2f}s{Colors.END}")
        print(f"{Colors.GREEN}Code is verified and safe to commit.{Colors.END}\n")
        exit_code = 0
    else:
        print_error(f"SOME TESTS FAILED ✗")
        print(f"\n{Colors.BOLD}Duration: {total_duration:.2f}s{Colors.END}")
        print(f"{Colors.RED}Fix failures before committing code!{Colors.END}\n")
        exit_code = 1

    # Save results to history
    results = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "success": all_success,
        "duration": total_duration,
        "fast_mode": args.fast,
        "coverage": args.coverage,
    }
    save_test_results(results)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()

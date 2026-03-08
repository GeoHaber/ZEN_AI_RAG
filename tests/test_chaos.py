# -*- coding: utf-8 -*-
"""
test_chaos.py - Chaos Engineering Tests
=======================================
These tests simulate real-world failure modes and edge cases.
They are designed to find bugs that only appear under stress.
"""

import pytest
import sys
import os
import time
import random
import string
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# =============================================================================
# 1. FUZZ TESTING
# =============================================================================
class TestFuzzing:
    """Fuzz testing with random inputs."""

    def generate_random_string(self, min_len=0, max_len=1000):
        """Generate random string with various characters."""
        length = random.randint(min_len, max_len)
        chars = string.printable + "🎉🔥💯中文العربية"
        return "".join(random.choice(chars) for _ in range(length))

    def test_fuzz_text_chunker(self):
        """Fuzz test the text chunker with random inputs."""
        from zena_mode.chunker import TextChunker

        chunker = TextChunker()

        for _ in range(50):
            random_text = self.generate_random_string(0, 5000)
            try:
                result = chunker.chunk_document(random_text, metadata={}, strategy="recursive")
                assert isinstance(result, list)
            except Exception as e:
                pytest.fail(f"Chunker crashed on random input: {e}")

    def test_fuzz_message_formatting(self):
        """Fuzz test message formatting."""
        from utils import format_message_with_attachment

        for _ in range(50):
            random_text = self.generate_random_string(0, 2000)
            try:
                result = format_message_with_attachment(random_text, "test.txt", "content")
                assert isinstance(result, str)
            except Exception as e:
                pytest.fail(f"format_message_with_attachment crashed: {e}")

    def test_fuzz_normalize_input(self):
        """Fuzz test input normalization."""
        from utils import normalize_input

        fuzz_inputs = [
            "",
            " " * 1000,
            "\n" * 500,
            "\t" * 500,
            "a" * 10000,
            "\x00" * 100,
            "🎉" * 1000,
            self.generate_random_string(100, 5000),
        ]

        for inp in fuzz_inputs:
            try:
                result = normalize_input(inp)
                assert result is None or isinstance(result, str)
            except Exception as e:
                pytest.fail(f"normalize_input crashed on: {repr(inp[:50])}: {e}")


# =============================================================================
# 2. CONCURRENT STRESS
# =============================================================================
class TestConcurrentStress:
    """Heavy concurrent operations."""

    def test_100_concurrent_config_reads(self):
        """100 threads reading config simultaneously."""
        from config_system import config

        results = []
        errors = []

        def worker(thread_id):
            """Worker."""
            try:
                for _ in range(50):
                    _ = config.llm_port
                    _ = config.host
                    _ = str(config)
                results.append(thread_id)
            except Exception as e:
                errors.append((thread_id, str(e)))

        with ThreadPoolExecutor(max_workers=100) as executor:
            futures = [executor.submit(worker, i) for i in range(100)]
            for f in as_completed(futures):
                f.result()

        assert len(errors) == 0, f"Errors: {errors[:5]}"
        assert len(results) == 100

    def test_rapid_dict_mutations(self):
        """Rapidly mutating a shared dict (simulating app_state)."""
        shared_state = {}
        lock = threading.Lock()
        errors = []

        def mutator(thread_id):
            """Mutator."""
            try:
                for i in range(100):
                    key = f"key_{thread_id}_{i % 10}"
                    with lock:
                        shared_state[key] = {"value": i, "thread": thread_id}
                        if len(shared_state) > 20:
                            # Prune old keys
                            to_remove = list(shared_state.keys())[:5]
                            for k in to_remove:
                                shared_state.pop(k, None)
            except Exception as e:
                errors.append((thread_id, str(e)))

        threads = [threading.Thread(target=mutator, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors: {errors}"


# =============================================================================
# 3. MEMORY PRESSURE
# =============================================================================
class TestMemoryPressure:
    """Test behavior under memory pressure."""

    def test_large_string_processing(self):
        """Process very large strings without memory explosion."""
        # 10MB string
        large = "X" * (10 * 1024 * 1024)

        # Should be able to process
        assert len(large) == 10 * 1024 * 1024

        # Generator-based processing shouldn't hold all in memory
        count = sum(1 for c in large if c == "X")
        assert count == 10 * 1024 * 1024

        del large  # Clean up

    def test_many_small_allocations(self):
        """Many small allocations shouldn't cause fragmentation issues."""
        objects = []
        for _ in range(10000):
            objects.append({"id": len(objects), "data": "x" * 100})

        assert len(objects) == 10000

        # Clear gradually
        while objects:
            objects.pop()

        assert len(objects) == 0


# =============================================================================
# 4. TIMEOUT AND DEADLOCK
# =============================================================================
class TestTimeoutAndDeadlock:
    """Test timeout handling and deadlock prevention."""

    def test_lock_timeout(self):
        """Locks should not cause infinite waits."""
        lock = threading.Lock()
        acquired = []

        def try_acquire(thread_id):
            """Try acquire."""
            got_lock = lock.acquire(timeout=0.1)
            acquired.append((thread_id, got_lock))
            if got_lock:
                time.sleep(0.05)
                lock.release()

        # Thread 0 gets lock, others should timeout
        threads = [threading.Thread(target=try_acquire, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=2)

        # At least one should have gotten the lock
        successes = [a for a in acquired if a[1]]
        assert len(successes) >= 1

    def test_no_deadlock_on_nested_operations(self):
        """Nested operations shouldn't deadlock."""
        lock = threading.RLock()  # Reentrant lock

        def nested_operation():
            with lock:
                with lock:  # Nested acquire
                    return True

        result = nested_operation()
        assert result is True


# =============================================================================
# 5. ERROR RECOVERY
# =============================================================================
class TestErrorRecovery:
    """Test that system recovers from errors gracefully."""

    def test_exception_in_thread_doesnt_crash_main(self):
        """Exceptions in threads shouldn't crash the main program."""
        errors = []

        def failing_worker():
            raise ValueError("Intentional test error")

        def catching_worker():
            """Catching worker."""
            try:
                failing_worker()
            except ValueError as e:
                errors.append(str(e))

        threads = [threading.Thread(target=catching_worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 5
        assert all("Intentional" in e for e in errors)

    def test_partial_failure_handling(self):
        """Partial failures in a batch shouldn't fail the entire batch."""
        results = []
        errors = []

        def process_item(item):
            if item % 3 == 0:
                raise ValueError(f"Item {item} failed")
            return item * 2

        for i in range(10):
            try:
                results.append(process_item(i))
            except ValueError as e:
                errors.append(str(e))

        # Should have both successes and failures
        assert len(results) > 0
        assert len(errors) > 0
        assert len(results) + len(errors) == 10


# =============================================================================
# 6. EDGE CASE INPUTS
# =============================================================================
class TestEdgeCaseInputs:
    """Test extreme and unusual inputs."""

    def test_very_long_single_line(self):
        """Very long single-line input."""
        from zena_mode.chunker import TextChunker

        chunker = TextChunker()

        # 50,000 character single line
        long_line = "word " * 10000

        result = chunker.chunk_document(long_line, metadata={}, strategy="recursive")
        assert isinstance(result, list)

    def test_deeply_nested_json(self):
        """Deeply nested JSON structures."""
        import json

        # Create 50-level deep nesting
        nested = "value"
        for _ in range(50):
            nested = {"child": nested}

        # Should serialize and deserialize
        serialized = json.dumps(nested)
        deserialized = json.loads(serialized)
        assert deserialized == nested

    def test_binary_in_string(self):
        """Binary data embedded in strings."""
        binary_string = "Hello\x00World\x01\x02\x03End"

        # Should handle without crashing
        assert len(binary_string) > 0
        assert "\x00" in binary_string

        # Encoding should work
        encoded = binary_string.encode("utf-8")
        decoded = encoded.decode("utf-8")
        assert decoded == binary_string

    def test_unicode_normalization(self):
        """Different Unicode normalizations of same character."""
        import unicodedata

        # é can be represented two ways
        composed = "é"  # Single character
        decomposed = "e\u0301"  # e + combining accent

        # They look the same but are different
        assert composed != decomposed

        # But normalize to same
        assert unicodedata.normalize("NFC", composed) == unicodedata.normalize("NFC", decomposed)


# =============================================================================
# 7. REAL-WORLD FAILURE SCENARIOS
# =============================================================================
class TestRealWorldFailures:
    """Simulate real-world failure scenarios."""

    def test_config_reload_during_access(self):
        """Config reload while being accessed shouldn't crash."""
        from config_system import config

        results = []

        def reader():
            """Reader."""
            for _ in range(100):
                try:
                    _ = config.llm_port
                    _ = config.host
                    results.append("ok")
                except Exception as e:
                    results.append(f"error: {e}")

        threads = [threading.Thread(target=reader) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        errors = [r for r in results if r.startswith("error")]
        assert len(errors) == 0, f"Errors: {errors[:5]}"

    def test_rapid_state_changes(self):
        """Rapid state changes shouldn't corrupt state."""
        state = {"count": 0, "status": "idle"}
        lock = threading.Lock()

        def modifier():
            """Modifier."""
            for i in range(100):
                with lock:
                    state["count"] = i
                    state["status"] = f"step_{i}"
                    # Verify consistency
                    assert state["status"] == f"step_{i}"

        threads = [threading.Thread(target=modifier) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # State should be valid
        assert isinstance(state["count"], int)
        assert state["status"].startswith("step_")


# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-x"])

import concurrent.futures
import threading
import time

from ui_state import UIState


class DummySelect:
    def __init__(self):
        self.options = []
        self.update_called = 0

    def update(self):
        self.update_called += 1


def test_concurrent_clear_and_append():
    state = UIState({'chat_container': [], 'chat_history': []})

    def worker(i):
        # alternate between append and clear to provoke races
        if i % 3 == 0:
            state.clear_chat()
        else:
            state.append_chat_message(i)

    # Run many concurrent workers
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as ex:
        futures = [ex.submit(worker, i) for i in range(200)]
        for f in concurrent.futures.as_completed(futures, timeout=10):
            f.result()

    # After concurrent ops, ensure structures are consistent and same length
    cont = state.get('chat_container')
    hist = state.get('chat_history')

    assert isinstance(cont, list)
    assert isinstance(hist, list)
    assert len(cont) == len(hist)
    # All items must be integers (we only appended ints)
    assert all(isinstance(x, int) for x in cont)
    assert all(isinstance(x, int) for x in hist)


def test_update_model_options_calls_update():
    sel = DummySelect()
    state = UIState({'model_select': sel})

    state.update_model_options(['a', 'b', 'c'])

    assert sel.options == ['a', 'b', 'c']
    assert sel.update_called >= 1

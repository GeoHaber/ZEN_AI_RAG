"""Shim: ensure running `python start_llm.py` executes the full orchestrator
by delegating to the implementation in `_Extra_files/start_llm.py`.

This file historically re-exported symbols which meant running the shim
did not execute the orchestrator's `if __name__ == '__main__'` startup
logic. We now explicitly call the same startup sequence so the single
`start_llm.py` entrypoint launches all necessary jobs (hub, engine, UI).
"""
import sys
from importlib import import_module

# Import the implementation module from the canonical location
_impl = import_module("zena_mode.server")

# Re-export public attributes so `from start_llm import validate_environment` works in tests.
for _name in dir(_impl):
	if _name.startswith("_"):
		continue
	try:
		globals()[_name] = getattr(_impl, _name)
	except Exception:
		# Ignore attributes that cannot be bound
		pass

def _sync_impl_namespace():
	"""Copy current `start_llm` module globals into the implementation module.

	This ensures tests that patch names on `start_llm` (e.g. `start_llm.SERVER_EXE`)
	are visible to `_Extra_files.start_llm` when we call its functions.
	"""
	for name, value in list(globals().items()):
		# Only sync simple names (no modules or private symbols)
		if name.startswith("__"):
			continue
		# Avoid copying delegator wrapper functions back into the implementation
		# (they would overwrite the real impl functions and cause recursion).
		if callable(value) and getattr(value, '__module__', None) == __name__:
			continue
		try:
			setattr(_impl, name, value)
		except Exception:
			# ignore attributes that cannot be set on the impl module
			pass

# Override start_server with a wrapper that syncs patched globals first.
def start_server(*args, **kwargs):
	_sync_impl_namespace()
	return _impl.start_server(*args, **kwargs)

# Also override other potentially invoked entry points to call into impl
def instance_guard(*args, **kwargs):
	_sync_impl_namespace()
	return _impl.instance_guard(*args, **kwargs)

def scale_swarm(*args, **kwargs):
	_sync_impl_namespace()
	return _impl.scale_swarm(*args, **kwargs)


if __name__ == "__main__":
	try:
		# If running in hub-only mode for tests, start the hub immediately
		if "--hub-only" in sys.argv and hasattr(_impl, 'start_hub'):
			_impl.start_hub()
			import time
			while True: time.sleep(1)

		# Run the same startup sequence as the original module's __main__ block.
		if hasattr(_impl, 'validate_environment'):
			_impl.validate_environment()

		if "--guard-bypass" not in sys.argv and hasattr(_impl, 'instance_guard'):
			_impl.instance_guard()

		if "--swarm" in sys.argv and hasattr(_impl, 'scale_swarm'):
			try:
				idx = sys.argv.index("--swarm")
				count = int(sys.argv[idx + 1])
			except Exception:
				count = 1
			_impl.scale_swarm(count)
			# If scaling only, keep process alive.
			import time
			while True: time.sleep(1)

		# Support a lightweight hub-only mode for tests.
		if "--hub-only" in sys.argv and hasattr(_impl, 'start_hub'):
			_impl.start_hub()
			import time
			while True: time.sleep(1)

		# Start the main server/orchestrator
		if hasattr(_impl, 'start_server'):
			_impl.start_server()
		else:
			raise RuntimeError("Orchestrator implementation missing start_server()")
	except Exception as e:
		# Mirror original behavior: print and exit non-zero on fatal error
		print(f"\n❌ FATAL STARTUP ERROR: {e}")
		import traceback
		traceback.print_exc()
		sys.exit(1)

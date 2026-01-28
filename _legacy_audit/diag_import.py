
import time
print("Importing sentence_transformers...", flush=True)
start = time.time()
try:
    import sentence_transformers
    print(f"Success! Took {time.time() - start:.2f}s", flush=True)
except Exception as e:
    print(f"Failed: {e}", flush=True)

print("Importing qdrant_client...", flush=True)
start = time.time()
try:
    import qdrant_client
    print(f"Success! Took {time.time() - start:.2f}s", flush=True)
except Exception as e:
    print(f"Failed: {e}", flush=True)

import traceback

print("FAISS_CHECK_START")
try:
    import faiss

    print("faiss imported:", getattr(faiss, "__file__", "<builtin>"))
    # Try to detect avx modules (names vary)
    has_avx512 = hasattr(faiss, "swigfaiss_avx512")
    has_avx2 = any(hasattr(faiss, name) for name in ("swigfaiss_avx2", "swigfaiss", "swigfaiss_avx2"))
    print("has_avx512:", has_avx512)
    print("has_avx2:", has_avx2)
except Exception:
    traceback.print_exc()
print("FAISS_CHECK_END")

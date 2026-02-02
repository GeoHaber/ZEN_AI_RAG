import concurrent.futures
from zena_mode.rag_manager import RAGManager


def test_update_and_read_consistency():
    mgr = RAGManager()

    def writer(i):
        docs = [f'doc-{i}-{j}' for j in range(5)]
        paths = [f'path-{i}-{j}' for j in range(5)]
        mgr.update_documents(docs, paths)

    def reader():
        d = mgr.documents
        p = mgr.file_paths
        # Ensure lengths match
        assert len(d) == len(p)

    # Run concurrent writers/readers
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        writers = [ex.submit(writer, i) for i in range(20)]
        readers = [ex.submit(reader) for _ in range(50)]
        for f in writers + readers:
            f.result()


def test_clear_documents():
    mgr = RAGManager()
    mgr.update_documents(['a', 'b'], ['p1', 'p2'])
    mgr.clear_documents()
    assert mgr.documents == []
    assert mgr.file_paths == []

import requests, json, time

base = "http://localhost:5050"
print("Waiting for crawl to complete...")
for i in range(60):
    time.sleep(5)
    status = requests.get(f"{base}/api/crawl/status").json()
    running = status["running"]
    progress = status.get("progress", [])
    for p in progress:
        if "pages" in p:
            url = p["url"]
            st = p["status"]
            pg = p["pages"]
            ch = p.get("chunks", 0)
            print(f"  [{i*5}s] {url}: {st} - {pg} pages, {ch} chunks")
        elif "error" in p:
            print(f"  [{i*5}s] ERROR: {str(p['error'])[:200]}")
    if not running:
        break

print()
print("Final status:", json.dumps(status, indent=2))

# Check stats
stats = requests.get(f"{base}/api/stats").json()
print()
print("Index stats:", json.dumps(stats, indent=2))

# Test search
if stats.get("n_chunks", 0) > 0:
    r = requests.post(f"{base}/api/search", json={"query": "Oradea population history", "k": 3})
    data = r.json()
    print()
    print(f"Search: {data['query']} ({data['elapsed_sec']}s)")
    for i, res in enumerate(data["results"]):
        print(f"  #{i+1} [{res['score']:.4f}] {res['page_title'][:50]}")
        print(f"       {res['text'][:120]}...")

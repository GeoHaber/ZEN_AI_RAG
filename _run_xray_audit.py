"""One-shot X-Ray audit of ZEN_AI_RAG connectivity."""
import sys, json, os
sys.path.insert(0, r"C:\Users\Yo930\Documents\GitHub\X_Ray_LLM")
os.chdir(r"C:\Users\Yo930\Documents\GitHub\ZEN_AI_RAG")

from analyzers import analyze_connections, detect_dead_functions

# --- Connection analysis ---
r = analyze_connections(".")
with open("_xray_connections.json", "w", encoding="utf-8") as f:
    json.dump(r, f, indent=2, default=str)

print("=== ORPHAN UI (calls with no backend) ===")
for o in r.get("orphan_ui", []):
    print(f"  {o['file']}:{o['line']}  {o.get('method','?')} {o['url']}")

print("\n=== ORPHAN BACKEND (handlers nobody calls from UI) ===")
for o in r.get("orphan_backend", []):
    print(f"  {o['file']}:{o['line']}  {o.get('method','?')} {o['route']}")

print(f"\nTotal orphan backend: {len(r.get('orphan_backend', []))}")
print(f"Total orphan UI: {len(r.get('orphan_ui', []))}")
print(f"Wired: {r.get('summary',{}).get('wired_count',0)}")

# --- Dead function detection ---
print("\n=== DEAD FUNCTIONS ===")
d = detect_dead_functions(".")
with open("_xray_dead_functions.json", "w", encoding="utf-8") as f:
    json.dump(d, f, indent=2, default=str)

for fn in d.get("dead_functions", []):
    print(f"  {fn['file']}:{fn['line']}  {fn['name']}  ({fn.get('lines',0)} lines)")

print(f"\nTotal defined: {d.get('total_defined',0)}")
print(f"Total dead: {d.get('total_dead',0)}")
print(f"Total called: {d.get('total_called',0)}")

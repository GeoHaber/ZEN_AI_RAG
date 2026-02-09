import subprocess
import sys
import time
import os

def run_test(name, script_path):
    print(f"\n{'='*60}")
    print(f"🧪 RUNNING: {name}")
    print(f"{'='*60}")
    start = time.time()
    try:
        # Prepare environment
        env = os.environ.copy()
        env["PYTHONPATH"] = os.getcwd() # Project root
        
        # Run process
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=120,
            env=env
        )
        duration = time.time() - start
        
        # Output handling
        print(result.stdout)
        if result.stderr:
            print("--- STDERR ---")
            print(result.stderr)
            
        if result.returncode == 0:
            print(f"✅ PASS ({duration:.2f}s)")
            return True, duration
        else:
            print(f"❌ FAIL (Exit Code: {result.returncode})")
            return False, duration
            
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        return False, 0

def check_efficiency():
    print(f"\n{'='*60}")
    print(f"📊 EFFICIENCY AUDIT")
    print(f"{'='*60}")
    
    # Simple check using tasklist
    try:
        result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq python.exe'], capture_output=True, text=True)
        print(result.stdout)
        
        count = result.stdout.count("python.exe")
        print(f"Python Processes Detected: {count}")
        
        if count > 10:
            print("⚠️ WARNING: High number of Python processes detected (Risk of Zombies).")
        else:
            print("✅ Process count is within normal limits.")
            
    except Exception as e:
        print(f"Could not run tasklist: {e}")

def main():
    tests = [
        ("Backend Integration", "tests/test_async_backend.py"),
        ("RAG Pipeline", "tests/test_rag_pipeline.py"),
        ("Voice Diagnostics (Port 8005)", "tests/diagnose_voice_pipeline.py"),
        ("Swarm Endpoints", "tests/verify_swarm_fix.py"),
    ]
    
    results = []
    print("\n🚀 STARTING FULL SYSTEM REGRESSION TEST")
    
    for name, path in tests:
        if os.path.exists(path):
            passed, duration = run_test(name, path)
            results.append((name, passed, duration))
        else:
            print(f"⚠️ SKIPPING {name}: File not found ({path})")
            results.append((name, False, 0))

    check_efficiency()

    print(f"\n{'='*60}")
    print(f"📝 FINAL REPORT")
    print(f"{'='*60}")
    all_pass = True
    for name, passed, duration in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} | {name:<30} | {duration:.2f}s")
        if not passed: all_pass = False
    
    if all_pass:
        print("\n🎉 ALL SYSTEMS GO!")
        sys.exit(0)
    else:
        print("\n⚠️ SOME TESTS FAILED")
        sys.exit(1)

if __name__ == "__main__":
    main()

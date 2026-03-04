import subprocess
import sys
import time
import os

p = subprocess.Popen([sys.executable, "start_llm.py", "--hub-only"], cwd=os.getcwd(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
start = time.time()
timeout = 12
try:
    while time.time() - start < timeout:
        line = p.stdout.readline()
        if line:
            print(line, end='')
        else:
            time.sleep(0.1)
except Exception as e:
    print("EXC:", e)
finally:
    try:
        p.terminate()
    except Exception:
        pass
    try:
        p.wait(3)
    except Exception:
        try:
            p.kill()
        except Exception:
            pass
    print('\nCHILD_EXIT_CODE', p.returncode)

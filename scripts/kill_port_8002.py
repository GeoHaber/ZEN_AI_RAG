import psutil
import sys

port = 8002
killed = []
for proc in psutil.process_iter(["pid", "name"]):
    try:
        for conn in proc.connections(kind="inet"):
            if not conn.laddr.port == port:
                continue
            print("Killing", proc.pid, proc.info.get("name"))
            try:
                proc.terminate()
            except Exception as e:
                print("terminate failed", e)
            killed.append(proc.pid)
    except Exception:
        pass
print("killed:", killed)

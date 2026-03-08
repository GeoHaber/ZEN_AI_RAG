import time
import socket
import sys


def wait_for_port(port, timeout=60):
    """Wait for port."""
    start_time = time.time()
    # [X-Ray auto-fix] print(f"Waiting for port {port}...")
    while time.time() - start_time < timeout:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            result = sock.connect_ex(("127.0.0.1", port))
            if result == 0:
                # [X-Ray auto-fix] print(f"✅ Port {port} is OPEN!")
                return True
        time.sleep(1)
        print(".", end="", flush=True)
    print("\n❌ Timeout waiting for port.")
    return False


if __name__ == "__main__":
    if wait_for_port(8080, timeout=120):
        sys.exit(0)
    else:
        sys.exit(1)

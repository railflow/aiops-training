import os
import platform
import socket
import time

name = os.environ.get("NAME", "world")
# LOOP_SECONDS=0 (default): print once and exit, like a script.
# LOOP_SECONDS=10: print every 10 seconds forever, like a long-running service.
interval = int(os.environ.get("LOOP_SECONDS", "0"))

while True:
    print(f"Hello, {name}! from Python {platform.python_version()} on {socket.gethostname()}", flush=True)
    if interval <= 0:
        break
    time.sleep(interval)

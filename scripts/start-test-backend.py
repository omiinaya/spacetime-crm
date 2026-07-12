#!/usr/bin/env python3
"""Start the CRM test backend and wait for it to be ready."""

import subprocess
import sys
import time
import os
import urllib.request

os.chdir("/home/hindsight/spacetime-crm/server")
env = os.environ.copy()
env["STDB_HOST"] = "localhost"
env["STDB_PORT"] = "3003"
env["STDB_DB"] = "spacetime-crm-test"

logfile = "/tmp/crm-test-backend.log"
with open(logfile, "w") as f:
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "main:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8724",
        ],
        env=env,
        stdout=f,
        stderr=subprocess.STDOUT,
    )

# Wait for health
for i in range(30):
    time.sleep(2)
    try:
        r = urllib.request.urlopen("http://localhost:8724/api/health")
        if r.status == 200:
            print(f"Backend ready (PID={proc.pid})")
            # Keep running
            proc.wait()
            sys.exit(0)
    except Exception:
        pass
    # Check if process died
    if proc.poll() is not None:
        with open(logfile) as f:
            print(f"Backend died (exit={proc.returncode}):")
            print(f.read())
        sys.exit(1)

print("Backend did not become healthy in 60s")
with open(logfile) as f:
    print(f.read())
sys.exit(1)

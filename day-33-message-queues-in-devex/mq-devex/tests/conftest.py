"""Shared fixtures: a REAL nats-server with JetStream, started fresh for every test (about 0.3 s), so no test sees another's messages.
Tests skip if no nats-server binary is found. Find it via $NATS_SERVER_BIN or PATH; see ../README.md ("Run the tests") for how to get one
without installing anything system-wide.
"""
import asyncio
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for p in [ROOT / "lib", ROOT / "lab2-pipeline", ROOT / "lab3-infra-router", ROOT / "lab4-strangler", ROOT / "lab5-bridges"]:
    sys.path.insert(0, str(p))


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Server:
    def __init__(self, binary):
        self.binary = binary
        self.port = free_port()
        self.sd = tempfile.mkdtemp(prefix="nats-js-")
        self.proc = None

    @property
    def url(self):
        return f"nats://127.0.0.1:{self.port}"

    def start(self):
        self.proc = subprocess.Popen([self.binary, "-js", "-sd", self.sd, "-a", "127.0.0.1", "-p", str(self.port)],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        end = time.time() + 10
        while time.time() < end:
            try:
                socket.create_connection(("127.0.0.1", self.port), timeout=0.2).close()
                time.sleep(0.2)
                return
            except OSError:
                time.sleep(0.05)
        self.proc.kill()
        pytest.fail("nats-server did not start")

    def stop(self):
        if self.proc:
            self.proc.terminate()
            self.proc.wait(timeout=10)
            self.proc = None

    def cleanup(self):
        self.stop()
        shutil.rmtree(self.sd, ignore_errors=True)


@pytest.fixture()
def server():
    binary = os.environ.get("NATS_SERVER_BIN") or shutil.which("nats-server")
    if not binary:
        pytest.skip("nats-server not found (set NATS_SERVER_BIN or put it on PATH)")
    s = Server(binary)
    s.start()
    yield s
    s.cleanup()


@pytest.fixture()
def nats_url(server):
    import devbus

    async def make():
        nc, js = await devbus.connect(server.url)
        await devbus.ensure_stream(js)
        await nc.close()

    asyncio.run(make())
    return server.url


@pytest.fixture()
def state_dir(tmp_path):
    return str(tmp_path / "state")

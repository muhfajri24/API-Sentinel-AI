"""Own only explicitly launched loopback services, never terminate an existing one."""

from contextlib import contextmanager
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import httpx

ROOT = Path(__file__).resolve().parents[1]


def available(port: int) -> None:
    with socket.socket() as sock:
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            raise RuntimeError(
                f"Local demo port {port} is already in use; no existing process was stopped"
            ) from None


def wait_for(url: str, process: subprocess.Popen, timeout: float = 30) -> dict | str:
    deadline = time.monotonic() + timeout
    with httpx.Client(timeout=2, trust_env=False, follow_redirects=False) as client:
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError("An owned local service exited during startup")
            try:
                response = client.get(url)
                if response.status_code == 200:
                    try:
                        return response.json()
                    except ValueError:
                        return response.text
            except httpx.HTTPError:
                pass
            time.sleep(0.1)
    raise RuntimeError("An owned local service did not become healthy within the startup budget")


@contextmanager
def local_services(
    *, variant: str = "buggy", controller: bool = False, ui: bool = False, mode: str = "fixture"
):
    if variant not in {"buggy", "corrected"} or mode not in {"fixture", "live"}:
        raise ValueError("Unsupported local service mode")
    for port in [8101] + ([8100] if controller else []) + ([8501] if ui else []):
        available(port)
    processes = []
    env = {
        **os.environ,
        "SYNTHETIC_DEMO_VARIANT": variant,
        "META_MODE": mode,
        "ALLOWED_TEST_ORIGINS": "http://127.0.0.1:8101",
        "CONTROLLER_URL": "http://127.0.0.1:8100",
        "DEMO_API_URL": "http://127.0.0.1:8101",
    }
    if mode == "fixture":
        env["MODEL_API_KEY"] = ""
    with tempfile.TemporaryFile() as logs:
        try:
            demo = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "backend.app.demo_api:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8101",
                ],
                cwd=ROOT,
                env=env,
                stdout=logs,
                stderr=logs,
            )
            processes.append(demo)
            health = wait_for("http://127.0.0.1:8101/health", demo)
            if health != {"status": "ok", "synthetic": True, "variant": variant}:
                raise RuntimeError("Unexpected synthetic target identity")
            if controller:
                process = subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "uvicorn",
                        "backend.app.main:app",
                        "--host",
                        "127.0.0.1",
                        "--port",
                        "8100",
                    ],
                    cwd=ROOT,
                    env=env,
                    stdout=logs,
                    stderr=logs,
                )
                processes.append(process)
                wait_for("http://127.0.0.1:8100/health", process)
            if ui:
                process = subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "streamlit",
                        "run",
                        "ui/streamlit_app.py",
                        "--server.address=127.0.0.1",
                        "--server.port=8501",
                        "--server.headless=true",
                        "--browser.gatherUsageStats=false",
                    ],
                    cwd=ROOT,
                    env=env,
                    stdout=logs,
                    stderr=logs,
                )
                processes.append(process)
                wait_for("http://127.0.0.1:8501/_stcore/health", process)
            yield processes
        finally:
            for process in reversed(processes):
                if process.poll() is None:
                    process.terminate()
            for process in reversed(processes):
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()

"""Token manager service: launches token-usage-manager as a subprocess."""
import logging
import os
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class TokenManagerService:
    """Starts the token-usage-manager FastAPI service as a child process.

    The service exposes a Gemini API proxy with per-key quota management.
    It is typically accessed via a subdomain (e.g. token.yourdomain.com)
    routed by Cloudflare Tunnel to the configured *port*.

    Args:
        path: Filesystem path to the token-usage-manager repository root.
        port: Port the service listens on (default 8001).
    """

    def __init__(self, path: str, port: int = 8001):
        self._path = path
        self._port = port
        self._proc: subprocess.Popen | None = None

    def start(self) -> bool:
        """Start token-usage-manager. Returns True if the process was launched."""
        backend_dir = Path(self._path).expanduser().resolve() / "backend"
        if not backend_dir.exists():
            logger.error(
                "Token manager backend directory not found: %s — skipping startup",
                backend_dir,
            )
            return False

        env = {**os.environ, "PORT": str(self._port)}
        self._proc = subprocess.Popen(
            [
                "uv", "run", "uvicorn", "app.main:app",
                "--host", "0.0.0.0",
                "--port", str(self._port),
            ],
            cwd=str(backend_dir),
            env=env,
        )
        logger.info(
            "Token manager started on port %d (pid=%d)",
            self._port,
            self._proc.pid,
        )
        return True

    def stop(self):
        """Terminate the token manager process."""
        if self._proc is not None and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._proc.kill()
                self._proc.wait()
            logger.info("Token manager stopped")
        self._proc = None

    @property
    def is_running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

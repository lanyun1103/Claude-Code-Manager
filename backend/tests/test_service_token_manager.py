"""Tests for TokenManagerService."""
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from backend.services.token_manager_service import TokenManagerService


def _make_proc(poll_return=None, pid=12345) -> MagicMock:
    """Build a mock subprocess.Popen instance."""
    proc = MagicMock()
    proc.pid = pid
    proc.poll.return_value = poll_return  # None = still running; 0 = exited
    return proc


# ── start ─────────────────────────────────────────────────────────────────────


class TestStart:
    def test_returns_false_when_backend_dir_missing(self, tmp_path):
        svc = TokenManagerService(path=str(tmp_path / "nonexistent"), port=8001)
        assert svc.start() is False
        assert not svc.is_running

    @patch("backend.services.token_manager_service.subprocess.Popen")
    def test_launches_subprocess(self, mock_popen, tmp_path):
        (tmp_path / "backend").mkdir()
        mock_proc = _make_proc()
        mock_popen.return_value = mock_proc

        svc = TokenManagerService(path=str(tmp_path), port=8001)
        result = svc.start()

        assert result is True
        mock_popen.assert_called_once()

    @patch("backend.services.token_manager_service.subprocess.Popen")
    def test_command_contains_uvicorn_and_port(self, mock_popen, tmp_path):
        (tmp_path / "backend").mkdir()
        mock_popen.return_value = _make_proc()

        svc = TokenManagerService(path=str(tmp_path), port=9876)
        svc.start()

        cmd = mock_popen.call_args[0][0]
        assert "uvicorn" in cmd
        assert "9876" in cmd

    @patch("backend.services.token_manager_service.subprocess.Popen")
    def test_cwd_points_to_backend_subdir(self, mock_popen, tmp_path):
        (tmp_path / "backend").mkdir()
        mock_popen.return_value = _make_proc()

        svc = TokenManagerService(path=str(tmp_path), port=8001)
        svc.start()

        kwargs = mock_popen.call_args[1]
        assert kwargs["cwd"] == str(tmp_path / "backend")

    @patch("backend.services.token_manager_service.subprocess.Popen")
    def test_env_contains_port_var(self, mock_popen, tmp_path):
        (tmp_path / "backend").mkdir()
        mock_popen.return_value = _make_proc()

        svc = TokenManagerService(path=str(tmp_path), port=8001)
        svc.start()

        env = mock_popen.call_args[1]["env"]
        assert env["PORT"] == "8001"

    @patch("backend.services.token_manager_service.subprocess.Popen")
    def test_is_running_true_after_start(self, mock_popen, tmp_path):
        (tmp_path / "backend").mkdir()
        mock_popen.return_value = _make_proc(poll_return=None)

        svc = TokenManagerService(path=str(tmp_path), port=8001)
        svc.start()
        assert svc.is_running

    @patch("backend.services.token_manager_service.subprocess.Popen")
    def test_is_running_false_when_process_exited(self, mock_popen, tmp_path):
        (tmp_path / "backend").mkdir()
        mock_popen.return_value = _make_proc(poll_return=0)  # already exited

        svc = TokenManagerService(path=str(tmp_path), port=8001)
        svc.start()
        assert not svc.is_running


# ── stop ──────────────────────────────────────────────────────────────────────


class TestStop:
    @patch("backend.services.token_manager_service.subprocess.Popen")
    def test_terminates_process(self, mock_popen, tmp_path):
        (tmp_path / "backend").mkdir()
        mock_proc = _make_proc()
        mock_popen.return_value = mock_proc

        svc = TokenManagerService(path=str(tmp_path), port=8001)
        svc.start()
        svc.stop()

        mock_proc.terminate.assert_called_once()
        mock_proc.wait.assert_called_once()
        assert not svc.is_running

    @patch("backend.services.token_manager_service.subprocess.Popen")
    def test_kills_on_timeout(self, mock_popen, tmp_path):
        (tmp_path / "backend").mkdir()
        mock_proc = _make_proc()
        # First wait(timeout=10) times out; second wait() after kill() succeeds
        mock_proc.wait.side_effect = [
            subprocess.TimeoutExpired(cmd="uvicorn", timeout=10),
            None,
        ]
        mock_popen.return_value = mock_proc

        svc = TokenManagerService(path=str(tmp_path), port=8001)
        svc.start()
        svc.stop()

        mock_proc.terminate.assert_called_once()
        mock_proc.kill.assert_called_once()

    def test_stop_without_start_is_safe(self):
        svc = TokenManagerService(path="/tmp", port=8001)
        svc.stop()  # must not raise

    @patch("backend.services.token_manager_service.subprocess.Popen")
    def test_stop_idempotent(self, mock_popen, tmp_path):
        (tmp_path / "backend").mkdir()
        mock_proc = _make_proc()
        mock_popen.return_value = mock_proc

        svc = TokenManagerService(path=str(tmp_path), port=8001)
        svc.start()
        svc.stop()
        svc.stop()  # second call is safe — process already gone

        assert mock_proc.terminate.call_count == 1


# ── is_running ────────────────────────────────────────────────────────────────


class TestIsRunning:
    def test_false_before_start(self):
        svc = TokenManagerService(path="/tmp", port=8001)
        assert not svc.is_running

    def test_false_after_stop(self, tmp_path):
        (tmp_path / "backend").mkdir()
        with patch("backend.services.token_manager_service.subprocess.Popen") as mock_popen:
            mock_popen.return_value = _make_proc()
            svc = TokenManagerService(path=str(tmp_path), port=8001)
            svc.start()
            svc.stop()
            assert not svc.is_running

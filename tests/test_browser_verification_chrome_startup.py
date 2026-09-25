"""Tests for robust Headless Chrome / CDP startup state machine.

Covers:
- TEST 1: First Chrome startup fails, second succeeds (recovery, attempt=2)
- TEST 2: Chrome exits early (diagnostics capture exit_code, reason=early_exit, stderr)
- TEST 3: Both attempts fail (exactly 2 attempts, fail closed, no 3rd launch)
- TEST 4: First attempt succeeds (exactly 1 launch, no retry)
- TEST 5: Explicit custom_cdp_port (deterministic behavior, no random replacement)
- TEST 6: Failed attempt cleanup (process terminated/killed, files closed, fresh profile)
"""

from __future__ import annotations

import io
import json
from pathlib import Path
import tempfile
from unittest.mock import MagicMock, patch

import pytest

# Target helper under test in scripts/ci/run_browser_verification.py
from scripts.ci.run_browser_verification import (
    ChromeLaunchResult,
    MAX_CHROME_START_ATTEMPTS,
    launch_headless_chrome,
)


class FakePopen:
    """Mock process simulating Chrome lifecycle with poll(), terminate(), kill(), wait()."""

    def __init__(self, pid: int = 12345, returncode: int | None = None, stderr_text: str = ""):
        self.pid = pid
        self._returncode = returncode
        self.stderr_text = stderr_text
        self.terminated = False
        self.killed = False
        self.waited = False
        self.stderr = None

    def poll(self):
        return self._returncode

    @property
    def returncode(self):
        return self._returncode

    def terminate(self):
        self.terminated = True
        if self._returncode is None:
            self._returncode = -15

    def kill(self):
        self.killed = True
        if self._returncode is None:
            self._returncode = -9

    def wait(self, timeout=None):
        self.waited = True
        return self._returncode


class FakeHTTPResponse:
    def __init__(self, data: dict):
        self._raw = json.dumps(data).encode("utf-8")

    def read(self):
        return self._raw

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


def test_first_attempt_fails_second_succeeds():
    """TEST 1: First Chrome startup fails, second succeeds.

    Expected:
    - Overall startup succeeds.
    - First Chrome process is cleaned up.
    - Result has attempts == 2.
    """
    with tempfile.TemporaryDirectory() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)

        proc1 = FakePopen(pid=1001, returncode=None)
        proc2 = FakePopen(pid=1002, returncode=None)
        launched_procs = [proc1, proc2]

        def fake_popen(*args, **kwargs):
            p = launched_procs.pop(0)
            # simulate writing some stderr
            if "stderr" in kwargs and hasattr(kwargs["stderr"], "write"):
                kwargs["stderr"].write(f"log from pid {p.pid}\n")
                kwargs["stderr"].flush()
            return p

        # urlopen: fails for attempt 1 (returns nothing / raises), succeeds for attempt 2
        call_count = {"val": 0}

        def fake_urlopen(url, *args, **kwargs):
            call_count["val"] += 1
            # First attempt: raise error
            if len(launched_procs) == 1:  # proc1 active
                raise OSError("Connection refused")
            # Second attempt: return valid wsDebuggerUrl
            return FakeHTTPResponse({"webSocketDebuggerUrl": "ws://127.0.0.1:44000/devtools/page/TEST1"})

        with patch("subprocess.Popen", side_effect=fake_popen), \
             patch("urllib.request.urlopen", side_effect=fake_urlopen), \
             patch("scripts.ci.run_browser_verification.find_free_port", side_effect=[44001, 44002]):

            result = launch_headless_chrome(
                chrome_path="mock_chrome",
                tmp_dir=tmp_dir,
                custom_cdp_port=None,
                max_attempts=2,
                poll_timeout_sec=0.2,
                poll_interval_sec=0.02,
            )

            assert isinstance(result, ChromeLaunchResult)
            assert result.attempts == 2
            assert result.ws_url == "ws://127.0.0.1:44000/devtools/page/TEST1"
            assert result.proc == proc2
            # proc1 must have been terminated and waited
            assert proc1.terminated or proc1.killed
            assert proc1.waited


def test_chrome_exits_early_diagnostic_evidence():
    """TEST 2: Chrome exits early.

    Expected:
    - Early exit detected during polling.
    - Failure diagnostics contain exit_code and bounded stderr evidence.
    """
    with tempfile.TemporaryDirectory() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)

        # Chrome exits with returncode 127
        proc1 = FakePopen(pid=2001, returncode=127)
        proc2 = FakePopen(pid=2002, returncode=127)
        launched_procs = [proc1, proc2]

        def fake_popen(*args, **kwargs):
            p = launched_procs.pop(0)
            if "stderr" in kwargs and hasattr(kwargs["stderr"], "write"):
                kwargs["stderr"].write("error while loading shared libraries: libnss3.so\n")
                kwargs["stderr"].flush()
            return p

        with patch("subprocess.Popen", side_effect=fake_popen), \
             patch("scripts.ci.run_browser_verification.find_free_port", side_effect=[45001, 45002]):

            with pytest.raises(RuntimeError) as exc_info:
                launch_headless_chrome(
                    chrome_path="mock_chrome",
                    tmp_dir=tmp_dir,
                    custom_cdp_port=None,
                    max_attempts=2,
                    poll_timeout_sec=0.2,
                    poll_interval_sec=0.02,
                )

            err_msg = str(exc_info.value)
            assert "attempts=2" in err_msg
            assert "exit_code=127" in err_msg
            assert "early_exit" in err_msg
            assert "libnss3.so" in err_msg


def test_both_attempts_fail_fails_closed_no_third_attempt():
    """TEST 3: Both attempts fail.

    Expected:
    - Exactly 2 attempts executed.
    - Fails closed with RuntimeError.
    - No third launch occurs.
    """
    with tempfile.TemporaryDirectory() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)

        launch_count = {"val": 0}

        def fake_popen(*args, **kwargs):
            launch_count["val"] += 1
            return FakePopen(pid=3000 + launch_count["val"], returncode=None)

        def fake_urlopen(url, *args, **kwargs):
            raise OSError("CDP port not responding")

        with patch("subprocess.Popen", side_effect=fake_popen), \
             patch("urllib.request.urlopen", side_effect=fake_urlopen), \
             patch("scripts.ci.run_browser_verification.find_free_port", returncode=None, side_effect=[46001, 46002, 46003]):

            with pytest.raises(RuntimeError) as exc_info:
                launch_headless_chrome(
                    chrome_path="mock_chrome",
                    tmp_dir=tmp_dir,
                    custom_cdp_port=None,
                    max_attempts=2,
                    poll_timeout_sec=0.1,
                    poll_interval_sec=0.02,
                )

            assert launch_count["val"] == 2
            assert "attempts=2" in str(exc_info.value)
            assert "cdp_timeout" in str(exc_info.value) or "failed to bind" in str(exc_info.value).lower()


def test_first_attempt_succeeds_no_retry():
    """TEST 4: First attempt succeeds immediately.

    Expected:
    - Exactly 1 launch.
    - No retry.
    - Result.attempts == 1.
    """
    with tempfile.TemporaryDirectory() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)

        launch_count = {"val": 0}

        def fake_popen(*args, **kwargs):
            launch_count["val"] += 1
            return FakePopen(pid=4001, returncode=None)

        def fake_urlopen(url, *args, **kwargs):
            return FakeHTTPResponse({"webSocketDebuggerUrl": "ws://127.0.0.1:47000/devtools/page/TEST4"})

        with patch("subprocess.Popen", side_effect=fake_popen), \
             patch("urllib.request.urlopen", side_effect=fake_urlopen), \
             patch("scripts.ci.run_browser_verification.find_free_port", return_value=47001):

            result = launch_headless_chrome(
                chrome_path="mock_chrome",
                tmp_dir=tmp_dir,
                custom_cdp_port=None,
                max_attempts=2,
                poll_timeout_sec=0.5,
                poll_interval_sec=0.02,
            )

            assert launch_count["val"] == 1
            assert result.attempts == 1
            assert result.port == 47001
            assert result.ws_url == "ws://127.0.0.1:47000/devtools/page/TEST4"


def test_explicit_custom_cdp_port_contract():
    """TEST 5: Explicit custom_cdp_port contract.

    Expected:
    - When custom_cdp_port is passed, all attempts use strictly that port.
    - No random replacement occurs.
    """
    with tempfile.TemporaryDirectory() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)

        ports_launched = []

        def fake_popen(cmd, *args, **kwargs):
            for arg in cmd:
                if arg.startswith("--remote-debugging-port="):
                    ports_launched.append(int(arg.split("=")[1]))
            return FakePopen(pid=5001 + len(ports_launched), returncode=None)

        def fake_urlopen(url, *args, **kwargs):
            raise OSError("CDP not responding")

        with patch("subprocess.Popen", side_effect=fake_popen), \
             patch("urllib.request.urlopen", side_effect=fake_urlopen):

            with pytest.raises(RuntimeError):
                launch_headless_chrome(
                    chrome_path="mock_chrome",
                    tmp_dir=tmp_dir,
                    custom_cdp_port=48999,
                    max_attempts=2,
                    poll_timeout_sec=0.1,
                    poll_interval_sec=0.02,
                )

            assert ports_launched == [48999, 48999]


def test_failed_attempt_cleanup_and_fresh_profile():
    """TEST 6: Failed attempt cleanup.

    Expected:
    - Attempt 1 process is terminated/killed and waited (reaped).
    - Attempt 2 uses a distinct fresh user-data-dir (profile not reused).
    """
    with tempfile.TemporaryDirectory() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)

        proc1 = FakePopen(pid=6001, returncode=None)
        proc2 = FakePopen(pid=6002, returncode=None)
        procs = [proc1, proc2]
        profiles_used = []

        def fake_popen(cmd, *args, **kwargs):
            p = procs.pop(0)
            for arg in cmd:
                if arg.startswith("--user-data-dir="):
                    profiles_used.append(arg.split("=")[1])
            return p

        def fake_urlopen(url, *args, **kwargs):
            if len(procs) == 1:
                raise OSError("Connection refused")
            return FakeHTTPResponse({"webSocketDebuggerUrl": "ws://127.0.0.1:49000/devtools/page/TEST6"})

        with patch("subprocess.Popen", side_effect=fake_popen), \
             patch("urllib.request.urlopen", side_effect=fake_urlopen), \
             patch("scripts.ci.run_browser_verification.find_free_port", side_effect=[49001, 49002]):

            result = launch_headless_chrome(
                chrome_path="mock_chrome",
                tmp_dir=tmp_dir,
                custom_cdp_port=None,
                max_attempts=2,
                poll_timeout_sec=0.2,
                poll_interval_sec=0.02,
            )

            # Cleanup check on proc1
            assert proc1.waited is True
            assert (proc1.terminated or proc1.killed) is True

            # Fresh profile check
            assert len(profiles_used) == 2
            assert profiles_used[0] != profiles_used[1]
            assert Path(profiles_used[0]).name != Path(profiles_used[1]).name

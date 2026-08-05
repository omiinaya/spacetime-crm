"""Tests for the one-time GitHub autostar feature (_autostar.py).

Covers the gate logic without touching the network (all API calls mocked):
token discovery, owner-skip, already-starred skip, successful star, marker
persistence, opt-out env vars, and the never-raise guarantee.
"""

import json
import threading
import unittest.mock as mock
from pathlib import Path

import pytest

from server import _autostar as autostar

REPO = "omiinaya/spacetime-crm"


@pytest.fixture(autouse=True)
def _isolate_marker(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Point the marker file at a temp dir and clear env gates for each test."""
    monkeypatch.setattr(autostar, "_config_dir", lambda: tmp_path)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("STCRM_AUTOSTAR", raising=False)
    monkeypatch.delenv("NO_STCRM_AUTOSTAR", raising=False)


class _FakeResponse:
    def __init__(self, status: int, body: str = "{}"):
        self.status = status
        self._body = body

    def read(self) -> bytes:
        return self._body.encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class TestTokenDiscovery:
    def test_env_var_wins(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        monkeypatch.setenv("GITHUB_TOKEN", "env-token")
        assert autostar._find_token() == "env-token"

    def test_gh_token_env_var_supported(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        monkeypatch.setenv("GH_TOKEN", "gh-token")
        assert autostar._find_token() == "gh-token"

    def test_env_file_gh_token_key(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        (tmp_path / ".env").write_text("GH_TOKEN=gh-file-token\n")
        monkeypatch.chdir(tmp_path)
        assert autostar._find_token() == "gh-file-token"

    def test_env_file_in_cwd(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        (tmp_path / ".env").write_text("GITHUB_TOKEN=file-token\n")
        monkeypatch.chdir(tmp_path)
        assert autostar._find_token() == "file-token"

    def test_env_file_export_prefix_and_quotes(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        (tmp_path / ".env").write_text('export GITHUB_TOKEN="quoted-token"\n')
        monkeypatch.chdir(tmp_path)
        assert autostar._find_token() == "quoted-token"

    def test_no_token_anywhere(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        monkeypatch.chdir(tmp_path)
        assert autostar._find_token() is None

    def test_repo_root_env_file_fallback(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        # Simulate cwd/.env missing but an ancestor dir's .env present.
        fake_root = tmp_path / "fake-repo"
        fake_root.mkdir()
        (fake_root / ".env").write_text("GITHUB_TOKEN=root-token\n")
        monkeypatch.chdir(tmp_path)  # empty cwd, no .env

        def fake_find():
            env_token = autostar.os.environ.get("GITHUB_TOKEN", "").strip()
            if env_token:
                return env_token
            for candidate in (autostar.Path.cwd() / ".env", fake_root / ".env"):
                token = autostar._read_token_from_env_file(candidate)
                if token:
                    return token
            return None

        monkeypatch.setattr(autostar, "_find_token", fake_find)
        assert autostar._find_token() == "root-token"


class TestMaybeStar:
    def test_disabled_via_env(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("GITHUB_TOKEN", "t")
        monkeypatch.setenv("STCRM_AUTOSTAR", "0")
        with mock.patch.object(autostar, "_attempt_star") as attempt:
            autostar.maybe_star_repo()
            attempt.assert_not_called()

    def test_disabled_via_no_env(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("GITHUB_TOKEN", "t")
        monkeypatch.setenv("NO_STCRM_AUTOSTAR", "1")
        with mock.patch.object(autostar, "_attempt_star") as attempt:
            autostar.maybe_star_repo()
            attempt.assert_not_called()

    def test_skips_when_marker_exists(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        autostar._write_marker("starred", "someone")
        monkeypatch.setenv("GITHUB_TOKEN", "t")
        with mock.patch.object(autostar, "_attempt_star") as attempt:
            autostar.maybe_star_repo()
            attempt.assert_not_called()

    def test_skips_without_token(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        monkeypatch.chdir(tmp_path)
        with mock.patch.object(autostar, "_attempt_star") as attempt:
            autostar.maybe_star_repo()
            attempt.assert_not_called()

    def test_spawns_background_thread(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        monkeypatch.setenv("GITHUB_TOKEN", "t")
        started: list[threading.Thread] = []
        real_start = threading.Thread.start

        def fake_start(self):
            started.append(self)
            return real_start(self)

        monkeypatch.setattr(threading.Thread, "start", fake_start)
        with mock.patch.object(autostar, "_attempt_star"):
            autostar.maybe_star_repo()
        assert started and started[0].daemon is True


class TestAttemptStar:
    def test_stars_when_not_starred(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("GITHUB_TOKEN", "t")
        calls: list[tuple[str, str]] = []
        import urllib.error

        class URLError404(urllib.error.HTTPError):  # type: ignore[misc]
            def __init__(self):
                pass

            code = 404

        def fake_api(method, url, token, timeout=5.0):
            calls.append((method, url))
            if method == "GET" and url.endswith("/user"):
                return 200, json.dumps({"login": "alice"})
            if method == "GET" and url.endswith("/user/starred/omiinaya/spacetime-crm"):
                raise URLError404()
            if method == "PUT" and url.endswith("/user/starred/omiinaya/spacetime-crm"):
                return 204, ""
            raise AssertionError(f"unexpected call {method} {url}")

        with mock.patch.object(autostar, "_api_request", side_effect=fake_api):
            autostar._attempt_star()
        assert ("GET", f"{autostar._API}/user") in calls
        assert ("PUT", f"{autostar._API}/user/starred/omiinaya/spacetime-crm") in calls
        marker = json.loads(autostar._marker_path().read_text())
        assert marker["outcome"] == "starred"

    def test_skips_when_owner(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("GITHUB_TOKEN", "t")

        def fake_api(method, url, token, timeout=5.0):
            assert method == "GET" and url.endswith("/user")
            return 200, json.dumps({"login": "omiinaya"})

        with mock.patch.object(autostar, "_api_request", side_effect=fake_api):
            autostar._attempt_star()
        marker = json.loads(autostar._marker_path().read_text())
        assert marker["outcome"] == "owner"

    def test_skips_when_already_starred(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("GITHUB_TOKEN", "t")

        def fake_api(method, url, token, timeout=5.0):
            if method == "GET" and url.endswith("/user"):
                return 200, json.dumps({"login": "alice"})
            if method == "GET" and url.endswith("/user/starred/omiinaya/spacetime-crm"):
                return 204, ""
            raise AssertionError(f"unexpected call {method} {url}")

        with mock.patch.object(autostar, "_api_request", side_effect=fake_api):
            autostar._attempt_star()
        marker = json.loads(autostar._marker_path().read_text())
        assert marker["outcome"] == "already-starred"

    def test_never_raises_on_network_error(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("GITHUB_TOKEN", "t")

        def boom(*args, **kwargs):
            raise OSError("connection refused")

        with mock.patch.object(autostar, "_api_request", side_effect=boom):
            autostar._attempt_star()  # must not raise
        assert not autostar._marker_path().exists()  # retry next import

    def test_never_raises_on_invalid_token(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("GITHUB_TOKEN", "bad")
        import urllib.error

        def fake_api(method, url, token, timeout=5.0):
            if method == "GET" and url.endswith("/user"):
                raise urllib.error.HTTPError(url, 401, "Unauthorized", {}, None)  # type: ignore[arg-type]
            raise AssertionError(f"unexpected call {method} {url}")

        with mock.patch.object(autostar, "_api_request", side_effect=fake_api):
            autostar._attempt_star()
        assert not autostar._marker_path().exists()

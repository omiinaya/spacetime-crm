#!/usr/bin/env python3
"""PID file lock for cyber-elf daemon — prevents duplicate instances per repo.

Usage:
    python3 scripts/daemon_lock.py acquire <repo_name>   # returns 0 if acquired, 1 if exists
    python3 scripts/daemon_lock.py release <repo_name>   # releases lock (or use --pidfile arg)

Each repo should have exactly one daemon instance. This lock provides the
atomic file locking needed to enforce that.
"""

import os
import sys
import atexit
import fcntl
import signal

LOCK_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".daemon-locks")
os.makedirs(LOCK_DIR, exist_ok=True)


def acquire(repo: str) -> bool:
    """Acquire an exclusive lock for this repo. Returns True if acquired."""
    pid_file = os.path.join(LOCK_DIR, f"{repo}.pid")
    try:
        fd = os.open(pid_file, os.O_RDWR | os.O_CREAT)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        os.truncate(fd, 0)
        os.write(fd, str(os.getpid()).encode())
        os.fsync(fd)

        def cleanup():
            try:
                os.unlink(pid_file)
            except FileNotFoundError:
                pass

        atexit.register(cleanup)
        signal.signal(signal.SIGTERM, lambda *_: cleanup())
        signal.signal(signal.SIGINT, lambda *_: cleanup())
        return True
    except (IOError, OSError):
        try:
            with open(pid_file) as f:
                old_pid = int(f.read().strip())
            os.kill(old_pid, 0)
            return False  # still alive
        except (ProcessLookupError, ValueError, FileNotFoundError):
            pass
        except PermissionError:
            return False
        # Stale — remove and retry
        try:
            os.unlink(pid_file)
        except FileNotFoundError:
            pass
        try:
            fd = os.open(pid_file, os.O_RDWR | os.O_CREAT | os.O_EXCL)
            os.write(fd, str(os.getpid()).encode())
            os.fsync(fd)

            def cleanup2():
                try:
                    os.unlink(pid_file)
                except FileNotFoundError:
                    pass

            atexit.register(cleanup2)
            return True
        except FileExistsError:
            return False
        except Exception:
            return False
    except Exception:
        return True


def release(repo: str) -> bool:
    """Remove the PID file for this repo."""
    pid_file = os.path.join(LOCK_DIR, f"{repo}.pid")
    try:
        os.unlink(pid_file)
        return True
    except FileNotFoundError:
        return True
    except Exception:
        return False


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 scripts/daemon_lock.py acquire|release <repo>")
        sys.exit(1)

    action = sys.argv[1]
    repo = sys.argv[2]

    if action == "acquire":
        if acquire(repo):
            print(f"Lock acquired for {repo}")
            sys.exit(0)
        else:
            print(f"Lock already held for {repo} (duplicate instance)")
            sys.exit(1)
    elif action == "release":
        release(repo)
        print(f"Lock released for {repo}")
        sys.exit(0)
    else:
        print(f"Unknown action: {action}")
        sys.exit(1)

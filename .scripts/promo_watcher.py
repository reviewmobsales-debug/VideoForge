#!/usr/bin/env python3
"""Auto-watch daemon for VideoForge promo pipeline.
Polls VIDEO_DIR every 30s and triggers auto_promo_pipeline.py on new .mp4 files."""
import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path("/Users/openclawmaskin/VideoForge")
VIDEO_DIR = REPO_ROOT / "demo"
SCRIPT = REPO_ROOT / ".scripts" / "auto_promo_pipeline.py"
STATE_FILE = REPO_ROOT / ".scripts" / ".watcher_state.json"
PID_FILE = REPO_ROOT / ".scripts" / ".watcher.pid"
LOG_FILE = REPO_ROOT / ".scripts" / ".watcher.log"
POLL_INTERVAL = 30

def log(msg: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass
    print(line)

def is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False

def acquire_or_exit():
    # Robust PID check: verify actual live process is a promo_watcher.py instance
    if PID_FILE.exists():
        try:
            old_pid = int(PID_FILE.read_text().strip())
            if old_pid != os.getpid() and is_running(old_pid):
                # verify it's actually our script by checking cmdline
                import psutil
                try:
                    proc = psutil.Process(old_pid)
                    cmdline = " ".join(proc.cmdline()).lower()
                    if "promo_watcher.py" in cmdline:
                        log(f"[VideoForge Promo Watcher] another instance is running (PID {old_pid}), exiting")
                        sys.exit(0)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except (ValueError, TypeError):
            pass
    # Stale or no PID file → acquire
    PID_FILE.write_text(str(os.getpid()))

def release():
    try:
        if PID_FILE.exists() and PID_FILE.read_text().strip() == str(os.getpid()):
            PID_FILE.unlink()
    except Exception:
        pass

def load_state():
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {"known": []}

def save_state(state):
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f)
    except Exception as e:
        log(f"[warn] Could not save state: {e}")

def current_mp4s():
    if not VIDEO_DIR.exists():
        return []
    return sorted([p.name for p in VIDEO_DIR.glob("*.mp4") if p.is_file()])

def run_pipeline():
    log("Triggering auto_promo_pipeline.py")
    try:
        subprocess.run([sys.executable, str(SCRIPT)], check=True, cwd=str(REPO_ROOT))
    except subprocess.CalledProcessError as e:
        log(f"[error] Pipeline failed: {e}")

def update_db_status(status: str, details: str):
    db = Path.home() / ".hermes" / "shared_memory.db"
    if not db.exists():
        return
    try:
        import datetime
        conn = sqlite3.connect(str(db))
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS task_status (
                task_id TEXT PRIMARY KEY,
                agent TEXT NOT NULL,
                status TEXT NOT NULL,
                details TEXT,
                updated_at TEXT NOT NULL
            )
        """)
        cur.execute("""
            INSERT INTO task_status (task_id, agent, status, details, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(task_id) DO UPDATE SET
                status=excluded.status,
                details=excluded.details,
                updated_at=excluded.updated_at
        """, ("auto-pro", "researcher", status, details, datetime.datetime.now(datetime.timezone.utc).isoformat()))
        conn.commit()
        conn.close()
    except Exception:
        pass

def main():
    try:
        acquire_or_exit()
        log("[VideoForge Promo Watcher] started (PID: {})".format(os.getpid()))
        state = load_state()
        while True:
            current = current_mp4s()
            new_files = [f for f in current if f not in state["known"]]
            if new_files:
                log(f"[watch] New files detected: {new_files}")
                run_pipeline()
                state["known"] = current
                save_state(state)
                update_db_status("WATCHING", f"auto-triggered for {new_files}")
            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        pass
    finally:
        release()

if __name__ == "__main__":
    main()

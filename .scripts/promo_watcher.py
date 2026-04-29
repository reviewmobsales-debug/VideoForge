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
POLL_INTERVAL = 30

def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"known": []}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def current_mp4s():
    if not VIDEO_DIR.exists():
        return []
    return sorted([p.name for p in VIDEO_DIR.glob("*.mp4") if p.is_file()])

def run_pipeline():
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Triggering auto_promo_pipeline.py")
    try:
        subprocess.run([sys.executable, str(SCRIPT)], check=True, cwd=str(REPO_ROOT))
    except subprocess.CalledProcessError as e:
        print(f"[error] Pipeline failed: {e}")

def update_db_status(status: str, details: str):
    db = Path.home() / ".hermes" / "shared_memory.db"
    if not db.exists():
        return
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
    """, ("auto-pro", "researcher", status, details, __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()))
    conn.commit()
    conn.close()

def main():
    print("[VideoForge Promo Watcher] started")
    state = load_state()
    while True:
        current = current_mp4s()
        new_files = [f for f in current if f not in state["known"]]
        if new_files:
            print(f"[watch] New files detected: {new_files}")
            run_pipeline()
            state["known"] = current
            save_state(state)
            update_db_status("WATCHING", f"auto-triggered for {new_files}")
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()

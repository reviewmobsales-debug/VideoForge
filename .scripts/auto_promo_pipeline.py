#!/usr/bin/env python3
"""Auto-promo pipeline for VideoForge — generates captions, hashtags, and post-ready content."""
import json
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path, PurePath
from datetime import datetime, timezone

REPO_ROOT = Path("/Users/openclawmaskin/VideoForge")
VIDEO_DIR = REPO_ROOT / "demo"
PROMO_DIR = REPO_ROOT / "promo"
DB_PATH = Path.home() / ".hermes" / "shared_memory.db"

def ensure_dirs():
    PROMO_DIR.mkdir(parents=True, exist_ok=True)
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)

def ffprobe(video_path: Path) -> dict:
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,avg_frame_rate,duration",
        "-show_entries", "format=duration,bit_rate,size",
        "-of", "json",
        str(video_path),
    ]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True)
        data = json.loads(out)
    except Exception:
        data = {}
    streams = data.get("streams", [{}])[0] if data.get("streams") else {}
    fmt = data.get("format", {})
    duration = float(fmt.get("duration", 0) or streams.get("duration", 0) or 0)
    width = streams.get("width", 0)
    height = streams.get("height", 0)
    fps_str = streams.get("avg_frame_rate", "0/1")
    try:
        num, den = fps_str.split("/")
        fps = float(num) / float(den) if den != "0" else 0
    except Exception:
        fps = 0
    size = int(fmt.get("size", 0) or 0)
    bitrate = int(fmt.get("bit_rate", 0) or 0)
    return {
        "duration_sec": round(duration, 2),
        "width": width,
        "height": height,
        "fps": round(fps, 2),
        "file_size_bytes": size,
        "bitrate": bitrate,
    }

def extract_thumbnails(video_path: Path, out_dir: Path) -> list[str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    probe = ffprobe(video_path)
    dur = probe["duration_sec"]
    if dur <= 0:
        return []
    timestamps = []
    if dur < 5:
        timestamps = [dur * 0.5]
    else:
        timestamps = [1, dur * 0.33, dur * 0.5, dur * 0.66, dur - 1]
    thumbs = []
    for i, ts in enumerate(timestamps):
        t = max(0, ts)
        thumb_name = out_dir / f"thumb_{i:02d}.jpg"
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", str(video_path), "-ss", str(t),
                "-vframes", "1", "-q:v", "2", str(thumb_name)
            ],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        if thumb_name.exists():
            thumbs.append(str(thumb_name.relative_to(REPO_ROOT)))
    return thumbs

# ── Caption / hashtag banks ──

def generate_captions(video_meta: dict, niche: str = "ai_tool") -> dict:
    duration = video_meta["duration_sec"]
    short = duration < 20
    caps = {}

    # Global / English
    caps["universal"] = [
        "Level up your app reviews with AI — auto-reply smarter, not harder.",
        "The fastest way to turn angry reviews into loyal users.",
        "One dashboard. Every platform. Zero missed reviews.",
    ]

    # TikTok → snappy, punchy, trend-aware (youthful/edgy)
    caps["tiktok"] = [
        "POV: you never miss another review again 📲⚡ #AIMarketing",
        "Reply to every app review in under 5 seconds 💬🤖\n\nNo team needed.",
        "This AI tool makes responding to reviews actually FUN 🎯\nTry it 👇",
    ]

    # Instagram Reels → aesthetic, emojis, story-driven
    caps["instagram"] = [
        "Turn every review into a conversation 💬✨\nAI-powered replies that feel human.\n\nLink in bio.",
        "Your app deserves replies this fast ⚡🤍\n#AppGrowth #AIMarketing",
        "One dashboard → all platforms → done.\nStop drowning in reviews. Start growing ⬆️",
    ]

    # YouTube Shorts → searchable, value-first, CTA
    caps["youtube_shorts"] = [
        "Auto-reply to App Store & Google Play reviews with AI 🤖\nSave 10+ hours a week.",
        "This simple AI tool increased our review response rate from 12% → 98% 📈",
        "Stop ignoring negative reviews. Fix them in seconds with AI 👇",
    ]

    # Twitter/X → concise, punchy, maybe threaded
    caps["twitter"] = [
        "AI just made replying to app reviews effortless.\n\nOne dashboard. All platforms. Zero missed reviews. 🚀",
        "Your support team called — they want this tool.\n\nAuto-reply to every review in seconds ⚡",
    ]

    # LinkedIn → professional, ROI-focussed
    caps["linkedin"] = [
        "For app founders: AI review automation cuts response time by 95% and boosts ratings.\n\nOne dashboard, every platform.",
        "Customer retention starts with being heard. Automate review replies without losing the human touch.",
    ]

    return caps

def generate_hashtags(niche: str = "ai_tool") -> dict:
    core = ["#AIMarketing", "#AppGrowth", "#SaaS", "#AI", "#AppStore"]
    secondary = ["#ReviewManagement", "#CustomerSupport", "#StartupLife", "#ProductHunt", "#GrowthHacking"]
    audience = ["#IndieHackers", "#AppDevelopers", "#SaaSFounders", "#DigitalMarketing", "#MarTech"]
    trending = ["#AITools", "#Automation", "#NoCode", "#BuildInPublic", "#TechTrends"]
    return {
        "core": core,
        "secondary": secondary,
        "audience": audience,
        "trending": trending,
        "platform_bundles": {
            "tiktok": " ".join(core[:3] + trending[:2] + audience[:1]),
            "instagram": " ".join(core[:4] + secondary[:3] + audience[:2]),
            "youtube_shorts": " ".join(core[:4] + secondary[:2] + trending[:2]),
            "twitter": " ".join(core[:3] + trending[:3]),
            "linkedin": " ".join(secondary[:3] + audience[:3]),
        },
    }

def platform_posts(video_meta: dict, captions: dict, hashtags: dict, video_name: str) -> dict:
    posts = {}
    for platform in ["tiktok", "instagram", "youtube_shorts", "twitter", "linkedin"]:
        cap = captions[platform][0] if captions.get(platform) else captions["universal"][0]
        tag_bundle = hashtags["platform_bundles"].get(platform, "")
        posts[platform] = {
            "caption": cap,
            "hashtags": tag_bundle,
            "full_text": f"{cap}\n\n{tag_bundle}".strip(),
            "cta": "Link in bio / Try free 👇" if platform in ("tiktok", "instagram", "youtube_shorts") else "Learn more at reviewmob.ai",
            "character_count": len(f"{cap}\n\n{tag_bundle}".strip()),
            "ready": True,
        }
    return posts

def build_metadata(video_path: Path, niche: str = "ai_tool") -> dict:
    video_name = video_path.stem
    relative_path = str(video_path.relative_to(REPO_ROOT))
    meta = ffprobe(video_path)
    captions = generate_captions(meta, niche)
    hashtags = generate_hashtags(niche)
    thumb_dir = PROMO_DIR / video_name / "thumbnails"
    thumbs = extract_thumbnails(video_path, thumb_dir)
    posts = platform_posts(meta, captions, hashtags, video_name)
    data = {
        "video_id": video_name,
        "video_file": relative_path,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "niche": niche,
        "video_properties": meta,
        "captions": captions,
        "hashtags": hashtags,
        "thumbnails": thumbs,
        "platform_posts": posts,
        "status": {
            "promo_ready": True,
            "posted": {},
            "scheduled": {},
        },
    }
    return data

def save_metadata(data: dict, video_name: str):
    out_path = PROMO_DIR / video_name / "metadata.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"[saved] {out_path}")

def update_task_status(task_name: str, status: str, details: str = ""):
    if not DB_PATH.exists():
        print("[warn] shared_memory.db not found, skipping DB update")
        return
    conn = sqlite3.connect(str(DB_PATH))
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
    """, (task_name, "researcher", status, details, datetime.now(timezone.utc).isoformat()))
    conn.commit()
    conn.close()
    print(f"[db] task '{task_name}' → {status}")

def scan_and_process():
    ensure_dirs()
    videos = sorted(VIDEO_DIR.glob("*.mp4"))
    if not videos:
        print("[info] No .mp4 files found in", VIDEO_DIR)
        return
    for vp in videos:
        if not vp.is_file():
            continue
        meta_path = PROMO_DIR / vp.stem / "metadata.json"
        if meta_path.exists():
            print(f"[skip] Already processed: {vp.name}")
            continue
        print(f"[process] {vp.name}")
        data = build_metadata(vp)
        save_metadata(data, vp.stem)
    update_task_status("auto-pro", "COMPLETED", f"Processed {len(videos)} video(s)")
    print("[done] auto-pro pipeline complete")

if __name__ == "__main__":
    scan_and_process()

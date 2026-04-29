#!/usr/bin/env python3
"""
tiktok_football_edit.py — 24/7 Autonomous TikTok Football Edit Generator
Input : football_footage/*.mp4, tiktok_base.mp3
Output: output.mp4  (1080×1920, ~15s, beat-synced, text overlays)
Deploy: auto-push to VideoForge repo → GitHub Pages
"""
import argparse
import json
import math
import os
import random
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

try:
    import librosa
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
except ImportError as e:
    print(f"Missing deps: {e}. Install: pip install librosa numpy pillow", file=sys.stderr)
    sys.exit(1)

BASEDIR = Path.home() / "VideoForge"
FOOTDIR = BASEDIR / "football_footage"
OUTPATH = BASEDIR / "demo" / "output.mp4"
MUSICPATH = BASEDIR / "tiktok_base.mp3"
PROMODIR = BASEDIR / "promo"
GIT_REPO = BASEDIR
TARGET_W, TARGET_H = 1080, 1920
TARGET_DURATION = 15.0

# ── Theme bank ──
THEMES = [
    {"title": "GOAL MACHINE",    "subtitle": "UNSTOPPABLE",    "colors": ["#FF3B30","#FFFFFF"]},
    {"title": "DRIBBLE KING",    "subtitle": "NO LOOK",        "colors": ["#34C759","#FFFFFF"]},
    {"title": "FUTURE LEGEND",   "subtitle": "BORN READY",     "colors": ["#007AFF","#FFFFFF"]},
    {"title": "BARCA DNA",       "subtitle": "LA MASIA",       "colors": ["#AF52DE","#FFD60A"]},
    {"title": "SKILL SHOW",      "subtitle": "NEXT LEVEL",     "colors": ["#FF9500","#FFFFFF"]},
    {"title": "HAT TRICK",       "subtitle": "ICE COLD",       "colors": ["#64D2FF","#FFFFFF"]},
    {"title": "TOP CORNER",      "subtitle": "PERFECTION",     "colors": ["#FF2D55","#FFFFFF"]},
]

# ── Beat detection ──

def detect_beats(audio_path: str):
    y, sr = librosa.load(audio_path, sr=44100, mono=True)
    tempo_raw, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    tempo = float(tempo_raw[0]) if hasattr(tempo_raw, '__iter__') else float(tempo_raw)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    beats = [{"time": float(t)} for t in beat_times]
    duration = float(len(y) / sr)
    return {"tempo": tempo, "beats": beats, "duration": duration, "sr": sr}

# ── Text overlay PNG generation ──

def make_text_png(theme: dict, out_png: Path, w=1080, h=300):
    """Generate a transparent PNG with bold TikTok-style text."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Try system fonts
    font_paths = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
        "/System/Library/Fonts/ArialHB.ttc",
    ]
    font_large = None
    font_small = None
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                font_large = ImageFont.truetype(fp, 72)
                font_small = ImageFont.truetype(fp, 42)
                break
            except Exception:
                continue
    if font_large is None:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()

    title = theme["title"]
    subtitle = theme["subtitle"]
    color1 = theme["colors"][0]
    color2 = theme["colors"][1]

    # Shadow outline effect for title
    tx, ty = w // 2, h // 2 - 20
    for dx in (-2, -1, 0, 1, 2):
        for dy in (-2, -1, 0, 1, 2):
            draw.text((tx+dx, ty+dy), title, font=font_large, fill="#000000", anchor="mm")
    draw.text((tx, ty), title, font=font_large, fill=color1, anchor="mm")

    # Subtitle
    sx, sy = w // 2, h // 2 + 60
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            draw.text((sx+dx, sy+dy), subtitle, font=font_small, fill="#000000", anchor="mm")
    draw.text((sx, sy), subtitle, font=font_small, fill=color2, anchor="mm")

    out_png.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_png, "PNG")
    return str(out_png)

# ── Video segmentation ──

def segment_video(video_path: Path, beat_data: dict, tmpdir: Path):
    """Cut input video into segments aligned with beats (max segments for 15s output)."""
    beats = beat_data["beats"]
    # Source duration
    src_dur = float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)
    ]).decode().strip())
    # Budget: allow segments up to ~17s to leave room for xfade overlap (~2s total)
    seg_budget = min(src_dur - 0.5, 17.0)
    raw_times = sorted({round(b["time"], 2) for b in beats if 0.3 < b["time"] < seg_budget})
    chosen = []
    last = -999
    for t in raw_times:
        if t - last >= 1.5:
            chosen.append(t)
            last = t
    if len(chosen) > 7:
        step = len(chosen) // 7
        chosen = chosen[::step][:7]
    segments = [0.0] + chosen + [seg_budget]
    segments = sorted(set(round(s, 2) for s in segments))

    seg_files = []
    n = len(segments) - 1
    for i in range(n):
        start = segments[i]
        end = segments[i+1]
        seg_path = tmpdir / f"seg_{i:03d}.mp4"
        seg_files.append(seg_path)
        dur = end - start
        cmd = [
            "ffmpeg", "-y", "-ss", str(start), "-i", str(video_path),
            "-t", str(dur),
            "-vf", f"scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=decrease,pad={TARGET_W}:{TARGET_H}:(ow-iw)/2:(oh-ih)/2:black,fps=30,setpts=PTS-STARTPTS",
            "-c:v", "libx264", "-preset", "ultrafast", "-an", "-f", "mp4", str(seg_path)
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return seg_files

# ── Render with xfade transitions ──

def render_with_transitions(seg_files: list[Path], transition: str, out_path: Path, text_png: str = ""):
    tx_cfg = {
        "zoom-crossfade": ("fade", 0.4),
        "shake":          ("fade", 0.25),
        "glitch":         ("pixelize", 0.3),
        "motion-blur":    ("smoothleft", 0.4),
        "crossfade":      ("fade", 0.3),
        "hard-cut":       ("fastfade", 0.05),
    }
    tx_name, tx_dur = tx_cfg.get(transition, ("fade", 0.3))

    # Build concat demuxer list
    concat_list = out_path.parent / "concat.txt"
    with open(concat_list, "w") as f:
        for sf in seg_files:
            dur = float(subprocess.check_output([
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", str(sf)
            ]).decode().strip())
            f.write(f"file '{sf}'\nduration {dur}\n")

    # Build xfade chain with all inputs
    flat_inputs = [item for sf in seg_files for item in ("-i", str(sf))]

    fc_parts = []
    for i, sf in enumerate(seg_files):
        fc_parts.append(f"[{i}:v:0]setsar=1[v{i}];")

    prev_label = "v0"
    actual_dur = float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(seg_files[0])
    ]).decode().strip())
    for i in range(1, len(seg_files)):
        seg_dur = float(subprocess.check_output([
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(seg_files[i])
        ]).decode().strip())
        offset = actual_dur - tx_dur
        xf = f"xfade=transition={tx_name}:duration={tx_dur}:offset={round(offset,3)}"
        fc_parts.append(f"[{prev_label}][v{i}]{xf}[t{i}];")
        prev_label = f"t{i}"
        actual_dur += seg_dur - tx_dur

    filter_complex = "".join(fc_parts) + f"[{prev_label}]format=yuv420p[outv]"
    cmd = ["ffmpeg", "-y"] + flat_inputs + [
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-an", "-t", str(TARGET_DURATION),
        str(out_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 or not out_path.exists() or out_path.stat().st_size < 50000:
        # Fallback: simple concat without transitions
        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
            "-vf", f"scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=decrease,pad={TARGET_W}:{TARGET_H}:(ow-iw)/2:(oh-ih)/2:black",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-an", "-t", str(TARGET_DURATION),
            str(out_path)
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Overlay text PNG
    if text_png and os.path.exists(text_png):
        tmp_out = str(out_path) + ".text.mp4"
        subprocess.run([
            "ffmpeg", "-y", "-i", str(out_path), "-i", text_png,
            "-filter_complex", "[0:v][1:v]overlay=(W-w)/2:(H-h)/2:enable='between(t,0,15)'[outv]",
            "-map", "[outv]", "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-an",
            tmp_out
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.replace(tmp_out, out_path)


def add_music(video_path: Path, music_path: Path, out_path: Path):
    subprocess.run([
        "ffmpeg", "-y", "-i", str(video_path), "-i", str(music_path),
        "-filter_complex", "[0:v]copy[v];[1:a]afade=t=out:st=13:d=2,atrim=start=0:end=15[a]",
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k", "-shortest",
        str(out_path)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# ── Git push ──

def git_push(video_path: Path, meta: dict):
    """Commit and push output.mp4 to VideoForge repo."""
    repo = GIT_REPO
    demo_dir = repo / "demo"
    demo_dir.mkdir(parents=True, exist_ok=True)
    # Copy to demo as output.mp4
    dest = demo_dir / "output.mp4"
    if dest.exists():
        dest.unlink()
    # Use cp instead of os.replace to keep source
    subprocess.run(["cp", str(video_path), str(dest)], check=True)

    # Write metadata JSON
    meta_path = demo_dir / "latest_meta.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    # Git operations
    subprocess.run(["git", "-C", str(repo), "add", str(dest.relative_to(repo)), str(meta_path.relative_to(repo))],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    subprocess.run(["git", "-C", str(repo), "commit", "-m", f"auto-vid: hourly TikTok edit {ts}"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["git", "-C", str(repo), "push", "origin", "main"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"[deploy] pushed {dest.name} to origin/main")

# ── Update shared_memory DB ──

def update_db(task_id: str, status: str, details: str = ""):
    db = Path.home() / ".hermes" / "shared_memory.db"
    if not db.exists():
        print("[warn] shared_memory.db not found")
        return
    import sqlite3
    conn = sqlite3.connect(str(db))
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS task_status (
            task_id TEXT PRIMARY KEY, agent TEXT, status TEXT, details TEXT, updated_at TEXT
        )
    """)
    cur.execute("""
        INSERT INTO task_status (task_id, agent, status, details, updated_at)
        VALUES (?, 'coder', ?, ?, ?)
        ON CONFLICT(task_id) DO UPDATE SET
            status=excluded.status, details=excluded.details, updated_at=excluded.updated_at
    """, (task_id, status, details, datetime.now(timezone.utc).isoformat()))
    conn.commit()
    conn.close()
    print(f"[db] {task_id} → {status}")

# ── Main pipeline ──

def run_pipeline(no_push=False):
    print("="*60)
    print("Auto Video Pipeline — TikTok Football Edit")
    print("="*60)

    # Prerequisites check
    if not MUSICPATH.exists():
        raise FileNotFoundError(f"Music missing: {MUSICPATH}")
    if not FOOTDIR.exists() or not any(FOOTDIR.glob("*.mp4")):
        raise FileNotFoundError(f"Footage missing in {FOOTDIR}")

    # Pick random inputs
    videos = sorted(FOOTDIR.glob("*.mp4"))
    video_path = random.choice(videos)
    theme = random.choice(THEMES)
    tx = random.choice(["zoom-crossfade", "glitch", "motion-blur", "crossfade"])
    print(f"[input] {video_path.name}")
    print(f"[theme] {theme['title']} / {theme['subtitle']} | transition={tx}")

    # Beat detection
    print("[beats] detecting...")
    beat_data = detect_beats(str(MUSICPATH))
    print(f"[beats] tempo={beat_data['tempo']:.1f} BPM, beats={len(beat_data['beats'])}, dur={beat_data['duration']:.1f}s")

    # Work in temp dir
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        # 1) Text overlay PNG
        png_path = tmp / "overlay.png"
        make_text_png(theme, png_path)

        # 2) Segment video at beat times
        print("[cut] segmenting video...")
        seg_files = segment_video(video_path, beat_data, tmp)
        print(f"[cut] {len(seg_files)} segments")

        # 3) Render with transitions
        raw_path = tmp / "raw.mp4"
        print(f"[render] transitions={tx} ...")
        render_with_transitions(seg_files, tx, raw_path, str(png_path))

        # 4) Add music with fade-out
        final_path = tmp / "final.mp4"
        print("[audio] adding music with fade-out...")
        add_music(raw_path, MUSICPATH, final_path)

        # 5) Verify output
        probe_out = subprocess.run([
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height,avg_frame_rate",
            "-show_entries", "format=duration,bit_rate,size",
            "-of", "json", str(final_path)
        ], capture_output=True, text=True)
        probe = json.loads(probe_out.stdout)
        stream = probe.get("streams", [{}])[0]
        fmt = probe.get("format", {})
        meta = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "theme": theme,
            "transition": tx,
            "source_video": video_path.name,
            "music": MUSICPATH.name,
            "output": "demo/output.mp4",
            "properties": {
                "width": stream.get("width"),
                "height": stream.get("height"),
                "duration_sec": round(float(fmt.get("duration", 0)), 2),
                "file_size_bytes": int(fmt.get("size", 0)),
                "bitrate": int(fmt.get("bit_rate", 0)),
            },
        }
        print(f"[verify] {meta['properties']['width']}x{meta['properties']['height']} {meta['properties']['duration_sec']}s {meta['properties']['file_size_bytes']} bytes")

        # 6) Copy to output location
        OUTPATH.parent.mkdir(parents=True, exist_ok=True)
        if Path(final_path).resolve() != OUTPATH.resolve():
            subprocess.run(["cp", str(final_path), str(OUTPATH)], check=True)
        print(f"[saved] {OUTPATH}")

        # 7) Git push
        if not no_push:
            print("[deploy] pushing to GitHub Pages...")
            git_push(OUTPATH, meta)
        else:
            print("[deploy] skipped (no-push)")

    # 8) Update DB
    update_db("auto-vid", "COMPLETED", json.dumps(meta, ensure_ascii=False))
    print("[done] pipeline complete.")
    return meta


def main():
    parser = argparse.ArgumentParser(description="TikTok football edit pipeline")
    parser.add_argument("--video", default="", help="Override input video")
    parser.add_argument("--music", default=str(MUSICPATH), help="Override music file")
    parser.add_argument("--theme", default="", help="Theme title to force")
    parser.add_argument("--transition", default="", help="Transition to force")
    parser.add_argument("--output", default=str(OUTPATH), help="Output path")
    parser.add_argument("--no-push", action="store_true", help="Skip git push")
    args = parser.parse_args()

    if args.video:
        os.environ["_TIKTOK_VIDEO"] = args.video
    if args.music:
        os.environ["_TIKTOK_MUSIC"] = args.music
    if args.theme:
        os.environ["_TIKTOK_THEME"] = args.theme
    if args.transition:
        os.environ["_TIKTOK_TX"] = args.transition
    if args.output:
        os.environ["_TIKTOK_OUTPUT"] = args.output

    meta = run_pipeline(no_push=args.no_push)
    print(json.dumps(meta, indent=2, ensure_ascii=False))



if __name__ == "__main__":
    main()

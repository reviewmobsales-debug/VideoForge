#!/usr/bin/env python3
"""
tiktok_football_edit.py — 24/7 Autonomous TikTok Football Edit Generator
Input : football_footage/*.mp4, tiktok_base.mp3
Output: output.mp4  (1080×1920, 30fps, h264, aac, ~15s, beat-synced, text overlays, AI thumbnail)
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
from typing import Any

try:
    import librosa
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
except ImportError as e:
    print(f"Missing deps: {e}. Install: pip install librosa numpy pillow", file=sys.stderr)
    sys.exit(1)

# ── Paths ──
BASEDIR = Path.home() / "VideoForge"
FOOTDIR = BASEDIR / "football_footage"
OUTPATH = BASEDIR / "demo" / "output.mp4"
THUMBDIR = BASEDIR / "output" / "thumbnails"
MUSICPATH = BASEDIR / "tiktok_base.mp3"
PROMODIR = BASEDIR / "promo"
GIT_REPO = BASEDIR

# ── TikTok Export Spec ──
TARGET_W, TARGET_H = 1080, 1920
TARGET_FPS = 30
TARGET_DURATION = 15.0
TIKTOK_PRESET = {
    "vcodec": "libx264",
    "pix_fmt": "yuv420p",
    "preset": "fast",
    "crf": "23",
    "r": str(TARGET_FPS),
    "acodec": "aac",
    "audio_bitrate": "192k",
    "ac": "2",                 # stereo
    "ar": "48000",
    "movflags": "+faststart",
    "tune": "fastdecode",
    "profile:v": "high",
    "level": "4.2",
}

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

# ── 12 TikTok Transitions ──
TRANSITIONS = {
    "fade":          ("fade", 0.35),
    "wipeleft":      ("wipeleft", 0.40),
    "wiperight":     ("wiperight", 0.40),
    "slideleft":     ("slideleft", 0.40),
    "slideright":    ("slideright", 0.40),
    "circlecrop":    ("circlecrop", 0.45),
    "pixelize":      ("pixelize", 0.35),
    "dissolve":      ("dissolve", 0.40),
    "smoothleft":    ("smoothleft", 0.40),
    "zoomin":        ("zoomin", 0.45),
    "diagtl":        ("diagtl", 0.40),
    "hblur":         ("hblur", 0.40),
}

# ── Helpers ──

def _ffprobe(path: Path, key: str) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", f"format={key}",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True,
    )
    return float(out.stdout.strip())


def _build_ffmpeg_cmd(base: list[str], **overrides: Any) -> list[str]:
    preset = {**TIKTOK_PRESET, **overrides}
    cmd = base + [
        "-c:v", preset["vcodec"],
        "-preset", preset["preset"],
        "-crf", preset["crf"],
        "-pix_fmt", preset["pix_fmt"],
        "-r", preset["r"],
        "-profile:v", preset["profile:v"],
        "-level", preset["level"],
        "-movflags", preset["movflags"],
        "-tune", preset["tune"],
        "-c:a", preset["acodec"],
        "-b:a", preset["audio_bitrate"],
        "-ac", preset["ac"],
        "-ar", preset["ar"],
    ]
    return cmd


# ── Beat detection ──

def detect_beats(audio_path: str):
    y, sr = librosa.load(audio_path, sr=44100, mono=True)
    # librosa 0.11+ returns times directly with units='time'
    tempo_raw, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    tempo = float(tempo_raw[0]) if hasattr(tempo_raw, "__iter__") else float(tempo_raw)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    beats = [{"time": float(t)} for t in beat_times]
    duration = float(len(y) / sr)
    return {"tempo": tempo, "beats": beats, "duration": duration, "sr": sr}


def optimized_beat_segments(beat_data: dict, seg_budget: float, min_gap: float = 1.2, max_segs: int = 7):
    """Return beat times filtered for minimum gap and capped count."""
    raw = sorted({round(b["time"], 2) for b in beat_data["beats"] if 0.3 < b["time"] < seg_budget})
    chosen = []
    last = -999
    for t in raw:
        if t - last >= min_gap:
            chosen.append(t)
            last = t
    if len(chosen) > max_segs:
        step = max(1, len(chosen) // max_segs)
        chosen = chosen[::step][:max_segs]
    return chosen


# ── Text overlay PNG generation ──

def make_text_png(theme: dict, out_png: Path, w=1080, h=300):
    """Generate a transparent PNG with bold TikTok-style text."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    font_paths = [
        "/System/Library/Fonts/Supplemental/Arial Black.ttf",
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
                font_large = ImageFont.truetype(fp, 84)
                font_small = ImageFont.truetype(fp, 48)
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

    tx, ty = w // 2, h // 2 - 25
    for dx in (-3, -2, -1, 0, 1, 2, 3):
        for dy in (-3, -2, -1, 0, 1, 2, 3):
            draw.text((tx+dx, ty+dy), title, font=font_large, fill="#000000", anchor="mm")
    draw.text((tx, ty), title, font=font_large, fill=color1, anchor="mm")

    sx, sy = w // 2, h // 2 + 70
    for dx in (-2, -1, 0, 1, 2):
        for dy in (-2, -1, 0, 1, 2):
            draw.text((sx+dx, sy+dy), subtitle, font=font_small, fill="#000000", anchor="mm")
    draw.text((sx, sy), subtitle, font=font_small, fill=color2, anchor="mm")

    out_png.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_png, "PNG")
    return str(out_png)


# ── AI Thumbnail Generation ──

def generate_thumbnail(video_path: Path, theme: dict, out_path: Path, beat_time: float = 2.0):
    """Extract a frame and composite an AI-style branded thumbnail using PIL."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    raw_frame = out_path.with_suffix(".raw.jpg")
    subprocess.run(
        ["ffmpeg", "-y", "-ss", str(beat_time), "-i", str(video_path),
         "-vframes", "1", "-q:v", "2", "-f", "image2", str(raw_frame)],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    frame = Image.open(raw_frame).convert("RGBA")
    frame = frame.resize((TARGET_W, TARGET_H), Image.LANCZOS)

    # Dark gradient overlay at bottom for text readability
    overlay = Image.new("RGBA", (TARGET_W, TARGET_H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for y in range(TARGET_H - 500, TARGET_H):
        alpha = int(180 * ((y - (TARGET_H - 500)) / 500))
        od.line([(0, y), (TARGET_W, y)], fill=(0, 0, 0, alpha))

    canvas = Image.alpha_composite(frame, overlay)
    d = ImageDraw.Draw(canvas)

    # Load bold font
    font_paths = [
        "/System/Library/Fonts/Supplemental/Arial Black.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
    ]
    title_font = None
    sub_font = None
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                title_font = ImageFont.truetype(fp, 110)
                sub_font = ImageFont.truetype(fp, 56)
                break
            except Exception:
                continue
    if title_font is None:
        title_font = ImageFont.load_default()
        sub_font = ImageFont.load_default()

    title = theme.get("title", "TRENDING")
    subtitle = theme.get("subtitle", "WATCH NOW")
    color1 = theme.get("colors", ["#FFFFFF", "#00FFFF"])[0]
    color2 = theme.get("colors", ["#FFFFFF", "#00FFFF"])[1]

    # Glow/shadow for title
    tx, ty = TARGET_W // 2, TARGET_H - 220
    for radius in range(8, 0, -2):
        for dx in (-radius, 0, radius):
            for dy in (-radius, 0, radius):
                d.text((tx+dx, ty+dy), title, font=title_font, fill=(0,0,0,180), anchor="mm")
    d.text((tx, ty), title, font=title_font, fill=color1, anchor="mm")

    sx, sy = TARGET_W // 2, TARGET_H - 110
    for dx in (-2, 0, 2):
        for dy in (-2, 0, 2):
            d.text((sx+dx, sy+dy), subtitle, font=sub_font, fill=(0,0,0,200), anchor="mm")
    d.text((sx, sy), subtitle, font=sub_font, fill=color2, anchor="mm")

    # Add subtle vignette by darkening edges
    enhancer = ImageEnhance.Brightness(canvas)
    canvas = enhancer.enhance(1.05)

    # Sharpen
    canvas = canvas.filter(ImageFilter.SHARPEN)

    # Save as JPEG for small size
    rgb = canvas.convert("RGB")
    rgb.save(out_path, "JPEG", quality=92, optimize=True)
    if raw_frame.exists():
        raw_frame.unlink()
    return str(out_path)


# ── Video segmentation ──

def segment_video(video_path: Path, beat_data: dict, tmpdir: Path):
    """Cut input video into segments aligned with beats (max segments for 15s output)."""
    src_dur = _ffprobe(video_path, "duration")
    seg_budget = min(src_dur - 0.5, 17.0)
    chosen = optimized_beat_segments(beat_data, seg_budget)
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
        vf = (
            f"scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=decrease,"
            f"pad={TARGET_W}:{TARGET_H}:(ow-iw)/2:(oh-ih)/2:black,"
            f"fps={TARGET_FPS},setpts=PTS-STARTPTS"
        )
        cmd = [
            "ffmpeg", "-y", "-ss", str(start), "-i", str(video_path),
            "-t", str(dur),
            "-vf", vf,
            "-c:v", "libx264", "-preset", "ultrafast", "-an", "-f", "mp4", str(seg_path)
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return seg_files


# ── Render with xfade transitions ──

def render_with_transitions(seg_files: list[Path], transition: str, out_path: Path, text_png: str = ""):
    tx_name, tx_dur = TRANSITIONS.get(transition, TRANSITIONS["fade"])

    # Build xfade chain with all inputs
    flat_inputs = [item for sf in seg_files for item in ("-i", str(sf))]

    fc_parts = []
    for i, _ in enumerate(seg_files):
        fc_parts.append(f"[{i}:v:0]setsar=1[v{i}];")

    prev_label = "v0"
    actual_dur = _ffprobe(seg_files[0], "duration")
    for i in range(1, len(seg_files)):
        seg_dur = _ffprobe(seg_files[i], "duration")
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
        "-pix_fmt", "yuv420p", "-r", str(TARGET_FPS),
        "-an", "-t", str(TARGET_DURATION),
        str(out_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 or not out_path.exists() or out_path.stat().st_size < 50000:
        # Fallback: simple concat without transitions
        concat_list = out_path.parent / "concat.txt"
        with open(concat_list, "w") as f:
            for sf in seg_files:
                dur = _ffprobe(sf, "duration")
                f.write(f"file '{sf}'\nduration {dur}\n")
        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
            "-vf", f"scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=decrease,pad={TARGET_W}:{TARGET_H}:(ow-iw)/2:(oh-ih)/2:black,fps={TARGET_FPS}",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-pix_fmt", "yuv420p", "-an",
            "-t", str(TARGET_DURATION), str(out_path)
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Overlay text PNG
    if text_png and os.path.exists(text_png):
        tmp_out = str(out_path) + ".text.mp4"
        subprocess.run([
            "ffmpeg", "-y", "-i", str(out_path), "-i", text_png,
            "-filter_complex", "[0:v][1:v]overlay=(W-w)/2:(H-h)/2:enable='between(t,0,15)'[outv]",
            "-map", "[outv]", "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-pix_fmt", "yuv420p", "-r", str(TARGET_FPS), "-an",
            tmp_out
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.replace(tmp_out, out_path)


# ── TikTok-optimized music mix ──

def add_music(video_path: Path, music_path: Path, out_path: Path):
    """Add music with TikTok-standard loudness, fade-out, and stereo AAC."""
    subprocess.run([
        "ffmpeg", "-y", "-i", str(video_path), "-i", str(music_path),
        "-filter_complex",
        (
            "[0:v]copy[v];"
            "[1:a]afade=t=out:st=13:d=2,"
            "atrim=start=0:end=15,"
            "loudnorm=I=-14:TP=-2:LRA=11[a]"
        ),
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-r", str(TARGET_FPS),
        "-c:a", "aac", "-b:a", "192k", "-ac", "2", "-ar", "48000",
        "-shortest", "-movflags", "+faststart",
        str(out_path)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# ── TikTok export wrapper ──

def tiktok_export(src_path: Path, dst_path: Path, duration: float = TARGET_DURATION):
    """Re-encode any source into strict TikTok-ready spec."""
    cmd = [
        "ffmpeg", "-y", "-i", str(src_path),
        "-vf", f"scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=decrease,pad={TARGET_W}:{TARGET_H}:(ow-iw)/2:(oh-ih)/2:black,fps={TARGET_FPS}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-r", str(TARGET_FPS),
        "-profile:v", "high", "-level", "4.2",
        "-c:a", "aac", "-b:a", "192k", "-ac", "2", "-ar", "48000",
        "-movflags", "+faststart", "-shortest",
        "-t", str(duration),
        str(dst_path),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# ── AI Agent Academy campaign renderer ──

CAMPAIGN_PHRASES = ("BUILD AI AGENTS", "MAKE MONEY", ".5 CPM", "JOIN NOW")


def _campaign_font(size: int):
    font_paths = [
        "/System/Library/Fonts/Supplemental/Arial Black.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
        "/System/Library/Fonts/ArialHB.ttc",
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _fit_campaign_font(text: str, max_width: int, start_size: int, min_size: int = 44):
    measure = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    for size in range(start_size, min_size - 1, -4):
        font = _campaign_font(size)
        bbox = measure.textbbox((0, 0), text, font=font, stroke_width=8)
        if bbox[2] - bbox[0] <= max_width:
            return font
    return _campaign_font(min_size)


def _hex_rgb(color: str) -> tuple[int, int, int]:
    color = color.lstrip("#")
    return tuple(int(color[i:i+2], 16) for i in (0, 2, 4))


def _snap_campaign_time(beats: list[float], target: float) -> float:
    if not beats:
        return target
    candidates = [beat for beat in beats if target - 0.2 <= beat <= target + 0.75]
    if not candidates:
        return target
    return min(candidates, key=lambda beat: abs(beat - target))


def _campaign_schedule(beats: list[float]) -> list[dict[str, float | str]]:
    targets = [0.55, 3.8, 7.1, 10.55]
    starts: list[float] = []
    for target in targets:
        start = _snap_campaign_time(beats, target)
        if starts and start <= starts[-1] + 1.8:
            start = _snap_campaign_time(beats, starts[-1] + 3.25)
        starts.append(min(start, TARGET_DURATION - 1.0))

    schedule = []
    for index, phrase in enumerate(CAMPAIGN_PHRASES):
        end = starts[index + 1] - 0.12 if index + 1 < len(starts) else TARGET_DURATION
        schedule.append({"text": phrase, "start": starts[index], "end": end})
    return schedule


def _beat_pulse(beats: list[float], t: float, width: float = 0.16) -> float:
    pulse = 0.0
    for beat in beats:
        distance = abs(t - beat)
        if distance <= width:
            pulse = max(pulse, (1.0 - distance / width) ** 2)
    return pulse


def _campaign_background() -> Image.Image:
    yy, xx = np.mgrid[0:TARGET_H, 0:TARGET_W]
    x = xx / TARGET_W
    y = yy / TARGET_H
    magenta = np.exp(-(((x - 0.14) ** 2) / 0.09 + ((y - 0.20) ** 2) / 0.08))
    cyan = np.exp(-(((x - 0.86) ** 2) / 0.10 + ((y - 0.70) ** 2) / 0.10))
    center = np.exp(-(((x - 0.50) ** 2) / 0.30 + ((y - 0.48) ** 2) / 0.18))

    arr = np.zeros((TARGET_H, TARGET_W, 3), dtype=np.float32)
    arr[..., 0] = 5 + 55 * magenta + 12 * center
    arr[..., 1] = 9 + 48 * cyan + 10 * center
    arr[..., 2] = 18 + 72 * cyan + 50 * magenta + 20 * center
    vignette = 1.0 - (np.abs(x - 0.5) * 0.25 + np.abs(y - 0.5) * 0.18)
    arr *= vignette[..., None]
    base = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB").convert("RGBA")

    draw = ImageDraw.Draw(base, "RGBA")
    for y_pos in range(0, TARGET_H, 96):
        draw.line([(0, y_pos), (TARGET_W, y_pos)], fill=(255, 255, 255, 13), width=1)
    for x_pos in range(-TARGET_W, TARGET_W * 2, 120):
        draw.line([(x_pos, 0), (x_pos + TARGET_W // 2, TARGET_H)], fill=(0, 255, 235, 11), width=1)
    return base


def _campaign_scanlines() -> Image.Image:
    overlay = Image.new("RGBA", (TARGET_W, TARGET_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    for y_pos in range(0, TARGET_H, 6):
        draw.line([(0, y_pos), (TARGET_W, y_pos)], fill=(0, 0, 0, 34), width=1)
    return overlay


def _campaign_nodes() -> list[tuple[float, float, float, float, int]]:
    rng = random.Random(42)
    return [
        (
            rng.uniform(80, TARGET_W - 80),
            rng.uniform(260, TARGET_H - 260),
            rng.uniform(10, 56),
            rng.uniform(0, math.tau),
            rng.randint(3, 6),
        )
        for _ in range(34)
    ]


def _draw_campaign_network(draw: ImageDraw.ImageDraw, nodes: list[tuple[float, float, float, float, int]], t: float, pulse: float):
    points = []
    for x, y, drift, phase, radius in nodes:
        px = x + math.sin(t * 0.9 + phase) * drift
        py = y + math.cos(t * 0.7 + phase) * drift * 0.65
        points.append((px, py, radius))

    line_alpha = int(28 + 78 * pulse)
    for i, (x1, y1, _) in enumerate(points):
        for x2, y2, _ in points[i + 1:]:
            distance = math.hypot(x1 - x2, y1 - y2)
            if distance < 235:
                alpha = max(0, int(line_alpha * (1.0 - distance / 235)))
                draw.line([(x1, y1), (x2, y2)], fill=(75, 255, 235, alpha), width=1)

    for px, py, radius in points:
        glow = int(72 + 120 * pulse)
        draw.ellipse((px - radius * 3, py - radius * 3, px + radius * 3, py + radius * 3), fill=(12, 220, 255, 32))
        draw.ellipse((px - radius, py - radius, px + radius, py + radius), fill=(235, 255, 255, glow))


def _draw_glitch_text(
    frame: Image.Image,
    text: str,
    center: tuple[int, int],
    font: ImageFont.ImageFont,
    t: float,
    pulse: float,
):
    layer = Image.new("RGBA", (TARGET_W, TARGET_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer, "RGBA")
    rng = random.Random(int(t * 1000) + sum(ord(ch) for ch in text))
    cx, cy = center
    glitch = pulse > 0.05 or rng.random() < 0.12
    jitter = int(24 * pulse) + (rng.randint(0, 8) if glitch else 0)

    bar_count = 4 + int(10 * pulse)
    for _ in range(bar_count):
        y_pos = cy + rng.randint(-180, 170)
        x_pos = rng.randint(48, 240)
        width = rng.randint(420, 980)
        height = rng.randint(7, 28)
        fill = (0, 255, 235, int(34 + 100 * pulse)) if rng.random() > 0.45 else (255, 43, 214, int(28 + 96 * pulse))
        draw.rectangle((x_pos, y_pos, x_pos + width, y_pos + height), fill=fill)

    offsets = [
        (-jitter - 5, rng.randint(-5, 5), (255, 45, 210, 205)),
        (jitter + 5, rng.randint(-5, 5), (0, 255, 235, 205)),
        (0, 0, (255, 255, 255, 255)),
    ]
    for dx, dy, fill in offsets:
        draw.text(
            (cx + dx, cy + dy),
            text,
            font=font,
            fill=fill,
            anchor="mm",
            stroke_width=8,
            stroke_fill=(0, 0, 0, 225),
        )

    if glitch:
        for _ in range(3 + int(5 * pulse)):
            dy = rng.randint(-110, 110)
            dx = rng.randint(-42, 42)
            alpha = rng.randint(55, 125)
            fill = (255, 255, 255, alpha) if rng.random() > 0.5 else (0, 255, 235, alpha)
            draw.text((cx + dx, cy + dy), text, font=font, fill=fill, anchor="mm", stroke_width=3, stroke_fill=(0, 0, 0, alpha))

    frame.alpha_composite(layer)


def render_ai_agent_academy_campaign(music_path: Path, out_path: Path):
    if not music_path.exists():
        raise FileNotFoundError(f"Music missing: {music_path}")

    print("="*60)
    print("Campaign Video Pipeline — AI Agent Academy")
    print("="*60)
    print("[beats] detecting...")
    beat_data = detect_beats(str(music_path))
    beats = [float(item["time"]) for item in beat_data["beats"] if 0.0 < float(item["time"]) < TARGET_DURATION]
    schedule = _campaign_schedule(beats)
    print(f"[beats] tempo={beat_data['tempo']:.1f} BPM, beats={len(beats)}")
    print("[campaign] " + " | ".join(f"{item['text']}@{item['start']:.2f}s" for item in schedule))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    background = _campaign_background()
    scanlines = _campaign_scanlines()
    nodes = _campaign_nodes()
    fonts = {
        phrase: _fit_campaign_font(phrase, 960, 168 if phrase != ".5 CPM" else 220)
        for phrase in CAMPAIGN_PHRASES
    }
    brand_font = _fit_campaign_font("AI AGENT ACADEMY", 890, 74, 42)
    tag_font = _fit_campaign_font("ON WHOP", 420, 46, 32)
    micro_font = _fit_campaign_font("AUTOMATE. LAUNCH. SCALE.", 780, 38, 28)

    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-pix_fmt", "rgba",
        "-s", f"{TARGET_W}x{TARGET_H}",
        "-r", str(TARGET_FPS),
        "-i", "-",
        "-i", str(music_path),
        "-filter_complex",
        (
            "[1:a]atrim=start=0:end=15,"
            "afade=t=out:st=13:d=2,"
            "loudnorm=I=-14:TP=-2:LRA=11[a]"
        ),
        "-map", "0:v",
        "-map", "[a]",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-r", str(TARGET_FPS),
        "-profile:v", "high",
        "-level", "4.2",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ac", "2",
        "-ar", "48000",
        "-movflags", "+faststart",
        "-t", str(TARGET_DURATION),
        str(out_path),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    assert proc.stdin is not None

    total_frames = int(TARGET_DURATION * TARGET_FPS)
    active: dict[str, float | str] | None
    try:
        for frame_index in range(total_frames):
            t = frame_index / TARGET_FPS
            beat = _beat_pulse(beats, t)
            active = next((item for item in schedule if item["start"] <= t < item["end"]), None)
            switch = 0.0
            if active:
                switch = max(0.0, 1.0 - abs(t - float(active["start"])) / 0.28)
            pulse = max(beat, switch)

            frame = background.copy()
            draw = ImageDraw.Draw(frame, "RGBA")
            if pulse > 0:
                draw.rectangle((0, 0, TARGET_W, TARGET_H), fill=(255, 255, 255, int(34 * pulse)))

            sweep_y = int((t * 240) % (TARGET_H + 280)) - 140
            draw.rectangle((0, sweep_y, TARGET_W, sweep_y + 26), fill=(0, 255, 235, 26))
            draw.rectangle((0, TARGET_H - sweep_y - 46, TARGET_W, TARGET_H - sweep_y - 22), fill=(255, 43, 214, 22))

            _draw_campaign_network(draw, nodes, t, pulse)

            panel_alpha = 138 + int(42 * pulse)
            draw.rounded_rectangle((98, 88, TARGET_W - 98, 260), radius=18, outline=(0, 255, 235, 120), width=2, fill=(0, 0, 0, panel_alpha))
            draw.text((TARGET_W // 2, 148), "AI AGENT ACADEMY", font=brand_font, fill=(255, 255, 255, 255), anchor="mm")
            draw.text((TARGET_W // 2, 214), "ON WHOP", font=tag_font, fill=(0, 255, 235, 235), anchor="mm")

            if active:
                phrase = str(active["text"])
                intro = min(1.0, max(0.0, (t - float(active["start"])) / 0.25))
                outro = min(1.0, max(0.0, (float(active["end"]) - t) / 0.20))
                scale_y = int((1.0 - min(intro, outro)) * 42)
                _draw_glitch_text(frame, phrase, (TARGET_W // 2, 900 + scale_y), fonts[phrase], t, pulse)

            draw.rounded_rectangle((138, TARGET_H - 300, TARGET_W - 138, TARGET_H - 168), radius=14, fill=(0, 0, 0, 158), outline=(255, 43, 214, 105), width=2)
            draw.text((TARGET_W // 2, TARGET_H - 234), "AUTOMATE. LAUNCH. SCALE.", font=micro_font, fill=(255, 255, 255, 224), anchor="mm")

            frame = Image.alpha_composite(frame, scanlines)
            opaque_frame = Image.new("RGBA", (TARGET_W, TARGET_H), (0, 0, 0, 255))
            opaque_frame.alpha_composite(frame)
            proc.stdin.write(opaque_frame.tobytes())

            if frame_index and frame_index % 90 == 0:
                print(f"[render] {frame_index}/{total_frames} frames")
    except BrokenPipeError as exc:
        stderr = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""
        raise RuntimeError(f"ffmpeg stopped while rendering:\n{stderr[-4000:]}") from exc
    finally:
        proc.stdin.close()

    stderr = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""
    returncode = proc.wait()
    if returncode != 0:
        raise RuntimeError(f"ffmpeg failed with exit code {returncode}:\n{stderr[-4000:]}")

    probe_out = subprocess.run([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,avg_frame_rate",
        "-show_entries", "format=duration,bit_rate,size",
        "-of", "json", str(out_path)
    ], capture_output=True, text=True, check=True)
    probe = json.loads(probe_out.stdout)
    stream = probe.get("streams", [{}])[0]
    fmt = probe.get("format", {})
    meta = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "campaign": "AI Agent Academy",
        "platform": "Whop",
        "output": str(out_path.relative_to(BASEDIR)) if out_path.is_relative_to(BASEDIR) else str(out_path),
        "overlays": list(CAMPAIGN_PHRASES),
        "beat_sync_points": [{"text": item["text"], "start": round(float(item["start"]), 2)} for item in schedule],
        "music": music_path.name,
        "properties": {
            "width": stream.get("width"),
            "height": stream.get("height"),
            "fps": stream.get("avg_frame_rate"),
            "duration_sec": round(float(fmt.get("duration", 0)), 2),
            "file_size_bytes": int(fmt.get("size", 0)),
            "bitrate": int(fmt.get("bit_rate", 0)),
        },
    }
    print(f"[saved] {out_path}")
    print(f"[verify] {meta['properties']['width']}x{meta['properties']['height']} {meta['properties']['duration_sec']}s {meta['properties']['file_size_bytes']} bytes")
    update_db("ai-agent-academy-promo", "COMPLETED", json.dumps(meta, ensure_ascii=False))
    return meta


# ── Git push ──

def git_push(video_path: Path, meta: dict, thumb_path: Path | None = None):
    """Commit and push output.mp4 + thumbnail to VideoForge repo."""
    repo = GIT_REPO
    demo_dir = repo / "demo"
    demo_dir.mkdir(parents=True, exist_ok=True)
    dest = demo_dir / "output.mp4"
    if Path(video_path).resolve() != dest.resolve():
        if dest.exists():
            dest.unlink()
        subprocess.run(["cp", str(video_path), str(dest)], check=True)
    else:
        print("[deploy] source and dest are identical, keeping existing file")

    # Copy thumbnail if present
    if thumb_path and thumb_path.exists():
        thumb_dest = demo_dir / "thumbnail.jpg"
        subprocess.run(["cp", str(thumb_path), str(thumb_dest)], check=True)
        print(f"[deploy] thumbnail -> {thumb_dest}")

    meta_path = demo_dir / "latest_meta.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    subprocess.run(["git", "-C", str(repo), "add", str(dest.relative_to(repo)), str(meta_path.relative_to(repo))],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if thumb_path and thumb_path.exists():
        thumb_dest = demo_dir / "thumbnail.jpg"
        subprocess.run(["git", "-C", str(repo), "add", str(thumb_dest.relative_to(repo))],
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

def run_pipeline(no_push=False, campaign_theme: dict | None = None):
    print("="*60)
    print("Auto Video Pipeline — TikTok Football Edit")
    print("="*60)

    if not MUSICPATH.exists():
        raise FileNotFoundError(f"Music missing: {MUSICPATH}")
    if not FOOTDIR.exists() or not any(FOOTDIR.glob("*.mp4")):
        raise FileNotFoundError(f"Footage missing in {FOOTDIR}")

    videos = sorted(FOOTDIR.glob("*.mp4"))
    video_path = random.choice(videos)
    theme = campaign_theme or random.choice(THEMES)
    tx = random.choice(list(TRANSITIONS.keys()))
    print(f"[input] {video_path.name}")
    print(f"[theme] {theme['title']} / {theme['subtitle']} | transition={tx}")

    print("[beats] detecting...")
    beat_data = detect_beats(str(MUSICPATH))
    print(f"[beats] tempo={beat_data['tempo']:.1f} BPM, beats={len(beat_data['beats'])}, dur={beat_data['duration']:.1f}s")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        png_path = tmp / "overlay.png"
        make_text_png(theme, png_path)

        print("[cut] segmenting video...")
        seg_files = segment_video(video_path, beat_data, tmp)
        print(f"[cut] {len(seg_files)} segments")

        raw_path = tmp / "raw.mp4"
        print(f"[render] transitions={tx} ...")
        render_with_transitions(seg_files, tx, raw_path, str(png_path))

        final_path = tmp / "final.mp4"
        print("[audio] adding music with TikTok loudness...")
        add_music(raw_path, MUSICPATH, final_path)

        # Thumbnail
        thumb_path = THUMBDIR / f"thumb_{theme['title'].replace(' ', '_').lower()}.jpg"
        THUMBDIR.mkdir(parents=True, exist_ok=True)
        beat_time = beat_data["beats"][2]["time"] if len(beat_data["beats"]) > 2 else 2.0
        print("[thumb] generating AI thumbnail...")
        generate_thumbnail(final_path, theme, thumb_path, beat_time=beat_time)

        # Verify
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
            "thumbnail": str(thumb_path.relative_to(BASEDIR)),
            "properties": {
                "width": stream.get("width"),
                "height": stream.get("height"),
                "fps": stream.get("avg_frame_rate"),
                "duration_sec": round(float(fmt.get("duration", 0)), 2),
                "file_size_bytes": int(fmt.get("size", 0)),
                "bitrate": int(fmt.get("bit_rate", 0)),
            },
        }
        print(f"[verify] {meta['properties']['width']}x{meta['properties']['height']} {meta['properties']['duration_sec']}s {meta['properties']['file_size_bytes']} bytes")

        OUTPATH.parent.mkdir(parents=True, exist_ok=True)
        if Path(final_path).resolve() != OUTPATH.resolve():
            subprocess.run(["cp", str(final_path), str(OUTPATH)], check=True)
        print(f"[saved] {OUTPATH}")

        public_demo = BASEDIR / "public" / "demo"
        public_demo.mkdir(parents=True, exist_ok=True)
        public_dest = public_demo / "output.mp4"
        subprocess.run(["cp", str(OUTPATH), str(public_dest)], check=True)
        print(f"[saved] {public_dest}")

        if not no_push:
            print("[deploy] pushing to GitHub Pages...")
            git_push(OUTPATH, meta, thumb_path)
        else:
            print("[deploy] skipped (no-push)")

    update_db("auto-vid", "COMPLETED", json.dumps(meta, ensure_ascii=False))
    print("[done] pipeline complete.")
    return meta


def main():
    parser = argparse.ArgumentParser(description="TikTok football edit pipeline")
    parser.add_argument("--campaign", default="", choices=["", "ai-agent-academy"], help="Render a campaign-specific promo")
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

    if args.campaign == "ai-agent-academy":
        output_path = Path(args.output).expanduser()
        if not output_path.is_absolute():
            output_path = BASEDIR / output_path
        music_path = Path(args.music).expanduser()
        if not music_path.is_absolute():
            music_path = BASEDIR / music_path
        meta = render_ai_agent_academy_campaign(music_path, output_path)
    else:
        meta = run_pipeline(no_push=args.no_push)
    print(json.dumps(meta, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

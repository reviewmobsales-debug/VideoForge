#!/usr/bin/env python3
"""VideoForge V2 - Professional Football Edit Generator"""
import subprocess, os, json, random, math, sys
from pathlib import Path

ROOT = Path(__file__).parent
FOOTAGE = ROOT / "footage"
OUT = ROOT / "public/demo"
TMP = ROOT / "tmp_edit"
TMP.mkdir(parents=True, exist_ok=True)

BEAT_JSON = FOOTAGE / "beat_times.json"
VIDEO_CLIPS = sorted([p for p in FOOTAGE.glob("*.mp4") if p.name != "demo.mp4"])

def run(cmd_list, shell=False):
    print(f"CMD: {' '.join(cmd_list)}")
    r = subprocess.run(cmd_list, shell=shell, capture_output=True, text=True)
    if r.returncode != 0 and r.stderr:
        print(f"ERROR: {r.stderr[:500]}")
    return r

def load_beats():
    with open(BEAT_JSON) as f:
        data = json.load(f)
    beats = data["beats"]
    total_clips = len(VIDEO_CLIPS)
    available = min(int(max(beats) / 2.5), total_clips * 4)
    cuts = []
    for i in range(available):
        t = beats[i % len(beats)] + (i // len(beats)) * (60.0 / max(data.get("tempo",140), 80))
        if t + 2.0 < max(beats) + 5:
            cuts.append(t)
    cuts = sorted(set([round(c,3) for c in cuts]))[:min(len(cuts), 28)]
    print(f"Using {len(cuts)} beat-synced cuts")
    return cuts

def get_duration(path):
    r = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",str(path)],
                       capture_output=True, text=True)
    return float(r.stdout.strip())

def make_subclip(src, start, dur, out_path, effect_name="none"):
    filters = []
    target_w, target_h = 1080, 1920
    filters.append(f"scale=-1:{target_h}:flags=lanczos")
    filters.append(f"crop={target_w}:{target_h}:(iw-{target_w})/2:0")
    if effect_name == "zoom_in":
        filters.append(f"crop=900:1600:90:160,scale={target_w}:{target_h}:flags=lanczos")
        filters.append("unsharp=3:3:0.5")
    elif effect_name == "zoom_out":
        filters.append(f"crop=1080:1920:0:0,scale={target_w}:{target_h}:flags=lanczos")
        filters.append("eq=contrast=1.05:saturation=1.1")
    elif effect_name == "shake":
        filters.append("crop=1040:1880:20+random(1)*30:20+random(1)*30,scale=1080:1920:flags=lanczos")
    elif effect_name == "glitch":
        filters.append("colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131")
        filters.append("noise=alls=2:allf=t+u")
    elif effect_name == "flash":
        filters.append("eq=brightness=0.15:contrast=1.2:saturation=1.3")
        filters.append("gblur=sigma=0.5")
    elif effect_name == "motion_blur":
        filters.append("tblend=all_mode=average,format=yuv420p")
        filters.append("gblur=sigma=1.2:steps=2:vertical=1")
    elif effect_name == "zoom_pulse":
        filters.append("zoompan=z='min(pzoom+0.003,1.2)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920")
    elif effect_name == "vignette":
        filters.append("vignette=angle=PI/4")
        filters.append("eq=brightness=0.05:saturation=1.1")
    else:
        filters.append("eq=saturation=1.1:contrast=1.05")
    filters.append("format=yuv420p")
    vf = ",".join(filters)
    cmd = [
        "ffmpeg","-y","-ss",str(start),"-t",str(dur),"-i",str(src),
        "-vf",vf,
        "-c:v","libx264","-preset","fast","-crf","23","-an","-r","30",
        str(out_path)
    ]
    run(cmd)

def get_effect_for_cut(cut_index):
    effects = ["zoom_in", "shake", "glitch", "zoom_out",
               "flash", "motion_blur", "zoom_pulse", "vignette"]
    return effects[cut_index % len(effects)]

def generate_thumbnail(video_path, out_path, title="FOOTBALL EDIT V2"):
    frame_path = TMP / "thumb_frame.png"
    run(["ffmpeg","-y","-i",str(video_path),"-ss","0.05","-vframes","1","-q:v","2",str(frame_path)])
    cmd = [
        "ffmpeg","-y","-i",str(frame_path),"-vf",
        f"gblur=sigma=1.5,eq=brightness=0.05:saturation=1.2,"
        f"drawtext=fontfile=/System/Library/Fonts/Helvetica.ttc:"
        f"text='{title}':fontcolor=white:fontsize=72:"
        f"x=(w-text_w)/2:y=(h/3):shadowcolor=black@0.8:shadowx=4:shadowy=4:borderw=3:bordercolor=black@0.6,"
        f"drawtext=fontfile=/System/Library/Fonts/Helvetica.ttc:"
        f"text='VideoForge V2':fontcolor=#ff3366:fontsize=42:"
        f"x=(w-text_w)/2:y=(h/3)+90:shadowcolor=black@0.7:shadowx=3:shadowy=3,"
        f"drawtext=fontfile=/System/Library/Fonts/Helvetica.ttc:"
        f"text='Beat-Sync':fontcolor=cyan:fontsize=30:"
        f"x=(w-text_w)/2:y=(h/3)+155:shadowcolor=black@0.7:shadowx=2:shadowy=2,"
        "format=yuv420p",
        "-q:v","2", str(out_path)
    ]
    run(cmd)
    print(f"Thumbnail saved: {out_path}")

def main():
    print("=== VideoForge V2 ===")
    print(f"Clips: {VIDEO_CLIPS}")
    beats = load_beats()
    total_duration = get_duration(FOOTAGE / "beat.mp3")
    print(f"Audio duration: {total_duration:.2f}s")
    beat_pairs = []
    clip_idx = 0
    for i in range(len(beats)-1):
        start = beats[i]
        end = beats[i+1]
        dur = end - start
        if dur < 0.3: continue
        if dur > 2.2:
            end = start + 2.2
            dur = 2.2
        clip = VIDEO_CLIPS[clip_idx % len(VIDEO_CLIPS)]
        src_dur = get_duration(clip)
        cycle_offset = (clip_idx // len(VIDEO_CLIPS)) * 1.5
        src_start = random.uniform(0.2, max(0.3, src_dur - dur - 0.5)) + cycle_offset
        if src_start + dur > src_dur:
            src_start = 0
        effect = get_effect_for_cut(i)
        beat_pairs.append((clip, src_start, dur, effect))
        clip_idx += 1
    print(f"Segments to render: {len(beat_pairs)}")
    seg_files = []
    for idx, (clip, s, d, effect) in enumerate(beat_pairs):
        out_seg = TMP / f"seg_{idx:03d}.mp4"
        make_subclip(clip, s, d, out_seg, effect)
        seg_files.append(out_seg)
    valid_segments = [s for s in seg_files if s.exists() and s.stat().st_size > 1000]
    print(f"Valid segments: {len(valid_segments)}/{len(seg_files)}")
    if len(valid_segments) < 2:
        print("ERROR: Not enough segments generated!")
        return
    concat_file = TMP / "concat.txt"
    with open(concat_file, "w") as f:
        for seg in valid_segments:
            f.write(f"file '{seg.resolve()}'\n")
    concat_tmp = TMP / "concat_raw.mp4"
    run([
        "ffmpeg","-y","-f","concat","-safe","0","-i",str(concat_file),
        "-c","copy", str(concat_tmp)
    ])
    vid_dur = get_duration(concat_tmp)
    print(f"Video duration: {vid_dur:.2f}s")
    aud_start = 0
    aud_fade = min(1.5, vid_dur * 0.1)
    fade_out_start = max(vid_dur - aud_fade, 0.1)
    final_video = OUT / "demo.mp4"
    cmd = [
        "ffmpeg","-y","-i",str(concat_tmp),
        "-ss",str(aud_start),"-t",str(vid_dur),"-i",str(FOOTAGE / "beat.mp3"),
        "-filter_complex",
        f"[1:a]afade=t=in:st=0:d={aud_fade},afade=t=out:st={fade_out_start}:d={aud_fade},"
        f"loudnorm=I=-14:TP=-1.5:LRA=11[a]",
        "-map", "0:v:0", "-map", "[a]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-shortest", str(final_video)
    ]
    run(cmd)
    thumb_path = OUT / "thumbnail.jpg"
    generate_thumbnail(final_video, thumb_path, "FOOTBALL EDIT V2")
    with open(OUT / "metadata.json", "w") as f:
        json.dump({
            "version": "V2",
            "duration": vid_dur,
            "segments": len(valid_segments),
            "effects": ["zoom_in", "zoom_out", "shake", "glitch", "flash", "motion_blur", "zoom_pulse", "vignette"],
            "format": "1080x1920",
            "fps": 30,
            "codec": "h264+aac",
            "thumbnail": str(thumb_path.name),
            "generator": "VideoForge V2 with Librosa beat-detection"
        }, f, indent=2)
    print(f"\n=== VideoForge V2 Complete ===")
    print(f"Output: {final_video}")
    print(f"Thumbnail: {thumb_path}")

if __name__ == "__main__":
    main()

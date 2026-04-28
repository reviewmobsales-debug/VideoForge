"use client";

import React, { useRef, useState, useCallback } from "react";
import VideoPlayer from "@/components/video/VideoPlayer";
import CanvasOverlay from "@/components/video/CanvasOverlay";
import Timeline from "@/components/video/Timeline";
import AutoCutPanel from "@/components/video/AutoCutPanel";
import TransitionPanel from "@/components/video/TransitionPanel";
import { Button } from "@/components/ui/button";
import { Upload, Download, Layers } from "lucide-react";
import type { CutPoint, TransitionPreset } from "@/types";
import { useAudioAnalysis } from "@/hooks/useAudioAnalysis";
import { presetToFFmpegFilter } from "@/lib/transitions";

function formatFFmpegCuts(cuts: CutPoint[], preset: TransitionPreset, duration: number): string {
  // Returns a rough multi-filter concat string for server-side export
  const segments: string[] = [];
  let prev = 0;
  for (const c of cuts) {
    segments.push(`[0:v]trim=start=${prev.toFixed(3)}:end=${c.time.toFixed(3)},setpts=PTS-STARTPTS[v${segments.length}];`);
    prev = c.time;
  }
  segments.push(`[0:v]trim=start=${prev.toFixed(3)}:end=${duration.toFixed(3)},setpts=PTS-STARTPTS[v${segments.length}];`);

  let filter = segments.join("");
  for (let i = 0; i < segments.length - 1; i++) {
    const xf = presetToFFmpegFilter(preset, preset.duration, 0); // simplified
    filter += `[v${i}][v${i + 1}]${xf || "xfade=transition=fade:duration=0.3:offset=0"}[t${i}];`;
  }
  return filter;
}

export default function EditorPage() {
  const [src, setSrc] = useState<string>("");
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [cuts, setCuts] = useState<CutPoint[]>([]);
  const [selectedTransition, setSelectedTransition] = useState<TransitionPreset | null>(null);
  const [generating, setGenerating] = useState(false);
  const [audioBuffer, setAudioBuffer] = useState<AudioBuffer | null>(null);
  const analysis = useAudioAnalysis(audioBuffer);
  const [overlays] = useState([
    {
      id: "1",
      type: "text" as const,
      startTime: 0,
      endTime: 5,
      x: 320,
      y: 100,
      content: "VideoForge",
      style: { fontSize: 48, color: "#ffffff" },
    },
  ]);

  const videoPlayerRef = useRef<HTMLDivElement>(null);

  const handleSeek = useCallback(
    (time: number) => {
      setCurrentTime(time);
      const video = videoPlayerRef.current?.querySelector("video") as HTMLVideoElement | null;
      if (video) video.currentTime = time;
    },
    []
  );

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const url = URL.createObjectURL(file);
    setSrc(url);
    setCurrentTime(0);
    setCuts([]);
    setAudioBuffer(null);

    try {
      const arrayBuffer = await file.arrayBuffer();
      const audioCtx = new AudioContext();
      const ab = await audioCtx.decodeAudioData(arrayBuffer);
      setAudioBuffer(ab);
    } catch {
      // Video without audio or decode error: silently proceed
    }
  };

  const onCutsGenerated = useCallback((newCuts: CutPoint[]) => {
    setCuts(newCuts);
  }, []);

  return (
    <div className="flex h-screen flex-col bg-background text-foreground">
      {/* Header */}
      <header className="flex items-center justify-between border-b border-border px-6 py-3">
        <div className="flex items-center gap-2">
          <Layers className="h-5 w-5 text-primary" />
          <h1 className="text-lg font-semibold tracking-tight">VideoForge Editor</h1>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => document.getElementById('upload-input')?.click()}>
            <Upload className="mr-1 inline h-3.5 w-3.5" /> Import
          </Button>
          <Button size="sm">
            <Download className="mr-1 inline h-3.5 w-3.5" /> Export
          </Button>
          <input id="upload-input" type="file" accept="video/*,audio/*" className="hidden" onChange={handleUpload} />
        </div>
      </header>

      {/* Workspace */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left: Canvas / Preview */}
        <div className="flex flex-1 flex-col items-center justify-center bg-muted/30 p-6">
          <div ref={videoPlayerRef} className="relative w-full max-w-3xl rounded-xl shadow-lg">
            {src ? (
              <>
                <VideoPlayer
                  src={src}
                  className="aspect-video w-full"
                  onTimeUpdate={setCurrentTime}
                  onDurationChange={setDuration}
                  onPlayStateChange={setIsPlaying}
                />
                <CanvasOverlay
                  width={1280}
                  height={720}
                  currentTime={currentTime}
                  overlays={overlays}
                  className="z-10"
                />
              </>
            ) : (
              <div className="flex aspect-video w-full max-w-3xl items-center justify-center rounded-xl border-2 border-dashed border-border bg-muted">
                <div className="text-center">
                  <Upload className="mx-auto mb-2 h-10 w-10 text-muted-foreground" />
                  <p className="text-sm text-muted-foreground">Drop a video or click Import</p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right: Properties / Tools */}
        <aside className="w-80 border-l border-border bg-muted/20 p-4 space-y-4 overflow-auto">
          <div className="rounded-md border border-border bg-card p-3 space-y-2">
            <p className="text-xs text-muted-foreground">Playback</p>
            <div className="flex items-center justify-between text-sm">
              <span>Time</span>
              <span className="font-mono">{currentTime.toFixed(2)}s</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span>Duration</span>
              <span className="font-mono">{duration.toFixed(2)}s</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span>Playing</span>
              <span className="font-mono">{isPlaying ? "Yes" : "No"}</span>
            </div>
          </div>

          <AutoCutPanel
            beats={analysis?.beats || []}
            energy={analysis?.energy || []}
            duration={duration}
            onCutsGenerated={onCutsGenerated}
          />

          <TransitionPanel onSelect={setSelectedTransition} />

          {selectedTransition && cuts.length > 0 && (
            <div className="rounded-md border border-border bg-card p-3 space-y-2">
              <p className="text-xs text-muted-foreground">Export Plan</p>
              <div className="space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-foreground">Transition</span>
                  <span className="font-medium text-primary">{selectedTransition.name}</span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-foreground">Clips</span>
                  <span className="font-medium">{cuts.length + 1}</span>
                </div>
              </div>
              <Button size="sm" className="w-full" disabled={generating} onClick={() => {
                setGenerating(true);
                setTimeout(() => setGenerating(false), 800);
              }}>
                {generating ? "Rendering..." : "Quick Render"}
              </Button>
            </div>
          )}
        </aside>
      </div>

      {/* Bottom: Timeline */}
      <div className="border-t border-border bg-background p-4">
        <Timeline
          duration={duration}
          currentTime={currentTime}
          onSeek={handleSeek}
          beats={analysis?.beats || []}
          cuts={cuts}
        />
      </div>
    </div>
  );
}

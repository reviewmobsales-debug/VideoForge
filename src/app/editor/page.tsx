"use client";

import React, { useRef, useState, useCallback } from "react";
import VideoPlayer from "@/components/video/VideoPlayer";
import CanvasOverlay from "@/components/video/CanvasOverlay";
import Timeline from "@/components/video/Timeline";
import { Button } from "@/components/ui/button";
import { Upload, Download, Layers, Settings2 } from "lucide-react";

export default function EditorPage() {
  const [src, setSrc] = useState<string>("");
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
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

  const handleUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const url = URL.createObjectURL(file);
    setSrc(url);
    setCurrentTime(0);
  };

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
          <Button variant="outline" size="sm">
            <Settings2 className="mr-1 inline h-3.5 w-3.5" /> Settings
          </Button>
          <Button size="sm">
            <Download className="mr-1 inline h-3.5 w-3.5" /> Export
          </Button>
          <input id="upload-input" type="file" accept="video/*" className="hidden" onChange={handleUpload} />
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
                ></VideoPlayer>
                <CanvasOverlay
                  width={1280}
                  height={720}
                  currentTime={currentTime}
                  overlays={overlays}
                  className="z-10"
                ></CanvasOverlay>
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

        {/* Right: Properties panel */}
        <aside className="w-72 border-l border-border bg-muted/20 p-4">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-muted-foreground">Properties</h2>
          <div className="space-y-3">
            <div className="rounded-md border border-border bg-card p-3">
              <p className="text-xs text-muted-foreground">Playback</p>
              <div className="mt-1 flex items-center justify-between text-sm">
                <span>Time</span>
                <span className="font-mono">{currentTime.toFixed(2)}s</span>
              </div>
              <div className="mt-1 flex items-center justify-between text-sm">
                <span>Duration</span>
                <span className="font-mono">{duration.toFixed(2)}s</span>
              </div>
              <div className="mt-1 flex items-center justify-between text-sm">
                <span>Playing</span>
                <span className="font-mono">{isPlaying ? "Yes" : "No"}</span>
              </div>
            </div>
          </div>
        </aside>
      </div>

      {/* Bottom: Timeline */}
      <div className="border-t border-border bg-background p-4">
        <Timeline
          duration={duration}
          currentTime={currentTime}
          onSeek={handleSeek}
        ></Timeline>
      </div>
    </div>
  );
}

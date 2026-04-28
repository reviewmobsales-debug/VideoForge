"use client";

import { useRef, useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import { Scissors } from "lucide-react";

interface TimelineProps {
  duration: number;
  currentTime: number;
  onSeek: (time: number) => void;
  className?: string;
  beats?: Array<{ time: number; confidence: number }>;
  cuts?: Array<{ time: number; confidence: number; type: string }>;
}

export default function Timeline({ duration, currentTime, onSeek, className, beats = [], cuts = [] }: TimelineProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  const handlePointerMove = (e: React.PointerEvent) => {
    if (!isDragging || !containerRef.current || duration <= 0) return;
    const rect = containerRef.current.getBoundingClientRect();
    const x = Math.max(0, Math.min(e.clientX - rect.left, rect.width));
    const pct = x / rect.width;
    onSeek(pct * duration);
  };

  useEffect(() => {
    const up = () => setIsDragging(false);
    window.addEventListener("pointerup", up);
    return () => window.removeEventListener("pointerup", up);
  }, []);

  const progress = duration > 0 ? (currentTime / duration) * 100 : 0;

  return (
    <div
      ref={containerRef}
      className={cn(
        "relative h-12 cursor-pointer rounded-md border border-border bg-muted/50 select-none",
        className
      )}
      onPointerDown={(e) => {
        setIsDragging(true);
        handlePointerMove(e);
      }}
      onPointerMove={handlePointerMove}
    >
      {/* Progress fill */}
      <div
        className="absolute inset-y-0 left-0 rounded-l-md bg-primary/20"
        style={{ width: `${progress}%` }}
      ></div>

      {/* Playhead */}
      <div
        className="absolute top-0 bottom-0 w-0.5 bg-primary"
        style={{ left: `${progress}%` }}
      >
        <div className="absolute -top-1 -left-1.5 h-4 w-4 rounded-full bg-primary ring-2 ring-background"></div>
      </div>

      {/* Duration labels */}
      <div className="absolute bottom-0 left-1 text-[10px] text-muted-foreground">0:00</div>
      <div className="absolute bottom-0 right-1 text-[10px] text-muted-foreground">
        {formatDuration(duration)}
      </div>

      {/* Beat markers */}
      {beats.map((b, i) => {
        const left = duration > 0 ? (b.time / duration) * 100 : 0;
        const alpha = 0.3 + b.confidence * 0.7;
        return (
          <div
            key={`beat-${i}`}
            className="absolute top-0 bottom-0 w-0.5 bg-yellow-500/60"
            style={{ left: `${left}%`, opacity: alpha }}
            title={`Beat @ ${b.time.toFixed(2)}s`}
          />
        );
      })}

      {/* Cut markers */}
      {cuts.map((c, i) => {
        const left = duration > 0 ? (c.time / duration) * 100 : 0;
        const color = cutColor(c.type);
        return (
          <div
            key={`cut-${i}`}
            className="absolute top-0 bottom-0 flex flex-col items-center"
            style={{ left: `${left}%` }}
          >
            <div className="h-full w-0.5" style={{ backgroundColor: color }} />
            <div
              className="absolute -top-1 -translate-x-1/2 rotate-45 h-2 w-2 border-r-2 border-b-2"
              style={{ borderColor: color, top: '0.25rem' }}
            />
          </div>
        );
      })}

      {/* Icons for tracks */}
      <div className="absolute top-1 left-2 flex items-center gap-1">
        <Scissors className="h-3 w-3 text-muted-foreground" />
        <span className="text-[10px] text-muted-foreground">Main Track</span>
      </div>
    </div>
  );
}

function cutColor(type: string): string {
  switch (type) {
    case "beat": return "#eab308";
    case "drop": return "#ef4444";
    case "onset": return "#3b82f6";
    case "valley": return "#22c55e";
    case "energy_rise": return "#a855f7";
    default: return "#9ca3af";
  }
}

function formatDuration(seconds: number): string {
  if (!isFinite(seconds) || Number.isNaN(seconds)) return "0:00";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

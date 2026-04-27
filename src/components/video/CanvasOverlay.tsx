"use client";

import { useRef, useEffect } from "react";
import { cn } from "@/lib/utils";

interface CanvasOverlayProps {
  width: number;
  height: number;
  currentTime: number;
  overlays: Array<{
    id: string;
    type: "text" | "image" | "shape";
    startTime: number;
    endTime: number;
    x: number;
    y: number;
    content?: string;
    style?: Record<string, string | number>;
  }>;
  className?: string;
}

export default function CanvasOverlay({
  width,
  height,
  currentTime,
  overlays,
  className,
}: CanvasOverlayProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Set actual canvas resolution to match display size for crisp rendering
    canvas.width = width;
    canvas.height = height;

    ctx.clearRect(0, 0, width, height);

    const activeOverlays = overlays.filter(
      (o) => currentTime >= o.startTime && currentTime <= o.endTime
    );

    for (const overlay of activeOverlays) {
      ctx.save();
      if (overlay.type === "text" && overlay.content) {
        ctx.font = `${overlay.style?.fontSize || 36}px sans-serif`;
        ctx.fillStyle = String(overlay.style?.color || "white");
        ctx.textAlign = "center";
        ctx.shadowColor = "black";
        ctx.shadowBlur = 4;
        ctx.fillText(overlay.content, overlay.x, overlay.y);
      } else if (overlay.type === "shape") {
        ctx.fillStyle = String(overlay.style?.backgroundColor || "rgba(255,0,0,0.5)");
        const w = Number(overlay.style?.width || 100);
        const h = Number(overlay.style?.height || 100);
        ctx.fillRect(overlay.x - w / 2, overlay.y - h / 2, w, h);
      }
      ctx.restore();
    }
  }, [currentTime, overlays, width, height]);

  return (
    <canvas
      ref={canvasRef}
      width={width}
      height={height}
      className={cn("pointer-events-none absolute inset-0 h-full w-full", className)}
      style={{ objectFit: "contain" }}
    ></canvas>
  );
}

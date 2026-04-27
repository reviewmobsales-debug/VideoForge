"use client";

import { useRef, useState, useCallback, useEffect } from "react";
import { cn } from "@/lib/utils";
import { Play, Pause, Volume2, VolumeX, Maximize, SkipBack, SkipForward } from "lucide-react";

interface VideoPlayerProps {
  src?: string;
  overlayCanvasRef?: React.RefObject<HTMLCanvasElement | null>;
  className?: string;
  onTimeUpdate?: (time: number) => void;
  onDurationChange?: (duration: number) => void;
  onPlayStateChange?: (playing: boolean) => void;
}

export default function VideoPlayer({
  src,
  overlayCanvasRef,
  className,
  onTimeUpdate,
  onDurationChange,
  onPlayStateChange,
}: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [showControls, setShowControls] = useState(true);
  const controlsTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  const hideControls = useCallback(() => {
    if (controlsTimeout.current) clearTimeout(controlsTimeout.current);
    controlsTimeout.current = setTimeout(() => setShowControls(false), 3000);
  }, []);

  const togglePlay = useCallback(() => {
    const video = videoRef.current;
    if (!video) return;
    if (video.paused) {
      video.play();
    } else {
      video.pause();
    }
  }, []);

  const toggleMute = useCallback(() => {
    const video = videoRef.current;
    if (!video) return;
    video.muted = !video.muted;
    setIsMuted(video.muted);
  }, []);

  const handleVolumeChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const video = videoRef.current;
    if (!video) return;
    const val = parseFloat(e.target.value);
    video.volume = val;
    setVolume(val);
    setIsMuted(val === 0);
  }, []);

  const handleSeek = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const video = videoRef.current;
    if (!video) return;
    const val = parseFloat(e.target.value);
    video.currentTime = val;
    setCurrentTime(val);
  }, []);

  const skip = useCallback((seconds: number) => {
    const video = videoRef.current;
    if (!video) return;
    video.currentTime = Math.min(Math.max(video.currentTime + seconds, 0), duration);
  }, [duration]);

  const fullscreen = useCallback(() => {
    const container = containerRef.current;
    if (!container) return;
    if (document.fullscreenElement) {
      document.exitFullscreen();
    } else {
      container.requestFullscreen();
    }
  }, []);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const onPlay = () => {
      setIsPlaying(true);
      onPlayStateChange?.(true);
    };
    const onPause = () => {
      setIsPlaying(false);
      onPlayStateChange?.(false);
    };
    const onTime = () => {
      setCurrentTime(video.currentTime);
      onTimeUpdate?.(video.currentTime);
    };
    const onDuration = () => {
      setDuration(video.duration);
      onDurationChange?.(video.duration);
    };
    const onEnded = () => {
      setIsPlaying(false);
      onPlayStateChange?.(false);
    };

    video.addEventListener("play", onPlay);
    video.addEventListener("pause", onPause);
    video.addEventListener("timeupdate", onTime);
    video.addEventListener("durationchange", onDuration);
    video.addEventListener("ended", onEnded);

    return () => {
      video.removeEventListener("play", onPlay);
      video.removeEventListener("pause", onPause);
      video.removeEventListener("timeupdate", onTime);
      video.removeEventListener("durationchange", onDuration);
      video.removeEventListener("ended", onEnded);
    };
  }, [onPlayStateChange, onTimeUpdate, onDurationChange]);

  return (
    <div
      ref={containerRef}
      className={cn(
        "group relative flex items-center justify-center overflow-hidden rounded-xl bg-black",
        className
      )}
      onMouseMove={() => {
        setShowControls(true);
        hideControls();
      }}
      onMouseLeave={() => hideControls()}
    >
      <video
        ref={videoRef}
        src={src}
        className="h-full w-full object-contain"
        onClick={togglePlay}
        playsInline
        preload="metadata"
      />

      {/* Canvas overlay */}
      {overlayCanvasRef && (
        <canvas
          ref={overlayCanvasRef}
          className="pointer-events-none absolute inset-0 h-full w-full"
        />
      )}

      {/* Play overlay when paused */}
      {!isPlaying && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/20" onClick={togglePlay}>
          <button className="rounded-full bg-white/20 p-4 backdrop-blur-sm transition hover:bg-white/30">
            <Play className="h-10 w-10 text-white" fill="white" />
          </button>
        </div>
      )}

      {/* Controls */}
      <div
        className={cn(
          "absolute bottom-0 left-0 right-0 bg-black/60 px-4 py-2 transition-opacity duration-300",
          showControls ? "opacity-100" : "opacity-0"
        )}
      >
        {/* Progress bar */}
        <input
          type="range"
          min={0}
          max={duration || 0}
          step={0.01}
          value={currentTime}
          onChange={handleSeek}
          className="mb-2 h-1 w-full appearance-none rounded bg-white/30 accent-white hover:accent-white"
        />

        <div className="flex items-center justify-between text-white">
          <div className="flex items-center gap-2">
            <button onClick={() => skip(-5)} className="rounded p-1 hover:bg-white/10">
              <SkipBack className="h-4 w-4" />
            </button>
            <button onClick={togglePlay} className="rounded p-1 hover:bg-white/10">
              {isPlaying ? <Pause className="h-5 w-5" /> : <Play className="h-5 w-5" />}
            </button>
            <button onClick={() => skip(5)} className="rounded p-1 hover:bg-white/10">
              <SkipForward className="h-4 w-4" />
            </button>
            <button onClick={toggleMute} className="rounded p-1 hover:bg-white/10">
              {isMuted || volume === 0 ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
            </button>
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={isMuted ? 0 : volume}
              onChange={handleVolumeChange}
              className="w-20 accent-white"
            />
            <span className="ml-2 text-xs text-white/80">
              {formatTime(currentTime)} / {formatTime(duration)}
            </span>
          </div>
          <button onClick={fullscreen} className="rounded p-1 hover:bg-white/10">
            <Maximize className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

function formatTime(seconds: number): string {
  if (!isFinite(seconds) || Number.isNaN(seconds)) return "0:00";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

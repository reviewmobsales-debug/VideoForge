// VideoForge shared types

export type AspectRatio = "9:16" | "16:9" | "1:1" | "4:5";

export type VideoFormat = "mp4" | "webm" | "mov";

export type Platform = "tiktok" | "youtube" | "instagram" | "twitter";

export interface VideoClip {
  id: string;
  src: string;
  duration: number;
  startTime: number;
  endTime: number;
  volume: number;
}

export interface Track {
  id: string;
  name: string;
  clips: VideoClip[];
  visible: boolean;
  locked: boolean;
}

export interface Overlay {
  id: string;
  type: "text" | "image" | "shape" | "filter";
  startTime: number;
  endTime: number;
  x: number;
  y: number;
  width: number;
  height: number;
  content?: string;
  style?: Record<string, string | number>;
}

export interface ProjectData {
  id: string;
  name: string;
  width: number;
  height: number;
  fps: number;
  aspectRatio: AspectRatio;
  tracks: Track[];
  overlays: Overlay[];
  createdAt: string;
  updatedAt: string;
}

export interface Template {
  id: string;
  name: string;
  description: string;
  thumbnail: string;
  category: "tiktok" | "brainrot" | "youtube" | "general";
  tags: string[];
  duration: number;
  aspectRatio: AspectRatio;
  overlays: Overlay[];
  createdAt: string;
}

export interface BeatMarker {
  time: number;
  confidence: number;
}

export interface AudioAnalysisResult {
  bpm: number;
  beats: BeatMarker[];
  energy: number[];
  waveform: number[];
  duration: number;
}

export type AutoCutMode = "smart_montage" | "bass_drop_only" | "every_beat" | "energy_gates";

export interface CutPoint {
  time: number;
  confidence: number;
  type: "beat" | "drop" | "onset" | "valley" | "energy_rise";
}

export interface TransitionPreset {
  id: string;
  name: string;
  css: string; // raw CSS transform/filter for preview
  duration: number; // seconds
  description: string;
}

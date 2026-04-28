"use client";

import { useState, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import type { AutoCutMode, CutPoint, BeatMarker } from "@/types";
import { Scissors, Wand2, Zap, Layers, Activity } from "lucide-react";
import { generateAutoCuts } from "@/lib/autoCut";

interface AutoCutPanelProps {
  beats: BeatMarker[];
  energy: number[];
  duration: number;
  sampleRate?: number;
  hopSize?: number;
  onCutsGenerated?: (cuts: CutPoint[]) => void;
}

const MODE_LABELS: Record<AutoCutMode, { label: string; icon: React.ReactNode; desc: string }> = {
  smart_montage: { label: "Smart Montage", icon: <Wand2 className="h-4 w-4" />, desc: "Adaptive multi-strategy cuts" },
  bass_drop_only: { label: "Bass Drop", icon: <Zap className="h-4 w-4" />, desc: "Only hardest drops" },
  every_beat: { label: "Every Beat", icon: <Layers className="h-4 w-4" />, desc: "Cut on every detected beat" },
  energy_gates: { label: "Energy Gates", icon: <Activity className="h-4 w-4" />, desc: "Split by silence/loudness" },
};

export default function AutoCutPanel({ beats, energy, duration, sampleRate = 44100, hopSize = 512, onCutsGenerated }: AutoCutPanelProps) {
  const [mode, setMode] = useState<AutoCutMode>("smart_montage");
  const [cuts, setCuts] = useState<CutPoint[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);

  const generate = useCallback(() => {
    setIsGenerating(true);
    // Yield to event loop so UI updates
    setTimeout(() => {
      const result = generateAutoCuts(beats, energy, duration, mode, sampleRate, hopSize);
      setCuts(result);
      onCutsGenerated?.(result);
      setIsGenerating(false);
    }, 10);
  }, [beats, energy, duration, mode, sampleRate, hopSize, onCutsGenerated]);

  const totalClips = cuts.length + 1;

  return (
    <Card className="border border-border bg-card p-4 space-y-4">
      <div className="flex items-center gap-2">
        <Scissors className="h-4 w-4 text-primary" />
        <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Auto-Cut</h3>
      </div>

      <div className="space-y-1.5">
        {(Object.keys(MODE_LABELS) as AutoCutMode[]).map((m) => (
          <button
            key={m}
            onClick={() => setMode(m)}
            className={`w-full flex items-center gap-2 rounded-md px-2.5 py-2 text-sm transition ${
              mode === m ? "bg-primary/10 text-primary ring-1 ring-primary/30" : "hover:bg-muted text-foreground"
            }`}
          >
            {MODE_LABELS[m].icon}
            <div className="flex flex-col items-start leading-none">
              <span className="font-medium">{MODE_LABELS[m].label}</span>
              <span className="text-[10px] text-muted-foreground mt-0.5">{MODE_LABELS[m].desc}</span>
            </div>
          </button>
        ))}
      </div>

      <Button
        onClick={generate}
        disabled={isGenerating || beats.length === 0 || duration <= 0}
        size="sm"
        className="w-full"
      >
        {isGenerating ? "Analyzing..." : "Generate Cuts"}
      </Button>

      {cuts.length > 0 && (
        <div className="rounded-md border border-border bg-muted/30 p-2.5 space-y-1">
          <div className="flex items-center justify-between text-xs">
            <span className="text-muted-foreground">Cuts</span>
            <span className="font-semibold text-foreground">{cuts.length}</span>
          </div>
          <div className="flex items-center justify-between text-xs">
            <span className="text-muted-foreground">Clips</span>
            <span className="font-semibold text-foreground">{totalClips}</span>
          </div>
          <div className="flex items-center justify-between text-xs">
            <span className="text-muted-foreground">Avg clip</span>
            <span className="font-semibold text-foreground">
              {duration > 0 && totalClips > 0 ? (duration / totalClips).toFixed(2) : "0.00"}s
            </span>
          </div>
          <div className="max-h-24 overflow-auto space-y-0.5 mt-1">
            {cuts.map((c, i) => (
              <div key={`${c.time}-${i}`} className="flex items-center justify-between text-[10px] rounded px-1 py-0.5 bg-muted/50">
                <span className={`rounded px-1 py-0 inline-block leading-tight ${typeBadge(c.type)}`}>{c.type}</span>
                <span className="font-mono text-muted-foreground">{c.time.toFixed(2)}s</span>
                <span className="text-muted-foreground">{(c.confidence * 100).toFixed(0)}%</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}

function typeBadge(type: CutPoint["type"]): string {
  switch (type) {
    case "beat": return "text-yellow-700 bg-yellow-100";
    case "drop": return "text-red-700 bg-red-100";
    case "onset": return "text-blue-700 bg-blue-100";
    case "valley": return "text-green-700 bg-green-100";
    case "energy_rise": return "text-purple-700 bg-purple-100";
    default: return "text-gray-700 bg-gray-100";
  }
}

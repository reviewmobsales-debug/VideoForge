"use client";

import { useState, useCallback } from "react";
import { transitionPresets, getPresetById } from "@/lib/transitions";
import type { TransitionPreset } from "@/types";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Shuffle, Layers } from "lucide-react";

interface TransitionPanelProps {
  onSelect?: (preset: TransitionPreset) => void;
}

export default function TransitionPanel({ onSelect }: TransitionPanelProps) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [activeDemo, setActiveDemo] = useState<string | null>(null);

  const handleSelect = useCallback(
    (id: string) => {
      setSelectedId(id);
      const preset = getPresetById(id);
      if (preset) onSelect?.(preset);
    },
    [onSelect]
  );

  const triggerDemo = (id: string) => {
    setActiveDemo(null);
    setTimeout(() => setActiveDemo(id), 10);
    setTimeout(() => setActiveDemo((cur) => (cur === id ? null : cur)), 900);
  };

  return (
    <Card className="border border-border bg-card p-4 space-y-3">
      <div className="flex items-center gap-2">
        <Shuffle className="h-4 w-4 text-primary" />
        <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
          Transitions
        </h3>
      </div>

      <div className="grid grid-cols-2 gap-2 max-h-72 overflow-y-auto pr-1">
        {transitionPresets.map((preset) => (
          <button
            key={preset.id}
            onClick={() => handleSelect(preset.id)}
            className={`flex flex-col items-start rounded-md border px-2.5 py-2 text-left transition ${
              selectedId === preset.id
                ? "border-primary/50 bg-primary/10 ring-1 ring-primary/30"
                : "border-border bg-muted/30 hover:bg-muted/60"
            }`}
          >
            <span className="text-xs font-medium text-foreground">{preset.name}</span>
            <span className="text-[10px] text-muted-foreground mt-0.5 leading-tight">
              {preset.description}
            </span>
            <span className="text-[10px] text-muted-foreground mt-0.5">
              {preset.duration > 0 ? `${preset.duration}s` : "instant"}
            </span>

            {/* Mini CSS preview card */}
            <div className="mt-2 w-full flex justify-center">
              <MiniTransitionCard preset={preset} active={activeDemo === preset.id} />
            </div>
          </button>
        ))}
      </div>

      {selectedId && (
        <Button
          size="sm"
          variant="secondary"
          className="w-full"
          onClick={() => {
            if (selectedId) triggerDemo(selectedId);
          }}
        >
          <Layers className="mr-1 h-3.5 w-3.5" /> Preview
        </Button>
      )}
    </Card>
  );
}

function MiniTransitionCard({
  preset,
  active,
}: {
  preset: TransitionPreset;
  active: boolean;
}) {
  // Build a keyframe animation from the preset CSS and run it when active
  const css = buildKeyframes(preset.id, preset.css);
  return (
    <div
      className="relative h-10 w-16 overflow-hidden rounded border border-border bg-black"
      style={active ? { animation: `${preset.id} ${preset.duration || 0.3}s ease-in-out` } : {}}
    >
      <style>{css}</style>
      {/* Simulate a "video thumbnail" inside */}
      <div
        className="absolute inset-0 flex items-center justify-center rounded bg-gradient-to-br from-zinc-800 to-zinc-600 text-[8px] text-white/60"
        style={
          active
            ? { animation: `${preset.id} ${preset.duration || 0.3}s ease-in-out` }
            : undefined
        }
      >
        A
      </div>
      <div
        className="absolute inset-0 flex items-center justify-center rounded bg-gradient-to-br from-zinc-600 to-zinc-400 text-[8px] text-white/60"
        style={
          active
            ? {
                animation: `${preset.id}B ${preset.duration || 0.3}s ease-in-out`,
                animationDelay: `${(preset.duration || 0.3) * 0.5}s`,
                opacity: 0,
              }
            : { opacity: 0 }
        }
      >
        B
      </div>
    </div>
  );
}

function buildKeyframes(id: string, css: string): string {
  return `
    @keyframes ${id} { ${css} }
    @keyframes ${id}B { 
      0% { opacity: 0; }
      50% { opacity: 1; }
      100% { opacity: 0; }
    }
  `;
}

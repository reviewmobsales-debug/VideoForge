import type { TransitionPreset } from "@/types";

/**
 * Transition presets library for VideoForge.
 * Each preset defines a CSS transform/filter keyframe for runtime preview.
 * Final FFmpeg rendering maps these to filter_complex expressions.
 */

export const transitionPresets: TransitionPreset[] = [
  {
    id: "hard-cut",
    name: "Hard Cut",
    css: `from { opacity: 1; transform: none; } to { opacity: 0; transform: none; }`,
    duration: 0.0,
    description: "Instant switch, no transition blend.",
  },
  {
    id: "crossfade",
    name: "Crossfade",
    css: `from { opacity: 1; } to { opacity: 0; }`,
    duration: 0.3,
    description: "Soft opacity crossfade between clips.",
  },
  {
    id: "fade-to-black",
    name: "Fade to Black",
    css: `0% { opacity: 1; } 50% { opacity: 0; } 100% { opacity: 1; }`,
    duration: 0.5,
    description: "Dip to black, classic cinematic punctuation.",
  },
  {
    id: "cross-zoom",
    name: "Cross Zoom",
    css: `from { opacity: 1; transform: scale(1) rotate(0deg); } 50% { opacity: 0; transform: scale(2) rotate(3deg); } to { opacity: 1; transform: scale(1); }`,
    duration: 0.5,
    description: "Zoom + rotate burst synced to beat drops.",
  },
  {
    id: "whirl-spin",
    name: "Whirl Spin",
    css: `from { opacity: 1; transform: scale(1) rotate(0deg); filter: blur(0px); } 50% { opacity: 0; transform: scale(0.2) rotate(180deg); filter: blur(4px); } to { opacity: 1; transform: scale(1) rotate(360deg); filter: blur(0px); }`,
    duration: 0.6,
    description: "Fast spin out and in with motion blur.",
  },
  {
    id: "glitch-rgb",
    name: "Glitch RGB Split",
    css: `0% { filter: none; transform: translateX(0); } 20% { filter: hue-rotate(90deg); transform: translateX(-12px); } 40% { filter: hue-rotate(180deg); transform: translateX(12px); } 60% { filter: hue-rotate(270deg); transform: translateX(-6px); } 80% { filter: hue-rotate(360deg); transform: translateX(6px); } 100% { filter: none; transform: translateX(0); }`,
    duration: 0.4,
    description: "Rapid hue-shift and channel offset glitch.",
  },
  {
    id: "slide-left",
    name: "Slide Left",
    css: `from { opacity: 1; transform: translateX(0); } 50% { opacity: 0; transform: translateX(-100%); } to { opacity: 1; transform: translateX(0); }`,
    duration: 0.35,
    description: "Clip slides off screen left and re-enters.",
  },
  {
    id: "slide-up",
    name: "Slide Up",
    css: `from { opacity: 1; transform: translateY(0); } 50% { opacity: 0; transform: translateY(-100%); } to { opacity: 1; transform: translateY(0); }`,
    duration: 0.35,
    description: "Vertical wipe upward transition.",
  },
  {
    id: "page-curl",
    name: "Page Curl",
    css: `0% { transform: perspective(800px) rotateY(0deg); } 50% { transform: perspective(800px) rotateY(-90deg); opacity: 0; } 100% { transform: perspective(800px) rotateY(0deg); opacity: 1; }`,
    duration: 0.6,
    description: "3D page-turn curl effect.",
  },
  {
    id: "shake-impact",
    name: "Shake Impact",
    css: `0% { transform: translate(0,0); } 12% { transform: translate(-6px,-4px); } 25% { transform: translate(6px,4px); } 37% { transform: translate(-4px,6px); } 50% { transform: translate(4px,-6px); } 62% { transform: translate(-6px,2px); } 75% { transform: translate(6px,-2px); } 87% { transform: translate(-2px,6px); } 100% { transform: translate(0,0); }`,
    duration: 0.3,
    description: "Camera shake on impact, great for bass drops.",
  },
  {
    id: "blur-whip",
    name: "Blur Whip",
    css: `0% { filter: blur(0px) brightness(1); transform: translateX(0); } 50% { filter: blur(12px) brightness(1.3); transform: translateX(40px) scale(1.05); } 100% { filter: blur(0px) brightness(1); transform: translateX(0) scale(1); }`,
    duration: 0.4,
    description: "Flash transition with directional motion blur.",
  },
  {
    id: "vhs-rewind",
    name: "VHS Rewind",
    css: `0% { filter: none; transform: scale(1); letter-spacing: normal; } 30% { filter: contrast(1.5) brightness(0.8) saturate(1.4); transform: scale(1.05) skewX(-5deg); } 70% { filter: contrast(2) brightness(0.6) saturate(1.8); transform: scale(0.92) skewX(5deg); } 100% { filter: none; transform: scale(1); }`,
    duration: 0.5,
    description: "Retro VHS distortion with saturation bloom.",
  },
];

export const defaultTransition = transitionPresets[0];

export function getPresetById(id: string): TransitionPreset | undefined {
  return transitionPresets.find((p) => p.id === id);
}

/**
 * Map transition preset to an approximate FFmpeg filter_complex expression.
 * This is used server-side export pipeline.
 */
export function presetToFFmpegFilter(
  preset: TransitionPreset,
  duration: number,
  offset: number
): string {
  // Simplified mappings for server-side rendering
  switch (preset.id) {
    case "hard-cut":
      return "";
    case "crossfade":
      return `xfade=transition=fade:duration=${duration}:offset=${offset}`;
    case "fade-to-black":
      return `xfade=transition=fadeblack:duration=${duration}:offset=${offset}`;
    case "cross-zoom":
      return `xfade=transition=zoomin:duration=${duration}:offset=${offset}`;
    case "slide-left":
      return `xfade=transition=slideleft:duration=${duration}:offset=${offset}`;
    case "slide-up":
      return `xfade=transition=slideup:duration=${duration}:offset=${offset}`;
    case "whirl-spin":
      return `xfade=transition=zoomin:duration=${duration}:offset=${offset},rotate=angle=t*PI`;
    case "glitch-rgb":
      return `xfade=transition=pixelize:duration=${duration}:offset=${offset}`;
    case "blur-whip":
      return `xfade=transition=fade:duration=${duration}:offset=${offset},boxblur=5:1:enable='between(t,${offset},${offset + duration})'`;
    case "shake-impact":
      return `xfade=transition=fade:duration=${duration}:offset=${offset}`;
    case "page-curl":
      return `xfade=transition=fade:duration=${duration}:offset=${offset}`;
    case "vhs-rewind":
      return `xfade=transition=fade:duration=${duration}:offset=${offset},eq=contrast=1.5:brightness=0.5`;
    default:
      return `xfade=transition=fade:duration=${duration}:offset=${offset}`;
  }
}

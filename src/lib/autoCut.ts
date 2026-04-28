import type { BeatMarker, AutoCutMode, CutPoint } from "@/types";

/**
 * Smart auto-cut engine.
 * Generates CutPoint[] from beat/energy analysis with configurable strategies.
 */

const MIN_CLIP_SECONDS = 0.4;
const MAX_CLIP_SECONDS = 4.0;

export function generateAutoCuts(
  beats: BeatMarker[],
  energy: number[],
  duration: number,
  mode: AutoCutMode = "smart_montage",
  sampleRate?: number,
  hopSize?: number
): CutPoint[] {
  if (!duration || duration <= 0) return [];
  if (!energy.length) {
    // Fallback: use beats only
    const cuts: CutPoint[] = [];
    let lastCut = 0;
    for (const beat of beats) {
      if (beat.time > lastCut + MIN_CLIP_SECONDS) {
        cuts.push({ time: beat.time, confidence: beat.confidence, type: "beat" });
        lastCut = beat.time;
      }
    }
    return cuts;
  }

  // Infer hopSize from energy.length + duration if not provided
  const inferredHopSize = hopSize ?? (Math.floor((duration * 44100) / energy.length) || 512);
  const inferredSampleRate = sampleRate ?? 44100;

  const cuts: CutPoint[] = [];
  let lastCut = 0;

  const normalizedEnergy = normalize(energy);
  const energyTimes = normalizedEnergy.map((_, i) => (i * inferredHopSize) / inferredSampleRate);

  switch (mode) {
    case "bass_drop_only": {
      for (const beat of beats) {
        if (beat.confidence < 0.4) continue;
        const idx = timeToEnergyIndex(beat.time, inferredSampleRate, inferredHopSize);
        const localMax = localMaxAround(normalizedEnergy, idx, 15);
        if (normalizedEnergy[idx] >= localMax * 0.9 && beat.time > lastCut + MIN_CLIP_SECONDS) {
          cuts.push({ time: beat.time, confidence: beat.confidence, type: "drop" });
          lastCut = beat.time;
        }
      }
      break;
    }

    case "every_beat": {
      for (const beat of beats) {
        if (beat.time > lastCut + MIN_CLIP_SECONDS) {
          cuts.push({ time: beat.time, confidence: beat.confidence, type: "beat" });
          lastCut = beat.time;
        }
      }
      break;
    }

    case "energy_gates": {
      // Scan for segments where energy crosses a threshold
      let inGate = false;
      const ENERGY_THRESHOLD = 0.35;
      for (let i = 0; i < normalizedEnergy.length; i++) {
        const t = energyTimes[i];
        if (t > duration - MIN_CLIP_SECONDS) break;
        const val = normalizedEnergy[i];

        if (!inGate && val > ENERGY_THRESHOLD && t > lastCut + MIN_CLIP_SECONDS) {
          cuts.push({ time: t, confidence: val, type: "energy_rise" });
          inGate = true;
          lastCut = t;
        } else if (inGate && val < ENERGY_THRESHOLD * 0.5) {
          inGate = false;
        }
      }
      break;
    }

    case "smart_montage": {
      // Adaptive: prefers high-confidence beats, falls back to energy-gating
      const allCandidates: Array<{ time: number; confidence: number; type: CutPoint["type"] }> = [];

      // Add beats weighted by energy
      for (const beat of beats) {
        const idx = timeToEnergyIndex(beat.time, inferredSampleRate, inferredHopSize);
        const weight = beat.confidence * (normalizedEnergy[idx] || 0.5);
        allCandidates.push({ time: beat.time, confidence: weight, type: "beat" });
      }

      // Add energy valleys as secondary cuts
      for (let i = 1; i < normalizedEnergy.length - 1; i++) {
        if (
          normalizedEnergy[i - 1] > normalizedEnergy[i] &&
          normalizedEnergy[i + 1] > normalizedEnergy[i] &&
          normalizedEnergy[i] < 0.3
        ) {
          const t = energyTimes[i];
          allCandidates.push({ time: t, confidence: 1 - normalizedEnergy[i], type: "valley" });
        }
      }

      // Add sudden onsets
      for (let i = 1; i < normalizedEnergy.length; i++) {
        const diff = normalizedEnergy[i] - normalizedEnergy[i - 1];
        if (diff > 0.25) {
          allCandidates.push({ time: energyTimes[i], confidence: diff, type: "onset" });
        }
      }

      // Sort by time and greedily pick spaced cuts
      allCandidates.sort((a, b) => a.time - b.time);
      let previousCut = 0;
      let dynamicMin = MIN_CLIP_SECONDS;

      for (const cand of allCandidates) {
        const maxDistFromLast = cand.time - previousCut;
        if (cand.time > previousCut + dynamicMin) {
          cuts.push({ time: cand.time, confidence: cand.confidence, type: cand.type });
          previousCut = cand.time;
          // Adaptive minimum: tighten spacing for faster sections (high energy)
          const idx = Math.floor(
            Math.min(normalizedEnergy.length - 1, Math.max(0, timeToEnergyIndex(cand.time, inferredSampleRate, inferredHopSize)))
          );
          const en = normalizedEnergy[idx] || 0.5;
          dynamicMin = MIN_CLIP_SECONDS + (1 - en) * 0.6;
        }
      }

      // Ensure gap-filling: if final segment is too long, add an energy-based cut
      if (duration - previousCut > MAX_CLIP_SECONDS) {
        const searchStartIdx = timeToEnergyIndex(previousCut + MAX_CLIP_SECONDS * 0.5, inferredSampleRate, inferredHopSize);
        const searchEndIdx = timeToEnergyIndex(duration - MIN_CLIP_SECONDS, inferredSampleRate, inferredHopSize);
        let bestIdx = -1;
        let bestScore = -1;
        for (let i = searchStartIdx; i < searchEndIdx; i++) {
          const score = normalizedEnergy[i];
          if (score > bestScore) {
            bestScore = score;
            bestIdx = i;
          }
        }
        if (bestIdx >= 0) {
          cuts.push({ time: energyTimes[bestIdx], confidence: bestScore, type: "drop" });
        }
      }
      break;
    }
  }

  // Final safety pass: sort, deduplicate, clamp, ensure endpoints
  const unique = new Set<number>();
  const deduped = cuts.filter((c) => {
    const key = Math.round(c.time * 100);
    if (unique.has(key)) return false;
    unique.add(key);
    return true;
  });

  deduped.sort((a, b) => a.time - b.time);

  // Clamp to safe range
  const safe = deduped.filter((c) => c.time >= MIN_CLIP_SECONDS && c.time <= duration - MIN_CLIP_SECONDS);

  return safe;
}

function normalize(arr: number[]): number[] {
  if (!arr.length) return [];
  const min = Math.min(...arr);
  const max = Math.max(...arr);
  const range = max - min || 1;
  return arr.map((v) => (v - min) / range);
}

function timeToEnergyIndex(t: number, sampleRate: number, hopSize: number): number {
  return Math.floor((t * sampleRate) / hopSize);
}

function localMaxAround(arr: number[], center: number, radius: number): number {
  let mx = 0;
  const start = Math.max(0, center - radius);
  const end = Math.min(arr.length, center + radius + 1);
  for (let i = start; i < end; i++) {
    if (arr[i] > mx) mx = arr[i];
  }
  return mx || 1;
}

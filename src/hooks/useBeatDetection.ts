"use client";

import { useState, useEffect, useCallback, useRef } from "react";

export interface Beat {
  time: number;
  confidence: number;
}

export function useBeatDetection(audioBuffer: AudioBuffer | null) {
  const [beats, setBeats] = useState<Beat[]>([]);
  const [bpm, setBpm] = useState<number>(120);
  const [energy, setEnergy] = useState<number[]>([]);
  const processingRef = useRef(false);

  const detect = useCallback(async (): Promise<{
    beats: Beat[];
    bpm: number;
    energy: number[];
  }> => {
    if (!audioBuffer) return { beats: [], bpm: 120, energy: [] };

    processingRef.current = true;
    const sampleRate = audioBuffer.sampleRate;
    const channelData = audioBuffer.getChannelData(0);
    const frameSize = 2048;
    const hopSize = 512;
    const energies: number[] = [];

    for (let i = 0; i < channelData.length; i += hopSize) {
      let sum = 0;
      for (let j = 0; j < frameSize && i + j < channelData.length; j++) {
        sum += channelData[i + j] * channelData[i + j];
      }
      energies.push(Math.sqrt(sum / frameSize));
    }

    // Onset detection via flux
    const fluxes: number[] = [];
    for (let i = 1; i < energies.length; i++) {
      const diff = energies[i] - energies[i - 1];
      fluxes.push(diff > 0 ? diff : 0);
    }

    // Adaptive threshold peak picking
    const peaks: Beat[] = [];
    const windowLen = 20;
    for (let i = 0; i < fluxes.length; i++) {
      const start = Math.max(0, i - windowLen);
      const end = Math.min(fluxes.length, i + windowLen);
      let localMax = 0;
      for (let j = start; j < end; j++) localMax = Math.max(localMax, fluxes[j]);
      if (
        fluxes[i] > localMax * 0.75 &&
        fluxes[i] > fluxes[i - 1 || 0] &&
        fluxes[i] > fluxes[i + 1 || 0] &&
        fluxes[i] > 0.005
      ) {
        peaks.push({ time: (i * hopSize) / sampleRate, confidence: fluxes[i] });
      }
    }

    // BPM estimation
    let estimatedBpm = 120;
    if (peaks.length >= 2) {
      const intervals = [];
      for (let i = 1; i < peaks.length; i++) {
        intervals.push(peaks[i].time - peaks[i - 1].time);
      }
      const avg = intervals.reduce((a, b) => a + b, 0) / intervals.length;
      estimatedBpm = Math.round(60 / avg);
      if (estimatedBpm < 60) estimatedBpm *= 2;
      if (estimatedBpm > 200) estimatedBpm = Math.round(estimatedBpm / 2);
    }

    setBeats(peaks);
    setBpm(estimatedBpm);
    setEnergy(energies);
    processingRef.current = false;

    return { beats: peaks, bpm: estimatedBpm, energy: energies };
  }, [audioBuffer]);

  useEffect(() => {
    if (!audioBuffer || processingRef.current) return;
    detect();
  }, [audioBuffer, detect]);

  return { beats, bpm, energy, detect };
}

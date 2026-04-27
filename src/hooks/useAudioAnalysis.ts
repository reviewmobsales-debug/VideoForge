"use client";

import { useEffect, useRef, useCallback } from "react";

export interface AudioAnalysisResult {
  bpm: number;
  beats: Array<{ time: number; confidence: number }>;
  energy: number[];
  waveform: number[];
  duration: number;
}

export function useAudioAnalysis(audioBuffer: AudioBuffer | null) {
  const resultRef = useRef<AudioAnalysisResult | null>(null);

  const analyze = useCallback((): AudioAnalysisResult | null => {
    if (!audioBuffer) return null;

    const sampleRate = audioBuffer.sampleRate;
    const numChannels = audioBuffer.numberOfChannels;
    const length = audioBuffer.length;
    const duration = audioBuffer.duration;

    // Create offline context for analysis
    const offlineCtx = new OfflineAudioContext(numChannels, length, sampleRate);

    const source = offlineCtx.createBufferSource();
    source.buffer = audioBuffer;

    const analyzer = offlineCtx.createAnalyser();
    analyzer.fftSize = 2048;
    source.connect(analyzer);
    analyzer.connect(offlineCtx.destination);
    source.start(0);

    // Compute energy per frame
    const frameSize = 2048;
    const hopSize = 512;
    const energies: number[] = [];
    const waveform: number[] = [];

    const channelData = audioBuffer.getChannelData(0);
    for (let i = 0; i < channelData.length; i += hopSize) {
      let sum = 0;
      for (let j = 0; j < frameSize && i + j < channelData.length; j++) {
        sum += channelData[i + j] * channelData[i + j];
      }
      energies.push(Math.sqrt(sum / frameSize));
    }

    // Downsample waveform for display
    const samples = 800;
    const step = Math.max(1, Math.floor(channelData.length / samples));
    for (let i = 0; i < channelData.length; i += step) {
      waveform.push(channelData[i]);
    }

    // Beat detection via onset strength
    const onsetStrength: number[] = [];
    for (let i = 1; i < energies.length; i++) {
      onsetStrength.push(Math.max(0, energies[i] - energies[i - 1]));
    }

    // Pick peaks above adaptive threshold
    const beats: Array<{ time: number; confidence: number }> = [];
    const windowSize = 20;
    for (let i = 0; i < onsetStrength.length; i++) {
      const start = Math.max(0, i - windowSize);
      const end = Math.min(onsetStrength.length, i + windowSize);
      let localMax = 0;
      for (let j = start; j < end; j++) localMax = Math.max(localMax, onsetStrength[j]);
      if (onsetStrength[i] > localMax * 0.75 && onsetStrength[i] > 0.01) {
        beats.push({
          time: (i * hopSize) / sampleRate,
          confidence: onsetStrength[i],
        });
      }
    }

    // Estimate BPM from beat intervals
    let bpm = 120;
    if (beats.length >= 2) {
      let total = 0;
      let count = 0;
      for (let i = 1; i < beats.length; i++) {
        const interval = beats[i].time - beats[i - 1].time;
        if (interval > 0.2 && interval < 2.0) {
          total += interval;
          count++;
        }
      }
      const avgInterval = count > 0 ? total / count : 0.5;
      bpm = 60 / avgInterval;
      if (bpm < 60) bpm *= 2;
      if (bpm > 200) bpm /= 2;
    }

    const result: AudioAnalysisResult = {
      bpm,
      beats,
      energy: energies,
      waveform,
      duration,
    };

    resultRef.current = result;
    return result;
  }, [audioBuffer]);

  useEffect(() => {
    if (audioBuffer) {
      analyze();
    }
  }, [audioBuffer, analyze]);

  return resultRef.current;
}

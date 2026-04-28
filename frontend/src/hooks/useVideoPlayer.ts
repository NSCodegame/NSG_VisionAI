/**
 * Video Player Hook — Phase 23.6
 *
 * Sets up an HLS.js video player for a given feed.
 * Falls back to native HLS on Safari.
 */

import { useEffect, useRef, useState } from "react";

const HLS_BASE = import.meta.env.VITE_API_URL || "/api/v1";

export interface VideoPlayerState {
  isLoading: boolean;
  isPlaying: boolean;
  error: string | null;
  currentTime: number;
  duration: number;
}

export function useVideoPlayer(feedId: string, enabled = true) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const hlsRef = useRef<unknown>(null);
  const [state, setState] = useState<VideoPlayerState>({
    isLoading: true,
    isPlaying: false,
    error: null,
    currentTime: 0,
    duration: 0,
  });

  const manifestUrl = `${HLS_BASE}/streams/${feedId}/live.m3u8`;

  useEffect(() => {
    if (!enabled || !videoRef.current || !feedId) return;

    const video = videoRef.current;

    const setupHLS = async () => {
      setState((prev) => ({ ...prev, isLoading: true, error: null }));

      try {
        // Dynamic import of hls.js (optional dependency)
        const HlsModule = await import("hls.js").catch(() => null);
        const Hls = HlsModule?.default;

        if (Hls && Hls.isSupported()) {
          // Use HLS.js
          const hls = new Hls({
            lowLatencyMode: true,
            backBufferLength: 30,
            maxBufferLength: 10,
          });

          hlsRef.current = hls;
          hls.loadSource(manifestUrl);
          hls.attachMedia(video);

          hls.on(Hls.Events.MANIFEST_PARSED, () => {
            setState((prev) => ({ ...prev, isLoading: false }));
            video.play().catch(() => {
              // Autoplay blocked — user interaction needed
            });
          });

          hls.on(Hls.Events.ERROR, (_: unknown, data: { fatal: boolean; details: string }) => {
            if (data.fatal) {
              setState((prev) => ({
                ...prev,
                error: `Stream error: ${data.details}`,
                isLoading: false,
              }));
            }
          });
        } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
          // Native HLS (Safari)
          video.src = manifestUrl;
          video.addEventListener("loadedmetadata", () => {
            setState((prev) => ({ ...prev, isLoading: false }));
            video.play().catch(() => {});
          });
        } else {
          setState((prev) => ({
            ...prev,
            error: "HLS not supported in this browser",
            isLoading: false,
          }));
        }
      } catch (err) {
        setState((prev) => ({
          ...prev,
          error: "Failed to initialize video player",
          isLoading: false,
        }));
      }
    };

    setupHLS();

    // Track playback state
    const onPlay = () => setState((prev) => ({ ...prev, isPlaying: true }));
    const onPause = () => setState((prev) => ({ ...prev, isPlaying: false }));
    const onTimeUpdate = () =>
      setState((prev) => ({
        ...prev,
        currentTime: video.currentTime,
        duration: video.duration || 0,
      }));

    video.addEventListener("play", onPlay);
    video.addEventListener("pause", onPause);
    video.addEventListener("timeupdate", onTimeUpdate);

    return () => {
      video.removeEventListener("play", onPlay);
      video.removeEventListener("pause", onPause);
      video.removeEventListener("timeupdate", onTimeUpdate);

      // Destroy HLS instance
      if (hlsRef.current) {
        const hls = hlsRef.current as { destroy: () => void };
        hls.destroy();
        hlsRef.current = null;
      }
    };
  }, [feedId, enabled, manifestUrl]);

  const play = () => videoRef.current?.play();
  const pause = () => videoRef.current?.pause();
  const seek = (time: number) => {
    if (videoRef.current) videoRef.current.currentTime = time;
  };

  return { videoRef, state, play, pause, seek };
}

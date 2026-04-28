/**
 * WebSocket Hook — Phase 23.6
 *
 * Manages a WebSocket connection with JWT auth, auto-reconnect,
 * and heartbeat ping/pong.
 */

import { useEffect, useRef, useState, useCallback } from "react";

interface UseWebSocketOptions {
  url: string;
  onMessage?: (data: unknown) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  maxRetries?: number;
  heartbeatIntervalMs?: number;
}

export function useWebSocket({
  url,
  onMessage,
  onConnect,
  onDisconnect,
  maxRetries = 5,
  heartbeatIntervalMs = 30_000,
}: UseWebSocketOptions) {
  const [isConnected, setIsConnected] = useState(false);
  const [retryCount, setRetryCount] = useState(0);
  const socketRef = useRef<WebSocket | null>(null);
  const heartbeatRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const missedPongsRef = useRef(0);
  const retryTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const shouldReconnectRef = useRef(true);

  const clearHeartbeat = () => {
    if (heartbeatRef.current) {
      clearInterval(heartbeatRef.current);
      heartbeatRef.current = null;
    }
  };

  const startHeartbeat = useCallback((ws: WebSocket) => {
    clearHeartbeat();
    missedPongsRef.current = 0;

    heartbeatRef.current = setInterval(() => {
      if (ws.readyState !== WebSocket.OPEN) return;

      if (missedPongsRef.current >= 3) {
        console.warn("[WS] 3 missed pongs — closing connection");
        ws.close();
        return;
      }

      missedPongsRef.current += 1;
      ws.send(JSON.stringify({ type: "ping" }));
    }, heartbeatIntervalMs);
  }, [heartbeatIntervalMs]);

  const connect = useCallback(() => {
    if (!shouldReconnectRef.current) return;

    const token = localStorage.getItem("access_token");
    const wsUrl = token ? `${url}?token=${token}` : url;

    const ws = new WebSocket(wsUrl);
    socketRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      setRetryCount(0);
      missedPongsRef.current = 0;
      startHeartbeat(ws);
      onConnect?.();
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        // Handle pong
        if (data.type === "pong") {
          missedPongsRef.current = Math.max(0, missedPongsRef.current - 1);
          return;
        }

        onMessage?.(data);
      } catch {
        // Non-JSON message — ignore
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      clearHeartbeat();
      onDisconnect?.();

      if (!shouldReconnectRef.current) return;

      setRetryCount((prev) => {
        const next = prev + 1;
        if (next <= maxRetries) {
          const delay = Math.min(1000 * 2 ** (next - 1), 30_000); // Exponential backoff, max 30s
          retryTimeoutRef.current = setTimeout(connect, delay);
        }
        return next;
      });
    };

    ws.onerror = (err) => {
      console.error("[WS] Error:", err);
    };
  }, [url, onMessage, onConnect, onDisconnect, maxRetries, startHeartbeat]);

  useEffect(() => {
    shouldReconnectRef.current = true;
    connect();

    return () => {
      shouldReconnectRef.current = false;
      clearHeartbeat();
      if (retryTimeoutRef.current) clearTimeout(retryTimeoutRef.current);
      socketRef.current?.close();
    };
  }, [connect]);

  const send = useCallback((data: unknown) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify(data));
    }
  }, []);

  return { isConnected, retryCount, send };
}

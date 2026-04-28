import { useState, useEffect, useRef } from 'react';
import type { Alert } from '../types';

/**
 * Legacy alert hook — uses Vite proxy (/api/v1/ws/alerts) with real JWT token.
 * Prefer useAlertStream for new code.
 */
export const useAlerts = () => {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);
  const retryRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;

    const connect = () => {
      if (!mountedRef.current) return;

      // Use real token from localStorage; skip if missing
      const token = localStorage.getItem("access_token");
      if (!token) return;

      // Use Vite proxy path — avoids CORS and ws:// host mismatch
      const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
      const wsUrl = `${proto}//${window.location.host}/api/v1/ws/alerts?token=${token}`;

      const socket = new WebSocket(wsUrl);
      socketRef.current = socket;

      socket.onopen = () => {
        if (!mountedRef.current) { socket.close(); return; }
        setIsConnected(true);
      };

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "NEW_ALERT" && data.alert) {
            setAlerts(prev => [data.alert, ...prev].slice(0, 50));
            if (Notification.permission === "granted" && data.alert.priority === "P1_CRITICAL") {
              new Notification("CRITICAL ALERT", {
                body: `${data.alert.alert_type} detected on feed ${data.alert.feed_id}`,
                icon: '/favicon.ico'
              });
            }
          }
        } catch { /* ignore non-JSON */ }
      };

      socket.onclose = () => {
        if (!mountedRef.current) return;
        setIsConnected(false);
        // Retry after 5s
        retryRef.current = setTimeout(connect, 5000);
      };

      socket.onerror = () => {
        socket.close();
      };
    };

    connect();

    return () => {
      mountedRef.current = false;
      if (retryRef.current) clearTimeout(retryRef.current);
      socketRef.current?.close();
    };
  }, []);

  return { alerts, isConnected };
};

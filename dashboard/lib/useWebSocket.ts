"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { NexusEvent } from "./types";

const MAX_EVENTS = 200;
const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 15000;

interface UseWebSocketReturn {
  events: NexusEvent[];
  connected: boolean;
  reconnecting: boolean;
}

export function useWebSocket(url?: string): UseWebSocketReturn {
  const [events, setEvents] = useState<NexusEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [reconnecting, setReconnecting] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const retriesRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const wsUrl =
    url ??
    (typeof window !== "undefined"
      ? `ws://${window.location.hostname}:8080/api/ws/events`
      : "");

  const connect = useCallback(() => {
    if (!wsUrl) return;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        setReconnecting(false);
        retriesRef.current = 0;
      };

      ws.onmessage = (msg) => {
        try {
          const event: NexusEvent = JSON.parse(msg.data);
          setEvents((prev) => [event, ...prev].slice(0, MAX_EVENTS));
        } catch {
          // ignore malformed
        }
      };

      ws.onclose = () => {
        setConnected(false);
        wsRef.current = null;
        scheduleReconnect();
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {
      scheduleReconnect();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [wsUrl]);

  const scheduleReconnect = useCallback(() => {
    setReconnecting(true);
    const delay = Math.min(
      RECONNECT_BASE_MS * 2 ** retriesRef.current,
      RECONNECT_MAX_MS
    );
    retriesRef.current += 1;
    timerRef.current = setTimeout(connect, delay);
  }, [connect]);

  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [connect]);

  return { events, connected, reconnecting };
}

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../services/api";

export interface Message {
  role: "user" | "assistant";
  content: string;
}

interface SocketEvent {
  type: string;
  text?: string;
  message?: string;
  command_handled?: boolean;
}

export interface VoicePreferences {
  wakeWordEnabled: boolean;
  wakeWord: string;
}

export function useAssistant() {
  const socketRef = useRef<WebSocket | null>(null);
  const preferencesRef = useRef<VoicePreferences>({ wakeWordEnabled: false, wakeWord: "hey assistant" });
  const [messages, setMessages] = useState<Message[]>([]);
  const [connected, setConnected] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let socket: WebSocket | null = null;
    const connectionTimer = window.setTimeout(() => {
      const socketUrl = `${api.baseUrl.replace(/^http/, "ws")}/ws/voice`;
      socket = new WebSocket(socketUrl);
      socketRef.current = socket;
      socket.onopen = () => {
        if (socketRef.current !== socket) return;
        setConnected(true);
        socket?.send(JSON.stringify({
          type: "settings",
          wake_word_enabled: preferencesRef.current.wakeWordEnabled,
          wake_word: preferencesRef.current.wakeWord,
        }));
      };
      socket.onclose = () => {
        if (socketRef.current === socket) {
          socketRef.current = null;
          setConnected(false);
        }
      };
      socket.onerror = () => {
        if (socketRef.current === socket) {
          setError("Connection to the assistant was interrupted.");
        }
      };
      socket.onmessage = (event: MessageEvent<string>) => {
        if (socketRef.current !== socket) return;
        const payload = JSON.parse(event.data) as SocketEvent;
        if (payload.type === "assistant_start") {
          setError("");
          setStreaming(true);
          setMessages((current) => [...current, { role: "assistant", content: "" }]);
        } else if (payload.type === "token") {
          setMessages((current) => {
            const next = [...current];
            const last = next[next.length - 1];
            if (last?.role === "assistant") {
              next[next.length - 1] = { ...last, content: last.content + (payload.text ?? "") };
            }
            return next;
          });
        } else if (payload.type === "assistant_done") {
          setStreaming(false);
        } else if (payload.type === "transcript") {
          if (payload.text) {
            setError("");
            setMessages((current) => [...current, { role: "user", content: payload.text ?? "" }]);
          }
        } else if (payload.type === "error" || payload.type === "wake_required") {
          setStreaming(false);
          setError(payload.message ?? "The assistant could not process that request.");
        }
      };
    }, 0);

    return () => {
      window.clearTimeout(connectionTimer);
      if (socketRef.current === socket) socketRef.current = null;
      if (socket) {
        socket.onopen = null;
        socket.onclose = null;
        socket.onerror = null;
        socket.onmessage = null;
        if (socket.readyState === WebSocket.CONNECTING) {
          socket.addEventListener("open", () => socket?.close(), { once: true });
        } else if (socket.readyState === WebSocket.OPEN) {
          socket.close();
        }
      }
    };
  }, []);

  const sendText = useCallback((text: string) => {
    const trimmed = text.trim();
    const socket = socketRef.current;
    if (!trimmed || socket?.readyState !== WebSocket.OPEN) {
      if (socket?.readyState !== WebSocket.OPEN) setError("The backend is not connected yet.");
      return;
    }
    setError("");
    setMessages((current) => [...current, { role: "user", content: trimmed }]);
    socket.send(JSON.stringify({ type: "text", text: trimmed }));
  }, []);

  const sendAudio = useCallback(async (audio: Blob) => {
    const socket = socketRef.current;
    if (socket?.readyState !== WebSocket.OPEN) {
      setError("The backend is not connected yet.");
      return;
    }
    const bytes = new Uint8Array(await audio.arrayBuffer());
    let binary = "";
    for (let offset = 0; offset < bytes.length; offset += 0x8000) {
      binary += String.fromCharCode(...bytes.subarray(offset, offset + 0x8000));
    }
    setError("");
    socket.send(
      JSON.stringify({
        type: "audio",
        data: btoa(binary),
        mime_type: audio.type || "audio/webm",
      }),
    );
  }, []);

  const updateVoicePreferences = useCallback((preferences: VoicePreferences) => {
    preferencesRef.current = preferences;
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({
        type: "settings",
        wake_word_enabled: preferences.wakeWordEnabled,
        wake_word: preferences.wakeWord,
      }));
    }
  }, []);

  return { messages, connected, streaming, error, sendText, sendAudio, updateVoicePreferences };
}

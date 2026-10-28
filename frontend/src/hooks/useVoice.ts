import { useCallback, useEffect, useRef, useState } from "react";

export type ListeningMode = "push-to-talk" | "continuous";

export function useVoice(sendAudio: (audio: Blob) => Promise<void>, mode: ListeningMode) {
  const [recording, setRecording] = useState(false);
  const [error, setError] = useState("");
  const streamRef = useRef<MediaStream | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const continuousRef = useRef(false);
  const modeRef = useRef(mode);
  const restartRef = useRef<number | undefined>(undefined);

  useEffect(() => {
    modeRef.current = mode;
  }, [mode]);

  const startSegment = useCallback(async () => {
    try {
      if (!streamRef.current) streamRef.current = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = ["audio/webm;codecs=opus", "audio/webm"].find((item) => MediaRecorder.isTypeSupported(item));
      const recorder = new MediaRecorder(streamRef.current, mimeType ? { mimeType } : undefined);
      const chunks: BlobPart[] = [];
      recorder.ondataavailable = (event) => {
        if (event.data.size) chunks.push(event.data);
      };
      recorder.onstop = () => {
        setRecording(false);
        if (chunks.length) void sendAudio(new Blob(chunks, { type: recorder.mimeType || "audio/webm" }));
        if (continuousRef.current && modeRef.current === "continuous") {
          restartRef.current = window.setTimeout(() => void startSegment(), 400);
        }
      };
      recorder.onerror = () => setError("Audio recording failed. Check your microphone and permissions.");
      recorderRef.current = recorder;
      recorder.start();
      setRecording(true);
      setError("");
      if (modeRef.current === "continuous") {
        restartRef.current = window.setTimeout(() => {
          if (recorder.state === "recording") recorder.stop();
        }, 6000);
      }
    } catch (reason) {
      continuousRef.current = false;
      setError(reason instanceof Error ? reason.message : "Microphone access was denied.");
    }
  }, [sendAudio]);

  const start = useCallback(() => {
    continuousRef.current = mode === "continuous";
    void startSegment();
  }, [mode, startSegment]);

  const stop = useCallback(() => {
    continuousRef.current = false;
    if (restartRef.current !== undefined) window.clearTimeout(restartRef.current);
    if (recorderRef.current?.state === "recording") recorderRef.current.stop();
    setRecording(false);
  }, []);

  const toggle = useCallback(() => {
    if (recording) stop();
    else start();
  }, [recording, start, stop]);

  useEffect(
    () => () => {
      continuousRef.current = false;
      if (restartRef.current !== undefined) window.clearTimeout(restartRef.current);
      streamRef.current?.getTracks().forEach((track) => track.stop());
    },
    [],
  );

  return { recording, error, toggle, stop };
}

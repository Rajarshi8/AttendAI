"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Webcam from "react-webcam";

import { WebcamFeed } from "@/components/WebcamFeed";
import { markAttendance, recognizeUser } from "@/lib/api";
import { UserProfile } from "@/types";

export default function AttendancePage() {
  const webcamRef = useRef<Webcam | null>(null);
  const frameBufferRef = useRef<string[]>([]);
  const frameCounterRef = useRef(0);
  const processingRef = useRef(false);
  const lastMarkedUserRef = useRef<string | null>(null);

  const [running, setRunning] = useState(false);
  const [status, setStatus] = useState("Idle");
  const [recognizedUser, setRecognizedUser] = useState<UserProfile | null>(null);
  const [similarity, setSimilarity] = useState<number | null>(null);
  const [attendanceMessage, setAttendanceMessage] = useState<string | null>(null);

  const processRecognition = useCallback(async () => {
    if (processingRef.current) return;

    const frame = webcamRef.current?.getScreenshot();
    if (!frame) {
      setStatus("Waiting for webcam frame...");
      return;
    }

    frameBufferRef.current = [...frameBufferRef.current.slice(-11), frame];
    frameCounterRef.current += 1;

    if (frameCounterRef.current % 3 !== 0) {
      return;
    }

    processingRef.current = true;

    try {
      const result = await recognizeUser({
        frame,
        frames: frameBufferRef.current,
        require_liveness: true,
      });

      setStatus(result.message);

      if (result.matched && result.live && result.user) {
        setRecognizedUser(result.user);
        setSimilarity(result.similarity);

        if (lastMarkedUserRef.current !== result.user.id) {
          const attendanceResult = await markAttendance({ status: "present" });
          setAttendanceMessage(attendanceResult.message);
          lastMarkedUserRef.current = result.user.id;
        }
      } else {
        setRecognizedUser(null);
        setSimilarity(null);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Recognition request failed.";
      setStatus(errorMessage);
    } finally {
      processingRef.current = false;
    }
  }, []);

  useEffect(() => {
    if (!running) return;

    const id = setInterval(() => {
      void processRecognition();
    }, 850);

    return () => clearInterval(id);
  }, [processRecognition, running]);

  return (
    <div className="grid gap-6 lg:grid-cols-[1.3fr,1fr]">
      <section className="space-y-4">
        <h1 className="text-3xl font-bold">Live Attendance</h1>
        <p className="text-muted">The system processes every 3rd frame and performs head-movement liveness before recognition.</p>
        <WebcamFeed webcamRef={webcamRef} />

        <div className="flex gap-3">
          <button
            type="button"
            onClick={() => setRunning((prev) => !prev)}
            className="rounded-full bg-accent px-5 py-2.5 font-semibold text-accent-foreground"
          >
            {running ? "Stop" : "Start"} Recognition
          </button>

          <button
            type="button"
            onClick={() => {
              frameBufferRef.current = [];
              frameCounterRef.current = 0;
              lastMarkedUserRef.current = null;
              setRecognizedUser(null);
              setSimilarity(null);
              setAttendanceMessage(null);
              setStatus("Idle");
            }}
            className="rounded-full border border-border px-4 py-2"
          >
            Reset
          </button>
        </div>
      </section>

      <section className="space-y-4 rounded-2xl border border-border bg-panel p-5">
        <h2 className="text-xl font-semibold">Recognition Status</h2>
        <p className="text-muted">{status}</p>

        {recognizedUser ? (
          <div className="space-y-2 rounded-xl border border-border p-4">
            <p className="font-semibold">{recognizedUser.name}</p>
            <p className="text-sm text-muted">{recognizedUser.email}</p>
            <p className="text-sm text-muted">ID: {recognizedUser.user_id}</p>
            <p className="text-sm">
              Similarity: <span className="font-semibold">{similarity?.toFixed(4)}</span>
            </p>
          </div>
        ) : (
          <p className="text-sm text-muted">No active match.</p>
        )}

        {attendanceMessage && <p className="status-ok text-sm">{attendanceMessage}</p>}
      </section>
    </div>
  );
}

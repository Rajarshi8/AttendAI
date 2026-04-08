"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Webcam from "react-webcam";

import { WebcamFeed } from "@/components/WebcamFeed";
import { getActiveSession, getCurrentProfile, markAttendance } from "@/lib/api";
import { AttendanceRecord, CurrentUserProfile, SessionItem } from "@/types";

export default function AttendancePage() {
  const webcamRef = useRef<Webcam | null>(null);
  const [profile, setProfile] = useState<CurrentUserProfile | null>(null);
  const [activeSession, setActiveSession] = useState<SessionItem | null>(null);
  const [loadingSession, setLoadingSession] = useState(true);
  const [status, setStatus] = useState("Waiting for active attendance session...");
  const [attendanceMessage, setAttendanceMessage] = useState<string | null>(null);
  const [attendanceRecord, setAttendanceRecord] = useState<AttendanceRecord | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const pollActiveSession = useCallback(async () => {
    try {
      const response = await getActiveSession();
      setActiveSession(response.session);
      if (response.session) {
        setStatus(`Attendance active for ${response.session.class_name}.`);
      } else {
        setStatus("No active attendance session right now.");
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Could not fetch active session.";
      setStatus(errorMessage);
    } finally {
      setLoadingSession(false);
    }
  }, []);

  useEffect(() => {
    void (async () => {
      try {
        const currentProfile = await getCurrentProfile();
        setProfile(currentProfile);
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : "Could not load profile.";
        setStatus(errorMessage);
      }
      await pollActiveSession();
    })();
  }, [pollActiveSession]);

  useEffect(() => {
    const id = setInterval(() => {
      void pollActiveSession();
    }, 6000);

    return () => clearInterval(id);
  }, [pollActiveSession]);

  const getCurrentPosition = () =>
    new Promise<GeolocationPosition>((resolve, reject) => {
      if (!navigator.geolocation) {
        reject(new Error("Geolocation is not supported in this browser."));
        return;
      }

      navigator.geolocation.getCurrentPosition(resolve, reject, {
        enableHighAccuracy: true,
        timeout: 10000,
      });
    });

  const captureBurstFrames = async (count: number, delayMs: number) => {
    const frames: string[] = [];
    for (let index = 0; index < count; index += 1) {
      const frame = webcamRef.current?.getScreenshot();
      if (frame) frames.push(frame);
      await new Promise((resolve) => setTimeout(resolve, delayMs));
    }
    return frames;
  };

  const onMarkAttendance = async () => {
    if (!activeSession) return;

    setSubmitting(true);
    setAttendanceMessage(null);

    try {
      const position = await getCurrentPosition();
      const burstFrames = await captureBurstFrames(8, 120);
      const primaryFrame = burstFrames[burstFrames.length - 1] || webcamRef.current?.getScreenshot();

      if (!primaryFrame) {
        throw new Error("Could not capture webcam frame.");
      }

      const result = await markAttendance({
        session_id: activeSession.session_id,
        frame: primaryFrame,
        frames: burstFrames,
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
        require_liveness: true,
      });

      setAttendanceMessage(result.message);
      setAttendanceRecord(result.record);
      setStatus(result.message);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Attendance request failed.";
      setStatus(errorMessage);
      setAttendanceMessage(errorMessage);
    } finally {
      setSubmitting(false);
    }
  };

  if (!profile) {
    return <p className="text-muted">Loading student profile...</p>;
  }

  if (profile.role !== "student") {
    return (
      <div className="rounded-2xl border border-border bg-panel p-5">
        <h1 className="text-2xl font-bold">Student View</h1>
        <p className="mt-2 text-muted">This page is for student attendance marking only. Your current role is {profile.role}.</p>
      </div>
    );
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[1.3fr,1fr]">
      {activeSession && (
        <div className="fixed bottom-5 right-5 z-20 w-[min(92vw,380px)] rounded-2xl border border-border bg-panel p-4 shadow-glow">
          <p className="text-sm uppercase tracking-[0.1em] text-muted">Attendance Started</p>
          <p className="mt-1 font-semibold">{activeSession.class_name}</p>
          <p className="mt-1 text-sm text-muted">Tap Mark Attendance to submit face + geofence validation.</p>
          <button
            type="button"
            onClick={() => void onMarkAttendance()}
            disabled={submitting}
            className="mt-3 rounded-full bg-accent px-4 py-2 text-sm font-semibold text-accent-foreground disabled:opacity-70"
          >
            {submitting ? "Submitting..." : "Mark Attendance"}
          </button>
        </div>
      )}

      <section className="space-y-4">
        <h1 className="text-3xl font-bold">Student Attendance</h1>
        <p className="text-muted">Keep your face in frame. When attendance opens, capture face and location to submit.</p>
        <WebcamFeed webcamRef={webcamRef} />

        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            onClick={() => void onMarkAttendance()}
            disabled={!activeSession || submitting || loadingSession}
            className="rounded-full bg-accent px-5 py-2.5 font-semibold text-accent-foreground"
          >
            {submitting ? "Marking..." : activeSession ? "Mark Attendance" : "Waiting for Session"}
          </button>

          <button
            type="button"
            onClick={() => {
              setAttendanceRecord(null);
              setAttendanceMessage(null);
              setStatus("Ready");
            }}
            className="rounded-full border border-border px-4 py-2"
          >
            Clear
          </button>
        </div>

        {activeSession && (
          <div className="rounded-xl border border-border p-4 text-sm">
            <p>
              Active Class: <span className="font-semibold">{activeSession.class_name}</span>
            </p>
            <p>Session ID: {activeSession.session_id}</p>
            <p>Allowed Radius: {activeSession.radius_meters}m</p>
            <p>Started: {new Date(activeSession.start_time).toLocaleString()}</p>
          </div>
        )}
      </section>

      <section className="space-y-4 rounded-2xl border border-border bg-panel p-5">
        <h2 className="text-xl font-semibold">Attendance Status</h2>
        <p className="text-muted">{status}</p>

        {attendanceRecord ? (
          <div className="space-y-2 rounded-xl border border-border p-4">
            <p className="font-semibold">{attendanceRecord.user_name}</p>
            <p className="text-sm text-muted">{attendanceRecord.email}</p>
            <p className="text-sm text-muted">Session: {attendanceRecord.session_id || "-"}</p>
            <p className="text-sm text-muted">Status: {attendanceRecord.status}</p>
            <p className="text-sm">
              Distance: <span className="font-semibold">{attendanceRecord.distance != null ? `${attendanceRecord.distance.toFixed(2)}m` : "-"}</span>
            </p>
          </div>
        ) : (
          <p className="text-sm text-muted">No attendance submission yet.</p>
        )}

        {attendanceMessage && <p className="status-ok text-sm">{attendanceMessage}</p>}
      </section>
    </div>
  );
}

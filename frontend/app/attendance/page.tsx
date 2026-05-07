"use client";

import { useEffect, useRef, useState } from "react";
import Webcam from "react-webcam";
import { CheckCircle, Clock, MapPin, AlertTriangle, Loader2, RefreshCw, Wifi } from "lucide-react";

import { WebcamFeed } from "@/components/WebcamFeed";
import { getActiveSession, getCurrentProfile, markAttendance } from "@/lib/api";
import { subscribeToSessions } from "@/lib/appwrite";
import { AttendanceRecord, CurrentUserProfile, SessionItem } from "@/types";

// ─── Error code → friendly message map ────────────────────────────────────────

const ERROR_MESSAGES: Record<string, { icon: string; text: string }> = {
  OUT_OF_RANGE: {
    icon: "📍",
    text: "You are outside the classroom zone. Please move closer.",
  },
  LOW_GPS_ACCURACY: {
    icon: "📡",
    text: "GPS signal is too weak. Try moving outdoors or near a window.",
  },
  LIVENESS_FAILED: {
    icon: "🔄",
    text: "Liveness check failed. Please move your head slightly side-to-side.",
  },
  FACE_NOT_DETECTED: {
    icon: "🎥",
    text: "Face not detected. Ensure good lighting and look directly at the camera.",
  },
  FACE_MISMATCH: {
    icon: "⚠️",
    text: "Face does not match your registered profile. Contact your administrator.",
  },
};

// ─── Status pill ──────────────────────────────────────────────────────────────

type StatusType = "idle" | "loading" | "success" | "error" | "warning";

function StatusPill({ type, message }: { type: StatusType; message: string }) {
  const colors: Record<StatusType, string> = {
    idle: "border-border text-muted",
    loading: "border-blue-400/40 text-blue-400 dark:text-blue-300",
    success: "border-green-500/40 bg-green-500/10 text-green-600 dark:text-green-400",
    error: "border-red-500/40 bg-red-500/10 text-red-600 dark:text-red-400",
    warning: "border-yellow-500/40 bg-yellow-500/10 text-yellow-700 dark:text-yellow-300",
  };

  return (
    <div className={`flex items-start gap-2 rounded-xl border px-4 py-3 text-sm ${colors[type]}`}>
      {type === "loading" && <Loader2 className="mt-0.5 h-4 w-4 shrink-0 animate-spin" />}
      {type === "success" && <CheckCircle className="mt-0.5 h-4 w-4 shrink-0" />}
      {type === "error" && <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />}
      {type === "warning" && <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />}
      <span>{message}</span>
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function AttendancePage() {
  const webcamRef = useRef<Webcam | null>(null);
  const [profile, setProfile] = useState<CurrentUserProfile | null>(null);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [activeSession, setActiveSession] = useState<SessionItem | null>(null);
  const [loadingSession, setLoadingSession] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [attendanceRecord, setAttendanceRecord] = useState<AttendanceRecord | null>(null);
  const [statusType, setStatusType] = useState<StatusType>("idle");
  const [statusMessage, setStatusMessage] = useState("Connecting to session feed…");
  const [errorCode, setErrorCode] = useState<string | null>(null);

  // ── Initial load ────────────────────────────────────────────────────────────

  useEffect(() => {
    void (async () => {
      try {
        const currentProfile = await getCurrentProfile();
        setProfile(currentProfile);
      } catch (err) {
        setProfileError(err instanceof Error ? err.message : "Could not load profile.");
      }

      // One-shot fetch for initial state
      try {
        const response = await getActiveSession();
        if (response.session) {
          setActiveSession(response.session);
          setStatusType("idle");
          setStatusMessage(`Attendance open for ${response.session.class_name}.`);
        } else {
          setStatusMessage("No active attendance session. Waiting for your teacher to start one…");
        }
      } catch {
        setStatusMessage("Could not fetch session status.");
      } finally {
        setLoadingSession(false);
      }
    })();
  }, []);

  // ── Appwrite Realtime subscription (replaces polling) ───────────────────────

  useEffect(() => {
    const unsub = subscribeToSessions((event) => {
      const payload = event.payload as Record<string, unknown>;
      const isActive = Boolean(payload?.is_active);

      if (isActive) {
        // Build a minimal SessionItem from the realtime payload
        const session: SessionItem = {
          session_id: String(payload.session_id || payload.$id || ""),
          admin_id: String(payload.admin_id || ""),
          class_name: String(payload.class_name || "Unknown class"),
          start_time: String(payload.start_time || ""),
          end_time: payload.end_time ? String(payload.end_time) : null,
          latitude: Number(payload.latitude || 0),
          longitude: Number(payload.longitude || 0),
          radius_meters: Number(payload.radius_meters || 0),
          is_active: true,
        };
        setActiveSession(session);
        setSubmitted(false);
        setStatusType("idle");
        setStatusMessage(`🔔 Attendance opened for ${session.class_name}!`);
      } else {
        setActiveSession(null);
        setStatusType("warning");
        setStatusMessage("Attendance session has ended.");
      }
    });

    return unsub;
  }, []);

  // ── Helpers ──────────────────────────────────────────────────────────────────

  const getCurrentPosition = (): Promise<GeolocationPosition> =>
    new Promise((resolve, reject) => {
      if (!navigator.geolocation) {
        reject(new Error("Geolocation is not supported by your browser."));
        return;
      }
      navigator.geolocation.getCurrentPosition(resolve, reject, {
        enableHighAccuracy: true,
        timeout: 12000,
        maximumAge: 0,
      });
    });

  const captureBurstFrames = async (count: number, delayMs: number): Promise<string[]> => {
    const frames: string[] = [];
    for (let i = 0; i < count; i++) {
      const frame = webcamRef.current?.getScreenshot();
      if (frame) frames.push(frame);
      await new Promise((r) => setTimeout(r, delayMs));
    }
    return frames;
  };

  // ── Mark attendance ──────────────────────────────────────────────────────────

  const onMarkAttendance = async () => {
    if (!activeSession || submitting || submitted) return;

    setSubmitting(true);
    setErrorCode(null);
    setStatusType("loading");
    setStatusMessage("📸 Capturing your face and location…");

    try {
      let position: GeolocationPosition;
      try {
        position = await getCurrentPosition();
      } catch {
        setStatusType("error");
        setStatusMessage("Could not get your location. Please allow location access and try again.");
        return;
      }

      setStatusMessage("🔍 Verifying identity…");

      const burstFrames = await captureBurstFrames(8, 120);
      const primaryFrame = burstFrames[burstFrames.length - 1] ?? webcamRef.current?.getScreenshot() ?? null;

      if (!primaryFrame) {
        setStatusType("error");
        setStatusMessage("Could not capture webcam frame. Check camera permissions.");
        return;
      }

      const result = await markAttendance({
        session_id: activeSession.session_id,
        frame: primaryFrame,
        frames: burstFrames,
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
        gps_accuracy: position.coords.accuracy,
        require_liveness: true,
      });

      setAttendanceRecord(result.record);

      if (result.marked && result.record?.status === "present") {
        setSubmitted(true);
        setStatusType("success");
        setStatusMessage("✅ Attendance marked successfully!");
      } else if (result.error_code) {
        const mapped = ERROR_MESSAGES[result.error_code];
        setErrorCode(result.error_code);
        setStatusType(result.marked ? "warning" : "error");
        setStatusMessage(mapped ? `${mapped.icon} ${mapped.text}` : result.message);
      } else {
        setStatusType("warning");
        setStatusMessage(result.message);
      }
    } catch (err) {
      setStatusType("error");
      setStatusMessage(err instanceof Error ? err.message : "Attendance request failed. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  const onRetry = () => {
    setErrorCode(null);
    setStatusType("idle");
    setStatusMessage(activeSession ? `Attendance open for ${activeSession.class_name}.` : "Waiting for session…");
    setAttendanceRecord(null);
  };

  // ── Render guards ────────────────────────────────────────────────────────────

  if (!profile && !profileError) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <div className="flex flex-col items-center gap-3 text-muted">
          <Loader2 className="h-8 w-8 animate-spin" />
          <p className="text-sm">Loading your profile…</p>
        </div>
      </div>
    );
  }

  if (profileError) {
    return (
      <div className="rounded-2xl border border-border bg-panel p-5">
        <h1 className="text-2xl font-bold">Authentication Error</h1>
        <p className="mt-2 text-sm text-muted">{profileError}</p>
        <p className="mt-1 text-sm text-muted">Please log in from the Dashboard and try again.</p>
      </div>
    );
  }

  if (profile?.role !== "student") {
    return (
      <div className="rounded-2xl border border-border bg-panel p-5">
        <h1 className="text-2xl font-bold">Student View</h1>
        <p className="mt-2 text-muted">
          This page is for student attendance only. Your current role is{" "}
          <span className="font-semibold">{profile?.role}</span>.
        </p>
      </div>
    );
  }

  // ── Full render ───────────────────────────────────────────────────────────────

  return (
    <div className="grid gap-6 lg:grid-cols-[1.3fr,1fr]">
      {/* ── Floating session pill ─────────────────────────────────────────── */}
      {activeSession && !submitted && (
        <div className="fixed bottom-5 right-5 z-20 w-[min(92vw,380px)] animate-rise rounded-2xl border border-border bg-panel p-4 shadow-glow">
          <div className="flex items-center gap-2">
            <span className="relative flex h-2.5 w-2.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75" />
              <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-green-500" />
            </span>
            <p className="text-sm font-semibold">{activeSession.class_name}</p>
          </div>
          <p className="mt-1 text-xs text-muted">Tap below to submit attendance</p>
          <button
            type="button"
            onClick={() => void onMarkAttendance()}
            disabled={submitting || submitted}
            className="mt-3 w-full rounded-full bg-accent px-4 py-2 text-sm font-semibold text-accent-foreground disabled:opacity-70"
          >
            {submitting ? (
              <span className="flex items-center justify-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" /> Verifying…
              </span>
            ) : (
              "Mark Attendance"
            )}
          </button>
        </div>
      )}

      {/* ── Webcam column ────────────────────────────────────────────────────── */}
      <section className="space-y-4">
        <div>
          <h1 className="text-3xl font-bold">Student Attendance</h1>
          <p className="mt-1 text-muted">
            Keep your face in frame. When attendance opens, submit face + GPS in one tap.
          </p>
        </div>

        <WebcamFeed webcamRef={webcamRef} />

        <div className="flex flex-wrap gap-3">
          {!submitted ? (
            <button
              type="button"
              onClick={() => void onMarkAttendance()}
              disabled={!activeSession || submitting || loadingSession}
              className="rounded-full bg-accent px-5 py-2.5 font-semibold text-accent-foreground disabled:opacity-60"
            >
              {submitting ? (
                <span className="flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" /> Verifying…
                </span>
              ) : loadingSession ? (
                "Connecting…"
              ) : activeSession ? (
                "Mark Attendance"
              ) : (
                "Waiting for Session"
              )}
            </button>
          ) : (
            <div className="flex items-center gap-2 rounded-full bg-green-500/10 px-5 py-2.5 font-semibold text-green-600 dark:text-green-400">
              <CheckCircle className="h-5 w-5" />
              Attendance Submitted
            </div>
          )}

          {(errorCode || (statusType === "error" && !submitted)) && (
            <button
              type="button"
              onClick={onRetry}
              className="flex items-center gap-2 rounded-full border border-border px-4 py-2 text-sm"
            >
              <RefreshCw className="h-4 w-4" /> Try Again
            </button>
          )}
        </div>

        {/* ── Session info card ─────────────────────────────────────────────── */}
        {activeSession && (
          <div className="rounded-xl border border-border p-4 text-sm">
            <div className="flex items-center gap-2">
              <Wifi className="h-4 w-4 text-green-500" />
              <span className="font-semibold">Live Session</span>
            </div>
            <div className="mt-2 grid grid-cols-2 gap-1 text-muted">
              <span>Class:</span>
              <span className="font-medium text-[var(--text)]">{activeSession.class_name}</span>
              <span>Radius:</span>
              <span className="font-medium text-[var(--text)]">{activeSession.radius_meters}m</span>
              <span>Started:</span>
              <span className="font-medium text-[var(--text)]">{new Date(activeSession.start_time).toLocaleTimeString()}</span>
            </div>
          </div>
        )}
      </section>

      {/* ── Status / result column ───────────────────────────────────────────── */}
      <section className="space-y-4 rounded-2xl border border-border bg-panel p-5">
        <h2 className="text-xl font-semibold">Status</h2>

        <StatusPill type={statusType} message={statusMessage} />

        {attendanceRecord && (
          <div className="space-y-3 rounded-xl border border-border p-4 text-sm">
            <p className="font-semibold text-base">{attendanceRecord.user_name}</p>
            <div className="grid grid-cols-[auto,1fr] gap-x-3 gap-y-1 text-muted">
              <span>Email</span>
              <span className="text-[var(--text)]">{attendanceRecord.email}</span>
              <span>Status</span>
              <span
                className={`font-semibold ${
                  attendanceRecord.status === "present" ? "status-ok" : "status-warn"
                }`}
              >
                {attendanceRecord.status === "present" ? "✅ Present" : "❌ Denied"}
              </span>
              {attendanceRecord.distance != null && (
                <>
                  <span className="flex items-center gap-1">
                    <MapPin className="h-3.5 w-3.5" /> Distance
                  </span>
                  <span className="text-[var(--text)]">{attendanceRecord.distance.toFixed(1)}m from classroom</span>
                </>
              )}
              <span>
                <Clock className="inline h-3.5 w-3.5 mr-1" />
                Time
              </span>
              <span className="text-[var(--text)]">
                {new Date(attendanceRecord.timestamp).toLocaleTimeString()}
              </span>
            </div>
          </div>
        )}

        {!attendanceRecord && (
          <p className="text-sm text-muted">No attendance submission yet this session.</p>
        )}
      </section>
    </div>
  );
}

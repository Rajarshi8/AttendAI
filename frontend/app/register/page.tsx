"use client";

import Image from "next/image";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import Webcam from "react-webcam";
import { Camera, CheckCircle, Loader2, RotateCcw, User } from "lucide-react";

import { WebcamFeed } from "@/components/WebcamFeed";
import { getCurrentUser } from "@/lib/appwrite";
import { registerUser } from "@/lib/api";

const MIN_SAMPLES = 10;
const MAX_SAMPLES = 20;

export default function RegisterPage() {
  const webcamRef = useRef<Webcam | null>(null);

  const [samples, setSamples] = useState<string[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isAutoCapturing, setIsAutoCapturing] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [identity, setIdentity] = useState<{ name: string; email: string } | null>(null);
  const [registered, setRegistered] = useState(false);

  useEffect(() => {
    void (async () => {
      const user = await getCurrentUser();
      if (!user) return;
      setIdentity({ name: user.name || "", email: user.email || "" });
    })();
  }, []);

  const canSubmit = useMemo(() => samples.length >= MIN_SAMPLES, [samples.length]);
  const progress = Math.min((samples.length / MAX_SAMPLES) * 100, 100);

  // ── Manual capture ────────────────────────────────────────────────────────────

  const captureSample = () => {
    setError(null);
    const image = webcamRef.current?.getScreenshot();
    if (!image) {
      setError("Could not capture image. Check webcam permissions.");
      return;
    }
    setSamples((prev) => {
      if (prev.length >= MAX_SAMPLES) return prev;
      return [...prev, image];
    });
  };

  // ── Auto-capture burst ────────────────────────────────────────────────────────

  const startAutoBurst = async () => {
    if (isAutoCapturing) return;
    setError(null);
    setIsAutoCapturing(true);

    const needed = MAX_SAMPLES - samples.length;
    const captured: string[] = [];

    for (let i = 0; i < needed; i++) {
      const img = webcamRef.current?.getScreenshot();
      if (img) captured.push(img);
      await new Promise((r) => setTimeout(r, 200));
    }

    setSamples((prev) => [...prev, ...captured].slice(0, MAX_SAMPLES));
    setIsAutoCapturing(false);
  };

  // ── Reset ─────────────────────────────────────────────────────────────────────

  const resetSamples = () => {
    setSamples([]);
    setMessage(null);
    setError(null);
    setRegistered(false);
  };

  // ── Submit ────────────────────────────────────────────────────────────────────

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!canSubmit || registered) return;

    setIsSubmitting(true);
    setError(null);
    setMessage(null);

    try {
      await registerUser({ images: samples });
      setRegistered(true);
      setMessage("Face registered successfully! Your embedding is ready for attendance.");
      setSamples([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[1.2fr,1fr]">
      {/* ── Left: Webcam + capture ─────────────────────────────────────────────── */}
      <section className="space-y-4">
        <div>
          <h1 className="text-3xl font-bold">Register Face</h1>
          <p className="mt-1 text-muted">
            Capture {MIN_SAMPLES}–{MAX_SAMPLES} clear face images from different slight angles.
            The backend creates an averaged embedding for robust recognition.
          </p>
        </div>

        <WebcamFeed webcamRef={webcamRef} />

        {/* Progress bar */}
        <div className="space-y-1.5">
          <div className="flex justify-between text-xs text-muted">
            <span>Samples captured</span>
            <span className={samples.length >= MIN_SAMPLES ? "status-ok font-semibold" : ""}>
              {samples.length} / {MAX_SAMPLES}
            </span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-[var(--border)]">
            <div
              className="h-full rounded-full bg-accent transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
          {samples.length >= MIN_SAMPLES && samples.length < MAX_SAMPLES && (
            <p className="text-xs text-muted">
              Minimum reached ✓ — capture more for better accuracy.
            </p>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={captureSample}
            type="button"
            disabled={samples.length >= MAX_SAMPLES || isAutoCapturing}
            className="flex items-center gap-2 rounded-full bg-accent px-5 py-2.5 font-semibold text-accent-foreground disabled:opacity-60"
          >
            <Camera className="h-4 w-4" />
            Capture Sample
          </button>

          <button
            onClick={() => void startAutoBurst()}
            type="button"
            disabled={samples.length >= MAX_SAMPLES || isAutoCapturing}
            className="flex items-center gap-2 rounded-full border border-border px-4 py-2 disabled:opacity-60"
          >
            {isAutoCapturing ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" /> Capturing…
              </>
            ) : (
              <>
                <Camera className="h-4 w-4" /> Auto-Burst
              </>
            )}
          </button>

          <button
            onClick={resetSamples}
            type="button"
            className="flex items-center gap-2 rounded-full border border-border px-4 py-2"
          >
            <RotateCcw className="h-4 w-4" /> Reset
          </button>
        </div>

        {/* Sample thumbnails */}
        {samples.length > 0 && (
          <div className="grid grid-cols-5 gap-2">
            {samples.slice(0, 10).map((sample, index) => (
              <Image
                key={index}
                src={sample}
                alt={`Sample ${index + 1}`}
                width={80}
                height={64}
                unoptimized
                className="h-16 w-full rounded-md object-cover ring-1 ring-border"
              />
            ))}
          </div>
        )}
      </section>

      {/* ── Right: Profile + submit ────────────────────────────────────────────── */}
      <section className="rounded-2xl border border-border bg-panel p-5">
        <h2 className="text-xl font-semibold">Profile</h2>

        {identity ? (
          <div className="mt-3 flex items-center gap-3 rounded-xl border border-border p-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-accent/10">
              <User className="h-5 w-5 text-accent" />
            </div>
            <div>
              <p className="font-semibold">{identity.name || "Authenticated User"}</p>
              <p className="text-sm text-muted">{identity.email}</p>
            </div>
          </div>
        ) : (
          <p className="mt-3 text-sm status-warn">
            No active session found. Please log in from the Dashboard first.
          </p>
        )}

        <form onSubmit={handleSubmit} className="mt-5 space-y-4">
          {/* Sample count feedback */}
          <div className="rounded-xl border border-border p-3 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-muted">Samples ready</span>
              <span className={canSubmit ? "status-ok font-semibold" : "text-muted"}>
                {samples.length} / {MIN_SAMPLES} minimum
              </span>
            </div>
            {!canSubmit && (
              <p className="mt-1 text-xs text-muted">
                Capture {MIN_SAMPLES - samples.length} more sample{MIN_SAMPLES - samples.length !== 1 ? "s" : ""} to
                continue.
              </p>
            )}
          </div>

          {registered ? (
            <div className="flex items-center gap-2 rounded-xl border border-green-500/30 bg-green-500/10 p-3 text-sm text-green-600 dark:text-green-400">
              <CheckCircle className="h-5 w-5 shrink-0" />
              <span>Registration complete! You can now mark attendance.</span>
            </div>
          ) : (
            <button
              type="submit"
              disabled={!canSubmit || isSubmitting || !identity}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-accent px-4 py-2.5 font-semibold text-accent-foreground disabled:cursor-not-allowed disabled:opacity-70"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" /> Registering…
                </>
              ) : (
                "Register Face"
              )}
            </button>
          )}
        </form>

        {message && <p className="mt-3 text-sm status-ok">{message}</p>}
        {error && <p className="mt-3 text-sm status-warn">{error}</p>}

        <div className="mt-6 border-t border-border pt-4 text-xs text-muted space-y-1">
          <p>💡 <strong>Tips for best accuracy:</strong></p>
          <p>• Ensure good, even lighting on your face</p>
          <p>• Slightly vary head angle between captures</p>
          <p>• Avoid sunglasses or heavy filters</p>
          <p>• Stay within 60cm of the camera</p>
        </div>
      </section>
    </div>
  );
}

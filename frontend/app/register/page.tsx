"use client";

import Image from "next/image";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import Webcam from "react-webcam";

import { WebcamFeed } from "@/components/WebcamFeed";
import { getCurrentUser } from "@/lib/appwrite";
import { registerUser } from "@/lib/api";

export default function RegisterPage() {
  const webcamRef = useRef<Webcam | null>(null);

  const [samples, setSamples] = useState<string[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [identity, setIdentity] = useState<{ name: string; email: string } | null>(null);

  useEffect(() => {
    void (async () => {
      const user = await getCurrentUser();
      if (!user) {
        setIdentity(null);
        return;
      }
      setIdentity({
        name: user.name || "",
        email: user.email || "",
      });
    })();
  }, []);

  const canSubmit = useMemo(() => {
    return samples.length >= 10;
  }, [samples.length]);

  const captureSample = () => {
    setError(null);
    const image = webcamRef.current?.getScreenshot();
    if (!image) {
      setError("Could not capture image. Check webcam permissions.");
      return;
    }

    setSamples((prev) => {
      if (prev.length >= 20) return prev;
      return [...prev, image];
    });
  };

  const resetSamples = () => {
    setSamples([]);
    setMessage(null);
    setError(null);
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!canSubmit) return;

    setIsSubmitting(true);
    setError(null);
    setMessage(null);

    try {
      await registerUser({
        images: samples,
      });

      setMessage("User registered successfully with averaged face embedding.");
      setSamples([]);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Registration failed.";
      setError(errorMessage);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[1.2fr,1fr]">
      <section className="space-y-4">
        <h1 className="text-3xl font-bold">Register User</h1>
        <p className="text-muted">Capture 10 to 20 clear face images. The backend creates an averaged embedding for robust recognition.</p>
        <WebcamFeed webcamRef={webcamRef} />

        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={captureSample}
            type="button"
            className="rounded-full bg-accent px-5 py-2.5 font-semibold text-accent-foreground disabled:opacity-60"
            disabled={samples.length >= 20}
          >
            Capture Sample ({samples.length}/20)
          </button>
          <button onClick={resetSamples} type="button" className="rounded-full border border-border px-4 py-2">
            Reset Samples
          </button>
        </div>

        <div className="grid grid-cols-5 gap-2">
          {samples.slice(0, 10).map((sample, index) => (
            <Image
              key={index}
              src={sample}
              alt={`Sample ${index + 1}`}
              width={80}
              height={64}
              unoptimized
              className="h-16 w-full rounded-md object-cover"
            />
          ))}
        </div>
      </section>

      <section className="rounded-2xl border border-border bg-panel p-5">
        <h2 className="text-xl font-semibold">Profile Details</h2>
        {identity ? (
          <p className="mt-2 text-sm text-muted">
            Registering as {identity.name || "Authenticated User"} ({identity.email})
          </p>
        ) : (
          <p className="mt-2 text-sm status-warn">No active Appwrite session found. Login from Dashboard first.</p>
        )}
        <form onSubmit={handleSubmit} className="mt-4 space-y-3">
          <button
            type="submit"
            disabled={!canSubmit || isSubmitting || !identity}
            className="w-full rounded-xl bg-accent px-4 py-2.5 font-semibold text-accent-foreground disabled:cursor-not-allowed disabled:opacity-70"
          >
            {isSubmitting ? "Registering..." : "Register User"}
          </button>
        </form>

        {message && <p className="mt-3 text-sm status-ok">{message}</p>}
        {error && <p className="mt-3 text-sm status-warn">{error}</p>}
      </section>
    </div>
  );
}

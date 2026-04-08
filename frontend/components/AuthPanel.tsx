"use client";

import { FormEvent, useEffect, useState } from "react";

import { getCurrentUser, login, logout, signup } from "@/lib/appwrite";

export function AuthPanel() {
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [userName, setUserName] = useState<string | null>(null);

  useEffect(() => {
    void refreshUser();
  }, []);

  async function refreshUser() {
    const currentUser = await getCurrentUser();
    setUserName(currentUser?.name || currentUser?.email || null);
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setStatus(null);

    try {
      if (mode === "signup") {
        await signup(email.trim(), password, name.trim());
        setStatus("Account created and logged in.");
      } else {
        await login(email.trim(), password);
        setStatus("Logged in successfully.");
      }
      setPassword("");
      await refreshUser();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Authentication failed.";
      setStatus(message);
    } finally {
      setLoading(false);
    }
  }

  async function handleLogout() {
    setLoading(true);
    setStatus(null);

    try {
      await logout();
      setUserName(null);
      setStatus("Logged out.");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Logout failed.";
      setStatus(message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="rounded-2xl border border-border bg-panel p-5">
      <h2 className="text-xl font-semibold">Appwrite Authentication</h2>
      <p className="mt-2 text-sm text-muted">Login is required for register, recognize, and attendance APIs.</p>

      {userName ? (
        <div className="mt-4 space-y-3">
          <p className="text-sm">Signed in as <span className="font-semibold">{userName}</span></p>
          <button
            type="button"
            onClick={() => void handleLogout()}
            className="rounded-full border border-border px-4 py-2 text-sm"
            disabled={loading}
          >
            Logout
          </button>
        </div>
      ) : (
        <form onSubmit={onSubmit} className="mt-4 space-y-3">
          <div className="inline-flex rounded-full border border-border p-1">
            <button
              type="button"
              onClick={() => setMode("login")}
              className={`rounded-full px-3 py-1 text-sm ${mode === "login" ? "bg-accent text-accent-foreground" : "text-muted"}`}
            >
              Login
            </button>
            <button
              type="button"
              onClick={() => setMode("signup")}
              className={`rounded-full px-3 py-1 text-sm ${mode === "signup" ? "bg-accent text-accent-foreground" : "text-muted"}`}
            >
              Signup
            </button>
          </div>

          {mode === "signup" && (
            <input
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="Full name"
              className="w-full rounded-xl border border-border bg-transparent px-3 py-2 outline-none"
              required
            />
          )}

          <input
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="Email"
            className="w-full rounded-xl border border-border bg-transparent px-3 py-2 outline-none"
            required
          />

          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Password"
            className="w-full rounded-xl border border-border bg-transparent px-3 py-2 outline-none"
            required
            minLength={8}
          />

          <button
            type="submit"
            disabled={loading}
            className="rounded-full bg-accent px-4 py-2 text-sm font-semibold text-accent-foreground"
          >
            {loading ? "Please wait..." : mode === "signup" ? "Create account" : "Login"}
          </button>
        </form>
      )}

      {status && <p className="mt-3 text-sm text-muted">{status}</p>}
    </section>
  );
}

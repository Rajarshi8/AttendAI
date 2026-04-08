"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

import { downloadAttendanceCsv, getActiveSession, getAttendance, getCurrentProfile, startSession, stopSession } from "@/lib/api";
import { AttendanceRecord, CurrentUserProfile, SessionItem } from "@/types";

export default function AdminPage() {
  const [profile, setProfile] = useState<CurrentUserProfile | null>(null);
  const [activeSession, setActiveSession] = useState<SessionItem | null>(null);
  const [className, setClassName] = useState("Computer Networks");
  const [radiusMeters, setRadiusMeters] = useState(75);
  const [endTime, setEndTime] = useState("");
  const [adminMessage, setAdminMessage] = useState<string | null>(null);

  const [search, setSearch] = useState("");
  const [sessionFilter, setSessionFilter] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [records, setRecords] = useState<AttendanceRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async (filters: { search?: string; session_id?: string; start_date?: string; end_date?: string } = {}) => {
    setLoading(true);
    setError(null);

    try {
      const response = await getAttendance({
        search: filters.search || undefined,
        session_id: filters.session_id || undefined,
        start_date: filters.start_date || undefined,
        end_date: filters.end_date || undefined,
        limit: 200,
      });
      setRecords(response.items);
      setTotal(response.total);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Could not fetch attendance logs.";
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadSessionState = useCallback(async () => {
    try {
      const active = await getActiveSession();
      setActiveSession(active.session);
      setSessionFilter((prev) => prev || active.session?.session_id || "");
    } catch {
      setActiveSession(null);
    }
  }, []);

  useEffect(() => {
    void (async () => {
      try {
        const currentProfile = await getCurrentProfile();
        setProfile(currentProfile);
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : "Could not load profile.";
        setError(errorMessage);
      }

      await Promise.all([loadData({}), loadSessionState()]);
    })();
  }, [loadData, loadSessionState]);

  const onFilter = async (event: FormEvent) => {
    event.preventDefault();
    await loadData({
      search,
      session_id: sessionFilter,
      start_date: startDate,
      end_date: endDate,
    });
  };

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

  const onStartSession = async () => {
    setError(null);
    setAdminMessage(null);

    try {
      const position = await getCurrentPosition();
      const response = await startSession({
        class_name: className,
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
        radius_meters: radiusMeters,
        end_time: endTime ? new Date(endTime).toISOString() : undefined,
      });

      setActiveSession(response.session);
      setSessionFilter(response.session.session_id);
      setAdminMessage(response.message);
      await loadData({ search, session_id: response.session.session_id, start_date: startDate, end_date: endDate });
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Could not start attendance session.";
      setError(errorMessage);
    }
  };

  const onStopSession = async () => {
    if (!activeSession) return;

    setError(null);
    setAdminMessage(null);

    try {
      const response = await stopSession(activeSession.session_id);
      setActiveSession(response.session.is_active ? response.session : null);
      setAdminMessage(response.message);
      await loadData({ search, session_id: sessionFilter, start_date: startDate, end_date: endDate });
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Could not stop session.";
      setError(errorMessage);
    }
  };

  const onExportCsv = async () => {
    try {
      const blob = await downloadAttendanceCsv({
        search: search || undefined,
        session_id: sessionFilter || undefined,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
      });

      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "attendance_logs.csv";
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Could not export CSV.";
      setError(errorMessage);
    }
  };

  if (!profile) {
    return <p className="text-muted">Loading admin profile...</p>;
  }

  if (profile.role !== "admin") {
    return (
      <div className="rounded-2xl border border-border bg-panel p-5">
        <h1 className="text-2xl font-bold">Admin Access Required</h1>
        <p className="mt-2 text-muted">
          Your role is {profile.role}. Ask an existing administrator to set your user document role to admin in Appwrite.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Admin Panel</h1>
        <p className="mt-2 text-muted">Create attendance sessions with classroom geofence, then monitor logs and exports.</p>
      </div>

      <section className="grid gap-4 rounded-2xl border border-border bg-panel p-4 md:grid-cols-2">
        <div className="space-y-3">
          <h2 className="text-xl font-semibold">Attendance Session Control</h2>

          <label className="block text-sm text-muted">Class name</label>
          <input
            value={className}
            onChange={(e) => setClassName(e.target.value)}
            className="w-full rounded-xl border border-border bg-transparent px-3 py-2 outline-none"
            placeholder="Enter class name"
          />

          <label className="block text-sm text-muted">Radius (meters)</label>
          <input
            type="number"
            min={10}
            max={500}
            value={radiusMeters}
            onChange={(e) => setRadiusMeters(Number(e.target.value))}
            className="w-full rounded-xl border border-border bg-transparent px-3 py-2 outline-none"
          />

          <label className="block text-sm text-muted">Optional end time</label>
          <input
            type="datetime-local"
            value={endTime}
            onChange={(e) => setEndTime(e.target.value)}
            className="w-full rounded-xl border border-border bg-transparent px-3 py-2 outline-none"
          />

          <div className="flex flex-wrap gap-2">
            <button type="button" onClick={() => void onStartSession()} className="rounded-full bg-accent px-4 py-2 font-semibold text-accent-foreground">
              Start Attendance
            </button>
            <button
              type="button"
              onClick={() => void onStopSession()}
              disabled={!activeSession}
              className="rounded-full border border-border px-4 py-2 disabled:cursor-not-allowed disabled:opacity-60"
            >
              Stop Attendance
            </button>
          </div>
        </div>

        <div className="rounded-xl border border-border p-4">
          <h3 className="text-lg font-semibold">Live Session</h3>
          {activeSession ? (
            <div className="mt-2 space-y-1 text-sm">
              <p>
                Class: <span className="font-semibold">{activeSession.class_name}</span>
              </p>
              <p>Session ID: {activeSession.session_id}</p>
              <p>Radius: {activeSession.radius_meters}m</p>
              <p>Start: {new Date(activeSession.start_time).toLocaleString()}</p>
            </div>
          ) : (
            <p className="mt-2 text-sm text-muted">No active session.</p>
          )}

          {adminMessage && <p className="mt-3 text-sm status-ok">{adminMessage}</p>}
        </div>
      </section>

      <form onSubmit={onFilter} className="grid gap-3 rounded-2xl border border-border bg-panel p-4 md:grid-cols-4">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by name, email, ID"
          className="rounded-xl border border-border bg-transparent px-3 py-2 outline-none md:col-span-2"
        />
        <input
          value={sessionFilter}
          onChange={(e) => setSessionFilter(e.target.value)}
          placeholder="Filter by session ID"
          className="rounded-xl border border-border bg-transparent px-3 py-2 outline-none md:col-span-2"
        />
        <input
          type="date"
          value={startDate}
          onChange={(e) => setStartDate(e.target.value)}
          className="rounded-xl border border-border bg-transparent px-3 py-2 outline-none"
        />
        <input
          type="date"
          value={endDate}
          onChange={(e) => setEndDate(e.target.value)}
          className="rounded-xl border border-border bg-transparent px-3 py-2 outline-none"
        />

        <div className="flex flex-wrap gap-2 md:col-span-4">
          <button type="submit" className="rounded-full bg-accent px-4 py-2 font-semibold text-accent-foreground">
            {loading ? "Loading..." : "Apply Filters"}
          </button>
          <button
            type="button"
            onClick={() => {
              setSearch("");
              setSessionFilter(activeSession?.session_id || "");
              setStartDate("");
              setEndDate("");
              void loadData({ search: "", session_id: activeSession?.session_id || "", start_date: "", end_date: "" });
            }}
            className="rounded-full border border-border px-4 py-2"
          >
            Reset Filters
          </button>
          <button type="button" className="rounded-full border border-border px-4 py-2" onClick={() => void onExportCsv()}>
            Export CSV
          </button>
        </div>
      </form>

      {error && <p className="text-sm status-warn">{error}</p>}

      <div className="rounded-2xl border border-border bg-panel p-4">
        <p className="mb-3 text-sm text-muted">Total records: {total}</p>
        <div className="overflow-auto">
          <table className="min-w-full text-left text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="px-3 py-2">User</th>
                <th className="px-3 py-2">Session</th>
                <th className="px-3 py-2">ID</th>
                <th className="px-3 py-2">Email</th>
                <th className="px-3 py-2">Date</th>
                <th className="px-3 py-2">Timestamp</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2">Distance (m)</th>
              </tr>
            </thead>
            <tbody>
              {records.map((record) => (
                <tr key={record.id} className="border-b border-border/60">
                  <td className="px-3 py-2">{record.user_name}</td>
                  <td className="px-3 py-2">{record.session_id || "-"}</td>
                  <td className="px-3 py-2">{record.user_code}</td>
                  <td className="px-3 py-2">{record.email}</td>
                  <td className="px-3 py-2">{record.attendance_date}</td>
                  <td className="px-3 py-2">{new Date(record.timestamp).toLocaleString()}</td>
                  <td className="px-3 py-2">{record.status}</td>
                  <td className="px-3 py-2">{record.distance != null ? record.distance.toFixed(2) : "-"}</td>
                </tr>
              ))}
              {!records.length && (
                <tr>
                  <td className="px-3 py-4 text-muted" colSpan={8}>
                    No attendance records found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

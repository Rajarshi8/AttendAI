"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { Loader2, TrendingUp, Users, CheckCircle, XCircle, RefreshCw } from "lucide-react";

import {
  downloadAttendanceCsv,
  getActiveSession,
  getAttendance,
  getCurrentProfile,
  startSession,
  stopSession,
} from "@/lib/api";
import { subscribeToSessions } from "@/lib/appwrite";
import { AttendanceRecord, CurrentUserProfile, SessionItem } from "@/types";

// ─── Analytics types ──────────────────────────────────────────────────────────

interface AnalyticsSummary {
  total_students: number;
  present_count: number;
  denied_count: number;
  total_submissions: number;
  attendance_rate: number;
  by_session: { session_id: string; class_name: string; present: number; denied: number }[];
}

// ─── Stat card ────────────────────────────────────────────────────────────────

function StatCard({
  icon: Icon,
  label,
  value,
  color,
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  color: string;
}) {
  return (
    <div className="flex items-center gap-4 rounded-2xl border border-border bg-panel p-4">
      <div className={`rounded-xl p-2.5 ${color}`}>
        <Icon className="h-5 w-5" />
      </div>
      <div>
        <p className="text-xs uppercase tracking-wide text-muted">{label}</p>
        <p className="text-2xl font-bold">{value}</p>
      </div>
    </div>
  );
}

// ─── Colors ────────────────────────────────────────────────────────────────────

const CHART_COLORS = { present: "#22c55e", denied: "#f97316" };

// ─── Main component ────────────────────────────────────────────────────────────

export default function AdminPage() {
  const [profile, setProfile] = useState<CurrentUserProfile | null>(null);
  const [activeSession, setActiveSession] = useState<SessionItem | null>(null);
  const [className, setClassName] = useState("Computer Networks");
  const [radiusMeters, setRadiusMeters] = useState(75);
  const [endTime, setEndTime] = useState("");
  const [adminMessage, setAdminMessage] = useState<string | null>(null);
  const [sessionLoading, setSessionLoading] = useState(false);

  const [search, setSearch] = useState("");
  const [sessionFilter, setSessionFilter] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [records, setRecords] = useState<AttendanceRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [analytics, setAnalytics] = useState<AnalyticsSummary | null>(null);

  // ── Data fetching ────────────────────────────────────────────────────────────

  const loadData = useCallback(
    async (filters: { search?: string; session_id?: string; start_date?: string; end_date?: string } = {}) => {
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

        // Build client-side analytics from returned items
        const present = response.items.filter((r) => r.status === "present").length;
        const denied = response.items.filter((r) => r.status === "denied").length;
        const bySession: Record<string, { session_id: string; class_name: string; present: number; denied: number }> = {};
        for (const rec of response.items) {
          const sid = rec.session_id || "unknown";
          if (!bySession[sid]) {
            bySession[sid] = { session_id: sid, class_name: "", present: 0, denied: 0 };
          }
          if (rec.status === "present") bySession[sid].present++;
          else bySession[sid].denied++;
        }
        setAnalytics({
          total_students: response.total,
          present_count: present,
          denied_count: denied,
          total_submissions: response.items.length,
          attendance_rate: response.items.length > 0 ? Math.round((present / response.items.length) * 1000) / 10 : 0,
          by_session: Object.values(bySession).slice(0, 6),
        });
      } catch (err) {
        setError(err instanceof Error ? err.message : "Could not fetch attendance logs.");
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  const loadSessionState = useCallback(async () => {
    try {
      const active = await getActiveSession();
      setActiveSession(active.session);
      if (active.session) {
        setSessionFilter((prev) => prev || active.session?.session_id || "");
      }
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
        setError(err instanceof Error ? err.message : "Could not load profile.");
      }
      await Promise.all([loadData({}), loadSessionState()]);
    })();
  }, [loadData, loadSessionState]);

  // ── Realtime subscription ────────────────────────────────────────────────────

  useEffect(() => {
    const unsub = subscribeToSessions((event) => {
      const payload = event.payload as Record<string, unknown>;
      const isActive = Boolean(payload?.is_active);
      if (isActive) {
        const session: SessionItem = {
          session_id: String(payload.session_id || payload.$id || ""),
          admin_id: String(payload.admin_id || ""),
          class_name: String(payload.class_name || ""),
          start_time: String(payload.start_time || ""),
          end_time: payload.end_time ? String(payload.end_time) : null,
          latitude: Number(payload.latitude || 0),
          longitude: Number(payload.longitude || 0),
          radius_meters: Number(payload.radius_meters || 0),
          is_active: true,
        };
        setActiveSession(session);
      } else {
        setActiveSession(null);
      }
    });
    return unsub;
  }, []);

  // ── Session controls ─────────────────────────────────────────────────────────

  const getCurrentPosition = (): Promise<GeolocationPosition> =>
    new Promise((resolve, reject) => {
      if (!navigator.geolocation) {
        reject(new Error("Geolocation is not supported."));
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
    setSessionLoading(true);
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
      setError(err instanceof Error ? err.message : "Could not start attendance session.");
    } finally {
      setSessionLoading(false);
    }
  };

  const onStopSession = async () => {
    if (!activeSession) return;
    setError(null);
    setAdminMessage(null);
    setSessionLoading(true);
    try {
      const response = await stopSession(activeSession.session_id);
      setActiveSession(response.session.is_active ? response.session : null);
      setAdminMessage(response.message);
      await loadData({ search, session_id: sessionFilter, start_date: startDate, end_date: endDate });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not stop session.");
    } finally {
      setSessionLoading(false);
    }
  };

  const onFilter = async (event: FormEvent) => {
    event.preventDefault();
    await loadData({ search, session_id: sessionFilter, start_date: startDate, end_date: endDate });
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
      const a = document.createElement("a");
      a.href = url;
      a.download = "attendance_logs.csv";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not export CSV.");
    }
  };

  // ── Guards ────────────────────────────────────────────────────────────────────

  if (!profile) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <div className="flex flex-col items-center gap-3 text-muted">
          <Loader2 className="h-8 w-8 animate-spin" />
          <p className="text-sm">Loading admin profile…</p>
        </div>
      </div>
    );
  }

  if (profile.role !== "admin") {
    return (
      <div className="rounded-2xl border border-border bg-panel p-5">
        <h1 className="text-2xl font-bold">Admin Access Required</h1>
        <p className="mt-2 text-muted">
          Your role is <span className="font-semibold">{profile.role}</span>. Ask an existing
          administrator to set your user document role to admin in Appwrite.
        </p>
      </div>
    );
  }

  // ── Full render ───────────────────────────────────────────────────────────────

  const pieData = analytics
    ? [
        { name: "Present", value: analytics.present_count },
        { name: "Denied", value: analytics.denied_count },
      ]
    : [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Admin Panel</h1>
        <p className="mt-2 text-muted">
          Manage attendance sessions, monitor analytics, and export records.
        </p>
      </div>

      {/* ── Analytics cards ──────────────────────────────────────────────────── */}
      {analytics && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            icon={Users}
            label="Total Submissions"
            value={analytics.total_submissions}
            color="bg-blue-500/10 text-blue-500"
          />
          <StatCard
            icon={CheckCircle}
            label="Present"
            value={analytics.present_count}
            color="bg-green-500/10 text-green-500"
          />
          <StatCard
            icon={XCircle}
            label="Denied"
            value={analytics.denied_count}
            color="bg-orange-500/10 text-orange-500"
          />
          <StatCard
            icon={TrendingUp}
            label="Attendance Rate"
            value={`${analytics.attendance_rate}%`}
            color="bg-accent/10 text-accent"
          />
        </div>
      )}

      {/* ── Charts ───────────────────────────────────────────────────────────── */}
      {analytics && analytics.total_submissions > 0 && (
        <div className="grid gap-4 md:grid-cols-2">
          {/* Pie chart */}
          <div className="rounded-2xl border border-border bg-panel p-4">
            <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted">
              Overall Distribution
            </h3>
            <ResponsiveContainer width="100%" height={180}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={75}
                  paddingAngle={3}
                  dataKey="value"
                >
                  <Cell fill={CHART_COLORS.present} />
                  <Cell fill={CHART_COLORS.denied} />
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* Bar chart by session */}
          {analytics.by_session.length > 0 && (
            <div className="rounded-2xl border border-border bg-panel p-4">
              <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted">
                By Session
              </h3>
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={analytics.by_session} barSize={16}>
                  <XAxis
                    dataKey="class_name"
                    tick={{ fontSize: 11 }}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
                  <Tooltip />
                  <Bar dataKey="present" fill={CHART_COLORS.present} radius={[4, 4, 0, 0]} name="Present" />
                  <Bar dataKey="denied" fill={CHART_COLORS.denied} radius={[4, 4, 0, 0]} name="Denied" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}

      {/* ── Session controls ──────────────────────────────────────────────────── */}
      <section className="grid gap-4 rounded-2xl border border-border bg-panel p-4 md:grid-cols-2">
        <div className="space-y-3">
          <h2 className="text-xl font-semibold">Session Control</h2>

          <div>
            <label className="block text-sm text-muted">Class name</label>
            <input
              value={className}
              onChange={(e) => setClassName(e.target.value)}
              className="mt-1 w-full rounded-xl border border-border bg-transparent px-3 py-2 outline-none"
              placeholder="e.g. Computer Networks"
            />
          </div>

          <div>
            <label className="block text-sm text-muted">Radius (meters)</label>
            <input
              type="number"
              min={10}
              max={500}
              value={radiusMeters}
              onChange={(e) => setRadiusMeters(Number(e.target.value))}
              className="mt-1 w-full rounded-xl border border-border bg-transparent px-3 py-2 outline-none"
            />
          </div>

          <div>
            <label className="block text-sm text-muted">Optional end time</label>
            <input
              type="datetime-local"
              value={endTime}
              onChange={(e) => setEndTime(e.target.value)}
              className="mt-1 w-full rounded-xl border border-border bg-transparent px-3 py-2 outline-none"
            />
          </div>

          <div className="flex flex-wrap gap-2 pt-1">
            <button
              type="button"
              onClick={() => void onStartSession()}
              disabled={sessionLoading}
              className="flex items-center gap-2 rounded-full bg-accent px-4 py-2 font-semibold text-accent-foreground disabled:opacity-70"
            >
              {sessionLoading && !activeSession && <Loader2 className="h-4 w-4 animate-spin" />}
              Start Attendance
            </button>
            <button
              type="button"
              onClick={() => void onStopSession()}
              disabled={!activeSession || sessionLoading}
              className="rounded-full border border-border px-4 py-2 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {sessionLoading && activeSession ? (
                <span className="flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" /> Stopping…
                </span>
              ) : (
                "Stop Attendance"
              )}
            </button>
          </div>
        </div>

        {/* Live session status */}
        <div className="rounded-xl border border-border p-4">
          <h3 className="text-lg font-semibold">Live Session</h3>
          {activeSession ? (
            <div className="mt-2 space-y-2">
              <div className="flex items-center gap-2">
                <span className="relative flex h-2.5 w-2.5">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75" />
                  <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-green-500" />
                </span>
                <span className="font-semibold text-green-600 dark:text-green-400">Active</span>
              </div>
              <div className="grid grid-cols-[auto,1fr] gap-x-3 gap-y-1 text-sm text-muted">
                <span>Class:</span>
                <span className="font-medium text-[var(--text)]">{activeSession.class_name}</span>
                <span>ID:</span>
                <span className="truncate font-mono text-xs text-[var(--text)]">{activeSession.session_id}</span>
                <span>Radius:</span>
                <span className="text-[var(--text)]">{activeSession.radius_meters}m</span>
                <span>Start:</span>
                <span className="text-[var(--text)]">{new Date(activeSession.start_time).toLocaleTimeString()}</span>
              </div>
            </div>
          ) : (
            <p className="mt-2 text-sm text-muted">No active session.</p>
          )}
          {adminMessage && <p className="mt-3 text-sm status-ok">{adminMessage}</p>}
        </div>
      </section>

      {/* ── Filters ───────────────────────────────────────────────────────────── */}
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
          <button
            type="submit"
            className="flex items-center gap-2 rounded-full bg-accent px-4 py-2 font-semibold text-accent-foreground"
          >
            {loading && <Loader2 className="h-4 w-4 animate-spin" />}
            Apply Filters
          </button>
          <button
            type="button"
            onClick={() => {
              setSearch("");
              setSessionFilter(activeSession?.session_id || "");
              setStartDate("");
              setEndDate("");
              void loadData({ session_id: activeSession?.session_id || "" });
            }}
            className="flex items-center gap-2 rounded-full border border-border px-4 py-2"
          >
            <RefreshCw className="h-4 w-4" /> Reset
          </button>
          <button
            type="button"
            onClick={() => void onExportCsv()}
            className="rounded-full border border-border px-4 py-2"
          >
            Export CSV
          </button>
        </div>
      </form>

      {error && <p className="text-sm status-warn">{error}</p>}

      {/* ── Records table ─────────────────────────────────────────────────────── */}
      <div className="rounded-2xl border border-border bg-panel p-4">
        <p className="mb-3 text-sm text-muted">
          Total records: <span className="font-semibold text-[var(--text)]">{total}</span>
        </p>
        <div className="overflow-auto">
          <table className="min-w-full text-left text-sm">
            <thead>
              <tr className="border-b border-border">
                {["User", "Session", "Email", "Date", "Time", "Status", "Distance"].map((h) => (
                  <th key={h} className="px-3 py-2 font-semibold text-muted">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {records.map((record) => (
                <tr key={record.id} className="border-b border-border/50 hover:bg-[var(--bg-soft)]/40">
                  <td className="px-3 py-2 font-medium">{record.user_name}</td>
                  <td className="px-3 py-2 font-mono text-xs text-muted">{record.session_id?.slice(0, 12) || "—"}</td>
                  <td className="px-3 py-2 text-muted">{record.email}</td>
                  <td className="px-3 py-2">{record.attendance_date}</td>
                  <td className="px-3 py-2">{new Date(record.timestamp).toLocaleTimeString()}</td>
                  <td className="px-3 py-2">
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
                        record.status === "present"
                          ? "bg-green-500/10 text-green-600 dark:text-green-400"
                          : "bg-orange-500/10 text-orange-600 dark:text-orange-400"
                      }`}
                    >
                      {record.status}
                    </span>
                  </td>
                  <td className="px-3 py-2">
                    {record.distance != null ? `${record.distance.toFixed(1)}m` : "—"}
                  </td>
                </tr>
              ))}
              {!records.length && (
                <tr>
                  <td className="px-3 py-8 text-center text-muted" colSpan={7}>
                    {loading ? (
                      <div className="flex items-center justify-center gap-2">
                        <Loader2 className="h-4 w-4 animate-spin" /> Loading records…
                      </div>
                    ) : (
                      "No attendance records found."
                    )}
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

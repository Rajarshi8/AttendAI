"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

import { downloadAttendanceCsv, getAttendance } from "@/lib/api";
import { AttendanceRecord } from "@/types";

export default function AdminPage() {
  const [search, setSearch] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [records, setRecords] = useState<AttendanceRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async (filters: { search?: string; start_date?: string; end_date?: string } = {}) => {
    setLoading(true);
    setError(null);

    try {
      const response = await getAttendance({
        search: filters.search || undefined,
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

  useEffect(() => {
    void loadData({});
  }, [loadData]);

  const onFilter = async (event: FormEvent) => {
    event.preventDefault();
    await loadData({
      search,
      start_date: startDate,
      end_date: endDate,
    });
  };

  const onExportCsv = async () => {
    try {
      const blob = await downloadAttendanceCsv({
        search: search || undefined,
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

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Admin Panel</h1>
        <p className="mt-2 text-muted">Search and filter attendance logs, then export CSV for reporting.</p>
      </div>

      <form onSubmit={onFilter} className="grid gap-3 rounded-2xl border border-border bg-panel p-4 md:grid-cols-4">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by name, email, ID"
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
              setStartDate("");
              setEndDate("");
              void loadData({ search: "", start_date: "", end_date: "" });
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
                <th className="px-3 py-2">ID</th>
                <th className="px-3 py-2">Email</th>
                <th className="px-3 py-2">Date</th>
                <th className="px-3 py-2">Timestamp</th>
                <th className="px-3 py-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {records.map((record) => (
                <tr key={record.id} className="border-b border-border/60">
                  <td className="px-3 py-2">{record.user_name}</td>
                  <td className="px-3 py-2">{record.user_code}</td>
                  <td className="px-3 py-2">{record.email}</td>
                  <td className="px-3 py-2">{record.attendance_date}</td>
                  <td className="px-3 py-2">{new Date(record.timestamp).toLocaleString()}</td>
                  <td className="px-3 py-2">{record.status}</td>
                </tr>
              ))}
              {!records.length && (
                <tr>
                  <td className="px-3 py-4 text-muted" colSpan={6}>
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

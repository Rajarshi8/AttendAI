import { AttendanceListResponse, AttendanceMarkResponse, RecognizeResult, RegisterResponse } from "@/types";
import { getAuthJwt } from "@/lib/appwrite";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const jwt = await getAuthJwt();
  if (!jwt) {
    throw new Error("Authentication required. Please login first.");
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${jwt}`,
      ...(options?.headers || {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    let message = "Request failed";
    try {
      const payload = await response.json();
      message = payload.detail || message;
    } catch {
      // Keep fallback message for non-JSON responses.
    }
    throw new Error(message);
  }

  return (await response.json()) as T;
}

export function registerUser(payload: {
  images: string[];
  name?: string;
  email?: string;
  user_id?: string;
}) {
  return request<RegisterResponse>("/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function recognizeUser(payload: {
  frame?: string;
  frames?: string[];
  threshold?: number;
  require_liveness?: boolean;
}) {
  return request<RecognizeResult>("/recognize", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function markAttendance(payload?: { status?: string }) {
  const requestBody = { status: payload?.status || "present" };
  return request<AttendanceMarkResponse>("/attendance", {
    method: "POST",
    body: JSON.stringify(requestBody),
  });
}

export function getAttendance(params: {
  search?: string;
  start_date?: string;
  end_date?: string;
  limit?: number;
  offset?: number;
}) {
  const query = new URLSearchParams();
  if (params.search) query.set("search", params.search);
  if (params.start_date) query.set("start_date", params.start_date);
  if (params.end_date) query.set("end_date", params.end_date);
  query.set("limit", String(params.limit ?? 100));
  query.set("offset", String(params.offset ?? 0));

  return request<AttendanceListResponse>(`/attendance?${query.toString()}`);
}

export function getAttendanceCsvUrl(params: {
  search?: string;
  start_date?: string;
  end_date?: string;
}) {
  const query = new URLSearchParams();
  if (params.search) query.set("search", params.search);
  if (params.start_date) query.set("start_date", params.start_date);
  if (params.end_date) query.set("end_date", params.end_date);

  return `${API_BASE}/attendance/export?${query.toString()}`;
}

export async function downloadAttendanceCsv(params: {
  search?: string;
  start_date?: string;
  end_date?: string;
}) {
  const jwt = await getAuthJwt();
  if (!jwt) {
    throw new Error("Authentication required. Please login first.");
  }

  const query = new URLSearchParams();
  if (params.search) query.set("search", params.search);
  if (params.start_date) query.set("start_date", params.start_date);
  if (params.end_date) query.set("end_date", params.end_date);

  const response = await fetch(`${API_BASE}/attendance/export?${query.toString()}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${jwt}`,
    },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error("Failed to download attendance CSV.");
  }

  return response.blob();
}

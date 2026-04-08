import {
  ActiveSessionResponse,
  AttendanceListResponse,
  AttendanceMarkResponse,
  CurrentUserProfile,
  RecognizeResult,
  RegisterResponse,
  SessionItem,
  SessionStartResponse,
  SessionStopResponse,
} from "@/types";
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

export function markAttendance(payload?: {
  session_id: string;
  frame?: string;
  frames?: string[];
  latitude: number;
  longitude: number;
  threshold?: number;
  require_liveness?: boolean;
}) {
  const requestBody = {
    session_id: payload?.session_id,
    frame: payload?.frame,
    frames: payload?.frames || [],
    latitude: payload?.latitude,
    longitude: payload?.longitude,
    threshold: payload?.threshold,
    require_liveness: payload?.require_liveness ?? true,
  };

  return request<AttendanceMarkResponse>("/attendance", {
    method: "POST",
    body: JSON.stringify(requestBody),
  });
}

export function getCurrentProfile() {
  return request<CurrentUserProfile>("/users/me", {
    method: "GET",
  });
}

export function startSession(payload: {
  class_name: string;
  latitude: number;
  longitude: number;
  radius_meters: number;
  end_time?: string;
}) {
  return request<SessionStartResponse>("/sessions/start", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function stopSession(session_id: string) {
  return request<SessionStopResponse>("/sessions/stop", {
    method: "POST",
    body: JSON.stringify({ session_id }),
  });
}

export function getActiveSession() {
  return request<ActiveSessionResponse>("/sessions/active", {
    method: "GET",
  });
}

export function listSessions(params?: { mine?: boolean; limit?: number }) {
  const query = new URLSearchParams();
  if (params?.mine !== undefined) query.set("mine", String(params.mine));
  query.set("limit", String(params?.limit ?? 100));

  return request<SessionItem[]>(`/sessions?${query.toString()}`, {
    method: "GET",
  });
}

export function getAttendance(params: {
  search?: string;
  session_id?: string;
  start_date?: string;
  end_date?: string;
  limit?: number;
  offset?: number;
}) {
  const query = new URLSearchParams();
  if (params.search) query.set("search", params.search);
  if (params.session_id) query.set("session_id", params.session_id);
  if (params.start_date) query.set("start_date", params.start_date);
  if (params.end_date) query.set("end_date", params.end_date);
  query.set("limit", String(params.limit ?? 100));
  query.set("offset", String(params.offset ?? 0));

  return request<AttendanceListResponse>(`/attendance?${query.toString()}`);
}

export function getAttendanceCsvUrl(params: {
  search?: string;
  session_id?: string;
  start_date?: string;
  end_date?: string;
}) {
  const query = new URLSearchParams();
  if (params.search) query.set("search", params.search);
  if (params.session_id) query.set("session_id", params.session_id);
  if (params.start_date) query.set("start_date", params.start_date);
  if (params.end_date) query.set("end_date", params.end_date);

  return `${API_BASE}/attendance/export?${query.toString()}`;
}

export async function downloadAttendanceCsv(params: {
  search?: string;
  session_id?: string;
  start_date?: string;
  end_date?: string;
}) {
  const jwt = await getAuthJwt();
  if (!jwt) {
    throw new Error("Authentication required. Please login first.");
  }

  const query = new URLSearchParams();
  if (params.search) query.set("search", params.search);
  if (params.session_id) query.set("session_id", params.session_id);
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

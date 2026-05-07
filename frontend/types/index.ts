export type UserRole = "admin" | "student";

export interface UserProfile {
  id: string;
  user_id: string;
  name: string;
  email: string;
}

export interface CurrentUserProfile {
  user_id: string;
  name: string;
  email: string;
  role: UserRole;
  has_embedding: boolean;
}

export interface SessionItem {
  session_id: string;
  admin_id: string;
  class_name: string;
  start_time: string;
  end_time: string | null;
  latitude: number;
  longitude: number;
  radius_meters: number;
  is_active: boolean;
}

export interface ActiveSessionResponse {
  session: SessionItem | null;
}

export interface SessionStartResponse {
  message: string;
  session: SessionItem;
}

export interface SessionStopResponse {
  message: string;
  session: SessionItem;
}

export interface RecognizeResult {
  matched: boolean;
  live: boolean;
  similarity: number | null;
  user: UserProfile | null;
  message: string;
  error_code?: string | null;
}

export interface AttendanceRecord {
  id: string;
  user_id: string;
  session_id: string | null;
  user_name: string;
  user_code: string;
  email: string;
  status: string;
  distance: number | null;
  timestamp: string;
  attendance_date: string;
}

export interface AttendanceListResponse {
  total: number;
  limit: number;
  offset: number;
  items: AttendanceRecord[];
}

export interface AttendanceAnalyticsResponse {
  total_students: number;
  present_count: number;
  denied_count: number;
  total_submissions: number;
  attendance_rate: number;
  average_distance: number;
  by_session: { session_id: string; class_name: string; present: number; denied: number }[];
}

export interface AttendanceMarkResponse {
  marked: boolean;
  message: string;
  /** Machine-readable error code for contextual UI messages */
  error_code?: string | null;
  record: AttendanceRecord | null;
}

export interface RegisterResponse {
  id: string;
  name: string;
  email: string;
  user_id: string;
  role: UserRole;
  face_samples: number;
}

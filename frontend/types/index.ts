export interface UserProfile {
  id: string;
  user_id: string;
  name: string;
  email: string;
}

export interface RecognizeResult {
  matched: boolean;
  live: boolean;
  similarity: number | null;
  user: UserProfile | null;
  message: string;
}

export interface AttendanceRecord {
  id: string;
  user_id: string;
  user_name: string;
  user_code: string;
  email: string;
  status: string;
  timestamp: string;
  attendance_date: string;
}

export interface AttendanceListResponse {
  total: number;
  limit: number;
  offset: number;
  items: AttendanceRecord[];
}

export interface AttendanceMarkResponse {
  marked: boolean;
  message: string;
  record: AttendanceRecord | null;
}

export interface RegisterResponse {
  id: number;
  name: string;
  email: string;
  user_id: string;
  face_samples: number;
}

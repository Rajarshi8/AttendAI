CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    user_code VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(120) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    embedding JSON NOT NULL,
    face_samples INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS attendance (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(30) NOT NULL DEFAULT 'present',
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    attendance_date DATE NOT NULL DEFAULT CURRENT_DATE,
    CONSTRAINT uq_attendance_user_day UNIQUE (user_id, attendance_date)
);

CREATE INDEX IF NOT EXISTS ix_users_email ON users(email);
CREATE INDEX IF NOT EXISTS ix_users_user_code ON users(user_code);
CREATE INDEX IF NOT EXISTS ix_attendance_user_id ON attendance(user_id);
CREATE INDEX IF NOT EXISTS ix_attendance_date ON attendance(attendance_date);

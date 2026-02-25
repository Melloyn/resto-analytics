import sqlite3

class SQLiteUserRepository:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def init_auth_db(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name TEXT NOT NULL,
                    login TEXT NOT NULL UNIQUE,
                    email TEXT NOT NULL UNIQUE,
                    phone TEXT NOT NULL,
                    password_salt TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user',
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    ua_hash TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS login_attempts (
                    login TEXT PRIMARY KEY,
                    attempts INTEGER DEFAULT 0,
                    last_attempt TEXT NOT NULL
                )
            """)
            conn.commit()

    def get_login_attempts(self, login: str):
        with self._conn() as conn:
            row = conn.execute("SELECT attempts, last_attempt FROM login_attempts WHERE login = ?", (login,)).fetchone()
            if row:
                return {"attempts": row[0], "last_attempt": row[1]}
            return None

    def reset_login_attempts(self, login: str):
        with self._conn() as conn:
            conn.execute("UPDATE login_attempts SET attempts = 0 WHERE login = ?", (login,))
            conn.commit()

    def record_failed_attempt(self, login: str, attempt_time: str):
        with self._conn() as conn:
            conn.execute("""
               INSERT INTO login_attempts (login, attempts, last_attempt) 
               VALUES (?, 1, ?) 
               ON CONFLICT(login) DO UPDATE SET 
               attempts = attempts + 1, last_attempt = ?
            """, (login, attempt_time, attempt_time))
            conn.commit()

    def delete_login_attempts(self, login: str):
        with self._conn() as conn:
            conn.execute("DELETE FROM login_attempts WHERE login = ?", (login,))
            conn.commit()

    def get_user_by_login(self, login: str):
        with self._conn() as conn:
            row = conn.execute("""
                SELECT id, full_name, login, email, phone, password_salt, password_hash, role, status
                FROM users WHERE login = ?
            """, (login,)).fetchone()
            if row:
                return {
                    "id": row[0], "full_name": row[1], "login": row[2], "email": row[3], "phone": row[4],
                    "password_salt": row[5], "password_hash": row[6], "role": row[7], "status": row[8]
                }
            return None

    def create_user(self, full_name, login, email, phone, salt_hex, pw_hash, role, status, created_at):
        with self._conn() as conn:
            try:
                conn.execute("""
                    INSERT INTO users (full_name, login, email, phone, password_salt, password_hash, role, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (full_name, login, email, phone, salt_hex, pw_hash, role, status, created_at))
                conn.commit()
                return True, None
            except sqlite3.IntegrityError:
                return False, "integrity_error"

    def get_pending_users(self):
        with self._conn() as conn:
            return conn.execute("SELECT id, full_name, login, email, phone, created_at FROM users WHERE status = 'pending' ORDER BY created_at ASC").fetchall()

    def get_all_users(self):
        with self._conn() as conn:
            return conn.execute("SELECT id, full_name, login, email, phone, role, status, created_at FROM users ORDER BY created_at DESC").fetchall()

    def get_user_by_id(self, user_id):
        with self._conn() as conn:
            return conn.execute("""
                SELECT id, full_name, login, email, phone, role, status
                FROM users
                WHERE id = ?
            """, (user_id,)).fetchone()

    def update_user_status(self, user_id, status):
        with self._conn() as conn:
            conn.execute("UPDATE users SET status = ? WHERE id = ?", (status, user_id))
            conn.commit()

    def update_user_role(self, user_id, role):
        with self._conn() as conn:
            conn.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
            conn.commit()

    def check_admin_exists(self, admin_login: str):
        with self._conn() as conn:
            row = conn.execute("SELECT id FROM users WHERE login = ?", (admin_login,)).fetchone()
            return row is not None

    def create_session(self, token, user_id, expires_iso, now_iso, ua_hash):
        with self._conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO sessions (token, user_id, expires_at, created_at, last_seen_at, ua_hash)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (token, user_id, expires_iso, now_iso, now_iso, ua_hash))
            conn.commit()

    def get_session(self, token):
        with self._conn() as conn:
            return conn.execute("SELECT user_id, expires_at, ua_hash FROM sessions WHERE token = ?", (token,)).fetchone()

    def update_session_last_seen(self, token, now_iso):
        with self._conn() as conn:
            conn.execute("UPDATE sessions SET last_seen_at = ? WHERE token = ?", (now_iso, token))
            conn.commit()

    def delete_session(self, token):
        with self._conn() as conn:
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            conn.commit()

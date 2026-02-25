import sqlite3

class SQLiteUserRepository:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def _get_current_version(self, conn) -> int:
        # Check if schema_info exists and has a row
        row = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schema_info'").fetchone()
        if row:
            version_row = conn.execute("SELECT version FROM schema_info").fetchone()
            if version_row:
                return version_row[0]
        
        # Check for legacy state
        users_table = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'").fetchone()
        sessions_table = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'").fetchone()
        attempts_table = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='login_attempts'").fetchone()
        
        if users_table and sessions_table and attempts_table:
            # Deep inspection of users table columns to ensure it's truly baseline
            cols = conn.execute("PRAGMA table_info(users)").fetchall()
            col_names = [c[1] for c in cols]
            required_cols = {"id", "full_name", "login", "email", "phone", "password_salt", "password_hash", "role", "status", "created_at"}
            if required_cols.issubset(set(col_names)):
                # It's a complete legacy schema. We'll set it to 0 and let it migrate to 1 harmlessly 
                # (CREATE TABLE IF NOT EXISTS will just skip, but schema_info will get created)
                return 0
                
        return 0 # Completely empty database or a broken partial schema that needs to be brought to v1

    def _migrate_v1(self, conn):
        """Baseline schema (v1)."""
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

    def init_auth_db(self):
        # We assign function pointers, so TypeChecker won't yell if we explicitly ignore or wrap
        MIGRATIONS = [self._migrate_v1]
        
        with self._conn() as conn:
            # 1. Ensure schema_info table exists
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_info (
                    version INTEGER NOT NULL
                )
            """)
            
            # 2. Get current version (accounting for legacy)
            current_version = self._get_current_version(conn)
            
            # If schema_info is brand new but DB had a legacy structure, insert the starting version (0).
            has_version_row = conn.execute("SELECT COUNT(*) FROM schema_info").fetchone()[0] > 0
            if not has_version_row:
                conn.execute("INSERT INTO schema_info (version) VALUES (?)", (current_version,))
            
            # 3. Apply missing migrations sequentially
            for i in range(current_version, len(MIGRATIONS)):
                target_version = i + 1
                try:
                    # Execute migration step
                    MIGRATIONS[i](conn)
                    # Update schema_info to flag completion of this step within the transaction
                    conn.execute("UPDATE schema_info SET version = ?", (target_version,))
                except Exception as e:
                    # Because we are within a 'with self._conn() as conn:' block, 
                    # an exception here will bypass conn.commit() and rollback the whole init_auth_db block.
                    raise RuntimeError(f"Database migration to v{target_version} failed: {e}") from e
                    
            # 4. Commit all successful migrations
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

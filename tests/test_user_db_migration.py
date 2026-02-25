import sqlite3
import pytest
from infrastructure.repositories.sqlite_user_repository import SQLiteUserRepository

def create_legacy_v0_schema(db_path: str, partial=False):
    """Creates a legacy schema without schema_info."""
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE users (
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
        
        if not partial:
            conn.execute("""
                CREATE TABLE sessions (
                    token TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    ua_hash TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE login_attempts (
                    login TEXT PRIMARY KEY,
                    attempts INTEGER DEFAULT 0,
                    last_attempt TEXT NOT NULL
                )
            """)
        conn.commit()


def test_migration_from_empty(tmp_path):
    """Test that an empty database is fully initialized to v1."""
    db_file = tmp_path / "empty.db"
    repo = SQLiteUserRepository(str(db_file))
    
    # Run migrations
    repo.init_auth_db()
    
    with sqlite3.connect(str(db_file)) as conn:
        version = conn.execute("SELECT version FROM schema_info").fetchone()[0]
        assert version == 1
        
        # Verify all tables created
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        table_names = {t[0] for t in tables}
        assert {"schema_info", "users", "sessions", "login_attempts"}.issubset(table_names)


def test_migration_from_legacy_full(tmp_path):
    """Test that a legacy DB (users, sessions, attempts, but NO schema_info) gets recognized and bumped cleanly."""
    db_file = tmp_path / "legacy.db"
    create_legacy_v0_schema(str(db_file), partial=False)
    
    repo = SQLiteUserRepository(str(db_file))
    
    # init_auth_db should detect legacy, set starting v=0, and effectively NO-OP the CREATE TABLES, but finish with v=1
    repo.init_auth_db()
    
    with sqlite3.connect(str(db_file)) as conn:
        version = conn.execute("SELECT version FROM schema_info").fetchone()[0]
        assert version == 1


def test_migration_from_legacy_partial(tmp_path):
    """Test that a partial legacy DB (only users table) is treated as 0 and migrated to 1."""
    db_file = tmp_path / "partial.db"
    create_legacy_v0_schema(str(db_file), partial=True)
    
    repo = SQLiteUserRepository(str(db_file))
    repo.init_auth_db()
    
    with sqlite3.connect(str(db_file)) as conn:
        version = conn.execute("SELECT version FROM schema_info").fetchone()[0]
        assert version == 1
        
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        table_names = {t[0] for t in tables}
        assert "sessions" in table_names
        assert "login_attempts" in table_names


def test_migration_idempotence(tmp_path):
    """Test that running init_auth_db twice does nothing and stays at v1."""
    db_file = tmp_path / "idem.db"
    repo = SQLiteUserRepository(str(db_file))
    
    # First run
    repo.init_auth_db()
    
    # Second run
    repo.init_auth_db()
    
    with sqlite3.connect(str(db_file)) as conn:
        version = conn.execute("SELECT version FROM schema_info").fetchone()[0]
        assert version == 1

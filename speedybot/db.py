import os
import re
import secrets
import sqlite3
from typing import Any, Optional


def _migrate_db_files(directory: str, legacy_name: str = "speedping.db", target_name: str = "app.db") -> str:
    """Atomically rename legacy SQLite database and WAL/SHM files to target name."""
    legacy_path = os.path.join(directory, legacy_name)
    target_path = os.path.join(directory, target_name)
    try:
        if os.path.exists(legacy_path) and not os.path.exists(target_path):
            os.rename(legacy_path, target_path)
            for ext in ("-wal", "-shm"):
                leg_ext = f"{legacy_path}{ext}"
                tar_ext = f"{target_path}{ext}"
                if os.path.exists(leg_ext) and not os.path.exists(tar_ext):
                    os.rename(leg_ext, tar_ext)
            return os.path.abspath(target_path)
    except Exception:
        if os.path.exists(legacy_path):
            return os.path.abspath(legacy_path)
    return os.path.abspath(target_path)


def get_db_path() -> str:
    """Return canonical database path (app.db), automatically migrating legacy speedping.db."""
    # 1. Environment variable override
    env_db = os.environ.get("DATABASE_PATH") or os.environ.get("SPEEDYBOT_DB_PATH")
    if env_db:
        return os.path.abspath(env_db)

    # 2. Check current working directory first (preserves isolation in tests & local scripts)
    if os.path.exists("app.db"):
        return os.path.abspath("app.db")
    if os.path.exists("speedping.db"):
        return _migrate_db_files(".", "speedping.db", "app.db")

    # 3. Check project root directory (where main.py resides)
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    app_db_in_root = os.path.join(project_root, "app.db")
    speedping_in_root = os.path.join(project_root, "speedping.db")

    if os.path.exists(app_db_in_root):
        return app_db_in_root
    if os.path.exists(speedping_in_root):
        return _migrate_db_files(project_root, "speedping.db", "app.db")

    # 4. Check SPEEDYBOT_APP_DIR if configured
    configured_app_dir = os.environ.get("SPEEDYBOT_APP_DIR")
    if configured_app_dir and os.path.isdir(configured_app_dir):
        app_db_in_cfg = os.path.join(configured_app_dir, "app.db")
        speedping_in_cfg = os.path.join(configured_app_dir, "speedping.db")
        if os.path.exists(app_db_in_cfg):
            return app_db_in_cfg
        if os.path.exists(speedping_in_cfg):
            return _migrate_db_files(configured_app_dir, "speedping.db", "app.db")

    # Default fallback
    return os.path.abspath("app.db")


def get_connection(timeout: int = 20) -> sqlite3.Connection:
    """Return a configured sqlite3 connection with WAL mode and row factory."""
    conn = sqlite3.connect(get_db_path(), timeout=timeout)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
    except Exception:
        pass
    return conn


def get_brand_name(default: str = "Shop", conn: Optional[sqlite3.Connection] = None) -> str:
    """Return configured brand name by combining webapp_title, brand_name, and environment."""
    close_after = False
    if conn is None:
        try:
            conn = get_connection()
            close_after = True
        except Exception:
            conn = None
    try:
        if conn is not None:
            # 1. webapp_title in settings
            r1 = conn.execute("SELECT value FROM settings WHERE key = 'webapp_title'").fetchone()
            t1 = str(r1[0]).strip() if r1 and r1[0] else ""
            if t1 and t1.lower() != "speedybot":
                return t1

            # 2. brand_name in settings
            r2 = conn.execute("SELECT value FROM settings WHERE key = 'brand_name'").fetchone()
            t2 = str(r2[0]).strip() if r2 and r2[0] else ""
            if t2 and t2.lower() != "speedybot":
                return t2

            if t1 and t1.lower() != "speedybot":
                return t1
    except Exception:
        pass
    finally:
        if close_after and conn:
            conn.close()

    # 3. Environment variable BRAND_NAME
    env_brand = os.environ.get("BRAND_NAME", "").strip()
    if env_brand and env_brand.lower() != "speedybot":
        return env_brand

    return default


def get_brand_slug(default: str = "vpn", conn: Optional[sqlite3.Connection] = None) -> str:
    """Return lowercase alphanumeric slug of the brand name for configs and emails."""
    brand = get_brand_name(conn=conn)
    slug = re.sub(r"[^a-zA-Z0-9]", "", brand).lower()
    return slug if slug else default


def is_service_email_in_use(candidate: str, conn: Optional[sqlite3.Connection] = None) -> bool:
    """Check if candidate email/name is already allocated in database transactions."""
    close_after = False
    if conn is None:
        conn = get_connection()
        close_after = True

    try:
        # Check transactions
        r = conn.execute(
            "SELECT 1 FROM transactions WHERE LOWER(service_email) = LOWER(?) AND (status IS NULL OR status != 'REJECTED')",
            (candidate,),
        ).fetchone()
        if r:
            return True

        # Check trial_services
        r = conn.execute(
            "SELECT 1 FROM trial_services WHERE LOWER(email) = LOWER(?)",
            (candidate,),
        ).fetchone()
        if r:
            return True

        # Check linked_services
        r = conn.execute(
            "SELECT 1 FROM linked_services WHERE LOWER(email) = LOWER(?)",
            (candidate,),
        ).fetchone()
        if r:
            return True

        return False
    finally:
        if close_after:
            conn.close()


def resolve_unique_service_email(
    desired_name: Optional[str] = None,
    user_id: int = 0,
    tx_id: int = 0,
    conn: Optional[sqlite3.Connection] = None,
) -> str:
    """Resolve a unique service config email.

    If user provided a desired name, cleans it and increments a number if taken.
    Otherwise defaults to '{brand_slug}_{user_id}_{tx_id}'.
    """
    brand_slug = get_brand_slug(conn=conn)

    if desired_name and str(desired_name).strip():
        raw = str(desired_name).strip()
        # Clean: keep alphanumeric, hyphens and underscores
        cleaned = re.sub(r"[^a-zA-Z0-9_-]", "_", raw).strip("_-").lower()
        if not cleaned:
            cleaned = f"{brand_slug}_{user_id}"

        candidate = cleaned
        counter = 1
        while is_service_email_in_use(candidate, conn=conn):
            counter += 1
            candidate = f"{cleaned}_{counter}"
        return candidate

    # Default fallback
    if tx_id:
        return f"{brand_slug}_{int(user_id)}_{int(tx_id)}"
    return f"{brand_slug}_{int(user_id)}_{secrets.token_hex(4)}"

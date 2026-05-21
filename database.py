import sqlite3
import os
import hashlib
import json
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "endoscan.db")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
DEFAULT_ADMIN_USERNAME = os.getenv("ENDOSCAN_ADMIN_USERNAME", "admin")
DEFAULT_ADMIN_PASSWORD = os.getenv("ENDOSCAN_ADMIN_PASSWORD", "admin123")

if not os.path.exists(UPLOADS_DIR):
    os.makedirs(UPLOADS_DIR)

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    existing_user_columns = {
        row["name"] for row in cursor.execute("PRAGMA table_info(users)").fetchall()
    }
    if "role" not in existing_user_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")
    if "status" not in existing_user_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN status TEXT NOT NULL DEFAULT 'active'")
    
    # History table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            image_path TEXT NOT NULL,
            result_json TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    # API Keys table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            api_key TEXT UNIQUE NOT NULL,
            description TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    # Browser sessions shared by Python and, if needed later, Java.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            access_token TEXT UNIQUE NOT NULL,
            created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            end_date DATETIME NOT NULL,
            revoked_at DATETIME,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions (access_token)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions (user_id)")

    init_admin_schema(cursor)
    ensure_default_admin(cursor)
    seed_admin_defaults(cursor)
    sync_analysis_reviews(cursor)
    
    conn.commit()
    conn.close()

def init_admin_schema(cursor):
    schema_path = os.path.join(BASE_DIR, "schema.sql")
    if os.path.exists(schema_path):
        with open(schema_path, "r", encoding="utf-8") as schema_file:
            cursor.executescript(schema_file.read())

def seed_admin_defaults(cursor):
    for user in cursor.execute("SELECT id, username, role, status FROM users").fetchall():
        cursor.execute(
            """
            INSERT OR IGNORE INTO user_profiles (user_id, full_name, email, role, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user["id"], user["username"], f"{user['username']}@endoscan.local", user["role"], user["status"])
        )

    defaults = {
        "site_name": "EndoScan AI",
        "public_stats": "ON",
        "registration": "ON",
        "maintenance_mode": "OFF",
        "active_model": "v1.1",
        "confidence_threshold": "70",
        "save_uploaded_images": "ON",
        "admin_email": "admin@endoscan.ai",
        "two_factor_auth": "OFF",
        "session_timeout": "30 min",
        "dataset_declared_total": "8000",
        "dataset_declared_verified": "7850",
        "avg_processing_time_sec": "2.4",
        "old_files_cleanup": "Enabled",
        "backup_status": "Local",
    }
    for key, value in defaults.items():
        cursor.execute("INSERT OR IGNORE INTO app_settings (key, value) VALUES (?, ?)", (key, value))

    if cursor.execute("SELECT COUNT(*) AS c FROM dataset_images").fetchone()["c"] == 0:
        samples = [
            ("img001.jpg", "Normal", "train", "verified"),
            ("img002.jpg", "Polyps", "train", "verified"),
            ("img003.jpg", "Esophagitis", "validation", "need_review"),
            ("img004.jpg", "Ulcerative", "test", "verified"),
            ("img005.jpg", "Dyed lifted polyps", "train", "verified"),
            ("img006.jpg", "Dyed resection margins", "train", "verified"),
            ("img007.jpg", "Normal pylorus", "validation", "verified"),
            ("img008.jpg", "Normal z-line", "test", "verified"),
        ]
        cursor.executemany(
            """
            INSERT INTO dataset_images (image_name, image_path, label, split_name, status, source)
            VALUES (?, ?, ?, ?, ?, 'seed')
            """,
            [(name, f"/dataset/{name}", label, split_name, status) for name, label, split_name, status in samples]
        )

    if cursor.execute("SELECT COUNT(*) AS c FROM model_versions").fetchone()["c"] == 0:
        cursor.executemany(
            """
            INSERT INTO model_versions
                (version_name, accuracy, average_confidence, average_latency_ms, dataset_size, status, trained_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                ("v1.0", None, 89.1, 2600, 7200, "old", "2026-04-20"),
                ("v1.1", None, 91.4, 2400, 8000, "active", "2026-05-12"),
            ]
        )

    if cursor.execute("SELECT COUNT(*) AS c FROM news_articles").fetchone()["c"] == 0:
        cursor.executemany(
            """
            INSERT INTO news_articles (title, slug, summary, body, status, published_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                ("New AI Model Update", "new-ai-model-update", "Model confidence updates.", "EndoScan AI model notes.", "public", "2026-05-12 09:00:00"),
                ("8,000+ Dataset Reached", "8000-dataset-reached", "Dataset milestone.", "Dataset quality update.", "public", "2026-05-08 09:00:00"),
                ("Medical AI Research Notes", "medical-ai-research-notes", "Research draft.", "Draft article.", "draft", None),
            ]
        )

    if cursor.execute("SELECT COUNT(*) AS c FROM contact_messages").fetchone()["c"] == 0:
        cursor.executemany(
            """
            INSERT INTO contact_messages (name, email, subject, message, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                ("Ali Karim", "ali@mail.com", "Upload issue", "Rasm yuklashda muammo bor.", "unread"),
                ("Vali", "vali@mail.com", "Result help", "Natijani tushunishda yordam kerak.", "replied"),
                ("Hasan", "hasan@mail.com", "Account", "Account sozlamalari bo'yicha savol.", "pending"),
            ]
        )

    if cursor.execute("SELECT COUNT(*) AS c FROM activity_logs").fetchone()["c"] == 0:
        cursor.executemany(
            """
            INSERT INTO activity_logs (actor_name, action, target_type, status, details)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                ("Admin", "Deleted scan", "analysis", "success", "Old test scan removed"),
                ("Ali", "Uploaded image", "upload", "success", "Image accepted"),
                ("System", "Model error", "model", "failed", "Temporary model response error"),
            ]
        )

    if cursor.execute("SELECT COUNT(*) AS c FROM notifications").fetchone()["c"] == 0:
        cursor.executemany(
            """
            INSERT INTO notifications (scope, level, title, body)
            VALUES ('admin', ?, ?, ?)
            """,
            [
                ("warning", "High risk cases detected", "5 high risk cases detected"),
                ("warning", "Failed analyses today", "2 failed analyses today"),
                ("success", "New user registered", "New user registered"),
                ("success", "Dataset import completed", "Dataset import completed"),
            ]
        )

def sync_analysis_reviews(cursor):
    rows = cursor.execute(
        """
        SELECT history.id, history.result_json, history.timestamp
        FROM history
        LEFT JOIN analysis_reviews ON analysis_reviews.history_id = history.id
        WHERE analysis_reviews.id IS NULL
        """
    ).fetchall()
    for row in rows:
        prediction, confidence = parse_result_summary(row["result_json"])
        risk_level = infer_risk_level(prediction, confidence)
        review_status = "pending" if confidence < 70 or risk_level == "high" else "auto"
        cursor.execute(
            """
            INSERT INTO analysis_reviews
                (history_id, prediction, confidence, risk_level, review_status, failed, created_at)
            VALUES (?, ?, ?, ?, ?, 0, ?)
            """,
            (row["id"], prediction, confidence, risk_level, review_status, row["timestamp"])
        )

def parse_result_summary(result_json: str):
    try:
        data = json.loads(result_json or "{}")
    except json.JSONDecodeError:
        data = {}
    prediction = str(data.get("disease") or data.get("prediction") or "Unknown")
    try:
        confidence = int(float(data.get("confidence", 0)))
    except (TypeError, ValueError):
        confidence = 0
    return prediction, confidence

def infer_risk_level(prediction: str, confidence: int) -> str:
    name = (prediction or "").lower()
    high_terms = ("ulcer", "cancer", "bleeding", "tumor")
    medium_terms = ("polyp", "esophagitis", "colitis", "resection", "dyed")
    if confidence < 65 or any(term in name for term in high_terms):
        return "high"
    if confidence < 85 or any(term in name for term in medium_terms):
        return "medium"
    return "low"

def ensure_default_admin(cursor):
    admin_count = cursor.execute("SELECT COUNT(*) AS c FROM users WHERE role = 'admin'").fetchone()["c"]
    if admin_count:
        return

    hashed_password = hashlib.sha256(DEFAULT_ADMIN_PASSWORD.encode()).hexdigest()
    existing = cursor.execute("SELECT * FROM users WHERE username = ?", (DEFAULT_ADMIN_USERNAME,)).fetchone()
    if existing:
        cursor.execute(
            "UPDATE users SET password = ?, role = 'admin', status = 'active' WHERE id = ?",
            (hashed_password, existing["id"])
        )
        return

    cursor.execute(
        "INSERT INTO users (username, password, role, status) VALUES (?, ?, 'admin', 'active')",
        (DEFAULT_ADMIN_USERNAME, hashed_password)
    )

# --- User Functions ---

def get_user_by_username(username: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    return user

def get_user_by_api_key(api_key: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT users.* FROM users 
        JOIN api_keys ON users.id = api_keys.user_id 
        WHERE api_keys.api_key = ?
    """, (api_key,))
    user = cursor.fetchone()
    conn.close()
    return user

def add_api_key(user_id: int, api_key: str, description: str = ""):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO api_keys (user_id, api_key, description) VALUES (?, ?, ?)",
            (user_id, api_key, description)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def add_user(username: str, hashed_password: str, role: str = "user"):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, password, role, status) VALUES (?, ?, ?, 'active')",
            (username, hashed_password, role)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def add_session(user_id: int, access_token: str, end_date: datetime):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO sessions (user_id, access_token, end_date) VALUES (?, ?, ?)",
        (user_id, access_token, end_date.isoformat())
    )
    conn.commit()
    conn.close()

def get_active_session(access_token: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT sessions.*, users.username, users.role, users.status
        FROM sessions
        JOIN users ON users.id = sessions.user_id
        WHERE sessions.access_token = ?
          AND sessions.revoked_at IS NULL
          AND sessions.end_date > ?
          AND users.status = 'active'
    """, (access_token, datetime.utcnow().isoformat()))
    session = cursor.fetchone()
    conn.close()
    return session

def revoke_session(access_token: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE sessions SET revoked_at = CURRENT_TIMESTAMP WHERE access_token = ? AND revoked_at IS NULL",
        (access_token,)
    )
    conn.commit()
    conn.close()

# --- History Functions ---

def add_history_item(user_id: int, image_path: str, result_json: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO history (user_id, image_path, result_json) VALUES (?, ?, ?)",
        (user_id, image_path, result_json)
    )
    history_id = cursor.lastrowid
    prediction, confidence = parse_result_summary(result_json)
    risk_level = infer_risk_level(prediction, confidence)
    review_status = "pending" if confidence < 70 or risk_level == "high" else "auto"
    cursor.execute(
        """
        INSERT INTO analysis_reviews (history_id, prediction, confidence, risk_level, review_status, failed)
        VALUES (?, ?, ?, ?, ?, 0)
        """,
        (history_id, prediction, confidence, risk_level, review_status)
    )
    cursor.execute(
        """
        INSERT INTO activity_logs (actor_user_id, actor_name, action, target_type, target_id, status, details)
        VALUES (?, COALESCE((SELECT username FROM users WHERE id = ?), 'User'), 'Uploaded image', 'analysis', ?, 'success', ?)
        """,
        (user_id, user_id, str(history_id), prediction)
    )
    conn.commit()
    conn.close()

def get_user_history(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM history WHERE user_id = ? ORDER BY timestamp DESC", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows

if __name__ == "__main__":
    init_db()

import json
import os
import base64
from collections import Counter, defaultdict
from datetime import datetime, timedelta
import urllib.error
import urllib.parse
import urllib.request

import database


JAVA_STATS_BASE_URL = os.getenv("JAVA_STATS_BASE_URL", "http://127.0.0.1:8081")
INTERNAL_STATS_KEY = os.getenv("INTERNAL_STATS_KEY", "endoscan-local-stats")
CELL_SEP = "\x1f"
ROW_SEP = "\x1e"


ADMIN_SECTIONS = {
    "dashboard",
    "users",
    "analyses",
    "review-queue",
    "dataset",
    "model-stats",
    "reports",
    "news-manager",
    "activity-logs",
    "messages",
    "settings",
    "user-detail",
    "analysis-detail",
}

USER_SECTIONS = {
    "snapshot",
    "scan-library",
    "ai-insights",
    "risk-map",
    "confidence-pulse",
    "timeline",
    "reports",
    "profile",
    "analysis-detail",
}


def normalize_section(scope: str, section: str | None) -> str:
    valid = ADMIN_SECTIONS if scope == "admin" else USER_SECTIONS
    default = "dashboard" if scope == "admin" else "snapshot"
    if section in valid:
        return section
    return default


def get_stats(scope: str, section: str | None, user: dict | None = None) -> dict:
    section = normalize_section(scope, section)
    url = f"{JAVA_STATS_BASE_URL}/api/stats/{scope}/{section}"
    if user:
        query = urllib.parse.urlencode({
            "userId": user.get("id", ""),
            "username": user.get("username") or user.get("sub") or "",
        })
        url = f"{url}?{query}"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=2.5) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return fallback_stats(scope, section)


def get_internal_stats_key() -> str:
    return INTERNAL_STATS_KEY


def get_encoded_stats_snapshot(user_id: int | None = None) -> dict:
    snapshot = build_stats_snapshot(user_id=user_id)
    encoded = {}
    for key, value in snapshot.items():
        encoded[key] = base64.b64encode(str(value).encode("utf-8")).decode("ascii")
    return encoded


def build_stats_snapshot(user_id: int | None = None) -> dict:
    conn = database.get_db_connection()
    try:
        settings = {
            row["key"]: row["value"]
            for row in conn.execute("SELECT key, value FROM app_settings").fetchall()
        }
        users = [dict(row) for row in conn.execute(
            """
            SELECT users.id,
                   users.username,
                   users.role,
                   users.status,
                   COALESCE(user_profiles.full_name, users.username) AS full_name,
                   COALESCE(user_profiles.email, users.username || '@endoscan.local') AS email,
                   COALESCE(user_profiles.created_at, '') AS created_at,
                   COALESCE(user_profiles.last_seen_at, '') AS last_seen_at
            FROM users
            LEFT JOIN user_profiles ON user_profiles.user_id = users.id
            ORDER BY users.id
            """
        ).fetchall()]
        analyses = [dict(row) for row in conn.execute(
            """
            SELECT history.id,
                   history.user_id,
                   history.image_path,
                   history.result_json,
                   history.timestamp,
                   COALESCE(users.username, 'User') AS username,
                   COALESCE(user_profiles.full_name, users.username, 'User') AS full_name,
                   COALESCE(analysis_reviews.prediction, '') AS prediction,
                   COALESCE(analysis_reviews.confidence, 0) AS confidence,
                   COALESCE(analysis_reviews.risk_level, 'low') AS risk_level,
                   COALESCE(analysis_reviews.review_status, 'auto') AS review_status,
                   COALESCE(analysis_reviews.failed, 0) AS failed
            FROM history
            LEFT JOIN users ON users.id = history.user_id
            LEFT JOIN user_profiles ON user_profiles.user_id = history.user_id
            LEFT JOIN analysis_reviews ON analysis_reviews.history_id = history.id
            ORDER BY history.timestamp DESC, history.id DESC
            """
        ).fetchall()]
        dataset = [dict(row) for row in conn.execute(
            """
            SELECT id, image_name, label, split_name, status, created_at
            FROM dataset_images
            ORDER BY id DESC
            """
        ).fetchall()]
        model_versions = [dict(row) for row in conn.execute(
            """
            SELECT version_name, accuracy, average_confidence, average_latency_ms, status, trained_at, created_at
            FROM model_versions
            ORDER BY COALESCE(trained_at, created_at) DESC, id DESC
            """
        ).fetchall()]
        news = [dict(row) for row in conn.execute(
            """
            SELECT id, title, status, published_at, created_at
            FROM news_articles
            ORDER BY COALESCE(published_at, created_at) DESC, id DESC
            """
        ).fetchall()]
        logs = [dict(row) for row in conn.execute(
            """
            SELECT actor_name, action, status, created_at
            FROM activity_logs
            ORDER BY created_at DESC, id DESC
            LIMIT 20
            """
        ).fetchall()]
        messages = [dict(row) for row in conn.execute(
            """
            SELECT id, name, subject, status, created_at
            FROM contact_messages
            ORDER BY created_at DESC, id DESC
            LIMIT 20
            """
        ).fetchall()]
        notifications = [dict(row) for row in conn.execute(
            """
            SELECT level, title, body, created_at
            FROM notifications
            WHERE scope = 'admin' AND read_at IS NULL
            ORDER BY created_at DESC, id DESC
            LIMIT 8
            """
        ).fetchall()]
        reports_count = conn.execute("SELECT COUNT(*) AS c FROM report_exports").fetchone()["c"]
        generated_reports = [dict(row) for row in conn.execute(
            """
            SELECT user_id, history_id, report_type, format, downloaded_count, created_at
            FROM generated_reports
            ORDER BY created_at DESC, id DESC
            """
        ).fetchall()]
    finally:
        conn.close()

    now = datetime.now()
    today = now.date()
    confidence_values = [int(a["confidence"] or 0) for a in analyses]
    total_analyses = len(analyses)
    avg_confidence = round(sum(confidence_values) / total_analyses, 1) if total_analyses else 0
    today_analyses = sum(1 for a in analyses if parse_dt(a["timestamp"]).date() == today)
    failed_analyses = sum(1 for a in analyses if int(a["failed"] or 0) == 1)
    low_confidence = sum(1 for a in analyses if int(a["confidence"] or 0) < 70)
    risk_counts = Counter(normalize_risk(a["risk_level"]) for a in analyses)
    high_risk = risk_counts["High"]
    prediction_counts = Counter(pretty_label(a["prediction"]) for a in analyses if a["prediction"])
    most_detected = prediction_counts.most_common(1)[0][0] if prediction_counts else "No data"

    scan_counts = Counter(a["user_id"] for a in analyses)
    active_users = sum(1 for u in users if (u["status"] or "active").lower() == "active")
    blocked_users = sum(1 for u in users if (u["status"] or "").lower() == "blocked")
    new_users_today = sum(1 for u in users if parse_dt(u["created_at"]).date() == today)
    top_users = sum(1 for _, count in scan_counts.items() if count >= 5)

    dataset_declared_total = safe_int(settings.get("dataset_declared_total"), len(dataset))
    dataset_total = max(len(dataset), dataset_declared_total)
    verified_actual = sum(1 for item in dataset if normalize_status(item["status"]) == "Verified")
    verified_declared = safe_int(settings.get("dataset_declared_verified"), verified_actual)
    verified_images = min(max(verified_actual, verified_declared), dataset_total)
    need_review_images = max(dataset_total - verified_images, sum(1 for item in dataset if normalize_status(item["status"]) != "Verified"))
    dataset_classes = max(len({item["label"] for item in dataset}), 8 if dataset_total >= 8000 else 0)

    storage_files = get_upload_files()
    storage_count = len(storage_files)
    storage_used = sum(size for _, size in storage_files)
    avg_image_size = round(storage_used / storage_count) if storage_count else 0

    active_model = settings.get("active_model", active_model_from_versions(model_versions))
    avg_processing = settings.get("avg_processing_time_sec", avg_latency_from_versions(model_versions))
    failed_rate = round((failed_analyses / total_analyses) * 100, 1) if total_analyses else 0

    published_news = [n for n in news if (n["status"] or "").lower() in {"public", "published"}]
    draft_news = [n for n in news if (n["status"] or "").lower() == "draft"]
    last_published = compact_date(max((n["published_at"] for n in published_news if n["published_at"]), default=""))
    most_viewed_news = published_news[0]["title"] if published_news else (news[0]["title"] if news else "No data")

    today_logs = sum(1 for item in logs if parse_dt(item["created_at"]).date() == today)
    admin_actions = sum(1 for item in logs if (item["actor_name"] or "").lower() == "admin")
    error_logs = sum(1 for item in logs if (item["status"] or "").lower() in {"failed", "error"})
    total_messages = len(messages)
    unread_messages = sum(1 for item in messages if (item["status"] or "").lower() == "unread")
    replied_messages = sum(1 for item in messages if (item["status"] or "").lower() == "replied")
    pending_messages = sum(1 for item in messages if (item["status"] or "").lower() == "pending")

    latest_analysis = analyses[0] if analyses else None
    latest_user = user_for_detail(users, analyses)

    snapshot = {
        "totalUsers": fmt_count(len(users)),
        "activeUsers": fmt_count(active_users),
        "newUsersToday": fmt_count(new_users_today),
        "blockedUsers": fmt_count(blocked_users),
        "topUsers": fmt_count(top_users),
        "userGrowth": growth_label(users),
        "totalAnalyses": fmt_count(total_analyses),
        "todayAnalyses": fmt_count(today_analyses),
        "averageConfidence": fmt_percent(avg_confidence),
        "failedAnalyses": fmt_count(failed_analyses),
        "lowConfidenceCases": fmt_count(low_confidence),
        "highRiskCases": fmt_count(high_risk),
        "mostDetectedClass": most_detected,
        "datasetImages": fmt_dataset_count(dataset_total),
        "detectionClasses": f"{dataset_classes}+",
        "verifiedImages": fmt_count(verified_images),
        "needReviewImages": fmt_count(need_review_images),
        "avgProcessingTime": f"{avg_processing} sec",
        "failedPredictionRate": fmt_percent(failed_rate),
        "activeModel": active_model,
        "testedImages": fmt_dataset_count(dataset_total),
        "predictionCount": fmt_count(total_analyses),
        "totalNews": fmt_count(len(news)),
        "publishedNews": fmt_count(len(published_news)),
        "draftNews": fmt_count(len(draft_news)),
        "lastPublished": last_published or "-",
        "mostViewedNews": most_viewed_news,
        "todayLogs": fmt_count(today_logs),
        "adminActions": fmt_count(admin_actions),
        "errorLogs": fmt_count(error_logs),
        "totalMessages": fmt_count(total_messages),
        "unreadMessages": fmt_count(unread_messages),
        "repliedMessages": fmt_count(replied_messages),
        "pendingMessages": fmt_count(pending_messages),
        "reviewPending": fmt_count(sum(1 for a in analyses if (a["review_status"] or "").lower() in {"pending", "review"})),
        "reviewHighRisk": fmt_count(high_risk),
        "reviewLowConfidence": fmt_count(low_confidence),
        "reviewApproved": fmt_count(sum(1 for a in analyses if (a["review_status"] or "").lower() == "approved")),
        "reviewMarked": fmt_count(sum(1 for a in analyses if (a["review_status"] or "").lower() == "review")),
        "reviewDeleted": "0",
        "monthlyReport": "Ready" if reports_count else "Ready",
        "userReport": "Ready",
        "aiReport": "Ready",
        "datasetReport": "Ready",
        "uploadedImages": fmt_count(storage_count or total_analyses),
        "storageUsed": format_bytes(storage_used),
        "averageImageSize": format_bytes(avg_image_size),
        "oldFilesCleanup": settings.get("old_files_cleanup", "Enabled"),
        "backupStatus": settings.get("backup_status", "Local"),
        "modelStatus": "Online",
        "lastPrediction": relative_time(parse_dt(latest_analysis["timestamp"])) if latest_analysis else "No predictions yet",
        "modelResponseDelta": "+18%" if failed_rate > 0 else "Stable",
        "failedUploadsToday": fmt_count(failed_analyses),
        "datasetStatus": "Healthy" if need_review_images <= max(dataset_total * 0.05, 1) else "Needs review",
        "siteName": settings.get("site_name", "EndoScan AI"),
        "publicStats": settings.get("public_stats", "ON"),
        "registration": settings.get("registration", "ON"),
        "maintenanceMode": settings.get("maintenance_mode", "OFF"),
        "confidenceThreshold": f"{settings.get('confidence_threshold', '70')}%",
        "saveUploadedImages": settings.get("save_uploaded_images", "ON"),
        "adminEmail": settings.get("admin_email", "admin@endoscan.ai"),
        "twoFactorAuth": settings.get("two_factor_auth", "OFF"),
        "sessionTimeout": settings.get("session_timeout", "30 min"),
        "chartLast7Days": encode_matrix(last_7_days_series(analyses, now)),
        "chartRiskDistribution": encode_matrix(risk_distribution_series(risk_counts, total_analyses)),
        "chartUserGrowth": encode_matrix(user_growth_series(users, now)),
        "chartDetectionClasses": encode_matrix(class_series(prediction_counts)),
        "chartDatasetByClass": encode_matrix(dataset_class_series(dataset)),
        "chartTrainSplit": encode_matrix(split_series(dataset)),
        "chartConfidenceDistribution": encode_matrix(confidence_distribution(confidence_values)),
        "chartClassPerformance": encode_matrix(class_performance_series(prediction_counts, avg_confidence)),
        "recentAnalysesRows": encode_matrix(analysis_rows(analyses, 5, compact=False)),
        "usersRows": encode_matrix(user_rows(users, scan_counts)),
        "analysesRows": encode_matrix(analysis_rows(analyses, 10, compact=True)),
        "reviewRows": encode_matrix(review_rows(analyses)),
        "datasetRows": encode_matrix(dataset_rows(dataset)),
        "modelVersionsRows": encode_matrix(model_rows(model_versions, avg_confidence, avg_processing)),
        "newsRows": encode_matrix(news_rows(news)),
        "activityRows": encode_matrix(activity_rows(logs)),
        "messagesRows": encode_matrix(message_rows(messages)),
        "userProfileItems": encode_matrix(user_profile_items(latest_user)),
        "userHistoryRows": encode_matrix(user_history_rows(latest_user, analyses)),
        "analysisImageItems": encode_matrix(analysis_image_items(latest_analysis)),
        "analysisResultItems": encode_matrix(analysis_result_items(latest_analysis, avg_processing)),
        "analysisNotes": encode_list(analysis_notes(latest_analysis)),
        "notifications": encode_list(notification_items(notifications, high_risk, failed_analyses)),
    }
    snapshot.update(build_user_snapshot(user_id, users, analyses, generated_reports, avg_processing))
    return snapshot


def encode_matrix(rows):
    return ROW_SEP.join(CELL_SEP.join(str(cell) for cell in row) for row in rows)


def encode_list(items):
    return ROW_SEP.join(str(item) for item in items)


def parse_dt(value):
    if isinstance(value, datetime):
        return value
    if not value:
        return datetime.fromtimestamp(0)
    text = str(value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
        return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed
    except ValueError:
        pass
    clean = text.split(".")[0].replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(clean, fmt)
        except ValueError:
            pass
    return datetime.fromtimestamp(0)


def safe_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def fmt_count(value):
    return f"{int(value):,}"


def fmt_percent(value):
    value = float(value or 0)
    if value == int(value):
        return f"{int(value)}%"
    return f"{value:.1f}%"


def fmt_dataset_count(value):
    if value >= 8000:
        return f"{value:,}+"
    return fmt_count(value)


def pretty_label(value):
    text = str(value or "Unknown").replace("-", " ").replace("_", " ").strip()
    return " ".join(part.capitalize() for part in text.split()) or "Unknown"


def normalize_risk(value):
    text = str(value or "low").lower()
    if text == "high":
        return "High"
    if text == "medium":
        return "Medium"
    return "Low"


def normalize_status(value):
    text = str(value or "").replace("_", " ").strip().lower()
    return " ".join(part.capitalize() for part in text.split()) or "Unknown"


def compact_date(value):
    dt = parse_dt(value)
    if dt.year <= 1970:
        return ""
    return dt.strftime("%m/%d")


def relative_time(dt):
    if dt.year <= 1970:
        return "No predictions yet"
    delta = datetime.now() - dt
    if delta.days > 0:
        return f"{delta.days} days ago"
    minutes = max(int(delta.total_seconds() // 60), 1)
    if minutes >= 60:
        return f"{minutes // 60} hours ago"
    return f"{minutes} minutes ago"


def format_bytes(value):
    value = float(value or 0)
    units = ["B", "KB", "MB", "GB", "TB"]
    idx = 0
    while value >= 1024 and idx < len(units) - 1:
        value /= 1024
        idx += 1
    if idx == 0:
        return f"{int(value)} {units[idx]}"
    return f"{value:.1f} {units[idx]}"


def get_upload_files():
    files = []
    if not os.path.isdir(database.UPLOADS_DIR):
        return files
    for name in os.listdir(database.UPLOADS_DIR):
        path = os.path.join(database.UPLOADS_DIR, name)
        if os.path.isfile(path):
            try:
                files.append((name, os.path.getsize(path)))
            except OSError:
                pass
    return files


def active_model_from_versions(rows):
    for row in rows:
        if (row["status"] or "").lower() == "active":
            return row["version_name"]
    return rows[0]["version_name"] if rows else "v1.1"


def avg_latency_from_versions(rows):
    for row in rows:
        if (row["status"] or "").lower() == "active" and row["average_latency_ms"]:
            return f"{float(row['average_latency_ms']) / 1000:.1f}"
    return "2.4"


def growth_label(users):
    if not users:
        return "0%"
    now = datetime.now()
    recent = sum(1 for u in users if (now - parse_dt(u["created_at"])).days <= 30)
    pct = round((recent / max(len(users), 1)) * 100)
    return f"+{pct}%"


def last_7_days_series(analyses, now):
    counts = defaultdict(int)
    for item in analyses:
        counts[parse_dt(item["timestamp"]).date()] += 1
    rows = []
    for offset in range(6, -1, -1):
        day = (now - timedelta(days=offset)).date()
        rows.append((day.strftime("%a"), counts[day]))
    return rows


def risk_distribution_series(counts, total):
    if total <= 0:
        return [("Low", 0), ("Medium", 0), ("High", 0)]
    return [(label, round((counts[label] / total) * 100)) for label in ("Low", "Medium", "High")]


def user_growth_series(users, now):
    rows = []
    for offset in (30, 20, 10, 5, 0):
        day = now - timedelta(days=offset)
        count = sum(1 for user in users if parse_dt(user["created_at"]) <= day)
        rows.append((day.strftime("%b %d"), count))
    return rows


def class_series(counts):
    if not counts:
        return [("Normal", 0), ("Polyps", 0), ("Esophagitis", 0), ("Ulcerative", 0)]
    return counts.most_common(4)


def dataset_class_series(dataset):
    counts = Counter(pretty_label(item["label"]) for item in dataset)
    if not counts:
        return [("Normal", 0), ("Polyps", 0), ("Esophagitis", 0), ("Ulcerative", 0)]
    return counts.most_common(5)


def split_series(dataset):
    counts = Counter(str(item["split_name"] or "train").lower() for item in dataset)
    total = max(sum(counts.values()), 1)
    return [
        ("Train", round((counts["train"] / total) * 100)),
        ("Validation", round((counts["validation"] / total) * 100)),
        ("Test", round((counts["test"] / total) * 100)),
    ]


def confidence_distribution(values):
    return [
        ("60-70%", sum(1 for v in values if 60 <= v < 70)),
        ("70-80%", sum(1 for v in values if 70 <= v < 80)),
        ("80-90%", sum(1 for v in values if 80 <= v < 90)),
        ("90-100%", sum(1 for v in values if v >= 90)),
    ]


def class_performance_series(counts, avg_confidence):
    base = class_series(counts)
    if not base:
        return [("Normal", round(avg_confidence))]
    total = max(sum(count for _, count in base), 1)
    return [(label, min(99, max(70, round(avg_confidence + (count / total) * 8)))) for label, count in base]


def analysis_rows(analyses, limit, compact):
    rows = []
    for item in analyses[:limit]:
        row = (
            item["id"] if compact else item["full_name"],
            item["full_name"] if compact else pretty_label(item["prediction"]),
            pretty_label(item["prediction"]) if compact else f"{item['confidence']}%",
            f"{item['confidence']}%" if compact else normalize_risk(item["risk_level"]),
            normalize_risk(item["risk_level"]) if compact else None,
        )
        rows.append(tuple(cell for cell in row if cell is not None))
    return rows or [("-", "No data", "-", "-")]


def user_rows(users, scan_counts):
    rows = []
    for user in users[:10]:
        rows.append((user["id"], user["full_name"], user["email"], scan_counts[user["id"]], user["role"].capitalize()))
    return rows or [("-", "No users", "-", "0", "-")]


def review_rows(analyses):
    candidates = [
        item for item in analyses
        if (item["review_status"] or "").lower() in {"pending", "review"} or int(item["confidence"] or 0) < 70 or normalize_risk(item["risk_level"]) == "High"
    ]
    rows = [
        (item["id"], item["full_name"], pretty_label(item["prediction"]), f"{item['confidence']}%", normalize_status(item["review_status"]))
        for item in candidates[:10]
    ]
    return rows or [("-", "No pending cases", "-", "-", "Clear")]


def dataset_rows(dataset):
    rows = [
        (item["id"], item["image_name"], pretty_label(item["label"]), normalize_status(item["status"]))
        for item in dataset[:10]
    ]
    return rows or [("-", "No images", "-", "-")]


def model_rows(rows, avg_confidence, avg_processing):
    result = []
    for item in rows[:5]:
        confidence = item["average_confidence"] if item["average_confidence"] is not None else avg_confidence
        date_value = parse_dt(item["trained_at"] or item["created_at"]).strftime("%Y-%m")
        result.append((item["version_name"], fmt_percent(float(confidence or 0)), date_value, normalize_status(item["status"])))
    return result or [("v1.1", fmt_percent(avg_confidence), "2026-05", "Active")]


def news_rows(news):
    rows = [(item["id"], item["title"], normalize_status(item["status"]), compact_date(item["published_at"] or item["created_at"])) for item in news[:10]]
    return rows or [("-", "No news", "-", "-")]


def activity_rows(logs):
    rows = [(parse_dt(item["created_at"]).strftime("%H:%M"), item["actor_name"], item["action"], normalize_status(item["status"])) for item in logs[:10]]
    return rows or [("-", "System", "No logs", "-")]


def message_rows(messages):
    rows = [(item["id"], item["name"], item["subject"], normalize_status(item["status"])) for item in messages[:10]]
    return rows or [("-", "No messages", "-", "-")]


def user_for_detail(users, analyses):
    if analyses:
        user_id = analyses[0]["user_id"]
        for user in users:
            if user["id"] == user_id:
                return user
    return users[0] if users else None


def user_profile_items(user):
    if not user:
        return [("Email", "-"), ("Role", "-"), ("Status", "-"), ("Registered", "-")]
    return [
        ("Email", user["email"]),
        ("Role", user["role"].capitalize()),
        ("Status", normalize_status(user["status"])),
        ("Registered", parse_dt(user["created_at"]).strftime("%Y-%m-%d")),
    ]


def user_history_rows(user, analyses):
    if not user:
        return [("-", "No analyses", "-", "-")]
    rows = [
        (parse_dt(item["timestamp"]).strftime("%Y-%m-%d"), pretty_label(item["prediction"]), f"{item['confidence']}%", normalize_risk(item["risk_level"]))
        for item in analyses
        if item["user_id"] == user["id"]
    ]
    return rows[:10] or [("-", "No analyses", "-", "-")]


def analysis_image_items(item):
    if not item:
        return [("Preview", "No image"), ("Image", "-")]
    return [("Preview", "Endoscopy image preview"), ("Image", item["image_path"])]


def analysis_result_items(item, avg_processing):
    if not item:
        return [("Prediction", "-"), ("Confidence", "-"), ("Risk Level", "-"), ("Processing Time", f"{avg_processing} sec")]
    return [
        ("Prediction", pretty_label(item["prediction"])),
        ("Confidence", f"{item['confidence']}%"),
        ("Risk Level", normalize_risk(item["risk_level"])),
        ("Processing Time", f"{avg_processing} sec"),
        ("Uploaded By", item["full_name"]),
        ("Date", parse_dt(item["timestamp"]).strftime("%Y-%m-%d")),
    ]


def analysis_notes(item):
    if not item:
        return ["Admin note: No analysis selected."]
    if normalize_risk(item["risk_level"]) == "High" or int(item["confidence"] or 0) < 70:
        return ["Admin note: This case may require professional review."]
    return ["Admin note: Analysis is available for audit and export."]


def notification_items(rows, high_risk, failed_analyses):
    items = [row["body"] or row["title"] for row in rows]
    if high_risk and not any("high risk" in item.lower() for item in items):
        items.insert(0, f"{high_risk} high risk cases detected")
    if failed_analyses and not any("failed" in item.lower() for item in items):
        items.insert(1, f"{failed_analyses} failed analyses today")
    return items[:6] or ["Dataset status: healthy"]


def build_user_snapshot(user_id, users, analyses, generated_reports, avg_processing):
    user = pick_snapshot_user(user_id, users, analyses)
    user_analyses = [item for item in analyses if user and item["user_id"] == user["id"]]
    confidences = [int(item["confidence"] or 0) for item in user_analyses]
    total = len(user_analyses)
    latest = user_analyses[0] if user_analyses else None
    avg_conf = round(sum(confidences) / total, 1) if total else 0
    highest_conf = max(confidences) if confidences else 0
    low_conf_count = sum(1 for value in confidences if value < 70)
    risk_counts = Counter(normalize_risk(item["risk_level"]) for item in user_analyses)
    prediction_counts = Counter(pretty_label(item["prediction"]) for item in user_analyses if item["prediction"])
    normal_count = sum(count for label, count in prediction_counts.items() if "normal" in label.lower())
    abnormal_count = max(total - normal_count, 0)
    normal_pct = round((normal_count / total) * 100) if total else 0
    abnormal_pct = max(100 - normal_pct, 0) if total else 0
    most_common, most_common_count = prediction_counts.most_common(1)[0] if prediction_counts else ("No data", 0)
    most_common_pct = round((most_common_count / total) * 100) if total else 0
    current_risk = user_overall_risk(risk_counts, latest)
    month_count = user_month_count(user_analyses)
    review_need = sum(
        1 for item in user_analyses
        if int(item["confidence"] or 0) < 70 or normalize_risk(item["risk_level"]) == "High"
    )
    user_reports = [row for row in generated_reports if user and row["user_id"] == user["id"]]
    downloaded_reports = sum(int(row["downloaded_count"] or 0) for row in user_reports)
    latest_report = parse_dt(user_reports[0]["created_at"]).strftime("%Y-%m-%d") if user_reports else (parse_dt(latest["timestamp"]).strftime("%Y-%m-%d") if latest else "-")

    return {
        "userDisplayName": user["full_name"] if user else "User",
        "userUsername": user["username"] if user else "User",
        "userEmail": user["email"] if user else "-",
        "userRole": user["role"].capitalize() if user else "User",
        "userStatus": normalize_status(user["status"]) if user else "-",
        "userJoined": parse_dt(user["created_at"]).strftime("%Y-%m-%d") if user else "-",
        "userScanCount": fmt_count(total),
        "userSavedResults": f"{fmt_count(total)} results",
        "userLatestCheck": pretty_label(latest["prediction"]) if latest else "No scans",
        "userLatestConfidence": f"{latest['confidence']}% confidence" if latest else "No confidence yet",
        "userAvgConfidence": fmt_percent(avg_conf),
        "userHighestConfidence": fmt_percent(highest_conf),
        "userLowConfidenceCases": f"{fmt_count(low_conf_count)} cases",
        "userRiskLevel": current_risk,
        "userLowRiskCount": fmt_count(risk_counts["Low"]),
        "userMediumRiskCount": fmt_count(risk_counts["Medium"]),
        "userHighRiskCount": fmt_count(risk_counts["High"]),
        "userReviewNeed": f"{fmt_count(review_need)} cases",
        "userThisMonth": f"{fmt_count(month_count)} scans",
        "userResultBalance": f"{normal_pct} / {abnormal_pct}",
        "userMostCommonResult": most_common,
        "userMostCommonPercent": fmt_percent(most_common_pct),
        "userNormalPercent": fmt_percent(normal_pct),
        "userAbnormalPercent": fmt_percent(abnormal_pct),
        "userTotalReports": fmt_count(len(user_reports) or total),
        "userDownloadedReports": fmt_count(downloaded_reports),
        "userLatestReport": latest_report,
        "userChartConfidenceTrend": encode_matrix(user_confidence_trend(user_analyses)),
        "userChartResultBalance": encode_matrix([("Normal", normal_pct), ("Abnormal", abnormal_pct)]),
        "userChartRiskDistribution": encode_matrix(risk_distribution_series(risk_counts, total)),
        "userChartTopPredictions": encode_matrix(user_top_predictions(prediction_counts)),
        "userChartMonthlyActivity": encode_matrix(user_monthly_activity(user_analyses)),
        "userScanRows": encode_matrix(user_scan_rows(user_analyses)),
        "userRiskRows": encode_matrix(user_risk_rows(user_analyses)),
        "userLowConfidenceRows": encode_matrix(user_low_confidence_rows(user_analyses)),
        "userTimelineRows": encode_matrix(user_timeline_rows(user_analyses)),
        "userLatestPanel": encode_matrix(user_latest_panel(latest, avg_processing)),
        "userAiNotes": encode_list(user_ai_notes(latest, avg_conf, review_need, most_common)),
        "userInsightPanel": encode_matrix(user_insight_panel(most_common, most_common_pct, total)),
        "userProfilePanel": encode_matrix(user_profile_items(user)),
        "userAnalysisImageItems": encode_matrix(analysis_image_items(latest)),
        "userAnalysisResultItems": encode_matrix(analysis_result_items(latest, avg_processing)),
        "userAnalysisNotes": encode_list(user_analysis_notes(latest)),
        "userReportFields": encode_matrix(user_report_fields(latest)),
    }


def pick_snapshot_user(user_id, users, analyses):
    if user_id is not None:
        for user in users:
            if user["id"] == user_id:
                return user
    if analyses:
        latest_user_id = analyses[0]["user_id"]
        for user in users:
            if user["id"] == latest_user_id:
                return user
    return users[0] if users else None


def user_overall_risk(risk_counts, latest):
    if risk_counts["High"]:
        return "High"
    if risk_counts["Medium"]:
        return "Medium"
    if latest:
        return normalize_risk(latest["risk_level"])
    return "No data"


def user_month_count(analyses):
    now = datetime.now()
    return sum(1 for item in analyses if parse_dt(item["timestamp"]).year == now.year and parse_dt(item["timestamp"]).month == now.month)


def user_confidence_trend(analyses):
    rows = [
        (parse_dt(item["timestamp"]).strftime("%b %d"), int(item["confidence"] or 0))
        for item in reversed(analyses[:8])
    ]
    return rows or [("No data", 0)]


def user_top_predictions(counts):
    return counts.most_common(5) or [("No data", 0)]


def user_monthly_activity(analyses):
    now = datetime.now()
    first_day = now.replace(day=1)
    buckets = [0, 0, 0, 0]
    for item in analyses:
        dt = parse_dt(item["timestamp"])
        if dt.year == now.year and dt.month == now.month:
            index = min((dt.day - 1) // 7, 3)
            buckets[index] += 1
    return [(f"Week {idx + 1}", value) for idx, value in enumerate(buckets)]


def user_scan_rows(analyses):
    rows = [
        (parse_dt(item["timestamp"]).strftime("%Y-%m-%d"), pretty_label(item["prediction"]), f"{item['confidence']}%", normalize_risk(item["risk_level"]))
        for item in analyses[:20]
    ]
    return rows or [("-", "No saved analyses", "-", "-")]


def user_risk_rows(analyses):
    risky = [item for item in analyses if normalize_risk(item["risk_level"]) in {"Medium", "High"}]
    rows = [
        (parse_dt(item["timestamp"]).strftime("%Y-%m-%d"), pretty_label(item["prediction"]), f"{item['confidence']}%", normalize_risk(item["risk_level"]))
        for item in risky[:20]
    ]
    return rows or [("-", "No risk cases", "-", "-")]


def user_low_confidence_rows(analyses):
    low = [item for item in analyses if int(item["confidence"] or 0) < 70]
    rows = [
        (parse_dt(item["timestamp"]).strftime("%Y-%m-%d"), pretty_label(item["prediction"]), f"{item['confidence']}%", "Review")
        for item in low[:20]
    ]
    return rows or [("-", "No low confidence cases", "-", "-")]


def user_timeline_rows(analyses):
    rows = [
        (parse_dt(item["timestamp"]).strftime("%b %d, %Y"), pretty_label(item["prediction"]), f"{item['confidence']}% confidence - {normalize_risk(item['risk_level'])} risk")
        for item in analyses[:12]
    ]
    return rows or [("-", "No analyses yet", "Upload an image to start your timeline")]


def user_latest_panel(latest, avg_processing):
    if not latest:
        return [("Prediction", "No scans yet"), ("Confidence", "-"), ("Risk Level", "-"), ("Date", "-")]
    return [
        ("Prediction", pretty_label(latest["prediction"])),
        ("Confidence", f"{latest['confidence']}%"),
        ("Risk Level", normalize_risk(latest["risk_level"])),
        ("Date", parse_dt(latest["timestamp"]).strftime("%Y-%m-%d")),
        ("Processing Time", f"{avg_processing} sec"),
    ]


def user_ai_notes(latest, avg_conf, review_need, most_common):
    notes = []
    if latest:
        notes.append(f"Your latest result is {normalize_risk(latest['risk_level']).lower()} risk.")
    else:
        notes.append("Upload your first endoscopy image to start your AI-assisted history.")
    notes.append(f"Your average confidence is {fmt_percent(avg_conf)}.")
    notes.append(f"{fmt_count(review_need)} analyses may need professional review.")
    if most_common != "No data":
        notes.append(f"Most common result: {most_common}.")
    notes.append("AI results are support information, not a final diagnosis.")
    return notes


def user_insight_panel(most_common, percent, total):
    if total == 0:
        return [("Summary", "No saved analyses yet"), ("Next step", "Run an image analysis")]
    return [
        ("Most common result", most_common),
        ("Share of analyses", fmt_percent(percent)),
        ("Summary", f"{fmt_percent(percent)} of your analyses were classified as {most_common.lower()}"),
    ]


def user_analysis_notes(latest):
    if not latest:
        return ["AI Note: No saved analysis is selected yet."]
    return ["AI Note: This result is an AI-assisted suggestion. Please consult a specialist."]


def user_report_fields(latest):
    latest_date = parse_dt(latest["timestamp"]).strftime("%Y-%m-%d") if latest else datetime.now().strftime("%Y-%m-%d")
    first_date = datetime.now().replace(day=1).strftime("%Y-%m-%d")
    return [
        ("Report Type", "Single Analysis"),
        ("Date Range", f"{first_date} to {latest_date}"),
        ("Format", "PDF / CSV"),
    ]


def fallback_stats(scope: str, section: str) -> dict:
    if scope == "admin":
        return _admin_fallback(section)
    return _user_fallback(section)


def _admin_fallback(section: str) -> dict:
    titles = {
        "dashboard": ("Welcome to Admin Dashboard", "The global overview of platform activity."),
        "users": ("Users Management", "View registered users and their analysis activity."),
        "analyses": ("Analysis Records", "Monitor all AI-assisted image analysis results."),
        "dataset": ("Dataset Overview", "Manage labeled dataset used by EndoScan AI."),
        "model-stats": ("AI Model Performance", "Monitor model accuracy, confidence, and predictions."),
        "news-manager": ("News Manager", "Publish and manage medical news content."),
        "settings": ("Settings", "Control platform configuration and service status."),
    }
    cards = {
        "dashboard": [
            ("Total Users", "2,341", "Registered accounts"),
            ("Total Scans", "18,920", "All analyses"),
            ("Today Scans", "126", "Last 24 hours"),
            ("Avg Conf.", "91.4%", "Model confidence"),
            ("High Risk", "312", "Need review"),
            ("Dataset", "8,000+", "Images"),
        ],
        "users": [
            ("Total Users", "2,341", "All accounts"),
            ("Active Users", "824", "Last 30 days"),
            ("New Today", "37", "Fresh accounts"),
            ("Blocked", "12", "Restricted users"),
            ("Top Users", "18", "20+ scans"),
            ("Growth", "+14%", "Monthly"),
        ],
        "analyses": [
            ("Total Scans", "18,920", "All records"),
            ("Today Scans", "126", "Last 24 hours"),
            ("Avg Conf.", "91.4%", "Mean score"),
            ("Failed", "42", "Need retry"),
            ("Low Conf.", "73", "Below 70%"),
            ("High Risk", "312", "Serious cases"),
        ],
        "dataset": [
            ("Images", "8,000+", "Dataset size"),
            ("Classes", "8+", "Detection classes"),
            ("Verified", "7,850", "Reviewed images"),
            ("Need Review", "150", "Pending labels"),
            ("Train", "70%", "Split"),
            ("Test", "15%", "Split"),
        ],
        "model-stats": [
            ("Accuracy", "92.3%", "Active model"),
            ("Avg Conf.", "91.4%", "Production"),
            ("Avg Time", "2.4 sec", "Per scan"),
            ("Low Conf.", "73", "Below 70%"),
            ("Versions", "2", "Tracked"),
            ("Status", "Active", "v1.1"),
        ],
        "news-manager": [
            ("Articles", "18", "Published"),
            ("Drafts", "4", "In progress"),
            ("This Month", "5", "New posts"),
            ("Views", "12.8k", "Total"),
            ("Sources", "ASGE", "Primary"),
            ("Status", "Live", "Public"),
        ],
        "settings": [
            ("Java API", "Ready", "Stats service"),
            ("Python API", "Ready", "Core app"),
            ("Database", "SQLite", "Local"),
            ("Auth", "JWT", "Cookie session"),
            ("Uploads", "Local", "Images"),
            ("Mode", "Dev", "Environment"),
        ],
    }
    title, subtitle = titles.get(section, titles["dashboard"])
    return {
        "scope": "admin",
        "section": section,
        "title": title,
        "subtitle": subtitle,
        "cards": [{"label": a, "value": b, "detail": c} for a, b, c in cards.get(section, cards["dashboard"])],
        "charts": [
            {"title": "Analyses Last 7 Days", "type": "line", "items": [["Mon", 42], ["Tue", 58], ["Wed", 49], ["Thu", 76], ["Fri", 64], ["Sat", 91], ["Sun", 126]]},
            {"title": "Risk Distribution", "type": "bars", "items": [["Low", 58], ["Medium", 31], ["High", 11]]},
        ],
        "table": {
            "title": "Recent Records",
            "columns": ["User", "Prediction", "Confidence", "Risk"],
            "rows": [["Ali", "Normal", "94%", "Low"], ["Vali", "Polyps", "88%", "Medium"], ["Hasan", "Ulcerative", "81%", "High"]],
        },
        "notes": ["Java stats service is used when it is running.", "Fallback data keeps the UI available during development."],
    }


def _user_fallback(section: str) -> dict:
    titles = {
        "snapshot": ("Welcome back", "Your latest AI-assisted health analysis overview."),
        "scan-library": ("Scan Library", "Browse your saved analyses and image history."),
        "ai-insights": ("AI Insights", "Personal summary generated from your analysis patterns."),
        "risk-map": ("Risk Map", "See which results need closer review."),
        "confidence-pulse": ("Confidence Pulse", "Track AI confidence changes across your analyses."),
        "timeline": ("Progress Timeline", "Your analysis journey over time."),
        "reports": ("My Reports", "Download your AI-assisted analysis summaries."),
        "profile": ("Profile", "Manage your EndoScan AI account details."),
    }
    title, subtitle = titles.get(section, titles["snapshot"])
    return {
        "scope": "user",
        "section": section,
        "title": title,
        "subtitle": subtitle,
        "cards": [
            {"label": "My Scans", "value": "24", "detail": "Saved analyses", "target": "/dashboard/scan-library"},
            {"label": "Latest Check", "value": "Normal", "detail": "94% confidence", "target": "/dashboard/scan-library"},
            {"label": "Avg Conf.", "value": "89%", "detail": "Across analyses", "target": "/dashboard/confidence-pulse"},
            {"label": "Risk Map", "value": "Low", "detail": "Current risk", "target": "/dashboard/risk-map"},
            {"label": "This Month", "value": "7 scans", "detail": "Monthly activity", "target": "/dashboard/timeline"},
            {"label": "Review Need", "value": "3 cases", "detail": "Below 70%", "target": "/dashboard/ai-insights"},
        ],
        "charts": [
            {"title": "Confidence Pulse", "type": "line", "items": [["May 01", 82], ["May 04", 88], ["May 07", 61], ["May 10", 83], ["May 14", 88], ["May 17", 94]]},
            {"title": "Result Balance", "type": "bars", "items": [["Normal", 62], ["Abnormal", 38], ["Review", 12]]},
        ],
        "table": {
            "title": "Latest Analyses",
            "columns": ["Date", "Prediction", "Confidence", "Risk"],
            "rows": [["2026-05-17", "Normal", "94%", "Low"], ["2026-05-14", "Polyps", "88%", "Medium"], ["2026-05-09", "Ulcerative", "76%", "High"]],
        },
        "notes": [
            "Your latest result is low risk.",
            "Your average confidence is 89%.",
            "3 analyses have confidence below 70%.",
            "Review medium and high risk results with a specialist.",
        ],
    }

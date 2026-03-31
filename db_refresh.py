#!/usr/bin/env python3
"""
Database-backed data refresh for AP Dashboard.

Connects directly to the ap_learning_prod PostgreSQL database (read-only)
to pull student mastery and progress data. Merges new data with the
existing austin_way_mastery.csv — existing rows are updated, new rows are
added, but rows already present that the DB query doesn't return are KEPT.

Required env vars:
    DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
"""

import os
import csv
import logging
from pathlib import Path
from datetime import datetime

try:
    import psycopg2
    import psycopg2.extras
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
MASTERY_OUTPUT = BASE_DIR / "austin_way_mastery.csv"

FIELDNAMES = [
    "student_name", "student_email", "course", "unit_id", "unit_name",
    "mastered", "in_progress", "not_learned", "total",
    "unit_mastery_pct", "course_mastery_pct", "overall_mastery_pct",
]


def get_db_config():
    """Read DB connection params from env vars. Returns dict or None."""
    host = os.environ.get("DB_HOST")
    if not host:
        return None
    return {
        "host": host,
        "port": os.environ.get("DB_PORT", "5432"),
        "user": os.environ.get("DB_USER", "dev_team"),
        "password": os.environ.get("DB_PASSWORD", ""),
        "dbname": os.environ.get("DB_NAME", "ap_learning_prod"),
        "sslmode": "require",
    }


def get_connection():
    """Return a psycopg2 connection using env-var config, or None."""
    if not DB_AVAILABLE:
        logger.warning("psycopg2 not installed — pip install psycopg2-binary")
        return None
    cfg = get_db_config()
    if not cfg:
        return None
    try:
        conn = psycopg2.connect(**cfg)
        conn.set_session(readonly=True, autocommit=True)
        return conn
    except Exception as e:
        logger.error("DB connection failed: %s", e)
        return None


def discover_schema(conn):
    """Return a dict of {table_name: [column_name, ...]} for public tables."""
    sql = """
        SELECT table_name, column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        schema = {}
        for table, col in cur.fetchall():
            schema.setdefault(table, []).append(col)
    return schema


def _row_key(row):
    """Unique key for merging: (student_name, course, unit_id)."""
    return (
        str(row.get("student_name", "")).strip().lower(),
        str(row.get("course", "")).strip().lower(),
        str(row.get("unit_id", "")).strip().lower(),
    )


def _load_existing_csv():
    """Load the current austin_way_mastery.csv as a list of dicts."""
    if not MASTERY_OUTPUT.exists():
        return []
    try:
        with open(MASTERY_OUTPUT, "r", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    except Exception:
        return []


def _merge_rows(existing_rows, new_rows):
    """
    Merge new DB rows into existing CSV rows.
    - Rows matched by (student_name, course, unit_id) are UPDATED with new values.
    - New rows not in existing are ADDED.
    - Existing rows not in new are KEPT as-is.
    """
    existing_map = {}
    for row in existing_rows:
        existing_map[_row_key(row)] = row

    for row in new_rows:
        existing_map[_row_key(row)] = row

    return list(existing_map.values())


def _write_csv(rows):
    """Write rows to austin_way_mastery.csv."""
    with open(MASTERY_OUTPUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def refresh_mastery_from_db(conn=None):
    """
    Query the production DB for student mastery data and MERGE into
    austin_way_mastery.csv. Existing rows not returned by the DB are kept.

    Returns {"success": bool, "message": str, "rows": int, "new": int, "updated": int}.
    """
    result = {"success": False, "message": "", "rows": 0, "new": 0, "updated": 0}

    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True
    if conn is None:
        result["message"] = "No database connection (check DB_HOST env var)"
        return result

    try:
        schema = discover_schema(conn)
        if not schema:
            result["message"] = "No public tables found — check DB_NAME"
            return result

        new_rows = _query_mastery(conn, schema)
        if new_rows is None:
            result["message"] = "Could not locate student/skill tables. Run /db/schema to inspect."
            return result

        if not new_rows:
            result["message"] = "Query returned 0 rows — existing data preserved"
            return result

        existing_rows = _load_existing_csv()
        existing_keys = {_row_key(r) for r in existing_rows}
        new_keys = {_row_key(r) for r in new_rows}

        added = len(new_keys - existing_keys)
        updated = len(new_keys & existing_keys)

        merged = _merge_rows(existing_rows, new_rows)
        _write_csv(merged)

        result["success"] = True
        result["rows"] = len(merged)
        result["new"] = added
        result["updated"] = updated
        result["message"] = (
            f"DB refresh: {len(merged)} total rows "
            f"({added} added, {updated} updated, "
            f"{len(existing_keys - new_keys)} kept from previous)"
        )

    except Exception as e:
        logger.exception("DB refresh failed")
        result["message"] = f"DB error: {e}"
    finally:
        if close_conn and conn:
            conn.close()

    return result


def get_data_staleness():
    """Return how old austin_way_mastery.csv is, in hours. None if missing."""
    if not MASTERY_OUTPUT.exists():
        return None
    mtime = datetime.fromtimestamp(MASTERY_OUTPUT.stat().st_mtime)
    age = datetime.now() - mtime
    return age.total_seconds() / 3600


# ---------------------------------------------------------------------------
# Schema-adaptive query strategies
# ---------------------------------------------------------------------------

def _find_tables(schema, candidates):
    """Return the first table name from candidates that exists in schema."""
    for c in candidates:
        if c in schema:
            return c
    for c in candidates:
        for t in schema:
            if c in t:
                return t
    return None


def _pick(columns, candidates):
    """Return the first candidate that appears in columns, or None."""
    for c in candidates:
        if c in columns:
            return c
    return None


def _query_mastery(conn, schema):
    """
    Try progressively simpler query strategies until one works.
    Returns list of row-dicts in austin_way_mastery.csv format, or None.
    """
    strategies = [
        _strategy_skill_breakdown,
        _strategy_student_progress,
        _strategy_generic_progress,
    ]
    for strategy in strategies:
        try:
            rows = strategy(conn, schema)
            if rows is not None:
                return rows
        except Exception as e:
            logger.debug("Strategy %s failed: %s", strategy.__name__, e)
    return None


def _strategy_skill_breakdown(conn, schema):
    """Works if the DB has user_skills / skill_results style tables."""
    tables = list(schema.keys())
    tnames = " ".join(tables).lower()

    needs = ("user" in tnames or "student" in tnames) and "skill" in tnames
    if not needs:
        return None

    user_tbl = _find_tables(schema, ["users", "students", "user", "student"])
    skill_tbl = _find_tables(schema, [
        "user_skills", "student_skills", "user_skill_progress",
        "skill_results", "skill_progress",
    ])

    if not user_tbl or not skill_tbl:
        return None

    user_cols = [c.lower() for c in schema[user_tbl]]
    name_col = _pick(user_cols, ["display_name", "displayname", "name", "full_name", "first_name"])
    email_col = _pick(user_cols, ["email", "email_address"])
    user_id_col = _pick(user_cols, ["id", "user_id", "student_id"])

    skill_cols = [c.lower() for c in schema[skill_tbl]]
    sk_user_col = _pick(skill_cols, ["user_id", "student_id", "learner_id"])
    status_col = _pick(skill_cols, ["status", "mastery_status", "state", "mastery_level"])
    unit_ref = _pick(skill_cols, ["unit_id", "topic_id", "chapter_id"])
    course_ref = _pick(skill_cols, ["course_id", "course"])

    if not (name_col and user_id_col and sk_user_col and status_col):
        return None

    mastered_vals = "'mastered','Mastered','MASTERED','passed','completed'"
    in_progress_vals = "'in_progress','inProgress','IN_PROGRESS','started','active'"

    email_select = f"u.{email_col}" if email_col else "''"
    course_select = f"sk.{course_ref}" if course_ref else "'unknown'"
    unit_select = f"sk.{unit_ref}" if unit_ref else "''"

    sql = f"""
        SELECT
            u.{name_col}      AS student_name,
            {email_select}     AS student_email,
            {course_select}    AS course,
            {unit_select}      AS unit_id,
            {unit_select}      AS unit_name,
            COUNT(*) FILTER (WHERE sk.{status_col} IN ({mastered_vals}))     AS mastered,
            COUNT(*) FILTER (WHERE sk.{status_col} IN ({in_progress_vals}))  AS in_progress,
            COUNT(*) FILTER (WHERE sk.{status_col} NOT IN ({mastered_vals},{in_progress_vals})) AS not_learned,
            COUNT(*)           AS total
        FROM {skill_tbl} sk
        JOIN {user_tbl} u ON u.{user_id_col} = sk.{sk_user_col}
        GROUP BY u.{name_col}, {email_select}, {course_select}, {unit_select}
        ORDER BY u.{name_col}
    """

    return _run_mastery_query(conn, sql)


def _strategy_student_progress(conn, schema):
    """Works if there's a combined student_progress / learning_progress table."""
    tbl = _find_tables(schema, [
        "student_progress", "learning_progress", "learner_progress",
        "student_course_progress", "enrollments",
    ])
    if not tbl:
        return None

    cols = [c.lower() for c in schema[tbl]]
    name_or_id = _pick(cols, ["student_name", "user_name", "display_name", "user_id", "student_id"])
    course_col = _pick(cols, ["course_id", "course", "course_slug"])
    unit_col = _pick(cols, ["unit_id", "unit", "topic_id", "unit_name"])
    pct_col = _pick(cols, ["mastery_pct", "progress_pct", "completion_pct", "score", "mastery"])

    if not name_or_id or not pct_col:
        return None

    course_select = f"{tbl}.{course_col}" if course_col else "'unknown'"
    unit_select = f"{tbl}.{unit_col}" if unit_col else "''"

    sql = f"""
        SELECT
            {tbl}.{name_or_id} AS student_name,
            '' AS student_email,
            {course_select} AS course,
            {unit_select} AS unit_id,
            {unit_select} AS unit_name,
            COALESCE({tbl}.{pct_col}, 0) AS mastery_pct
        FROM {tbl}
        ORDER BY {tbl}.{name_or_id}
    """
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(sql)
        raw = [dict(r) for r in cur.fetchall()]

    rows = []
    for r in raw:
        pct = float(r.get("mastery_pct") or 0)
        total = 100
        mastered = int(pct)
        rows.append({
            "student_name": r["student_name"],
            "student_email": r.get("student_email", ""),
            "course": r["course"],
            "unit_id": r.get("unit_id", ""),
            "unit_name": r.get("unit_name", ""),
            "mastered": mastered,
            "in_progress": 0,
            "not_learned": total - mastered,
            "total": total,
            "unit_mastery_pct": round(pct, 1),
            "course_mastery_pct": 0,
            "overall_mastery_pct": 0,
        })
    return rows if rows else None


def _strategy_generic_progress(conn, schema):
    """Last resort: look for any table with 'progress' or 'mastery' in name."""
    candidates = [t for t in schema if "progress" in t or "mastery" in t or "result" in t]
    if not candidates:
        return None

    for tbl in candidates:
        cols = [c.lower() for c in schema[tbl]]
        id_col = _pick(cols, ["user_id", "student_id", "learner_id", "id"])
        if not id_col:
            continue

        sql = f"SELECT * FROM {tbl} LIMIT 500"
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(sql)
            raw = [dict(r) for r in cur.fetchall()]

        if raw:
            rows = []
            for r in raw:
                rows.append({
                    "student_name": str(r.get("student_name") or r.get("user_id") or r.get("student_id") or r.get("id", "")),
                    "student_email": str(r.get("email") or r.get("student_email") or ""),
                    "course": str(r.get("course_id") or r.get("course") or "unknown"),
                    "unit_id": str(r.get("unit_id") or r.get("topic_id") or ""),
                    "unit_name": str(r.get("unit_name") or r.get("unit_id") or ""),
                    "mastered": int(r.get("mastered") or r.get("score") or 0),
                    "in_progress": int(r.get("in_progress") or 0),
                    "not_learned": int(r.get("not_learned") or 0),
                    "total": int(r.get("total") or r.get("total_skills") or 0),
                    "unit_mastery_pct": float(r.get("mastery_pct") or r.get("progress_pct") or 0),
                    "course_mastery_pct": float(r.get("course_mastery_pct") or 0),
                    "overall_mastery_pct": float(r.get("overall_mastery_pct") or 0),
                })
            return rows if rows else None

    return None


def _run_mastery_query(conn, sql):
    """Execute a mastery SQL, compute rollup percentages, return CSV-format rows."""
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(sql)
        raw = [dict(r) for r in cur.fetchall()]

    if not raw:
        return []

    course_totals = {}
    for r in raw:
        key = (r["student_name"], r["course"])
        ct = course_totals.setdefault(key, {"mastered": 0, "total": 0})
        ct["mastered"] += int(r.get("mastered") or 0)
        ct["total"] += int(r.get("total") or 0)

    overall_totals = {}
    for (name, _), ct in course_totals.items():
        ot = overall_totals.setdefault(name, {"mastered": 0, "total": 0})
        ot["mastered"] += ct["mastered"]
        ot["total"] += ct["total"]

    rows = []
    for r in raw:
        m = int(r.get("mastered") or 0)
        ip = int(r.get("in_progress") or 0)
        nl = int(r.get("not_learned") or 0)
        total = int(r.get("total") or 0)
        unit_pct = round((m / total) * 100, 1) if total > 0 else 0

        ct = course_totals.get((r["student_name"], r["course"]), {})
        course_pct = round((ct["mastered"] / ct["total"]) * 100, 1) if ct.get("total") else 0

        ot = overall_totals.get(r["student_name"], {})
        overall_pct = round((ot["mastered"] / ot["total"]) * 100, 1) if ot.get("total") else 0

        rows.append({
            "student_name": r["student_name"],
            "student_email": r.get("student_email", ""),
            "course": r["course"],
            "unit_id": r.get("unit_id", ""),
            "unit_name": r.get("unit_name", ""),
            "mastered": m,
            "in_progress": ip,
            "not_learned": nl,
            "total": total,
            "unit_mastery_pct": unit_pct,
            "course_mastery_pct": course_pct,
            "overall_mastery_pct": overall_pct,
        })

    return rows

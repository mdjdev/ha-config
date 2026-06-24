#!/usr/bin/env python3
import json
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = "/config/playbee.db"
EXPORT_DIR = "/config/playbee/exports"
DEFAULT_RETENTION = 14


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def validate_identifier(value):
    value = str(value or "")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError(f"invalid identifier: {value}")
    return value


def normalize_shuffle_mode(value):
    if isinstance(value, bool):
        return "on" if value else "off"
    value = str(value or "").strip().lower()
    return "on" if value in {"1", "true", "on", "yes"} else "off"


def normalize_repeat_mode(value):
    if isinstance(value, bool):
        return "all" if value else "off"

    value = str(value or "").strip().lower()

    mapping = {
        "": "off",
        "0": "off",
        "false": "off",
        "off": "off",
        "none": "off",
        "no": "off",

        "1": "one",
        "one": "one",
        "track": "one",
        "single": "one",

        "2": "all",
        "true": "all",
        "on": "all",
        "yes": "all",
        "all": "all",
        "playlist": "all",
        "queue": "all",
    }

    return mapping.get(value, "off")


def normalize_resume_mode(value):
    value = str(value or "").strip().lower()

    if value in {"", "0", "false", "off", "none", "no"}:
        return "off"

    if re.fullmatch(r"\d+[hd]", value):
        return value

    if value.isdigit():
        return f"{value}h"

    return "off"


def init_db():
    conn = connect()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tags (
            tag_uid TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            media_url TEXT NOT NULL,
            shuffle_mode TEXT NOT NULL DEFAULT 'off',
            repeat_mode TEXT NOT NULL DEFAULT 'off',
            resume_mode TEXT NOT NULL DEFAULT 'off',
            resume_data TEXT DEFAULT NULL
        )
    """)
    conn.commit()
    conn.close()
    print(json.dumps({"ok": True, "action": "init"}))


def save_resume(tag_uid, queue_id, track_id, position):
    resume_data = json.dumps({
        "last_updated": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "track_id": track_id,
        "position": int(float(position)),
        "queue_id": queue_id
    })
    conn = connect()
    conn.execute("""
        UPDATE tags
        SET resume_data = ?
        WHERE tag_uid = ?
    """, (resume_data, tag_uid))
    conn.commit()
    conn.close()
    print(json.dumps({"ok": True, "action": "save_resume", "tag_uid": tag_uid}))


def clear_resume(tag_uid):
    conn = connect()
    conn.execute("""
        UPDATE tags
        SET resume_data = NULL
        WHERE tag_uid = ?
    """, (tag_uid,))
    conn.commit()
    conn.close()
    print(json.dumps({"ok": True, "action": "clear_resume", "tag_uid": tag_uid}))


def row_to_tag_payload(row, fallback=None):
    if row is None:
        return {"found": False, **(fallback or {})}

    parsed_resume_data = None
    if row["resume_data"]:
        try:
            parsed_resume_data = json.loads(row["resume_data"])
        except Exception:
            parsed_resume_data = None

    return {
        "found": True,
        "tag_uid": row["tag_uid"],
        "name": row["name"],
        "media_url": row["media_url"],
        "shuffle_mode": normalize_shuffle_mode(row["shuffle_mode"]),
        "repeat_mode": normalize_repeat_mode(row["repeat_mode"]),
        "resume_mode": normalize_resume_mode(row["resume_mode"]),
        "resume_data": parsed_resume_data
    }


def get_tag_by_id(tag_uid):
    conn = connect()
    row = conn.execute("""
        SELECT tag_uid, name, media_url, shuffle_mode, repeat_mode, resume_mode, resume_data
        FROM tags
        WHERE tag_uid = ?
    """, (tag_uid,)).fetchone()
    conn.close()

    print(json.dumps(row_to_tag_payload(row, {"tag_uid": tag_uid})))


def get_tag_by_name(name):
    conn = connect()
    row = conn.execute("""
        SELECT tag_uid, name, media_url, shuffle_mode, repeat_mode, resume_mode, resume_data
        FROM tags
        WHERE name = ?
    """, (name,)).fetchone()
    conn.close()

    print(json.dumps(row_to_tag_payload(row, {"name": name})))


def prune_json_exports(retention_days):
    deleted = []
    export_dir = Path(EXPORT_DIR)

    if not export_dir.exists():
        return deleted

    cutoff = datetime.now(timezone.utc).timestamp() - (retention_days * 86400)

    for path in export_dir.rglob("*.json"):
        try:
            if path.is_file() and path.stat().st_mtime < cutoff:
                path.unlink()
                deleted.append(str(path))
        except FileNotFoundError:
            pass

    return deleted


def list_user_tables(conn):
    rows = conn.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """).fetchall()
    return [row["name"] for row in rows]


def list_table_columns(conn, table_name):
    table_name = validate_identifier(table_name)
    rows = conn.execute(f'PRAGMA table_info("{table_name}")').fetchall()
    if not rows:
        raise ValueError(f"table not found: {table_name}")
    return [row["name"] for row in rows]


def export_table_json(conn, table_name, timestamp):
    table_name = validate_identifier(table_name)
    columns = list_table_columns(conn, table_name)

    table_dir = os.path.join(EXPORT_DIR, table_name)
    os.makedirs(table_dir, exist_ok=True)

    quoted_columns = ", ".join(f'"{col}"' for col in columns)
    rows = conn.execute(f'SELECT {quoted_columns} FROM "{table_name}"').fetchall()

    data = []
    for row in rows:
        item = {}
        for col in columns:
            item[col] = row[col]
        data.append(item)

    export_path = os.path.join(table_dir, f"{table_name}_{timestamp}.json")

    with open(export_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    return {
        "table": table_name,
        "row_count": len(data),
        "export_path": export_path
    }


def export_all_tables_json(retention_days=DEFAULT_RETENTION):
    os.makedirs(EXPORT_DIR, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")

    conn = connect()
    try:
        tables = list_user_tables(conn)
        exports = [export_table_json(conn, table_name, timestamp) for table_name in tables]
    finally:
        conn.close()

    deleted_exports = prune_json_exports(retention_days)

    print(json.dumps({
        "ok": True,
        "action": "export_all_tables_json",
        "export_dir": EXPORT_DIR,
        "retention_days": retention_days,
        "deleted_exports": deleted_exports,
        "table_count": len(exports),
        "tables": exports
    }))


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"ok": False, "error": "missing action"}))
        sys.exit(1)

    action = sys.argv[1]

    if action == "init":
        init_db()
    elif action == "save_resume" and len(sys.argv) == 6:
        save_resume(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
    elif action == "clear_resume" and len(sys.argv) == 3:
        clear_resume(sys.argv[2])
    elif action == "get_tag_by_id" and len(sys.argv) == 3:
        get_tag_by_id(sys.argv[2])
    elif action == "get_tag_by_name" and len(sys.argv) == 3:
        get_tag_by_name(sys.argv[2])
    elif action == "export_all_tables_json":
        retention_days = DEFAULT_RETENTION
        if len(sys.argv) == 3:
            retention_days = int(sys.argv[2])
        export_all_tables_json(retention_days)
    else:
        print(json.dumps({"ok": False, "error": "invalid arguments"}))
        sys.exit(1)


if __name__ == "__main__":
    main()

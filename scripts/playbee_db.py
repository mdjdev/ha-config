#!/usr/bin/env python3
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone

DB_PATH = "/config/playbee.db"


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


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


def upsert_tag(tag_uid, name, media_url, shuffle_mode, repeat_mode, resume_mode):
    conn = connect()
    conn.execute("""
        INSERT INTO tags (tag_uid, name, media_url, shuffle_mode, repeat_mode, resume_mode)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(tag_uid) DO UPDATE SET
            name=excluded.name,
            media_url=excluded.media_url,
            shuffle_mode=excluded.shuffle_mode,
            repeat_mode=excluded.repeat_mode,
            resume_mode=excluded.resume_mode
    """, (
        tag_uid,
        name,
        media_url,
        normalize_shuffle_mode(shuffle_mode),
        normalize_repeat_mode(repeat_mode),
        normalize_resume_mode(resume_mode)
    ))
    conn.commit()
    conn.close()
    print(json.dumps({"ok": True, "action": "upsert_tag", "tag_uid": tag_uid}))


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


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"ok": False, "error": "missing action"}))
        sys.exit(1)

    action = sys.argv[1]

    if action == "init":
        init_db()
    elif action == "upsert_tag" and len(sys.argv) == 8:
        upsert_tag(
            sys.argv[2],
            sys.argv[3],
            sys.argv[4],
            sys.argv[5],
            sys.argv[6],
            sys.argv[7]
        )
    elif action == "save_resume" and len(sys.argv) == 6:
        save_resume(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
    elif action == "clear_resume" and len(sys.argv) == 3:
        clear_resume(sys.argv[2])
    elif action == "get_tag_by_id" and len(sys.argv) == 3:
        get_tag_by_id(sys.argv[2])
    elif action == "get_tag_by_name" and len(sys.argv) == 3:
        get_tag_by_name(sys.argv[2])
    else:
        print(json.dumps({"ok": False, "error": "invalid arguments"}))
        sys.exit(1)


if __name__ == "__main__":
    main()

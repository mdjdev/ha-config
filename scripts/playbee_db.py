#!/usr/bin/env python3
import json
import sqlite3
import sys

DB_PATH = "/config/playbee.db"


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = connect()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tags (
            tag_uid TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            media_url TEXT NOT NULL,
            shuffle INTEGER NOT NULL DEFAULT 0,
            repeat_mode TEXT NOT NULL DEFAULT 'off',
            resume INTEGER NOT NULL DEFAULT 0,
            resume_data TEXT DEFAULT NULL
        )
    """)
    conn.commit()
    conn.close()
    print(json.dumps({"ok": True, "action": "init"}))


def upsert_tag(tag_uid, name, media_url, shuffle, repeat_mode, resume):
    conn = connect()
    conn.execute("""
        INSERT INTO tags (tag_uid, name, media_url, shuffle, repeat_mode, resume)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(tag_uid) DO UPDATE SET
            name=excluded.name,
            media_url=excluded.media_url,
            shuffle=excluded.shuffle,
            repeat_mode=excluded.repeat_mode,
            resume=excluded.resume
    """, (tag_uid, name, media_url, int(shuffle), repeat_mode, int(resume)))
    conn.commit()
    conn.close()
    print(json.dumps({"ok": True, "action": "upsert_tag", "tag_uid": tag_uid}))


def save_resume(tag_uid, queue_id, track_id, position):
    resume_data = json.dumps({
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
        "shuffle": bool(row["shuffle"]),
        "repeat_mode": row["repeat_mode"],
        "resume": bool(row["resume"]),
        "resume_data": parsed_resume_data
    }


def get_tag_by_id(tag_uid):
    conn = connect()
    row = conn.execute("""
        SELECT tag_uid, name, media_url, shuffle, repeat_mode, resume, resume_data
        FROM tags
        WHERE tag_uid = ?
    """, (tag_uid,)).fetchone()
    conn.close()

    print(json.dumps(row_to_tag_payload(row, {"tag_uid": tag_uid})))


def get_tag_by_name(name):
    conn = connect()
    row = conn.execute("""
        SELECT tag_uid, name, media_url, shuffle, repeat_mode, resume, resume_data
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
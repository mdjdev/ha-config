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
            shuffle INTEGER NOT NULL DEFAULT 0 CHECK (shuffle IN (0, 1)),
            repeat_mode TEXT NOT NULL DEFAULT 'off' CHECK (repeat_mode IN ('off', 'one', 'all'))
        )
    """)
    conn.commit()
    conn.close()
    print(json.dumps({"ok": True, "action": "init"}))

def upsert_tag(tag_uid, name, media_url, shuffle, repeat_mode):
    conn = connect()
    conn.execute("""
        INSERT INTO tags (tag_uid, name, media_url, shuffle, repeat_mode)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(tag_uid) DO UPDATE SET
            name=excluded.name,
            media_url=excluded.media_url,
            shuffle=excluded.shuffle,
            repeat_mode=excluded.repeat_mode
    """, (tag_uid, name, media_url, int(shuffle), repeat_mode))
    conn.commit()
    conn.close()
    print(json.dumps({"ok": True, "action": "upsert_tag", "tag_uid": tag_uid}))

def get_tag(tag_uid):
    conn = connect()
    row = conn.execute("""
        SELECT tag_uid, name, media_url, shuffle, repeat_mode
        FROM tags
        WHERE tag_uid = ?
    """, (tag_uid,)).fetchone()
    conn.close()

    if row is None:
        print(json.dumps({"found": False, "tag_uid": tag_uid}))
        return

    print(json.dumps({
        "found": True,
        "tag_uid": row["tag_uid"],
        "name": row["name"],
        "media_url": row["media_url"],
        "shuffle": bool(row["shuffle"]),
        "repeat_mode": row["repeat_mode"]
    }))

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"ok": False, "error": "missing action"}))
        sys.exit(1)

    action = sys.argv[1]

    if action == "init":
        init_db()
    elif action == "upsert_tag" and len(sys.argv) == 7:
        upsert_tag(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6])
    elif action == "get_tag" and len(sys.argv) == 3:
        get_tag(sys.argv[2])
    else:
        print(json.dumps({"ok": False, "error": "invalid arguments"}))
        sys.exit(1)

if __name__ == "__main__":
    main()
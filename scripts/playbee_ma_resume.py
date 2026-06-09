#!/usr/bin/env python3
import json
import sys
import urllib.request
import urllib.error

def main():
    if len(sys.argv) != 6:
        print(json.dumps({
            "ok": False,
            "error": "invalid arguments",
            "expected": "queue_id media_url track_id ha_url ha_token"
        }))
        sys.exit(1)

    queue_id = sys.argv[1]
    media_url = sys.argv[2]
    track_id = sys.argv[3]
    ha_url = sys.argv[4].rstrip("/")
    ha_token = sys.argv[5]

    api_url = f"{ha_url}/api"

    payload = {
        "message_id": "1",
        "command": "player_queues/play_media",
        "args": {
            "queue_id": queue_id,
            "media": media_url,
            "radio_mode": False,
            "start_item": track_id
        }
    }

    req = urllib.request.Request(
        api_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {ha_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            body = response.read().decode("utf-8", errors="ignore")
            print(json.dumps({
                "ok": True,
                "status": response.status,
                "body": body
            }))
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8", errors="ignore")
        print(json.dumps({
            "ok": False,
            "error": "http_error",
            "status": err.code,
            "body": body
        }))
        sys.exit(1)
    except Exception as err:
        print(json.dumps({
            "ok": False,
            "error": str(err)
        }))
        sys.exit(1)

if __name__ == "__main__":
    main()
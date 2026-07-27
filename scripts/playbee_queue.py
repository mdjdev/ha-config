#!/usr/bin/env python3
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib import request, error

SECRETS_FILE = Path("/config/secrets.yaml")
API_URL_KEY = "playbee_ma_api_url"
TOKEN_KEY = "playbee_ma_token"
LOG_DIR = "/config/playbee/logs"


def fail(error_name, exit_code=1, **extra):
    payload = {"ok": False, "error": error_name}
    payload.update(extra)
    print(json.dumps(payload))
    sys.exit(exit_code)


def normalize(value: str) -> str:
    return str(value or "").lower().replace("://", "").replace("/", "").replace(":", "")


def load_config():
    if not SECRETS_FILE.exists():
        raise FileNotFoundError(f"Secrets file not found: {SECRETS_FILE}")

    values = {}
    for line in SECRETS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip().strip("'").strip('"')

    api_url = values.get(API_URL_KEY)
    token = values.get(TOKEN_KEY)

    if not api_url:
        raise KeyError(f"Missing key: {API_URL_KEY}")
    if not token:
        raise KeyError(f"Missing key: {TOKEN_KEY}")

    return api_url.rstrip("/"), token


def post_json(url: str, token: str, payload: dict):
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": token,
        },
        method="POST",
    )
    with request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8")
        if not raw.strip():
            return {}
        return json.loads(raw)


def get_queue_items(queue_id: str):
    try:
        api_url, token = load_config()
    except Exception as err:
        fail("config_load_failed", message=str(err))

    payload = {
        "message_id": "playbee-queue-items",
        "command": "player_queues/items",
        "args": {
            "queue_id": queue_id
        }
    }

    try:
        response = post_json(api_url, token, payload)
    except error.HTTPError as err:
        detail = err.read().decode("utf-8", errors="ignore")
        fail("http_error", status=err.code, message=detail)
    except Exception as err:
        fail("request_failed", message=str(err))

    if not isinstance(response, list):
        fail(
            "unexpected_shape",
            message="Expected queue items array",
            response_type=type(response).__name__
        )

    return response


def find_item_for_track(queue_id: str, track_id: str):
    response = get_queue_items(queue_id)
    track_id_normalized = normalize(track_id)

    for index, item in enumerate(response):
        if not isinstance(item, dict):
            continue

        media_item = item.get("media_item", {}) or {}
        item_uri = media_item.get("uri", "")
        item_provider = media_item.get("provider", "")
        item_item_id = media_item.get("item_id", "")
        title = media_item.get("name", "")
        queue_item_id = item.get("queue_item_id", "")

        item_uri_normalized = normalize(item_uri)
        rebuilt_uri_normalized = normalize(f"{item_provider}://track/{item_item_id}")
        rebuilt_uri_alt_normalized = normalize(f"{item_provider}track{item_item_id}")

        if (
            item_uri == track_id
            or item_uri_normalized == track_id_normalized
            or rebuilt_uri_normalized == track_id_normalized
            or rebuilt_uri_alt_normalized == track_id_normalized
        ):
            print(json.dumps({
                "ok": True,
                "found": True,
                "action": "find_item_for_track",
                "queue_id": queue_id,
                "track_id": track_id,
                "index": index,
                "queue_item_id": queue_item_id,
                "item_uri": item_uri,
                "title": title
            }))
            sys.exit(0)

    os.makedirs(LOG_DIR, exist_ok=True)
    dump_filename = f"queue_dump_{datetime.now(timezone.utc).strftime('%Y-%m-%d_%H-%M-%S')}.json"
    dump_path = os.path.join(LOG_DIR, dump_filename)
    with open(dump_path, "w", encoding="utf-8") as f:
        json.dump(response, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(json.dumps({
        "ok": True,
        "found": False,
        "action": "find_item_for_track",
        "queue_id": queue_id,
        "track_id": track_id,
        "log_file": dump_path
    }))
    sys.exit(0)


def main():
    if len(sys.argv) < 2:
        fail("missing_action")

    action = sys.argv[1]

    if action == "find_item_for_track" and len(sys.argv) == 4:
        find_item_for_track(sys.argv[2], sys.argv[3])
    else:
        fail("invalid_arguments", action=action)


if __name__ == "__main__":
    main()

import os
import json
import time
from typing import Any

LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
DEFAULT_LOG_FILE = os.path.join(LOG_DIR, "sm_responses.log")


def _ensure_log_dir():
    os.makedirs(LOG_DIR, exist_ok=True)


def _safe_json(obj: Any):
    try:
        return json.loads(json.dumps(obj))
    except Exception:
        try:
            return json.loads(str(obj))
        except Exception:
            return str(obj)


def log_supermemory_response(response, *, filename: str | None = None):
    """Log a requests.Response (or dict-like) to a timestamped JSON entry inside the log file.

    If `filename` is provided it's written relative to the repository; otherwise the default
    `logs/sm_responses.log` is used (newline-delimited JSON entries).
    """
    _ensure_log_dir()
    target = filename if filename else DEFAULT_LOG_FILE

    entry = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status_code": None,
        "headers": None,
        "body": None,
    }

    # If it's a requests.Response, extract fields safely
    try:
        import requests
        if isinstance(response, requests.Response):
            entry["status_code"] = response.status_code
            # Convert headers to a plain dict
            entry["headers"] = dict(response.headers)
            try:
                entry["body"] = response.json()
            except Exception:
                entry["body"] = response.text
        else:
            # Try treating response as a dict-like object
            entry["body"] = _safe_json(response)
    except Exception:
        # Fallback: stringify
        entry["body"] = str(response)

    # Append newline-delimited JSON
    try:
        with open(target, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False))
            fh.write("\n")
    except Exception as e:
        # If writing fails, fall back to printing to stdout so caller can still see info
        print("SM_LOGGER ERROR: failed to write log:", e)
        print(json.dumps(entry, ensure_ascii=False, indent=2))

    return entry

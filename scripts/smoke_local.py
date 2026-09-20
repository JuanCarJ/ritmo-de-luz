from __future__ import annotations

import json
import urllib.request

BASE = "http://127.0.0.1:8000"

def main() -> int:
    with urllib.request.urlopen(BASE + "/health", timeout=5) as response:
        health = json.loads(response.read())
    assert health["status"] == "ok"
    with urllib.request.urlopen(BASE + "/api/demo", timeout=5) as response:
        demo = json.loads(response.read())
    assert demo["bands"] == 12
    print("local smoke: OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())


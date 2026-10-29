"""Create a 24-hour execution window in a fresh reproducibility checkout."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    if not (root / ".project-root").is_file():
        raise SystemExit("Run from a complete RQMC project checkout")
    clock = root / "state" / "supplement_v2" / "experimental_clock.json"
    locks = (
        root / "state" / "rescue_v1" / "RUN.lock",
        root / "state" / "supplement_v2" / "s2_s3.lock",
    )
    if clock.exists():
        raise SystemExit("Clock already exists; preserve it and use a fresh checkout")
    if any(path.exists() for path in locks):
        raise SystemExit("A research run is active; do not start another clock")
    started = datetime.now(timezone.utc)
    payload = {
        "started_utc": started.isoformat(),
        "deadline_utc": (started + timedelta(hours=24)).isoformat(),
        "scope": "S1-S3 supplementary experimental wall-clock cap",
    }
    clock.parent.mkdir(parents=True, exist_ok=True)
    clock.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()

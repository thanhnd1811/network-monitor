#!/usr/bin/env python3
"""
Network monitor for university campus IP lines.

Reads monitor/ips.json, pings each line (ICMP -> TCP fallback),
writes data/status.json and updates data/history.json.

Designed to run on:
- GitHub Actions (Ubuntu runner) every ~5 minutes via cron workflow
- Locally on Windows for testing
"""

import io
import json
import os
import platform
import socket
import subprocess
import sys
import time

# Ensure UTF-8 stdout on Windows so Vietnamese names print correctly
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IPS_FILE = ROOT / "monitor" / "ips.json"
STATUS_FILE = ROOT / "data" / "status.json"
HISTORY_FILE = ROOT / "data" / "history.json"

# Keep last N status changes per line
HISTORY_KEEP = 50
# Cap history file size
MAX_TOTAL_EVENTS = 2000


def icmp_ping(ip: str, timeout_s: int) -> bool:
    """Try ICMP ping. Returns True if host responds."""
    is_windows = platform.system().lower() == "windows"
    if is_windows:
        cmd = ["ping", "-n", "1", "-w", str(timeout_s * 1000), ip]
        flags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
    else:
        cmd = ["ping", "-c", "1", "-W", str(timeout_s), ip]
        flags = 0
    try:
        r = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout_s + 2,
            creationflags=flags,
        )
        return r.returncode == 0
    except Exception:
        return False


def tcp_check(ip: str, port: int, timeout_s: int) -> bool:
    """Try opening a TCP connection. RST or accept both prove host is up."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout_s)
            s.connect((ip, port))
            return True
    except ConnectionRefusedError:
        # Refused = host responded with RST = host is alive
        return True
    except (socket.timeout, OSError):
        return False


def check_line(line: dict, settings: dict) -> dict:
    """Check one line. Returns status dict."""
    ip = line["ip"]
    timeout = settings.get("ping_timeout_seconds", 3)
    fallback_ports = settings.get("tcp_fallback_ports", [80, 443, 53])

    t0 = time.monotonic()
    method = "icmp"
    up = icmp_ping(ip, timeout)

    if not up:
        for port in fallback_ports:
            if tcp_check(ip, port, timeout):
                up = True
                method = f"tcp/{port}"
                break

    latency_ms = int((time.monotonic() - t0) * 1000)

    return {
        "id": line["id"],
        "name": line["name"],
        "isp": line["isp"],
        "type": line["type"],
        "ip": ip,
        "ip_range": line.get("ip_range"),
        "up": up,
        "method": method if up else "none",
        "latency_ms": latency_ms,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


def main() -> int:
    config = load_json(IPS_FILE, None)
    if config is None:
        print(f"Cannot read {IPS_FILE}", file=sys.stderr)
        return 1

    settings = config.get("settings", {})
    locations = config["locations"]

    # Flatten lines for parallel ping
    all_lines = []
    for loc in locations:
        for line in loc["lines"]:
            all_lines.append((loc["id"], line))

    print(f"Checking {len(all_lines)} lines in parallel...")

    results_by_id = {}
    with ThreadPoolExecutor(max_workers=20) as ex:
        futures = {ex.submit(check_line, line, settings): (loc_id, line) for loc_id, line in all_lines}
        for fut in as_completed(futures):
            loc_id, line = futures[fut]
            try:
                res = fut.result()
            except Exception as e:
                res = {
                    "id": line["id"], "name": line["name"], "isp": line["isp"],
                    "type": line["type"], "ip": line["ip"],
                    "ip_range": line.get("ip_range"),
                    "up": False, "method": "error", "latency_ms": 0,
                    "checked_at": datetime.now(timezone.utc).isoformat(),
                    "error": str(e),
                }
            results_by_id[res["id"]] = res
            mark = "OK " if res["up"] else "DOWN"
            print(f"  [{mark}] {res['name']:32s} {res['ip']:18s} ({res['method']}, {res['latency_ms']}ms)")

    # Build the status output, preserving location grouping
    now_iso = datetime.now(timezone.utc).isoformat()
    locations_out = []
    total = 0
    down = 0
    for loc in locations:
        loc_lines = []
        loc_down = 0
        for line in loc["lines"]:
            r = results_by_id[line["id"]]
            loc_lines.append(r)
            total += 1
            if not r["up"]:
                down += 1
                loc_down += 1
        locations_out.append({
            "id": loc["id"],
            "name": loc["name"],
            "down_count": loc_down,
            "total_count": len(loc["lines"]),
            "lines": loc_lines,
        })

    status = {
        "school": config.get("school"),
        "generated_at": now_iso,
        "summary": {"total": total, "up": total - down, "down": down},
        "locations": locations_out,
    }
    save_json(STATUS_FILE, status)
    print(f"Wrote {STATUS_FILE}")

    # Update history: only record state changes (up <-> down)
    prev_status = load_json(STATUS_FILE.with_name("status.prev.json"), None)
    history = load_json(HISTORY_FILE, {"events": []})
    events = history.get("events", [])

    if prev_status:
        prev_by_id = {}
        for loc in prev_status.get("locations", []):
            for ln in loc["lines"]:
                prev_by_id[ln["id"]] = ln.get("up", True)

        for line_id, res in results_by_id.items():
            if line_id in prev_by_id and prev_by_id[line_id] != res["up"]:
                events.append({
                    "at": now_iso,
                    "id": line_id,
                    "name": res["name"],
                    "ip": res["ip"],
                    "from_up": prev_by_id[line_id],
                    "to_up": res["up"],
                })

    # Cap history size
    if len(events) > MAX_TOTAL_EVENTS:
        events = events[-MAX_TOTAL_EVENTS:]
    save_json(HISTORY_FILE, {"events": events})

    # Save current as prev for next run
    save_json(STATUS_FILE.with_name("status.prev.json"), status)

    print(f"Summary: {total - down}/{total} up, {down} down")
    return 0


if __name__ == "__main__":
    sys.exit(main())

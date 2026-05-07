"""
Local network probe — runs INSIDE the school network on a 24/7 PC.

What it does:
  1. Pings all 26 IPs from the local PC's perspective (ICMP + TCP fallback)
  2. Detects this PC's own public IP. If that IP is in the monitored list,
     marks it as UP automatically (because we're literally online via that line)
  3. Pushes the result to data/status.json in the GitHub repo via the
     GitHub Contents API (no git CLI required)

Why this beats GitHub Actions monitor:
  - From inside Vietnam, ISPs allow much more traffic between domestic IPs
    than from foreign IPs (GitHub runners are in US/EU)
  - Result: ~95% accuracy vs ~10-20% for foreign-origin probes

Run as Windows Task every 1-2 minutes. Configure with config.json next to
the executable.
"""

from __future__ import annotations

import base64
import io
import json
import os
import platform
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

# Ensure UTF-8 console output on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


# ----- where to find files -----
def app_dir() -> Path:
    """Return the directory containing the running script or frozen exe."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


HERE = app_dir()
CONFIG_FILE = HERE / "config.json"
LOG_FILE = HERE / "probe.log"


# ----- logging -----
def log(msg: str) -> None:
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)
    try:
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


# ----- probe logic (mirrors monitor/check.py) -----
def icmp_ping(ip: str, timeout_s: int) -> bool:
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
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout_s)
            s.connect((ip, port))
            return True
    except ConnectionRefusedError:
        return True
    except (socket.timeout, OSError):
        return False


def check_line(line: dict, settings: dict) -> dict:
    ip = line["ip"]
    timeout = settings.get("ping_timeout_seconds", 3)
    fallback_ports = settings.get("tcp_fallback_ports", [80, 443, 53])

    t0 = time.monotonic()
    method = "icmp"
    up = icmp_ping(ip, timeout)

    if not up and fallback_ports:
        with ThreadPoolExecutor(max_workers=len(fallback_ports)) as pex:
            futures = {pex.submit(tcp_check, ip, p, timeout): p for p in fallback_ports}
            for fut in as_completed(futures):
                port = futures[fut]
                try:
                    if fut.result():
                        up = True
                        method = f"tcp/{port}"
                        for f in futures:
                            f.cancel()
                        break
                except Exception:
                    pass

    return {
        "id": line["id"],
        "name": line["name"],
        "isp": line["isp"],
        "type": line["type"],
        "ip": ip,
        "ip_range": line.get("ip_range"),
        "up": up,
        "method": method if up else "none",
        "latency_ms": int((time.monotonic() - t0) * 1000),
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


# ----- self-IP detection (so we don't false-down our OWN line) -----
def get_my_public_ip(timeout_s: int = 5) -> str | None:
    """Try multiple services to learn my outgoing public IP."""
    services = [
        "https://api.ipify.org",
        "https://ifconfig.me/ip",
        "https://icanhazip.com",
    ]
    for url in services:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ftu-netmon/1.0"})
            with urllib.request.urlopen(req, timeout=timeout_s) as r:
                ip = r.read().decode("utf-8").strip()
                # Basic sanity check
                parts = ip.split(".")
                if len(parts) == 4 and all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
                    return ip
        except Exception:
            continue
    return None


# ----- GitHub Contents API push -----
def github_get_file_sha(token: str, owner: str, repo: str, path: str) -> str | None:
    """Get current SHA of file in repo (needed for update). Returns None if file doesn't exist."""
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "ftu-netmon/1.0",
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode("utf-8"))
            return data.get("sha")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def github_put_file(token: str, owner: str, repo: str, path: str,
                    content_bytes: bytes, message: str, sha: str | None) -> None:
    """Create or update a file via GitHub Contents API."""
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    body = {
        "message": message,
        "content": base64.b64encode(content_bytes).decode("ascii"),
        "branch": "main",
    }
    if sha:
        body["sha"] = sha
    req = urllib.request.Request(
        url,
        method="PUT",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "ftu-netmon/1.0",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        r.read()  # drain


# ----- main -----
def main() -> int:
    if not CONFIG_FILE.exists():
        log(f"FATAL: missing {CONFIG_FILE}. Edit config.json.example and rename to config.json.")
        return 2

    cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))

    token = cfg.get("github_token", "").strip()
    owner = cfg.get("github_owner", "").strip()
    repo = cfg.get("github_repo", "").strip()
    if not token or not owner or not repo:
        log("FATAL: github_token / github_owner / github_repo missing in config.json.")
        return 2

    school = cfg.get("school", "Đại học Ngoại thương")
    settings = cfg.get("settings", {})
    locations = cfg.get("locations", [])
    if not locations:
        log("FATAL: no locations defined in config.json.")
        return 2

    # Flatten lines + ping in parallel
    all_lines: list[tuple[str, dict]] = []
    for loc in locations:
        for line in loc.get("lines", []):
            all_lines.append((loc["id"], line))

    log(f"Probing {len(all_lines)} IPs from local network...")

    results: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=20) as ex:
        futures = {ex.submit(check_line, line, settings): line for _, line in all_lines}
        for fut in as_completed(futures):
            line = futures[fut]
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
            results[res["id"]] = res

    # Self-IP override: if our outgoing public IP matches one of the monitored IPs,
    # that line is alive by definition (we're using it right now).
    my_ip = get_my_public_ip()
    if my_ip:
        log(f"My public IP: {my_ip}")
        for r in results.values():
            if r["ip"] == my_ip and not r["up"]:
                r["up"] = True
                r["method"] = "self/online"
                r["latency_ms"] = 0
                log(f"  -> overriding {r['name']} to UP (this PC is on it)")

    # Build status output preserving location grouping
    locations_out = []
    total = up = 0
    for loc in locations:
        loc_lines = []
        loc_down = 0
        for line in loc.get("lines", []):
            r = results[line["id"]]
            loc_lines.append(r)
            total += 1
            if r["up"]:
                up += 1
            else:
                loc_down += 1
        locations_out.append({
            "id": loc["id"],
            "name": loc["name"],
            "down_count": loc_down,
            "total_count": len(loc.get("lines", [])),
            "lines": loc_lines,
        })

    status = {
        "school": school,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {"total": total, "up": up, "down": total - up},
        "source": "local-probe",
        "probe_public_ip": my_ip,
        "locations": locations_out,
    }
    log(f"Result: {up}/{total} UP. Pushing to GitHub...")

    content_bytes = (json.dumps(status, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

    # Upload via GitHub API. Get current sha first.
    path = cfg.get("github_path", "data/status.json")
    try:
        sha = github_get_file_sha(token, owner, repo, path)
        github_put_file(
            token, owner, repo, path, content_bytes,
            # NOTE: do NOT add "[skip ci]" — that would block GitHub Pages
            # from redeploying when status.json changes.
            message=f"chore(local-probe): update status ({up}/{total} up)",
            sha=sha,
        )
        log(f"Pushed to {owner}/{repo}:{path}  ({up}/{total} UP)")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:300]
        log(f"GitHub API error {e.code}: {body}")
        return 3
    except Exception as e:
        log(f"Push failed: {e}")
        return 3

    return 0


if __name__ == "__main__":
    sys.exit(main())

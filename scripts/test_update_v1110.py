#!/usr/bin/env python3
"""Simulate v1.1.8 → v1.1.10 update via GitHub installer (like the app)."""

import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO = "hochk2019/Golden-Signing"
UA = {"User-Agent": "GoldenSigning-Updater", "Accept": "application/vnd.github+json"}
update_root = Path.home() / "AppData" / "Local" / "GoldenSign" / "updates"
update_root.mkdir(parents=True, exist_ok=True)
log = update_root / "apply_update.log"


def logline(msg: str) -> None:
    line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
    print(line)
    with open(log, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def download(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": UA["User-Agent"]})
    with urllib.request.urlopen(req, timeout=120) as resp, open(dest, "wb") as fh:
        total = resp.headers.get("Content-Length")
        total_i = int(total) if total and total.isdigit() else 0
        done = 0
        while True:
            chunk = resp.read(256 * 1024)
            if not chunk:
                break
            fh.write(chunk)
            done += len(chunk)
            if total_i:
                pct = done * 100 // total_i
                print(f"\r  download {pct}%  {done/1e6:.1f}/{total_i/1e6:.1f} MB", end="")
        print()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        while True:
            b = fh.read(1024 * 1024)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def main() -> None:
    logline("=== manual update test start ===")
    d = fetch_json(f"https://api.github.com/repos/{REPO}/releases/latest")
    tag = d["tag_name"]
    logline(f"latest tag: {tag}")

    assets = {a["name"]: a for a in d.get("assets") or []}
    installer_name = f"GoldenSign-Setup-{tag.lstrip('v')}.exe"
    checksums_name = "checksums.txt"
    if installer_name not in assets:
        logline(f"ERROR: installer asset missing: {installer_name}")
        sys.exit(1)
    if checksums_name not in assets:
        logline("ERROR: checksums.txt missing")
        sys.exit(1)

    # Download checksums
    csum_path = update_root / "checksums.txt"
    download(assets[checksums_name]["browser_download_url"], csum_path)
    expected = ""
    for line in csum_path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1] == installer_name:
            expected = parts[0].lower()
            break
    if not expected:
        logline("ERROR: installer sha256 not in checksums.txt")
        sys.exit(1)
    logline(f"expected sha256: {expected}")

    # Download installer
    inst_path = update_root / f"installer-{tag}.exe"
    download(assets[installer_name]["browser_download_url"], inst_path)
    actual = sha256_file(inst_path)
    logline(f"actual sha256:   {actual}")
    if actual != expected:
        logline("ERROR: SHA256 mismatch")
        sys.exit(1)
    logline("SHA256 OK")

    # Kill running app
    subprocess.run(
        ["taskkill", "/F", "/IM", "GoldenSign.exe"],
        capture_output=True,
        check=False,
    )
    time.sleep(1.5)
    logline("app killed")

    # Run installer silent (no /DIR — Inno remembers via AppId)
    args = "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /CLOSEAPPLICATIONS"
    logline(f"running installer: {args}")
    p = subprocess.run(
        [str(inst_path), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CLOSEAPPLICATIONS"],
        capture_output=False,
    )
    logline(f"installer exit code: {p.returncode}")
    if p.returncode != 0:
        logline("ERROR: installer failed")
        sys.exit(p.returncode)

    # Relaunch
    exe = Path.home() / "AppData" / "Local" / "Programs" / "GoldenSign" / "GoldenSign.exe"
    if exe.is_file():
        subprocess.Popen([str(exe)], close_fds=True)
        logline("relaunched")
    else:
        logline("ERROR: new exe missing")
        sys.exit(1)
    logline("=== manual update test done ===")


if __name__ == "__main__":
    main()

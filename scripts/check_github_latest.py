#!/usr/bin/env python3
"""Check GitHub latest release for Golden Sign."""

import json
import urllib.request

req = urllib.request.Request(
    "https://api.github.com/repos/hochk2019/Golden-Signing/releases/latest",
    headers={"User-Agent": "GoldenSigning-Updater", "Accept": "application/vnd.github+json"},
)
with urllib.request.urlopen(req, timeout=20) as r:
    d = json.loads(r.read())
print("tag:", d.get("tag_name"))
for a in d.get("assets") or []:
    print(f"  {a['name']}  {a['size']}  {a['browser_download_url']}")
body = (d.get("body") or "")[:300]
print("body:", body)

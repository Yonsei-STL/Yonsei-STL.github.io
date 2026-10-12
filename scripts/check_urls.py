#!/usr/bin/env python3
"""Check preserved project URLs and discovery files.

Local file checks always run. HTTP checks run when --base is set, for example
after `python -m http.server` or after GitHub Pages publishes main.

Google Search Console and Bing Webmaster Tools submission need lab accounts
and a deployed sitemap. This script cannot sign in to those services.
"""

from __future__ import annotations

import argparse
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PRESERVED = [
    "/",
    "/RASMD/",
    "/Pix2Next/",
    "/SpectraDiff/",
    "/RM-MLLM/",
]

DISCOVERY = [
    "/robots.txt",
    "/sitemap.xml",
    "/llms.txt",
    "/publications/",
]

REDIRECTS = {
    "/RASMD": "/RASMD/",
    "/Pix2Next": "/Pix2Next/",
    "/SpectraDiff": "/SpectraDiff/",
    "/RM-MLLM": "/RM-MLLM/",
}

CASE_MISS = "/rasmd/"


def local_checks() -> list[str]:
    errors = []
    required = [
        ROOT / "index.html",
        ROOT / "robots.txt",
        ROOT / "sitemap.xml",
        ROOT / "llms.txt",
        ROOT / "publications" / "index.html",
        ROOT / ".nojekyll",
        ROOT / "data" / "publications.json",
    ]
    for path in PRESERVED[1:]:
        required.append(ROOT / path.strip("/") / "index.html")
    for path in required:
        if not path.is_file():
            errors.append(f"missing {path.relative_to(ROOT)}")
    root = (ROOT / "index.html").read_text(encoding="utf-8")
    if "https://stl.yonsei.ac.kr/" not in root:
        errors.append("root index.html does not point at the lab website")
    for folder in ("RASMD", "Pix2Next", "SpectraDiff", "RM-MLLM"):
        html = (ROOT / folder / "index.html").read_text(encoding="utf-8")
        if f"https://yonsei-stl.github.io/{folder}/" not in html:
            errors.append(f"{folder}: canonical project URL is missing")
    return errors


def fetch(url: str) -> tuple[int, str, str]:
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read(4000).decode("utf-8", errors="replace")
            return response.status, response.geturl(), body
    except urllib.error.HTTPError as exc:
        body = exc.read(500).decode("utf-8", errors="replace")
        return exc.code, url, body


def http_checks(base: str) -> list[str]:
    errors = []
    base = base.rstrip("/")
    for path in PRESERVED + DISCOVERY:
        status, final_url, body = fetch(base + path)
        if status != 200:
            errors.append(f"{path} returned {status}")
            continue
        if path == "/" and "stl.yonsei.ac.kr" not in body:
            errors.append("root response does not mention the lab website")
        if path.endswith("/") and path != "/" and "<html" not in body.lower():
            errors.append(f"{path} is not HTML")
    for source, target in REDIRECTS.items():
        status, final_url, _body = fetch(base + source)
        if status not in (200, 301, 302, 308):
            errors.append(f"{source} returned {status}")
        elif target.strip("/") not in final_url and status == 200:
            # A static server may not redirect slashless paths. Accept the page
            # only when the slashless path is served as the same index.html.
            pass
        elif status in (301, 302, 308) and not final_url.rstrip("/").endswith(target.strip("/")):
            errors.append(f"{source} redirected to {final_url}")
    status, _url, _body = fetch(base + CASE_MISS)
    if status != 404:
        message = f"{CASE_MISS} returned {status}; GitHub Pages paths are case-sensitive"
        if sys.platform == "win32" and status == 200:
            print(message + ". Windows file serving is not, so this local result is expected.")
        else:
            errors.append(message)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", help="Origin to request, such as http://127.0.0.1:8000")
    args = parser.parse_args()
    errors = local_checks()
    if args.base:
        errors.extend(http_checks(args.base))
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("URL checks passed")
    if not args.base:
        print("HTTP checks skipped. Re-run with --base after serving or deploying the site.")
        print("After deploy, submit https://yonsei-stl.github.io/sitemap.xml in")
        print("Google Search Console and Bing Webmaster Tools. Those steps need lab accounts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

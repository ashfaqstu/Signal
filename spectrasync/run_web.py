#!/usr/bin/env python3
"""SpectraSync Studio - Web Application Launcher

Usage:
  python run_web.py              # Normal mode: serves static bundle from web/dist + API
  python run_web.py --dev        # Dev mode: uvicorn (reload) + Vite dev server
  python run_web.py --port 8080  # Custom port
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
WEB_DIR = ROOT_DIR / "web"
DIST_DIR = WEB_DIR / "dist"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="SpectraSync Studio Web Application Server",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind server")
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Run in development mode (API with hot-reload + Vite dev server)",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not automatically open the web browser on startup",
    )
    return parser.parse_args()


def open_browser_delayed(url: str, delay: float = 1.0) -> None:
    def _target() -> None:
        time.sleep(delay)
        try:
            webbrowser.open_new_tab(url)
        except Exception:
            pass

    thread = threading.Thread(target=_target, daemon=True)
    thread.start()


def run_normal(host: str, port: int, auto_open: bool) -> None:
    # Check if frontend bundle exists
    if not DIST_DIR.exists() or not (DIST_DIR / "index.html").exists():
        print(f"[SpectraSync] web/dist directory not found at {DIST_DIR}.")
        print("[SpectraSync] Building frontend bundle with npm run build...")
        try:
            subprocess.run(["npm", "run", "build"], cwd=str(WEB_DIR), check=True, shell=True)
        except subprocess.CalledProcessError as e:
            print(f"[SpectraSync] Frontend build failed: {e}", file=sys.stderr)
            sys.exit(1)

    url = f"http://{host}:{port}"
    print(f"\n========================================================")
    print(f"  SpectraSync Studio is running at: {url}")
    print(f"========================================================\n")

    if auto_open:
        open_browser_delayed(url)

    import uvicorn
    uvicorn.run("server.main:app", host=host, port=port, log_level="info")


def run_dev(host: str, port: int, auto_open: bool) -> None:
    print("\n========================================================")
    print("  Starting SpectraSync Studio in DEV mode")
    print(f"  API Backend: http://{host}:{port}")
    print("  Vite Dev UI: http://localhost:5173")
    print("========================================================\n")

    # Start FastAPI with hot reload
    uvicorn_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "server.main:app",
        "--reload",
        "--host",
        host,
        "--port",
        str(port),
    ]

    # Start Vite dev server in web/
    npm_cmd = ["npm", "run", "dev"]

    procs = []
    try:
        proc_backend = subprocess.Popen(uvicorn_cmd, cwd=str(ROOT_DIR))
        procs.append(proc_backend)

        proc_frontend = subprocess.Popen(npm_cmd, cwd=str(WEB_DIR), shell=True)
        procs.append(proc_frontend)

        if auto_open:
            open_browser_delayed("http://localhost:5173", delay=1.5)

        # Wait for either process
        while True:
            for p in procs:
                ret = p.poll()
                if ret is not None:
                    print(f"\n[SpectraSync] Subprocess exited with code {ret}")
                    return
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[SpectraSync] Shutting down development servers...")
    finally:
        for p in procs:
            if p.poll() is None:
                p.terminate()
                try:
                    p.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    p.kill()


def main() -> None:
    args = parse_args()
    auto_open = not args.no_browser

    if args.dev:
        run_dev(args.host, args.port, auto_open)
    else:
        run_normal(args.host, args.port, auto_open)


if __name__ == "__main__":
    main()

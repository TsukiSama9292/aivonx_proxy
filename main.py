#!/usr/bin/env python3
"""
CLI launcher for running the Django ASGI app with sensible defaults.

Usage examples:
  python main.py --port 8000
  python main.py --args "--workers 2 --log-level debug"

Precedence for options:
  CLI args > environment variables (.env or system env) > defaults

Behavior:
  - Reads `.env` if present (python-dotenv).
  - If `DJANGO_DEBUG` is truthy, enables `--reload` by default.
  - Port is selected from `--port` or `DJANGO_PORT` or 8000.
  - Additional uvicorn args can be passed via `--args`.
"""
from __future__ import annotations
import os
import sys
import shlex
import subprocess
from pathlib import Path
import argparse

try:
    from dotenv import load_dotenv
except Exception:
    def load_dotenv(path=None):
        return False


def _truthy(v: str | None) -> bool:
    if v is None:
        return False
    return str(v).lower() in ("1", "true", "yes", "on")


def build_command(app_module: str, host: str, port: int, reload: bool, workers: int | None, extra_args: list[str]) -> list[str]:
    cmd = [sys.executable, "-m", "uvicorn", app_module, "--host", host, "--port", str(port)]
    if reload:
        cmd.append("--reload")
    if workers:
        cmd.extend(["--workers", str(workers)])
    if extra_args:
        cmd.extend(extra_args)
    return cmd


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Run the aivonx ASGI app via uvicorn")
    parser.add_argument("--port", "-p", type=int, help="Port to listen on (overrides DJANGO_PORT)")
    parser.add_argument("--host", default=os.getenv("DJANGO_HOST", "0.0.0.0"), help="Host to bind")
    parser.add_argument("--no-reload", dest="no_reload", action="store_true", help="Disable reload even if DJANGO_DEBUG is set")
    parser.add_argument("--reload", dest="reload", action="store_true", help="Force reload (overrides DJANGO_DEBUG)")
    parser.add_argument("--workers", type=int, default=None, help="Number of worker processes for uvicorn")
    parser.add_argument("--args", type=str, default="", help="Extra uvicorn CLI args (quoted string). Example: --args \"--log-level debug --proxy-headers\"")
    args = parser.parse_args(argv)

    # Determine port: CLI > DJANGO_PORT env > default
    port = args.port if args.port else int(os.getenv("DJANGO_PORT", "8000"))

    # Determine reload mode: CLI --reload > DJANGO_DEBUG (env/.env) > default False
    env_debug = _truthy(os.getenv("DJANGO_DEBUG"))
    if args.reload:
        reload_mode = True
    elif args.no_reload:
        reload_mode = False
    else:
        reload_mode = env_debug

    # Parse extra args into tokens
    extra_args: list[str] = []
    if args.args:
        try:
            extra_args = shlex.split(args.args)
        except Exception:
            extra_args = [args.args]

    # Ensure module import path includes `src` so `aivonx.asgi` is importable
    project_root = Path(__file__).resolve().parent
    src_dir = project_root / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    app_module = "aivonx.asgi:application"
    cmd = build_command(app_module, args.host, port, reload_mode, args.workers, extra_args)

    print("Starting server with:")
    print(" ", " ".join(shlex.quote(p) for p in cmd))

    # Forward environment (including loaded .env) to subprocess
    env = os.environ.copy()

    # Run uvicorn as a subprocess with cwd=src so imports resolve
    try:
        proc = subprocess.Popen(cmd, env=env, cwd=str(src_dir))
        proc.wait()
        return proc.returncode or 0
    except KeyboardInterrupt:
        return 0
    except FileNotFoundError:
        print("uvicorn not found. Ensure dependencies installed (uvicorn).", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

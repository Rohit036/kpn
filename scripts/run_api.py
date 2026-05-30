import argparse
import os
import sys

import uvicorn


ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(ROOT_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run FastAPI server for KPN agent")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    # Prefer the environment PORT when provided (Railway and other PaaS set this)
    port_env = os.getenv("PORT")
    try:
        port = int(port_env) if port_env is not None else args.port
    except Exception:
        port = args.port
    uvicorn.run("app.main:app", host=args.host, port=port, reload=args.reload)


if __name__ == "__main__":
    main()

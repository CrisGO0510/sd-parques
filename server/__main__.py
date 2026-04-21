"""Entry point: `python -m server`."""
from __future__ import annotations

import argparse
import logging
import sys

from server.server import Server


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)s [%(levelname)s] [%(threadName)s] %(message)s",
    )

    server = Server(host=args.host, port=args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logging.info("shutdown requested")
        server.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())

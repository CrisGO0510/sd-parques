"""Entry point: `python -m server`."""
from __future__ import annotations

import argparse
import logging
import sys

from server.server import Server


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port-tcp", type=int, default=5000, dest="port_tcp")
    parser.add_argument("--port-ws",  type=int, default=5001, dest="port_ws",
                        help="WebSocket listener port (0 disables)")
    parser.add_argument("--no-ws",    action="store_true",
                        help="Disable the WebSocket listener entirely")
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

    server = Server(host=args.host, port=args.port_tcp)

    # Start WS listener if requested (must be before serve_forever which blocks).
    if not args.no_ws and args.port_ws >= 0:
        import threading

        from server.ws_bridge import start_ws_listener

        # serve_forever blocks — we start TCP in a thread, then WS in another,
        # then main just waits for Ctrl+C.
        tcp_thread = threading.Thread(
            target=server.serve_forever, daemon=True, name="tcp-listener",
        )
        tcp_thread.start()
        server.wait_ready(timeout=2.0)

        start_ws_listener(server, args.host, args.port_ws)

        try:
            tcp_thread.join()
        except KeyboardInterrupt:
            logging.info("shutdown requested")
            server.shutdown()
        return 0

    # No WS: use the existing flow.
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logging.info("shutdown requested")
        server.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())

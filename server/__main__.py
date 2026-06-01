"""Entry point: `python -m server`."""
from __future__ import annotations

import argparse
import logging
import os
import sys

from server.server import Server


def main() -> int:
    def get_public_port() -> int:
        """Get the public port from Render environment or fallback to defaults."""
        try:
            return int(os.getenv('PORT', '5001'))
        except ValueError:
            return 5001

    # Check if running on Render (has PORT env variable)
    is_render = 'PORT' in os.environ
    public_port = get_public_port()

    parser = argparse.ArgumentParser(prog="python -m server")
    parser.add_argument("--host", default="0.0.0.0")
    # On Render: TCP disabled, only WS on public port. Locally: TCP on 5000, WS on 5001.
    parser.add_argument("--port-tcp", type=int, default=0 if is_render else 5000, dest="port_tcp",
                        help="TCP listener port (0 = disabled, required for Render)")
    parser.add_argument("--port-ws",  type=int, default=public_port, dest="port_ws",
                        help="WebSocket listener port (uses PORT env var on Render)")
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
    if not args.no_ws and args.port_ws > 0:
        import threading

        from server.ws_bridge import start_ws_listener

        # On Render: TCP is disabled (port 0), only WS listener runs.
        # Locally: TCP in a thread, then WS in another.
        if args.port_tcp > 0:
            # Local mode: start both TCP and WS
            tcp_thread = threading.Thread(
                target=server.serve_forever, daemon=True, name="tcp-listener",
            )
            tcp_thread.start()
            server.wait_ready(timeout=2.0)

        start_ws_listener(server, args.host, args.port_ws)

        if args.port_tcp > 0:
            try:
                tcp_thread.join()
            except KeyboardInterrupt:
                logging.info("shutdown requested")
                server.shutdown()
        else:
            # Render mode: only WS, wait for interrupt
            try:
                while True:
                    import time
                    time.sleep(1)
            except KeyboardInterrupt:
                logging.info("shutdown requested")
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

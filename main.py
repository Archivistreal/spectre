import sys
import argparse
import asyncio
import logging
import threading
from typing import List

from core.node import SpectreNode
from server.host import SpectreContentServer


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


async def run_single_node(name: str, host: str, port: int, role: str):
    node = SpectreNode(name, host, port, role=role)
    await node.start()
    logging.info(f"[{name}] Daemon node ({role}) active on tcp://{host}:{port}. Press Ctrl+C to stop.")
    try:
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        pass
    finally:
        await node.stop()


async def run_nodes(roles: List[str], host: str = "127.0.0.1", base_port: int = 19001):
    nodes: List[SpectreNode] = []
    for idx, role in enumerate(roles):
        port = base_port + idx
        node = SpectreNode(f"{role.capitalize()}Node", host, port, role=role)
        await node.start()
        nodes.append(node)

    logging.info(f"Started {len(nodes)} daemon node(s) on {host}. Press Ctrl+C to stop.")
    try:
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        pass
    finally:
        for node in nodes:
            await node.stop()


async def run_server(host: str = "0.0.0.0", port: int = 19080):
    server = SpectreContentServer(host, port)
    await server.start()
    logging.info(f"Spectre HTML Content Server active on tcp://{host}:{port}. Press Ctrl+C to stop.")
    try:
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        pass
    finally:
        await server.stop()


def start_demo_mode():
    from PyQt6.QtWidgets import QApplication
    from browser.ui import SpectreBrowserWindow

    logging.info("Starting Spectre Protocol All-In-One Demo Network...")

    loop = asyncio.new_event_loop()

    async def _start_demo_async():
        guard = SpectreNode("GuardNode", "127.0.0.1", 19001, role="guard")
        relay = SpectreNode("RelayNode", "127.0.0.1", 19002, role="relay")
        exit_node = SpectreNode("ExitNode", "127.0.0.1", 19003, role="exit")
        server = SpectreContentServer("127.0.0.1", 19080)

        await guard.start()
        await relay.start()
        await exit_node.start()
        await server.start()

        logging.info("Spectre 3-Hop Onion Network & Content Server active!")
        return guard, relay, exit_node, server

    def _async_loop_worker(l):
        asyncio.set_event_loop(l)
        l.run_forever()

    guard, relay, exit_node, server = loop.run_until_complete(_start_demo_async())

    thread = threading.Thread(target=_async_loop_worker, args=(loop,), daemon=True)
    thread.start()

    try:
        app = QApplication(sys.argv)
        browser = SpectreBrowserWindow(
            guard_addr=("127.0.0.1", 19001),
            relay_addr=("127.0.0.1", 19002),
            exit_addr=("127.0.0.1", 19003),
            server_addr=("127.0.0.1", 19080),
        )
        browser.show()
        browser.load_current_url()

        sys.exit(app.exec())

    finally:
        async def _stop():
            await guard.stop()
            await relay.stop()
            await exit_node.stop()
            await server.stop()

        asyncio.run_coroutine_threadsafe(_stop(), loop).result()
        loop.call_soon_threadsafe(loop.stop)


def main():
    parser = argparse.ArgumentParser(description="Spectre Protocol - 3-Hop Onion Network & Browser")
    parser.add_argument("--demo", action="store_true", help="Spin up local 3-hop network, content server, and launch browser")
    parser.add_argument("--browser", action="store_true", help="Launch PyQt6 Browser client")
    parser.add_argument("--server", action="store_true", help="Run Spectre HTML Content Server")
    parser.add_argument("--nodes", action="store_true", help="Spin up 3 daemon nodes locally (Guard, Relay, Exit)")
    parser.add_argument("--node", action="store_true", help="Run a single daemon node on a server")
    parser.add_argument("--role", type=str, choices=["guard", "relay", "exit"], default="guard", help="Node role for single daemon node")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Listen address for server or daemon node")
    parser.add_argument("--port", type=int, default=19001, help="Listen port for server or daemon node")
    parser.add_argument("--guard", type=str, default="127.0.0.1:19001", help="Guard node host:port for browser client")
    parser.add_argument("--relay", type=str, default="127.0.0.1:19002", help="Relay node host:port for browser client")
    parser.add_argument("--exit-node", type=str, default="127.0.0.1:19003", help="Exit node host:port for browser client")
    parser.add_argument("--content-server", type=str, default="127.0.0.1:19080", help="Content server host:port for browser client")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose debug logging")

    args = parser.parse_args()
    setup_logging(args.verbose)

    def parse_addr(addr_str: str, default_port: int) -> tuple:
        if ":" in addr_str:
            h, p = addr_str.split(":", 1)
            return h, int(p)
        return addr_str, default_port

    if args.node:
        asyncio.run(run_single_node(f"{args.role.capitalize()}Node", args.host, args.port, role=args.role))
    elif args.server:
        asyncio.run(run_server(args.host, args.port if args.port != 19001 else 19080))
    elif args.nodes:
        asyncio.run(run_nodes(["guard", "relay", "exit"], host=args.host if args.host != "0.0.0.0" else "127.0.0.1"))
    elif args.browser:
        from PyQt6.QtWidgets import QApplication
        from browser.ui import SpectreBrowserWindow
        app = QApplication(sys.argv)
        browser = SpectreBrowserWindow(
            guard_addr=parse_addr(args.guard, 19001),
            relay_addr=parse_addr(args.relay, 19002),
            exit_addr=parse_addr(args.exit_node, 19003),
            server_addr=parse_addr(args.content_server, 19080),
        )
        browser.show()
        sys.exit(app.exec())
    elif args.demo or len(sys.argv) == 1:
        start_demo_mode()


if __name__ == "__main__":
    main()

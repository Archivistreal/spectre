import sys
import argparse
import asyncio
import logging
import signal
import time
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


async def run_nodes(roles: List[str], base_port: int = 19001):
    nodes: List[SpectreNode] = []
    for idx, role in enumerate(roles):
        port = base_port + idx
        node = SpectreNode(f"{role.capitalize()}Node", "127.0.0.1", port, role=role)
        await node.start()
        nodes.append(node)

    logging.info(f"Started {len(nodes)} daemon node(s). Press Ctrl+C to stop.")
    try:
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        pass
    finally:
        for node in nodes:
            await node.stop()


async def run_server(host: str = "127.0.0.1", port: int = 19080):
    server = SpectreContentServer(host, port)
    await server.start()
    logging.info(f"Content Server running on {host}:{port}. Press Ctrl+C to stop.")
    try:
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        pass
    finally:
        await server.stop()


def start_demo_mode():
    import multiprocessing
    from PyQt6.QtWidgets import QApplication
    from browser.ui import SpectreBrowserWindow

    logging.info("Starting Spectre Protocol Demo Network...")

    async def _start_demo_async():
        # Spin up 3 daemon nodes
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

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    guard, relay, exit_node, server = loop.run_until_complete(_start_demo_async())

    try:
        # Launch PyQt6 Browser GUI
        app = QApplication(sys.argv)
        browser = SpectreBrowserWindow(
            guard_addr=("127.0.0.1", 19001),
            relay_addr=("127.0.0.1", 19002),
            exit_addr=("127.0.0.1", 19003),
            server_addr=("127.0.0.1", 19080),
        )
        browser.show()

        # Load initial page automatically
        browser.load_current_url()

        # Run Qt event loop along with asyncio event processing
        sys.exit(app.exec())

    finally:
        loop.run_until_complete(guard.stop())
        loop.run_until_complete(relay.stop())
        loop.run_until_complete(exit_node.stop())
        loop.run_until_complete(server.stop())


def main():
    parser = argparse.ArgumentParser(description="Spectre Protocol - 3-Hop Onion Network & Browser")
    parser.add_argument("--demo", action="store_true", help="Spin up local 3-hop network, content server, and launch browser")
    parser.add_argument("--browser", action="store_true", help="Launch PyQt6 Browser client")
    parser.add_argument("--server", action="store_true", help="Run Spectre .spectre Content Server")
    parser.add_argument("--nodes", action="store_true", help="Spin up 3 daemon nodes (Guard, Relay, Exit)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose debug logging")

    args = parser.parse_args()
    setup_logging(args.verbose)

    if args.demo or (not args.browser and not args.server and not args.nodes):
        start_demo_mode()
    elif args.browser:
        from PyQt6.QtWidgets import QApplication
        from browser.ui import SpectreBrowserWindow
        app = QApplication(sys.argv)
        browser = SpectreBrowserWindow()
        browser.show()
        sys.exit(app.exec())
    elif args.server:
        asyncio.run(run_server())
    elif args.nodes:
        asyncio.run(run_nodes(["guard", "relay", "exit"]))


if __name__ == "__main__":
    main()

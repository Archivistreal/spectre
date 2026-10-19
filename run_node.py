#!/usr/bin/env python3
"""
Spectre Protocol - Standalone Node Script
Run this script to immediately join the Spectre P2P Onion Network as a node.
"""

import sys
import argparse
import asyncio
import logging
from core.node import SpectreNode


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


async def main():
    parser = argparse.ArgumentParser(description="Become a Spectre Protocol P2P Node")
    parser.add_argument("--role", type=str, choices=["guard", "relay", "exit"], default="relay", help="Role of node in onion network (default: relay)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Listen IP address (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=19001, help="Listen TCP port (default: 19001)")
    parser.add_argument("--name", type=str, default=None, help="Custom node identifier name")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose debug logs")

    args = parser.parse_args()
    setup_logging(args.verbose)

    node_name = args.name or f"SpectreNode_{args.role.capitalize()}_{args.port}"
    node = SpectreNode(node_name, args.host, args.port, role=args.role)

    try:
        await node.start()
        print(f"\n=======================================================")
        print(f" SPECTRE P2P NODE ACTIVE ({args.role.upper()})")
        print(f" Address: tcp://{args.host}:{node.port}")
        print(f" Identity PubKey: {node.identity_pub_bytes.hex()[:16]}...")
        print(f" Status: Ready for Onion Circuit connections")
        print(f"=======================================================\n")
        print("Press Ctrl+C to stop node...")

        await asyncio.Event().wait()
    except KeyboardInterrupt:
        print("\nStopping Spectre Node...")
    except Exception as err:
        logging.error(f"Error starting node on {args.host}:{args.port}: {err}")
    finally:
        await node.stop()
        print("Spectre Node shut down cleanly.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

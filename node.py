#!/usr/bin/env python3
"""
Spectre Protocol - Top-Level Node Launcher
Executes the Spectre Node launcher (run_node.py) with project path properly set.
"""

import os
import sys

# Ensure repository root directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from run_node import main as node_main
import asyncio

if __name__ == "__main__":
    try:
        asyncio.run(node_main())
    except KeyboardInterrupt:
        pass

# Spectre Protocol

An encrypted, 3-hop onion routing network with a PyQt6 GUI desktop browser, local TCP socket daemon nodes, 512-byte fixed cell padding against traffic analysis, and custom HTML `.spec` / `.spectre` content server.

---

## Overview Architecture

```text
+-------------------+        +----------------+        +----------------+        +---------------+        +----------------------+
|  PyQt6 HTML Client|        |   Guard Node   |        |   Relay Node   |        |   Exit Node   |        | .spec / .spectre Host|
|  (Spectre Browser)| ===>   |  (Port 19001)  | ===>   |  (Port 19002)  | ===>   | (Port 19003)  | ===>   | Server (Port 19080)  |
+-------------------+        +----------------+        +----------------+        +---------------+        +----------------------+
     Client Circuit           Hop 1 (Outer Layer)      Hop 2 (Middle)            Hop 3 (Inner Layer)      Target Content Server
```

### High-Security Features

1. **Fixed 512-Byte Cell Padding**: All cells are padded to 512 bytes with random bytes before onion wrapping, preventing side-channel traffic analysis and payload size correlation.
2. **Anti-Replay Protection**: Sequence counters are embedded into onion commands and tracked per circuit to reject replay attacks.
3. **In-Place Key Zeroization**: Sensitive session keys and Diffie-Hellman secrets are explicitly zeroized in memory when circuit sessions terminate.
4. **Cryptographic Primitives**: Ed25519 node identity signatures, ephemeral X25519 Diffie-Hellman key exchanges, HKDF-SHA256 key derivation, and ChaCha20-Poly1305 AEAD multi-layer encryption.
5. **Full HTML Website Rendering**: Rich HTML `.spec` and `.spectre` websites with inline CSS, links, lists, blockquotes, and formatting rendered in the PyQt6 browser.

---

## Directory Structure

```text
spectre-net/
├── core/
│   ├── __init__.py
│   ├── crypto.py      # X25519, Ed25519, HKDF, ChaCha20-Poly1305, zeroization, & 512-byte cell padding
│   └── node.py        # Guard, Relay, and Exit daemon nodes with sequence replay protection
├── browser/
│   ├── __init__.py
│   └── ui.py          # PyQt6 HTML desktop browser client with history and status tracking
├── server/
│   ├── __init__.py
│   └── host.py        # Sample HTML .spec / .spectre content server (genesis.spec, manifesto.spec)
├── tests/
│   ├── __init__.py
│   ├── test_crypto.py # Unit tests for crypto, padding, and zeroize functions
│   ├── test_circuit.py# Integration tests for 3-hop circuit building
│   ├── test_server.py # Tests for HTML content server
│   └── test_browser.py# Unit tests for browser navigation history
├── main.py            # Entry point CLI (demo mode, browser, daemon nodes, or content server)
├── requirements.txt   # Dependencies: PyQt6, cryptography, pytest, pytest-asyncio
└── README.md          # Protocol specifications and setup guide
```

---

## Quick Start & Installation

```bash
pip install -r requirements.txt
```

---

## Usage Guide

### 1. Demo Mode (All-In-One)
Spins up 3 local daemon nodes (Guard, Relay, Exit), the HTML `.spec` content server, and opens the PyQt6 GUI browser:
```bash
python main.py --demo
```

### 2. Standalone Execution

**Start 3 Daemon Nodes (Guard, Relay, Exit):**
```bash
python main.py --nodes
```

**Start HTML Content Server:**
```bash
python main.py --server
```

**Launch PyQt6 HTML Browser:**
```bash
python main.py --browser
```

---

## Running Test Suite

```bash
QT_QPA_PLATFORM=offscreen pytest
```

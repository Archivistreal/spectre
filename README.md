# Spectre Protocol

An encrypted, 3-hop onion routing network with a PyQt6 GUI desktop browser, local TCP socket daemon nodes, and custom `.spectre` markup content server.

---

## Overview Architecture

```text
+-------------------+        +----------------+        +----------------+        +---------------+        +----------------------+
|  PyQt6 Client     |        |   Guard Node   |        |   Relay Node   |        |   Exit Node   |        | .spectre Host        |
|  (Spectre Browser)| ===>   |  (Port 19001)  | ===>   |  (Port 19002)  | ===>   | (Port 19003)  | ===>   | Server (Port 19080)  |
+-------------------+        +----------------+        +----------------+        +---------------+        +----------------------+
     Client Circuit           Hop 1 (Outer Layer)      Hop 2 (Middle)            Hop 3 (Inner Layer)      Target Content Server
```

### Key Components

1. **`core/crypto.py`**:
   - **Identity Authentication**: Ed25519 node keypair generation and cell signature verification.
   - **Key Negotiation**: Ephemeral X25519 Diffie-Hellman key exchange per hop.
   - **Key Derivation**: HKDF-SHA256 deriving 256-bit symmetric keys.
   - **AEAD Payload Encryption**: ChaCha20-Poly1305 multi-layer onion wrapping and peeling.

2. **`core/node.py`**:
   - **Framing Protocol**: 4-byte big-endian binary framing over TCP streams.
   - **Cell Types**: `CREATE`, `CREATED`, `RELAY` (with commands `EXTEND`, `FORWARD`, `DESTINATION_DATA`).
   - **Circuit Management**: Multi-hop circuit setup and asynchronous packet forwarding.

3. **`server/host.py`**:
   - **Spectre Content Server**: TCP server hosting default documents (`genesis.spectre`, `manifesto.spectre`).

4. **`browser/ui.py`**:
   - **PyQt6 Desktop Browser**: Address bar, Back/Forward navigation history, connection status bar.
   - **`.spectre` Markup Renderer**: Custom parser rendering headers (`#`, `##`, `###`), blockquotes (`>`), bold text (`**text**`), code blocks (```spectre), list items (`-`), and interactive links (`[label](url)`).

---

## Directory Structure

```text
spectre-net/
├── core/
│   ├── __init__.py
│   ├── crypto.py      # X25519 handshakes, Ed25519, and ChaCha20-Poly1305 AEAD onion wrapping/peeling
│   └── node.py        # Core networking logic for Guard, Relay, and Exit daemon nodes (TCP sockets)
├── browser/
│   ├── __init__.py
│   └── ui.py          # PyQt6 desktop client, address bar, navigation history, and .spectre markup renderer
├── server/
│   ├── __init__.py
│   └── host.py        # Sample .spectre content server hosting genesis.spectre and manifesto.spectre
├── tests/
│   ├── __init__.py
│   ├── test_crypto.py # Unit tests for key derivation and onion wrapping
│   ├── test_circuit.py# Integration tests for 3-hop circuit building
│   ├── test_server.py # Tests for .spectre content server
│   └── test_browser.py# Unit tests for browser markup renderer & navigation history
├── main.py            # Entry point to launch demo mode, browser, daemon nodes, or server
├── requirements.txt   # Dependencies: PyQt6, cryptography, pytest, pytest-asyncio
└── README.md          # Setup instructions and protocol specification
```

---

## Quick Start & Installation

### Requirements
- Python 3.10+
- Qt6 libraries (installed automatically via `PyQt6` wheel)

### Installation
```bash
pip install -r requirements.txt
```

---

## Usage Guide

### 1. Demo Mode (All-In-One)
Spins up 3 local daemon nodes (Guard, Relay, Exit), the `.spectre` content server, and opens the PyQt6 GUI browser:
```bash
python main.py --demo
```

### 2. Standalone Service Execution

**Start 3 Daemon Nodes (Guard, Relay, Exit):**
```bash
python main.py --nodes
```

**Start `.spectre` Content Server:**
```bash
python main.py --server
```

**Launch Browser GUI:**
```bash
python main.py --browser
```

---

## Running Test Suite

Run unit and integration tests across the codebase:
```bash
QT_QPA_PLATFORM=offscreen pytest
```

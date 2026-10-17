# Spectre Protocol

An encrypted, 3-hop onion routing network with a PyQt6 GUI desktop browser, local TCP socket daemon nodes, 512-byte fixed cell padding against traffic analysis, and native HTML `.spec` website hosting featuring `spectre.spec`.

---

## Overview Architecture

```text
+-------------------+        +----------------+        +----------------+        +---------------+        +----------------------+
|  PyQt6 HTML Client|        |   Guard Node   |        |   Relay Node   |        |   Exit Node   |        | .spec Content Server |
| (spectre.spec)    | ===>   |  (Port 19001)  | ===>   |  (Port 19002)  | ===>   | (Port 19003)  | ===>   | (spectre.spec:19080) |
+-------------------+        +----------------+        +----------------+        +---------------+        +----------------------+
     Client Circuit           Hop 1 (Outer Layer)      Hop 2 (Middle)            Hop 3 (Inner Layer)      Target Content Server
```

### High-Security Features & `.spec` Web Ecosystem

1. **Flagship Website (`spectre.spec`)**: The primary web portal on the Spectre Onion Web hosting protocol specifications, features, and links to `genesis.spec` and `manifesto.spec`.
2. **Fixed 512-Byte Cell Padding**: All cells are padded to 512 bytes with random padding before onion encryption, preventing side-channel traffic analysis and size correlation.
3. **Anti-Replay Protection**: Sequence counters are embedded into onion commands and tracked per circuit to reject replay attacks.
4. **In-Place Key Zeroization**: Sensitive session keys and Diffie-Hellman secrets are explicitly zeroized in memory when circuit sessions terminate.
5. **Cryptographic Primitives**: Ed25519 node identity signatures, ephemeral X25519 Diffie-Hellman key exchanges, HKDF-SHA256 key derivation, and ChaCha20-Poly1305 AEAD multi-layer encryption.
6. **Native HTML Website Rendering**: Rich HTML `.spec` websites rendered directly in the PyQt6 browser.

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
│   └── ui.py          # PyQt6 HTML desktop browser client defaulting to spectre.spec
├── server/
│   ├── __init__.py
│   └── host.py        # HTML .spec content server hosting spectre.spec, genesis.spec, and manifesto.spec
├── tests/
│   ├── __init__.py
│   ├── test_crypto.py # Unit tests for crypto, padding, and zeroize functions
│   ├── test_circuit.py# Integration tests for 3-hop circuit building
│   ├── test_server.py # Tests for spectre.spec and .spec HTML content server
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
Spins up 3 local daemon nodes (Guard, Relay, Exit), the HTML `.spec` content server, and opens the PyQt6 GUI browser displaying `spectre.spec`:
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

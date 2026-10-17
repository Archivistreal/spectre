# Spectre Protocol

An encrypted, 3-hop onion routing network with a PyQt6 GUI desktop browser, daemon server nodes, variable 512-1024 byte cell padding against traffic analysis, and native HTML `.spec` website hosting featuring `spectre.spec`.

---

## Overview Architecture

```text
+-------------------+        +----------------------+        +----------------------+        +---------------------+        +-----------------------+
|  PyQt6 HTML Client|        |   Guard Server Node  |        |   Relay Server Node  |        |   Exit Server Node  |        | .spec Content Server  |
|  (spectre.spec)   | ===>   |  (e.g. 10.0.0.1:19001)| ===>   | (e.g. 10.0.0.2:19002)| ===>   |(e.g. 10.0.0.3:19003)| ===>   | (10.0.0.4:19080)      |
+-------------------+        +----------------------+        +----------------------+        +---------------------+        +-----------------------+
     Client Circuit           Hop 1 (Outer Layer)              Hop 2 (Middle Layer)           Hop 3 (Inner Layer)             Target Content Server
```

---

## Multi-Server Deployment Guide (Real Servers)

You can deploy Spectre Protocol across 4 independent physical or cloud servers (Guard, Relay, Exit, Content Server) over real TCP network sockets:

### 1. Server 1 (Guard Node):
```bash
python main.py --node --role guard --host 0.0.0.0 --port 19001
```

### 2. Server 2 (Relay Node):
```bash
python main.py --node --role relay --host 0.0.0.0 --port 19002
```

### 3. Server 3 (Exit Node):
```bash
python main.py --node --role exit --host 0.0.0.0 --port 19003
```

### 4. Server 4 (Content Server hosting spectre.spec):
```bash
python main.py --server --host 0.0.0.0 --port 19080
```

### 5. Client Machine (PyQt6 Browser):
Connect to the 3 remote node servers over real TCP sockets:
```bash
python main.py --browser \
  --guard 10.0.0.1:19001 \
  --relay 10.0.0.2:19002 \
  --exit-node 10.0.0.3:19003 \
  --content-server 10.0.0.4:19080
```

---

## Local All-In-One Demo Mode

To test everything locally on 1 machine:
```bash
python main.py --demo
```

---

## Running Test Suite

```bash
QT_QPA_PLATFORM=offscreen pytest
```

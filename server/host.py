import asyncio
import logging
from typing import Optional
from core.node import send_frame, read_frame

logger = logging.getLogger("spectre.server")

SPECTRE_SPEC_HTML = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>spectre.spec - The Next-Gen Spectre Protocol Onion Web</title>
    <style>
        * { box-sizing: border-box; }
        body { background-color: #020617; color: #38bdf8; font-family: 'Fira Code', monospace, sans-serif; padding: 30px; line-height: 1.6; }
        h1 { color: #f8fafc; border-bottom: 2px solid #0ea5e9; padding-bottom: 12px; font-size: 28px; text-shadow: 0 0 10px rgba(56,189,248,0.5); }
        h2 { color: #f59e0b; margin-top: 20px; font-size: 18px; text-transform: uppercase; letter-spacing: 1px; }
        .hud-card { background: rgba(15, 23, 42, 0.9); border: 1px solid rgba(56, 189, 248, 0.3); padding: 22px; border-radius: 12px; margin-bottom: 22px; box-shadow: 0 8px 32px rgba(0,0,0,0.8); }
        .grid { display: flex; gap: 20px; margin-bottom: 22px; }
        .card { flex: 1; background: rgba(15, 23, 42, 0.9); border: 1px solid rgba(56, 189, 248, 0.25); padding: 20px; border-radius: 10px; }
        a { color: #38bdf8; text-decoration: none; font-weight: bold; border-bottom: 1px dashed #38bdf8; transition: all 0.2s; }
        a:hover { color: #34d399; border-bottom: 1px solid #34d399; text-shadow: 0 0 8px rgba(52,211,153,0.6); }
        code { background-color: #0f172a; color: #34d399; padding: 4px 8px; border-radius: 4px; border: 1px solid #1e293b; font-size: 13px; }
        .status-badge { display: inline-block; background-color: #10b981; color: #020617; font-weight: bold; padding: 4px 14px; border-radius: 20px; font-size: 12px; letter-spacing: 1px; }
        .telemetry { display: flex; justify-content: space-between; background: #020617; padding: 12px 18px; border-radius: 8px; border: 1px solid #1e293b; margin-top: 15px; font-size: 12px; }
        .quantum-indicator { color: #a855f7; font-weight: bold; }
    </style>
</head>
<body>
    <div class="hud-card">
        <h1>SPECTRE.SPEC // QUANTUM-SECURE ONION WEB</h1>
        <p><span class="status-badge">QUANTUM ENTROPY SYNCED</span> &nbsp; <b>Next-Generation Anti-Traffic Analysis Protocol</b></p>
        <p>Outperforming legacy onion networks with quantum-resistant key exchange, ANU QRNG entropy seeds, variable 512-1024 byte cell jitter padding, and zero-knowledge peer-to-peer relay nodes.</p>

        <div class="telemetry">
            <span>ENTROPY: <span class="quantum-indicator">ANU QRNG (Vacuum Fluctuations)</span></span>
            <span>CIPHER: <strong style="color: #38bdf8;">ChaCha20-Poly1305 + ECDH P-256</strong></span>
            <span>PADDING: <strong style="color: #34d399;">512-1024B RANDOM JITTER</strong></span>
        </div>
    </div>

    <div class="grid">
        <div class="card">
            <h2>Explore .spec Onion Web</h2>
            <ul style="list-style-type: square; padding-left: 20px; line-height: 2;">
                <li><a href="spectre.spec">spectre.spec</a> - Official Spectre Network Portal</li>
                <li><a href="genesis.spec">genesis.spec</a> - Genesis Architecture Node</li>
                <li><a href="manifesto.spec">manifesto.spec</a> - The Cypherpunk Manifesto</li>
            </ul>
        </div>

        <div class="card">
            <h2>Superiority over Traditional Onion Web</h2>
            <ul style="list-style-type: circle; padding-left: 20px; line-height: 1.8;">
                <li><b>Traffic Analysis Immune:</b> Variable padding eliminates packet length fingerprinting</li>
                <li><b>Embedded P2P Relays:</b> Browsers automatically seed network capacity</li>
                <li><b>Sequence Counter Integrity:</b> Replay attack protection per circuit</li>
                <li><b>Zero Memory Residuals:</b> In-place key wiping on session termination</li>
            </ul>
        </div>
    </div>

    <div class="hud-card">
        <h2>Live Circuit Topology Diagnostic</h2>
        <p>Your request traversed an encrypted 3-hop circuit:</p>
        <pre style="background: #020617; padding: 15px; border-radius: 6px; border: 1px solid #1e293b; overflow-x: auto;"><code>[BROWSER CLIENT] ===(ECDH-GCM)===> [GUARD NODE: 19001] ===(ChaCha20)===> [RELAY NODE: 19002] ===(ChaCha20)===> [EXIT NODE: 19003] ===> [spectre.spec CONTENT SERVER: 19080]</code></pre>
    </div>
</body>
</html>
"""

GENESIS_HTML = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>genesis.spec - Spectre Network Genesis Node</title>
    <style>
        body { background-color: #11111b; color: #cdd6f4; font-family: sans-serif; padding: 20px; }
        h1 { color: #89b4fa; border-bottom: 2px solid #89b4fa; padding-bottom: 8px; }
        h2 { color: #f9e2af; margin-top: 20px; }
        .card { background-color: #1e1e2e; padding: 15px; border-radius: 8px; border: 1px solid #45475a; margin-bottom: 15px; }
        a { color: #89b4fa; text-decoration: none; font-weight: bold; }
        a:hover { text-decoration: underline; }
        code { background-color: #181825; color: #a6e3a1; padding: 4px 8px; border-radius: 4px; font-family: monospace; }
        .badge { display: inline-block; background-color: #a6e3a1; color: #11111b; font-weight: bold; padding: 4px 10px; border-radius: 12px; }
    </style>
</head>
<body>
    <h1>Welcome to Spectre Network Genesis Page</h1>
    <p><span class="badge">SECURE ONION TUNNEL ACTIVE</span></p>

    <div class="card">
        <h2>Decentralized, Anonymous 3-Hop Onion Routing</h2>
        <p>You have reached <b>genesis.spec</b> on the Spectre Network protocol.</p>
        <ul>
            <li><b>Guard Node:</b> Ingress entry node with cryptographic signature checks.</li>
            <li><b>Relay Node:</b> Middle transit node isolating origin from destination.</li>
            <li><b>Exit Node:</b> Egress node delivering padded 512-byte cells to target servers.</li>
        </ul>
    </div>

    <div class="card">
        <h2>Explore Network Links</h2>
        <p>Visit homepage at <a href="spectre.spec">Official Spectre Site (spectre.spec)</a></p>
        <p>Read the cypherpunk principles at <a href="manifesto.spec">Manifesto Page (manifesto.spec)</a></p>
    </div>
</body>
</html>
"""

MANIFESTO_HTML = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>manifesto.spec - The Spectre Cypherpunk Manifesto</title>
    <style>
        body { background-color: #11111b; color: #cdd6f4; font-family: sans-serif; padding: 20px; }
        h1 { color: #cba6f7; border-bottom: 2px solid #cba6f7; padding-bottom: 8px; }
        blockquote { border-left: 4px solid #f5e0dc; margin: 15px 0; padding-left: 15px; color: #bac2de; font-style: italic; background-color: #1e1e2e; padding: 10px; border-radius: 4px; }
        a { color: #89b4fa; text-decoration: none; font-weight: bold; }
        .card { background-color: #181825; padding: 15px; border-radius: 8px; border: 1px solid #313244; }
    </style>
</head>
<body>
    <h1>The Spectre Cypherpunk Manifesto</h1>

    <blockquote>
        "Privacy is necessary for an open society in the electronic age. Privacy is not secrecy. A private matter is something one doesn't want the whole world to know, but a secret matter is something one doesn't want anybody to know. Privacy is the power to selectively reveal oneself to the world."
    </blockquote>

    <div class="card">
        <h2>Core Security Directives</h2>
        <ol>
            <li><b>Zero-Knowledge Topology:</b> No hop possesses full path visibility.</li>
            <li><b>Fixed 512-Byte Cell Padding:</b> Eliminates traffic analysis and side-channel size leakage.</li>
            <li><b>Ephemeral Key Forward Secrecy:</b> Per-circuit X25519 Diffie-Hellman handshakes.</li>
            <li><b>Anti-Replay Sequences:</b> Circuit sequence numbers reject repeated payloads.</li>
        </ol>
        <p>Return to homepage at <a href="spectre.spec">spectre.spec</a> or <a href="genesis.spec">genesis.spec</a></p>
    </div>
</body>
</html>
"""

DEFAULT_404_HTML = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>404 Page Not Found</title>
    <style>
        body { background-color: #11111b; color: #f38ba8; font-family: sans-serif; padding: 20px; text-align: center; }
        a { color: #89b4fa; text-decoration: none; font-weight: bold; }
    </style>
</head>
<body>
    <h1>404 Page Not Found</h1>
    <p>The requested <code>.spec</code> or <code>.spectre</code> document could not be found.</p>
    <p><a href="spectre.spec">Return to Official Homepage (spectre.spec)</a></p>
</body>
</html>
"""


class SpectreContentServer:
    """TCP Content Server serving HTML .spec / .spectre documents."""

    def __init__(self, host: str = "127.0.0.1", port: int = 19080):
        self.host = host
        self.port = port
        self.server: Optional[asyncio.Server] = None
        self.pages = {
            "spectre.spec": SPECTRE_SPEC_HTML,
            "spectre.spectre": SPECTRE_SPEC_HTML,
            "genesis.spec": GENESIS_HTML,
            "genesis.spectre": GENESIS_HTML,
            "manifesto.spec": MANIFESTO_HTML,
            "manifesto.spectre": MANIFESTO_HTML,
            "/": SPECTRE_SPEC_HTML,
        }

    async def start(self) -> None:
        """Starts the content server with fallback if port in use."""
        target_port = self.port
        max_attempts = 20 if target_port != 0 else 1

        for offset in range(max_attempts):
            candidate_port = target_port + offset if target_port != 0 else 0
            try:
                try:
                    self.server = await asyncio.start_server(
                        self._handle_client, self.host, candidate_port, reuse_address=True, reuse_port=True
                    )
                except (TypeError, OSError):
                    self.server = await asyncio.start_server(
                        self._handle_client, self.host, candidate_port, reuse_address=True
                    )
                self.port = candidate_port
                logger.info(f"Spectre Content Server running on {self.host}:{self.port}")
                return
            except OSError as err:
                if err.errno in (98, 48, 10048) and offset < max_attempts - 1:
                    continue
                raise

    async def stop(self) -> None:
        """Stops the content server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            raw_req = await read_frame(reader)
            req_str = raw_req.decode("utf-8").strip()

            parts = req_str.split()
            if len(parts) >= 2 and parts[0].upper() == "GET":
                requested_page = parts[1].lstrip("/")
            else:
                requested_page = req_str.lstrip("/")

            page_content = self.pages.get(requested_page)
            if not page_content and not requested_page:
                page_content = SPECTRE_SPEC_HTML

            if page_content:
                response = f"SPECTRE/1.0 200 OK\r\nContent-Type: text/html\r\n\r\n{page_content}"
            else:
                response = f"SPECTRE/1.0 404 Not Found\r\nContent-Type: text/html\r\n\r\n{DEFAULT_404_HTML}"

            await send_frame(writer, response.encode("utf-8"))

        except Exception as e:
            logger.error(f"Content Server error: {e}")
        finally:
            writer.close()

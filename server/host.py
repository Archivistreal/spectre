import asyncio
import logging
from typing import Optional
from core.node import send_frame, read_frame

logger = logging.getLogger("spectre.server")

GENESIS_HTML = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Spectre Network Genesis Page</title>
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
        <p>You have reached <b>genesis.spec</b> / <b>genesis.spectre</b> on the Spectre Network protocol.</p>
        <ul>
            <li><b>Guard Node:</b> Ingress entry node with cryptographic signature checks.</li>
            <li><b>Relay Node:</b> Middle transit node isolating origin from destination.</li>
            <li><b>Exit Node:</b> Egress node delivering padded 512-byte cells to target servers.</li>
        </ul>
    </div>

    <div class="card">
        <h2>Explore Network Links</h2>
        <p>Read the cypherpunk principles at <a href="manifesto.spec">Manifesto Page (manifesto.spec)</a></p>
        <p>Reload root document at <a href="genesis.spec">Genesis Page (genesis.spec)</a></p>
    </div>

    <div class="card">
        <h2>Protocol Status</h2>
        <pre><code>[SPECTRE-NET] Cipher: ChaCha20-Poly1305 AEAD | Padding: 512-Byte Fixed | DH: X25519</code></pre>
    </div>
</body>
</html>
"""

MANIFESTO_HTML = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>The Spectre Cypherpunk Manifesto</title>
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
        <p>Return to <a href="genesis.spec">Genesis Page (genesis.spec)</a></p>
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
    <p><a href="genesis.spec">Return to Genesis Page</a></p>
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
            "genesis.spec": GENESIS_HTML,
            "genesis.spectre": GENESIS_HTML,
            "manifesto.spec": MANIFESTO_HTML,
            "manifesto.spectre": MANIFESTO_HTML,
            "/": GENESIS_HTML,
        }

    async def start(self) -> None:
        """Starts the content server."""
        self.server = await asyncio.start_server(self._handle_client, self.host, self.port)
        logger.info(f"Spectre Content Server running on {self.host}:{self.port}")

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
                page_content = GENESIS_HTML

            if page_content:
                response = f"SPECTRE/1.0 200 OK\r\nContent-Type: text/html\r\n\r\n{page_content}"
            else:
                response = f"SPECTRE/1.0 404 Not Found\r\nContent-Type: text/html\r\n\r\n{DEFAULT_404_HTML}"

            await send_frame(writer, response.encode("utf-8"))

        except Exception as e:
            logger.error(f"Content Server error: {e}")
        finally:
            writer.close()

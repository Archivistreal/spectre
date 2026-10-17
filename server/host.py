import asyncio
import logging
from typing import Optional
from core.node import send_frame, read_frame

logger = logging.getLogger("spectre.server")

SPECTRE_SPEC_HTML = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>spectre.spec - The Official Spectre Protocol Homepage</title>
    <style>
        body { background-color: #11111b; color: #cdd6f4; font-family: 'Segoe UI', sans-serif; padding: 25px; line-height: 1.6; }
        h1 { color: #89b4fa; border-bottom: 2px solid #89b4fa; padding-bottom: 10px; font-size: 28px; }
        h2 { color: #f9e2af; margin-top: 20px; font-size: 20px; }
        .hero { background: linear-gradient(135deg, #1e1e2e 0%, #181825 100%); padding: 20px; border-radius: 10px; border: 1px solid #45475a; margin-bottom: 20px; }
        .grid { display: flex; gap: 15px; margin-bottom: 20px; }
        .card { flex: 1; background-color: #1e1e2e; padding: 18px; border-radius: 8px; border: 1px solid #313244; }
        a { color: #89b4fa; text-decoration: none; font-weight: bold; }
        a:hover { text-decoration: underline; color: #b4befe; }
        code { background-color: #181825; color: #a6e3a1; padding: 4px 8px; border-radius: 4px; font-family: monospace; }
        .status-badge { display: inline-block; background-color: #a6e3a1; color: #11111b; font-weight: bold; padding: 4px 12px; border-radius: 15px; font-size: 13px; }
    </style>
</head>
<body>
    <div class="hero">
        <h1>spectre.spec</h1>
        <p><span class="status-badge">SPECTRE ONION WEB ACTIVE</span> &nbsp; <b>Welcome to the official homepage of Spectre Protocol</b></p>
        <p>An encrypted, 3-hop onion routing network engineered for absolute privacy, zero-knowledge topology, fixed 512-byte cell padding, and native <code>.spec</code> website hosting.</p>
    </div>

    <div class="grid">
        <div class="card">
            <h2>Explore Spectre Web Sites</h2>
            <ul>
                <li><a href="spectre.spec">spectre.spec</a> - Official Spectre Network Portal</li>
                <li><a href="genesis.spec">genesis.spec</a> - Network Genesis & Architecture Node</li>
                <li><a href="manifesto.spec">manifesto.spec</a> - The Cypherpunk Manifesto</li>
            </ul>
        </div>

        <div class="card">
            <h2>Security Specifications</h2>
            <ul>
                <li><b>Traffic Analysis Resistance:</b> Fixed 512-byte cell padding</li>
                <li><b>Anti-Replay Protection:</b> Sequence counters per circuit</li>
                <li><b>Memory Zeroization:</b> Ephemeral key wiping on drop</li>
                <li><b>AEAD Cipher:</b> ChaCha20-Poly1305 / X25519 / Ed25519</li>
            </ul>
        </div>
    </div>

    <div class="card">
        <h2>Host Your Own .spec Website</h2>
        <p>You can create any <code>.spec</code> website by hosting HTML files over the Spectre content server network.</p>
        <pre><code>[SPECTRE-NET] Active Circuit: Guard (Port 19001) -> Relay (Port 19002) -> Exit (Port 19003) -> Host (spectre.spec)</code></pre>
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

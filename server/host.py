import asyncio
import logging
from typing import Optional
from core.node import send_frame, read_frame

logger = logging.getLogger("spectre.server")

GENESIS_SPECTRE = """# Welcome to Spectre Network Genesis Page

## Decentralized, Anonymous 3-Hop Onion Routing

You have reached **genesis.spectre**, the root document of the Spectre Protocol.

### Network Architecture
- **Guard Node**: Ingress hop with cryptographic identity verification.
- **Relay Node**: Transit node providing anonymity and session isolation.
- **Exit Node**: Egress node communicating with `.spectre` hosts.

### Navigation Links
- Explore the protocol philosophy at [Manifesto Page](manifesto.spectre)
- View protocol stats at [Genesis Page](genesis.spectre)

```spectre
[SPECTRE] Cryptographic Onion Tunnel Active
[ENCRYPTION] ChaCha20-Poly1305 / X25519 DH / Ed25519 Identity
```
"""

MANIFESTO_SPECTRE = """# The Spectre Cypherpunk Manifesto

## Privacy is a Fundamental Human Right

> "Privacy is necessary for an open society in the electronic age. Privacy is not secrecy. A private matter is something one doesn't want the whole world to know, but a secret matter is something one doesn't want anybody to know. Privacy is the power to selectively reveal oneself to the world."

### Our Core Principles
1. **Zero Knowledge Routing**: No single hop knows both origin and final destination.
2. **Forward Secrecy**: Ephemeral X25519 key negotiation per circuit.
3. **Decentralization**: Independent daemon nodes communicating via socket framing.

### Explore More
- Return to [Genesis Page](genesis.spectre)
"""

DEFAULT_404_SPECTRE = """# 404 Page Not Found

The requested document could not be found on this Spectre content server.

Return to [Genesis Page](genesis.spectre)
"""


class SpectreContentServer:
    """TCP Content Server serving .spectre markup documents."""

    def __init__(self, host: str = "127.0.0.1", port: int = 19080):
        self.host = host
        self.port = port
        self.server: Optional[asyncio.Server] = None
        self.pages = {
            "genesis.spectre": GENESIS_SPECTRE,
            "manifesto.spectre": MANIFESTO_SPECTRE,
            "/": GENESIS_SPECTRE,
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

            # Simple request parsing: "GET page_name" or raw page name
            parts = req_str.split()
            if len(parts) >= 2 and parts[0].upper() == "GET":
                requested_page = parts[1].lstrip("/")
            else:
                requested_page = req_str.lstrip("/")

            page_content = self.pages.get(requested_page)
            if not page_content and not requested_page:
                page_content = GENESIS_SPECTRE

            if page_content:
                response = f"SPECTRE/1.0 200 OK\r\nContent-Type: text/spectre\r\n\r\n{page_content}"
            else:
                response = f"SPECTRE/1.0 404 Not Found\r\nContent-Type: text/spectre\r\n\r\n{DEFAULT_404_SPECTRE}"

            await send_frame(writer, response.encode("utf-8"))

        except Exception as e:
            logger.error(f"Content Server error: {e}")
        finally:
            writer.close()


if __name__ == "__main__":
    async def main():
        logging.basicConfig(level=logging.INFO)
        server = SpectreContentServer()
        await server.start()
        print("Server running. Press Ctrl+C to stop.")
        await asyncio.Event().wait()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

import asyncio
import json
import struct
import logging
from typing import Dict, Optional, Tuple, List
from core.crypto import (
    generate_identity_keypair,
    serialize_ed25519_public_key,
    deserialize_ed25519_public_key,
    sign_data,
    verify_signature,
    generate_ephemeral_keypair,
    serialize_x25519_public_key,
    deserialize_x25519_public_key,
    compute_shared_secret,
    derive_symmetric_key,
    encrypt_payload,
    decrypt_payload,
    wrap_onion,
    unwrap_onion_response,
)

logger = logging.getLogger("spectre.node")

# Framing Helpers

async def send_frame(writer: asyncio.StreamWriter, data: bytes) -> None:
    """Sends 4-byte big-endian length prefixed data over writer."""
    length = len(data)
    writer.write(struct.pack(">I", length) + data)
    await writer.drain()


async def read_frame(reader: asyncio.StreamReader) -> bytes:
    """Reads 4-byte big-endian length prefixed data from reader."""
    header = await reader.readexactly(4)
    length = struct.unpack(">I", header)[0]
    data = await reader.readexactly(length)
    return data


class SpectreNode:
    """
    Spectre Protocol Daemon Node.
    Can act as Guard, Relay, or Exit node.
    """

    def __init__(self, name: str, host: str, port: int, role: str = "relay"):
        self.name = name
        self.host = host
        self.port = port
        self.role = role  # "guard", "relay", "exit"

        self.identity_private_key, self.identity_public_key = generate_identity_keypair()
        self.identity_pub_bytes = serialize_ed25519_public_key(self.identity_public_key)

        self.server: Optional[asyncio.Server] = None
        # Circuit routing state: circuit_id -> dict
        # Dict stores: session_key, next_writer, next_reader, is_exit, etc.
        self.circuits: Dict[str, dict] = {}

    async def start(self) -> None:
        """Starts the node's TCP server."""
        self.server = await asyncio.start_server(self._handle_client, self.host, self.port)
        logger.info(f"[{self.name}] Node ({self.role}) running on {self.host}:{self.port}")

    async def stop(self) -> None:
        """Stops the node's TCP server and closes all active circuits."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        for cid, circuit in list(self.circuits.items()):
            if "next_writer" in circuit and circuit["next_writer"]:
                circuit["next_writer"].close()
        self.circuits.clear()

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """Handles incoming TCP connections to this node."""
        try:
            while True:
                data = await read_frame(reader)
                if not data:
                    break
                await self._process_cell(data, reader, writer)
        except (asyncio.IncompleteReadError, ConnectionResetError):
            pass
        except Exception as e:
            logger.error(f"[{self.name}] Error handling client: {e}")
        finally:
            writer.close()

    async def _process_cell(self, raw_data: bytes, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """Processes a single incoming wire cell."""
        cell = json.loads(raw_data.decode("utf-8"))
        cell_type = cell.get("type")
        circuit_id = cell.get("circuit_id")

        if cell_type == "CREATE":
            # Direct handshake from upstream (client or previous node)
            client_eph_pub_bytes = bytes.fromhex(cell["ephemeral_pub"])
            client_eph_pub = deserialize_x25519_public_key(client_eph_pub_bytes)

            node_eph_priv, node_eph_pub = generate_ephemeral_keypair()
            node_eph_pub_bytes = serialize_x25519_public_key(node_eph_pub)

            shared_secret = compute_shared_secret(node_eph_priv, client_eph_pub)
            session_key = derive_symmetric_key(shared_secret)

            sig = sign_data(self.identity_private_key, node_eph_pub_bytes + client_eph_pub_bytes)

            self.circuits[circuit_id] = {
                "session_key": session_key,
                "upstream_writer": writer,
                "next_writer": None,
                "next_reader": None,
            }

            resp = {
                "type": "CREATED",
                "circuit_id": circuit_id,
                "status": "OK",
                "ephemeral_pub": node_eph_pub_bytes.hex(),
                "identity_pub": self.identity_pub_bytes.hex(),
                "signature": sig.hex(),
            }
            await send_frame(writer, json.dumps(resp).encode("utf-8"))

        elif cell_type == "RELAY":
            # Onion-wrapped payload to peel
            circuit = self.circuits.get(circuit_id)
            if not circuit:
                logger.error(f"[{self.name}] Unknown circuit_id {circuit_id}")
                return

            session_key = circuit["session_key"]
            encrypted_payload = bytes.fromhex(cell["payload"])

            # Peel 1 layer using this node's session key
            peeled_bytes = decrypt_payload(session_key, encrypted_payload)
            peeled_cmd = json.loads(peeled_bytes.decode("utf-8"))

            cmd_type = peeled_cmd.get("cmd")

            if cmd_type == "EXTEND":
                # Extend circuit to target node
                target_host = peeled_cmd["target_host"]
                target_port = peeled_cmd["target_port"]
                target_eph_pub_hex = peeled_cmd["ephemeral_pub"]

                # Connect to target node
                next_reader, next_writer = await asyncio.open_connection(target_host, target_port)
                circuit["next_writer"] = next_writer
                circuit["next_reader"] = next_reader

                # Send CREATE cell to target
                create_cell = {
                    "type": "CREATE",
                    "circuit_id": circuit_id,
                    "ephemeral_pub": target_eph_pub_hex,
                }
                await send_frame(next_writer, json.dumps(create_cell).encode("utf-8"))

                # Read CREATED cell from target
                resp_bytes = await read_frame(next_reader)
                created_cell = json.loads(resp_bytes.decode("utf-8"))

                # Encrypt response with this node's session key before returning
                extended_payload = json.dumps({
                    "status": "EXTENDED",
                    "created_cell": created_cell
                }).encode("utf-8")

                encrypted_resp = encrypt_payload(session_key, extended_payload)
                relay_resp = {
                    "type": "RELAY_RESPONSE",
                    "circuit_id": circuit_id,
                    "payload": encrypted_resp.hex(),
                }
                await send_frame(writer, json.dumps(relay_resp).encode("utf-8"))

            elif cmd_type == "FORWARD":
                # Forward peeled RELAY payload to next hop
                next_writer = circuit.get("next_writer")
                if next_writer:
                    next_payload = peeled_cmd["inner_payload"]
                    relay_cell = {
                        "type": "RELAY",
                        "circuit_id": circuit_id,
                        "payload": next_payload,
                    }
                    await send_frame(next_writer, json.dumps(relay_cell).encode("utf-8"))

                    # Read response from next hop
                    next_reader = circuit["next_reader"]
                    raw_next_resp = await read_frame(next_reader)
                    next_resp_cell = json.loads(raw_next_resp.decode("utf-8"))

                    # Encrypt response with this node's key
                    inner_resp_bytes = bytes.fromhex(next_resp_cell["payload"])
                    enc_resp_bytes = encrypt_payload(session_key, inner_resp_bytes)

                    relay_resp = {
                        "type": "RELAY_RESPONSE",
                        "circuit_id": circuit_id,
                        "payload": enc_resp_bytes.hex(),
                    }
                    await send_frame(writer, json.dumps(relay_resp).encode("utf-8"))

            elif cmd_type == "DESTINATION_DATA":
                # Exit node functionality: forward plaintext data to content server
                target_host = peeled_cmd["target_host"]
                target_port = peeled_cmd["target_port"]
                req_data = peeled_cmd["data"].encode("utf-8")

                srv_reader, srv_writer = await asyncio.open_connection(target_host, target_port)
                await send_frame(srv_writer, req_data)
                resp_data = await read_frame(srv_reader)
                srv_writer.close()

                # Encrypt response with Exit node's session key
                enc_resp = encrypt_payload(session_key, resp_data)
                relay_resp = {
                    "type": "RELAY_RESPONSE",
                    "circuit_id": circuit_id,
                    "payload": enc_resp.hex(),
                }
                await send_frame(writer, json.dumps(relay_resp).encode("utf-8"))


class SpectreClientCircuit:
    """
    Client-side 3-hop circuit manager over real TCP sockets.
    Handles circuit construction (CREATE & EXTEND) and onion payload delivery.
    """

    def __init__(self, guard_address: Tuple[str, int], relay_address: Tuple[str, int], exit_address: Tuple[str, int]):
        self.guard_address = guard_address
        self.relay_address = relay_address
        self.exit_address = exit_address

        self.circuit_id: str = "circ_1001"
        self.session_keys: List[bytes] = []
        self.guard_writer: Optional[asyncio.StreamWriter] = None
        self.guard_reader: Optional[asyncio.StreamReader] = None

    async def build_circuit(self) -> List[bytes]:
        """Establishes 3-hop circuit through Guard, Relay, and Exit nodes."""
        self.session_keys.clear()

        # Step 1: Connect to Guard and CREATE hop 1
        g_host, g_port = self.guard_address
        self.guard_reader, self.guard_writer = await asyncio.open_connection(g_host, g_port)

        cli_eph_priv1, cli_eph_pub1 = generate_ephemeral_keypair()
        cli_eph_pub1_bytes = serialize_x25519_public_key(cli_eph_pub1)

        create_cell = {
            "type": "CREATE",
            "circuit_id": self.circuit_id,
            "ephemeral_pub": cli_eph_pub1_bytes.hex(),
        }
        await send_frame(self.guard_writer, json.dumps(create_cell).encode("utf-8"))

        raw_created = await read_frame(self.guard_reader)
        created_cell = json.loads(raw_created.decode("utf-8"))

        guard_eph_pub = deserialize_x25519_public_key(bytes.fromhex(created_cell["ephemeral_pub"]))
        guard_ident_pub = deserialize_ed25519_public_key(bytes.fromhex(created_cell["identity_pub"]))
        guard_sig = bytes.fromhex(created_cell["signature"])

        # Verify signature
        if not verify_signature(guard_ident_pub, guard_sig, bytes.fromhex(created_cell["ephemeral_pub"]) + cli_eph_pub1_bytes):
            raise ValueError("Guard node identity signature verification failed!")

        shared1 = compute_shared_secret(cli_eph_priv1, guard_eph_pub)
        key1 = derive_symmetric_key(shared1)
        self.session_keys.append(key1)

        # Step 2: EXTEND circuit to Relay (Hop 2)
        r_host, r_port = self.relay_address
        cli_eph_priv2, cli_eph_pub2 = generate_ephemeral_keypair()
        cli_eph_pub2_bytes = serialize_x25519_public_key(cli_eph_pub2)

        extend_cmd2 = {
            "cmd": "EXTEND",
            "target_host": r_host,
            "target_port": r_port,
            "ephemeral_pub": cli_eph_pub2_bytes.hex(),
        }
        enc_cmd2 = encrypt_payload(key1, json.dumps(extend_cmd2).encode("utf-8"))
        relay_cell2 = {
            "type": "RELAY",
            "circuit_id": self.circuit_id,
            "payload": enc_cmd2.hex(),
        }
        await send_frame(self.guard_writer, json.dumps(relay_cell2).encode("utf-8"))

        raw_resp2 = await read_frame(self.guard_reader)
        resp_cell2 = json.loads(raw_resp2.decode("utf-8"))
        dec_resp2 = decrypt_payload(key1, bytes.fromhex(resp_cell2["payload"]))
        ext_data2 = json.loads(dec_resp2.decode("utf-8"))
        created2 = ext_data2["created_cell"]

        relay_eph_pub = deserialize_x25519_public_key(bytes.fromhex(created2["ephemeral_pub"]))
        relay_ident_pub = deserialize_ed25519_public_key(bytes.fromhex(created2["identity_pub"]))
        relay_sig = bytes.fromhex(created2["signature"])

        if not verify_signature(relay_ident_pub, relay_sig, bytes.fromhex(created2["ephemeral_pub"]) + cli_eph_pub2_bytes):
            raise ValueError("Relay node identity signature verification failed!")

        shared2 = compute_shared_secret(cli_eph_priv2, relay_eph_pub)
        key2 = derive_symmetric_key(shared2)
        self.session_keys.append(key2)

        # Step 3: EXTEND circuit to Exit (Hop 3)
        e_host, e_port = self.exit_address
        cli_eph_priv3, cli_eph_pub3 = generate_ephemeral_keypair()
        cli_eph_pub3_bytes = serialize_x25519_public_key(cli_eph_pub3)

        extend_cmd3 = {
            "cmd": "EXTEND",
            "target_host": e_host,
            "target_port": e_port,
            "ephemeral_pub": cli_eph_pub3_bytes.hex(),
        }
        enc_cmd3_relay = encrypt_payload(key2, json.dumps(extend_cmd3).encode("utf-8"))
        forward_cmd2 = {
            "cmd": "FORWARD",
            "inner_payload": enc_cmd3_relay.hex(),
        }
        enc_cmd3_guard = encrypt_payload(key1, json.dumps(forward_cmd2).encode("utf-8"))

        relay_cell3 = {
            "type": "RELAY",
            "circuit_id": self.circuit_id,
            "payload": enc_cmd3_guard.hex(),
        }
        await send_frame(self.guard_writer, json.dumps(relay_cell3).encode("utf-8"))

        raw_resp3 = await read_frame(self.guard_reader)
        resp_cell3 = json.loads(raw_resp3.decode("utf-8"))
        # Response unwraps in order: key1 then key2
        unwrapped_resp3 = unwrap_onion_response(bytes.fromhex(resp_cell3["payload"]), [key1, key2])
        ext_data3 = json.loads(unwrapped_resp3.decode("utf-8"))
        created3 = ext_data3["created_cell"]

        exit_eph_pub = deserialize_x25519_public_key(bytes.fromhex(created3["ephemeral_pub"]))
        exit_ident_pub = deserialize_ed25519_public_key(bytes.fromhex(created3["identity_pub"]))
        exit_sig = bytes.fromhex(created3["signature"])

        if not verify_signature(exit_ident_pub, exit_sig, bytes.fromhex(created3["ephemeral_pub"]) + cli_eph_pub3_bytes):
            raise ValueError("Exit node identity signature verification failed!")

        shared3 = compute_shared_secret(cli_eph_priv3, exit_eph_pub)
        key3 = derive_symmetric_key(shared3)
        self.session_keys.append(key3)

        logger.info("3-Hop Onion Circuit built successfully!")
        return self.session_keys

    async def send_request(self, target_host: str, target_port: int, req_data: str) -> str:
        """
        Sends request data over the 3-hop onion circuit to the exit node,
        which fetches content from target_host:target_port.
        """
        if len(self.session_keys) != 3:
            raise RuntimeError("Circuit not fully established!")

        key1, key2, key3 = self.session_keys

        dest_cmd = {
            "cmd": "DESTINATION_DATA",
            "target_host": target_host,
            "target_port": target_port,
            "data": req_data,
        }

        # Layer 3 (Exit): Encrypt dest command
        enc_exit = encrypt_payload(key3, json.dumps(dest_cmd).encode("utf-8"))

        # Layer 2 (Relay): Forward command to Exit
        forward_relay = {
            "cmd": "FORWARD",
            "inner_payload": enc_exit.hex(),
        }
        enc_relay = encrypt_payload(key2, json.dumps(forward_relay).encode("utf-8"))

        # Layer 1 (Guard): Forward command to Relay
        forward_guard = {
            "cmd": "FORWARD",
            "inner_payload": enc_relay.hex(),
        }
        enc_guard = encrypt_payload(key1, json.dumps(forward_guard).encode("utf-8"))

        relay_cell = {
            "type": "RELAY",
            "circuit_id": self.circuit_id,
            "payload": enc_guard.hex(),
        }
        await send_frame(self.guard_writer, json.dumps(relay_cell).encode("utf-8"))

        raw_resp = await read_frame(self.guard_reader)
        resp_cell = json.loads(raw_resp.decode("utf-8"))

        # Unwrap 3 response layers (Guard -> Relay -> Exit)
        unwrapped_resp = unwrap_onion_response(bytes.fromhex(resp_cell["payload"]), self.session_keys)
        return unwrapped_resp.decode("utf-8")

    async def close(self) -> None:
        """Closes circuit connection."""
        if self.guard_writer:
            self.guard_writer.close()
            await self.guard_writer.wait_closed()

import os
import struct
import random
import math
import json
import urllib.request
from typing import List, Tuple
from cryptography.hazmat.primitives.asymmetric import ed25519, x25519
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from cryptography.exceptions import InvalidSignature, InvalidTag

MIN_CELL_SIZE = 512
MAX_CELL_SIZE = 1024


# --- Quantum Entropy Source Helper ---

def get_quantum_entropy(length: int = 32) -> bytes:
    """
    Fetches quantum entropy bytes from ANU QRNG (Vacuum Fluctuations).
    Falls back gracefully to OS hardware TRNG (os.urandom) if offline or on timeout.
    """
    try:
        url = f"https://qrng.anu.edu.au/API/jsonI.php?length={length}&type=uint8"
        req = urllib.request.Request(url, headers={"User-Agent": "SpectreProtocol/1.0"})
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("success") and "data" in data and len(data["data"]) >= length:
                    return bytes(data["data"][:length])
    except Exception:
        pass
    return os.urandom(length)


# --- Variable Cell Padding & Anti-Traffic Analysis Helpers ---

def pad_cell(payload: bytes, min_size: int = MIN_CELL_SIZE, max_size: int = MAX_CELL_SIZE) -> bytes:
    """
    Pads payload dynamically with random jitter bytes between min_size (512) and max_size (1024).
    Format: 4-byte big-endian payload length + payload + random padding bytes.
    Eliminates static 512-byte size fingerprinting and packet length correlation.
    """
    payload_len = len(payload)
    base_needed = payload_len + 4

    # Calculate target size with randomized padding
    if base_needed < min_size:
        target_size = random.randint(min_size, max_size)
    else:
        # For larger payloads, pad to a multiple of 256 bytes plus random jitter
        num_blocks = math.ceil(base_needed / 256)
        base_size = num_blocks * 256
        target_size = base_size + random.randint(32, 128)

    header = struct.pack(">I", payload_len)
    padding_needed = target_size - base_needed
    padding = os.urandom(padding_needed)
    return header + payload + padding


def unpad_cell(cell_data: bytes) -> bytes:
    """
    Unpads variable-length cell data.
    Extracts 4-byte length header and returns original payload bytes.
    """
    if len(cell_data) < 4:
        raise ValueError("Invalid cell data: shorter than header")

    payload_len = struct.unpack(">I", cell_data[:4])[0]
    if payload_len + 4 > len(cell_data):
        raise ValueError(f"Corrupted cell header: payload_len {payload_len} exceeds cell size {len(cell_data)}")

    return cell_data[4: 4 + payload_len]


# --- Zeroize Key Memory Helper ---

def zeroize_bytes(buffer: bytearray) -> None:
    """Securely overwrites bytearray memory in place with zeros."""
    for i in range(len(buffer)):
        buffer[i] = 0


# --- Ed25519 Identity Key Helpers ---

def generate_identity_keypair() -> Tuple[ed25519.Ed25519PrivateKey, ed25519.Ed25519PublicKey]:
    """Generates an Ed25519 private/public keypair for node identity."""
    private_key = ed25519.Ed25519PrivateKey.generate()
    return private_key, private_key.public_key()


def serialize_ed25519_public_key(public_key: ed25519.Ed25519PublicKey) -> bytes:
    """Serializes Ed25519 public key to 32 raw bytes."""
    from cryptography.hazmat.primitives import serialization
    return public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )


def deserialize_ed25519_public_key(data: bytes) -> ed25519.Ed25519PublicKey:
    """Deserializes 32 raw bytes to an Ed25519 public key."""
    return ed25519.Ed25519PublicKey.from_public_bytes(data)


def sign_data(private_key: ed25519.Ed25519PrivateKey, data: bytes) -> bytes:
    """Signs bytes data using Ed25519 private key."""
    return private_key.sign(data)


def verify_signature(public_key: ed25519.Ed25519PublicKey, signature: bytes, data: bytes) -> bool:
    """Verifies Ed25519 signature. Returns True if valid, False otherwise."""
    try:
        public_key.verify(signature, data)
        return True
    except InvalidSignature:
        return False


# --- X25519 Key Exchange Helpers ---

def generate_ephemeral_keypair() -> Tuple[x25519.X25519PrivateKey, x25519.X25519PublicKey]:
    """Generates ephemeral X25519 private/public keypair."""
    private_key = x25519.X25519PrivateKey.generate()
    return private_key, private_key.public_key()


def serialize_x25519_public_key(public_key: x25519.X25519PublicKey) -> bytes:
    """Serializes X25519 public key to 32 raw bytes."""
    from cryptography.hazmat.primitives import serialization
    return public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )


def deserialize_x25519_public_key(data: bytes) -> x25519.X25519PublicKey:
    """Deserializes 32 raw bytes to an X25519 public key."""
    return x25519.X25519PublicKey.from_public_bytes(data)


def compute_shared_secret(private_key: x25519.X25519PrivateKey, peer_public_key: x25519.X25519PublicKey) -> bytes:
    """Performs Diffie-Hellman exchange using X25519."""
    return private_key.exchange(peer_public_key)


# --- Symmetric Key Derivation & AEAD Encryption ---

def derive_symmetric_key(shared_secret: bytes, salt: bytes = None, info: bytes = b"spectre-onion-v1") -> bytes:
    """Derives a 32-byte symmetric key using HKDF-SHA256."""
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        info=info,
    )
    return hkdf.derive(shared_secret)


def encrypt_payload(key: bytes, plaintext: bytes) -> bytes:
    """
    Encrypts plaintext using ChaCha20-Poly1305 AEAD.
    Returns: 12-byte random nonce + ciphertext (with Poly1305 tag).
    """
    chacha = ChaCha20Poly1305(key)
    nonce = os.urandom(12)
    ciphertext = chacha.encrypt(nonce, plaintext, None)
    return nonce + ciphertext


def decrypt_payload(key: bytes, ciphertext_with_nonce: bytes) -> bytes:
    """
    Decrypts ciphertext_with_nonce using ChaCha20-Poly1305 AEAD.
    Expects 12-byte nonce prefixed to ciphertext.
    Raises InvalidTag if decryption fails.
    """
    if len(ciphertext_with_nonce) < 12:
        raise ValueError("Ciphertext payload too short")
    nonce = ciphertext_with_nonce[:12]
    ciphertext = ciphertext_with_nonce[12:]
    chacha = ChaCha20Poly1305(key)
    return chacha.decrypt(nonce, ciphertext, None)


# --- Multi-Hop Onion Layering Helpers ---

def wrap_onion(payload: bytes, keys: List[bytes]) -> bytes:
    """
    Wraps payload in onion layers from last key (Exit) to first key (Guard).
    Given keys = [key_guard, key_relay, key_exit], payload is encrypted with key_exit,
    then key_relay, then key_guard.
    """
    current_payload = payload
    for key in reversed(keys):
        current_payload = encrypt_payload(key, current_payload)
    return current_payload


def peel_onion_layer(ciphertext: bytes, key: bytes) -> bytes:
    """Peels a single onion layer using key."""
    return decrypt_payload(key, ciphertext)


def unwrap_onion_response(ciphertext: bytes, keys: List[bytes]) -> bytes:
    """
    Unwraps multi-layer response from nodes.
    On response path, Guard encrypts with key1, Relay with key2, Exit with key3.
    Client unwraps using key1, then key2, then key3.
    """
    current_payload = ciphertext
    for key in keys:
        current_payload = decrypt_payload(key, current_payload)
    return current_payload

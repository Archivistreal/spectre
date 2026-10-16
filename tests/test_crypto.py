import pytest
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
    peel_onion_layer,
    unwrap_onion_response,
    pad_cell,
    unpad_cell,
    zeroize_bytes,
    CELL_SIZE,
)
from cryptography.exceptions import InvalidTag


def test_fixed_cell_padding():
    payload = b"GET genesis.spectre SPECTRE/1.0"
    cell = pad_cell(payload)
    assert len(cell) == CELL_SIZE
    unpadded = unpad_cell(cell)
    assert unpadded == payload


def test_zeroize_bytes_memory():
    secret_key = bytearray(b"super_secret_32bytes_sessionkey!")
    assert len(secret_key) == 32
    zeroize_bytes(secret_key)
    assert secret_key == bytearray(32)


def test_ed25519_identity_and_signature():
    priv, pub = generate_identity_keypair()
    pub_bytes = serialize_ed25519_public_key(pub)
    assert len(pub_bytes) == 32
    pub_deser = deserialize_ed25519_public_key(pub_bytes)

    data = b"Spectre Network Node Identity Check"
    sig = sign_data(priv, data)
    assert verify_signature(pub_deser, sig, data) is True
    assert verify_signature(pub_deser, sig, b"Tampered data") is False


def test_x25519_key_exchange_and_hkdf():
    priv1, pub1 = generate_ephemeral_keypair()
    priv2, pub2 = generate_ephemeral_keypair()

    secret1 = compute_shared_secret(priv1, pub2)
    secret2 = compute_shared_secret(priv2, pub1)
    assert secret1 == secret2

    key1 = derive_symmetric_key(secret1, salt=b"salt123")
    key2 = derive_symmetric_key(secret2, salt=b"salt123")
    assert key1 == key2
    assert len(key1) == 32


def test_chacha20_poly1305_aead():
    key = derive_symmetric_key(b"test_secret_123")
    msg = b"Hello Spectre Onion Network!"
    ciphertext = encrypt_payload(key, msg)
    assert ciphertext != msg

    decrypted = decrypt_payload(key, ciphertext)
    assert decrypted == msg

    # Tampered ciphertext check
    tampered = bytearray(ciphertext)
    tampered[-1] ^= 0xFF
    with pytest.raises(InvalidTag):
        decrypt_payload(key, bytes(tampered))


def test_3hop_onion_wrap_and_peel():
    guard_key = derive_symmetric_key(b"guard_secret")
    relay_key = derive_symmetric_key(b"relay_secret")
    exit_key = derive_symmetric_key(b"exit_secret")

    keys = [guard_key, relay_key, exit_key]
    payload = pad_cell(b"GET genesis.spectre SPECTRE/1.0")

    # Client wraps onion (Exit -> Relay -> Guard)
    wrapped = wrap_onion(payload, keys)

    # Hop 1: Guard peels outer layer
    peeled_guard = peel_onion_layer(wrapped, guard_key)

    # Hop 2: Relay peels middle layer
    peeled_relay = peel_onion_layer(peeled_guard, relay_key)

    # Hop 3: Exit peels inner layer
    peeled_exit = peel_onion_layer(peeled_relay, exit_key)

    assert unpad_cell(peeled_exit) == b"GET genesis.spectre SPECTRE/1.0"


def test_onion_response_unwrap():
    guard_key = derive_symmetric_key(b"guard_secret")
    relay_key = derive_symmetric_key(b"relay_secret")
    exit_key = derive_symmetric_key(b"exit_secret")

    keys = [guard_key, relay_key, exit_key]
    raw_response = pad_cell(b"SPECTRE/1.0 200 OK\r\n\r\n# Welcome to Genesis Page")

    # Response path: Exit encrypts with exit_key, Relay encrypts with relay_key, Guard encrypts with guard_key
    resp_exit = encrypt_payload(exit_key, raw_response)
    resp_relay = encrypt_payload(relay_key, resp_exit)
    resp_guard = encrypt_payload(guard_key, resp_relay)

    # Client unwraps response in order: Guard -> Relay -> Exit
    unwrapped = unwrap_onion_response(resp_guard, keys)
    assert unpad_cell(unwrapped) == b"SPECTRE/1.0 200 OK\r\n\r\n# Welcome to Genesis Page"

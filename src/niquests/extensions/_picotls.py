"""
This module purpose is to have a "super" minimalist way to
speak with a TLS 1.2+ server. The goal of this is to extract
the certificate chain to be used for OCSP stapling / revocation.
It's not meant to establish a secure connection. Never!
"""

from __future__ import annotations

import hmac
from hashlib import sha256

import idna

LEGACY_TLS_VERSION = b"\x03\x03"
TLS_AES_128_GCM_SHA256 = b"\x13\x01"

CHANGE_CIPHER = b"\x14"
ALERT = b"\x15"
HANDSHAKE = b"\x16"
APPLICATION_DATA = b"\x17"

# SYMMETRIC CIPHERS
AES_ROUNDS = 10

# AES_SBOX is some permutation of numbers 0-255
AES_SBOX = [
    99,
    124,
    119,
    123,
    242,
    107,
    111,
    197,
    48,
    1,
    103,
    43,
    254,
    215,
    171,
    118,
    202,
    130,
    201,
    125,
    250,
    89,
    71,
    240,
    173,
    212,
    162,
    175,
    156,
    164,
    114,
    192,
    183,
    253,
    147,
    38,
    54,
    63,
    247,
    204,
    52,
    165,
    229,
    241,
    113,
    216,
    49,
    21,
    4,
    199,
    35,
    195,
    24,
    150,
    5,
    154,
    7,
    18,
    128,
    226,
    235,
    39,
    178,
    117,
    9,
    131,
    44,
    26,
    27,
    110,
    90,
    160,
    82,
    59,
    214,
    179,
    41,
    227,
    47,
    132,
    83,
    209,
    0,
    237,
    32,
    252,
    177,
    91,
    106,
    203,
    190,
    57,
    74,
    76,
    88,
    207,
    208,
    239,
    170,
    251,
    67,
    77,
    51,
    133,
    69,
    249,
    2,
    127,
    80,
    60,
    159,
    168,
    81,
    163,
    64,
    143,
    146,
    157,
    56,
    245,
    188,
    182,
    218,
    33,
    16,
    255,
    243,
    210,
    205,
    12,
    19,
    236,
    95,
    151,
    68,
    23,
    196,
    167,
    126,
    61,
    100,
    93,
    25,
    115,
    96,
    129,
    79,
    220,
    34,
    42,
    144,
    136,
    70,
    238,
    184,
    20,
    222,
    94,
    11,
    219,
    224,
    50,
    58,
    10,
    73,
    6,
    36,
    92,
    194,
    211,
    172,
    98,
    145,
    149,
    228,
    121,
    231,
    200,
    55,
    109,
    141,
    213,
    78,
    169,
    108,
    86,
    244,
    234,
    101,
    122,
    174,
    8,
    186,
    120,
    37,
    46,
    28,
    166,
    180,
    198,
    232,
    221,
    116,
    31,
    75,
    189,
    139,
    138,
    112,
    62,
    181,
    102,
    72,
    3,
    246,
    14,
    97,
    53,
    87,
    185,
    134,
    193,
    29,
    158,
    225,
    248,
    152,
    17,
    105,
    217,
    142,
    148,
    155,
    30,
    135,
    233,
    206,
    85,
    40,
    223,
    140,
    161,
    137,
    13,
    191,
    230,
    66,
    104,
    65,
    153,
    45,
    15,
    176,
    84,
    187,
    22,
]


def bytes_to_num(b):
    return int.from_bytes(b, "big")


def num_to_bytes(num, bytes_len):
    return int.to_bytes(num, bytes_len, "big")


def xor(a, b):
    return bytes(i ^ j for i, j in zip(a, b))


def egcd(a, b):
    if a == 0:
        return 0, 1
    y, x = egcd(b % a, a)
    return x - (b // a) * y, y


def mod_inv(a, p):
    return egcd(a, p)[0] if a >= 0 else p - egcd(-a, p)[0]


def add_two_ec_points(p1_x, p1_y, p2_x, p2_y, a, p):
    if p1_x == p2_x and p1_y == p2_y:
        s = (3 * p1_x * p1_x + a) * mod_inv(2 * p2_y, p)
    elif p1_x != p2_x:
        s = (p1_y - p2_y) * mod_inv(p1_x - p2_x, p)
    else:
        raise NotImplementedError

    x = s * s - p1_x - p2_x
    y = -p1_y + s * (p1_x - x)
    return x % p, y % p


def multiply_num_on_ec_point(num, g_x, g_y, a, p):
    x, y = None, None
    while num:
        if num & 1:
            x, y = add_two_ec_points(x, y, g_x, g_y, a, p) if x else (g_x, g_y)
        g_x, g_y = add_two_ec_points(g_x, g_y, g_x, g_y, a, p)
        num >>= 1
    return x, y


def gen_client_hello(hostname, client_random, ecdh_pubkey_x, ecdh_pubkey_y):
    CLIENT_HELLO = b"\x01"

    session_id = b""
    compression_method = b"\x00"  # no compression

    if not hostname.isascii():
        hostname = idna.encode(hostname)
    else:
        hostname = hostname.encode("ascii")

    hostname_prefix = b"\x00\x00"
    hostname_list_length = num_to_bytes(len(hostname) + 5, 2)
    hostname_item_length = num_to_bytes(len(hostname) + 3, 2)
    hostname_length = num_to_bytes(len(hostname), 2)

    hostname_extension = (
        hostname_prefix
        + hostname_list_length
        + hostname_item_length
        + b"\x00"
        + hostname_length
        + hostname
    )

    supported_versions = b"\x00\x2b"
    supported_versions_length = b"\x00\x03"
    another_supported_versions_length = b"\x02"
    tls1_3_version = b"\x03\x04"
    supported_version_extension = (
        supported_versions
        + supported_versions_length
        + another_supported_versions_length
        + tls1_3_version
    )

    signature_algos = b"\x00\x0d"
    signature_algos_length = b"\x00\x06"
    another_signature_algos_length = b"\x00\x04"
    rsa_pss_rsae_sha256_algo = b"\x08\x04"
    # ECDSA/SECP256r1/SHA256 (e.g. for EV certs sig, mandatory)
    ecdsa_secp256r1_sha256_algo = b"\x04\x03"
    signature_algos_extension = (
        signature_algos
        + signature_algos_length
        + another_signature_algos_length
        + rsa_pss_rsae_sha256_algo
        + ecdsa_secp256r1_sha256_algo
    )

    supported_groups = b"\x00\x0a"
    supported_groups_length = b"\x00\x04"
    another_supported_groups_length = b"\x00\x02"
    secp256r1_group = b"\x00\x17"
    supported_groups_extension = (
        supported_groups
        + supported_groups_length
        + another_supported_groups_length
        + secp256r1_group
    )

    ecdh_pubkey = (
        b"\x04" + num_to_bytes(ecdh_pubkey_x, 32) + num_to_bytes(ecdh_pubkey_y, 32)
    )

    key_share = b"\x00\x33"
    key_share_length = num_to_bytes(len(ecdh_pubkey) + 4 + 2, 2)
    another_key_share_length = num_to_bytes(len(ecdh_pubkey) + 4, 2)
    key_exchange_len = num_to_bytes(len(ecdh_pubkey), 2)
    key_share_extension = (
        key_share
        + key_share_length
        + another_key_share_length
        + secp256r1_group
        + key_exchange_len
        + ecdh_pubkey
    )

    extensions = (
        hostname_extension
        + supported_version_extension
        + signature_algos_extension
        + supported_groups_extension
        + key_share_extension
    )

    client_hello_data = (
        LEGACY_TLS_VERSION
        + client_random
        + num_to_bytes(len(session_id), 1)
        + session_id
        + num_to_bytes(len(TLS_AES_128_GCM_SHA256), 2)
        + TLS_AES_128_GCM_SHA256
        + num_to_bytes(len(compression_method), 1)
        + compression_method
        + num_to_bytes(len(extensions), 2)
    ) + extensions

    client_hello_len_bytes = num_to_bytes(len(client_hello_data), 3)
    client_hello_tlv = CLIENT_HELLO + client_hello_len_bytes + client_hello_data

    return client_hello_tlv


def handle_server_hello(server_hello):
    handshake_type = server_hello[0]

    SERVER_HELLO = 0x2
    assert handshake_type == SERVER_HELLO

    # server_hello_len = server_hello[1:4]
    # server_version = server_hello[4:6]

    server_random = server_hello[6:38]

    session_id_len = bytes_to_num(server_hello[38:39])
    session_id = server_hello[39 : 39 + session_id_len]

    cipher_suite = server_hello[39 + session_id_len : 39 + session_id_len + 2]
    assert cipher_suite == TLS_AES_128_GCM_SHA256

    # compression_method = server_hello[39 + session_id_len + 2 : 39 + session_id_len + 3]

    extensions_length = bytes_to_num(
        server_hello[39 + session_id_len + 3 : 39 + session_id_len + 3 + 2]
    )
    extensions = server_hello[
        39 + session_id_len + 3 + 2 : 39 + session_id_len + 3 + 2 + extensions_length
    ]

    public_ec_key = b""
    ptr = 0
    while ptr < extensions_length:
        extension_type = extensions[ptr : ptr + 2]
        extension_length = bytes_to_num(extensions[ptr + 2 : ptr + 4])
        KEY_SHARE = b"\x00\x33"
        if extension_type != KEY_SHARE:
            ptr += extension_length + 4
            continue
        group = extensions[ptr + 4 : ptr + 6]
        SECP256R1_GROUP = b"\x00\x17"
        assert group == SECP256R1_GROUP
        key_exchange_len = bytes_to_num(extensions[ptr + 6 : ptr + 8])

        public_ec_key = extensions[ptr + 8 : ptr + 8 + key_exchange_len]
        break

    if not public_ec_key:
        raise ValueError("No public ECDH key in server hello")

    public_ec_key_x = bytes_to_num(public_ec_key[1:33])
    public_ec_key_y = bytes_to_num(public_ec_key[33:])

    return server_random, session_id, public_ec_key_x, public_ec_key_y


def mutliply_blocks(x, y):
    z = 0
    for i in range(128):
        if x & (1 << (127 - i)):
            z ^= y
        y = (y >> 1) ^ (0xE1 << 120) if y & 1 else y >> 1
    return z


def ghash(h, data):
    CHUNK_LEN = 16

    y = 0
    for pos in range(0, len(data), CHUNK_LEN):
        chunk = bytes_to_num(data[pos : pos + CHUNK_LEN])
        y = mutliply_blocks(y ^ chunk, h)
    return y


def derive_secret(label, key, data, hash_len):
    full_label = b"tls13 " + label
    packed_data = (
        num_to_bytes(hash_len, 2)
        + num_to_bytes(len(full_label), 1)
        + full_label
        + num_to_bytes(len(data), 1)
        + data
    )

    secret = bytearray()
    i = 1
    while len(secret) < hash_len:
        secret += hmac.new(
            key, secret[-32:] + packed_data + num_to_bytes(i, 1), sha256
        ).digest()
        i += 1
    return bytes(secret[:hash_len])


def aes128_expand_key(key):
    RCON = [0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1B, 0x36]

    enc_keys = [[0, 0, 0, 0] for i in range(AES_ROUNDS + 1)]
    enc_keys[0] = [bytes_to_num(key[i : i + 4]) for i in [0, 4, 8, 12]]

    for t in range(1, AES_ROUNDS + 1):
        prev_key = enc_keys[t - 1]
        enc_keys[t][0] = (
            (AES_SBOX[(prev_key[3] >> 8 * 2) & 0xFF] << 8 * 3)
            ^ (AES_SBOX[(prev_key[3] >> 8 * 1) & 0xFF] << 8 * 2)
            ^ (AES_SBOX[(prev_key[3] >> 8 * 0) & 0xFF] << 8 * 1)
            ^ (AES_SBOX[(prev_key[3] >> 8 * 3) & 0xFF] << 8 * 0)
            ^ (RCON[t - 1] << 8 * 3)
            ^ prev_key[0]
        )

        for i in range(1, 4):
            enc_keys[t][i] = enc_keys[t][i - 1] ^ prev_key[i]
    return enc_keys


def aes128_encrypt(key, plaintext):
    TWOTIMES = [2 * num if 2 * num < 256 else 2 * num & 0xFF ^ 27 for num in range(256)]

    enc_keys = aes128_expand_key(key)

    t = [bytes_to_num(plaintext[4 * i : 4 * i + 4]) ^ enc_keys[0][i] for i in range(4)]
    for r in range(1, AES_ROUNDS):
        t = [
            [
                AES_SBOX[(t[(i + 0) % 4] >> 8 * 3) & 0xFF],
                AES_SBOX[(t[(i + 1) % 4] >> 8 * 2) & 0xFF],
                AES_SBOX[(t[(i + 2) % 4] >> 8 * 1) & 0xFF],
                AES_SBOX[(t[(i + 3) % 4] >> 8 * 0) & 0xFF],
            ]
            for i in range(4)
        ]

        t = [
            [
                c[1] ^ c[2] ^ c[3] ^ TWOTIMES[c[0] ^ c[1]],
                c[0] ^ c[2] ^ c[3] ^ TWOTIMES[c[1] ^ c[2]],
                c[0] ^ c[1] ^ c[3] ^ TWOTIMES[c[2] ^ c[3]],
                c[0] ^ c[1] ^ c[2] ^ TWOTIMES[c[3] ^ c[0]],
            ]
            for c in t
        ]

        t = [bytes_to_num(t[i]) ^ enc_keys[r][i] for i in range(4)]

    result = [
        bytes(
            [
                AES_SBOX[(t[(i + 0) % 4] >> 8 * 3) & 0xFF]
                ^ (enc_keys[-1][i] >> 8 * 3) & 0xFF,
                AES_SBOX[(t[(i + 1) % 4] >> 8 * 2) & 0xFF]
                ^ (enc_keys[-1][i] >> 8 * 2) & 0xFF,
                AES_SBOX[(t[(i + 2) % 4] >> 8 * 1) & 0xFF]
                ^ (enc_keys[-1][i] >> 8 * 1) & 0xFF,
                AES_SBOX[(t[(i + 3) % 4] >> 8 * 0) & 0xFF]
                ^ (enc_keys[-1][i] >> 8 * 0) & 0xFF,
            ]
        )
        for i in range(4)
    ]
    return b"".join(result)


def aes128_ctr_encrypt(key, msg, nonce, counter_start_val):
    BLOCK_SIZE = 16

    ans = []
    counter = counter_start_val
    for s in range(0, len(msg), BLOCK_SIZE):
        chunk = msg[s : s + BLOCK_SIZE]

        chunk_nonce = nonce + num_to_bytes(counter, 4)
        encrypted_chunk_nonce = aes128_encrypt(key, chunk_nonce)

        decrypted_chunk = xor(chunk, encrypted_chunk_nonce)
        ans.append(decrypted_chunk)

        counter += 1
    return b"".join(ans)


def aes128_ctr_decrypt(key, msg, nonce, counter_start_val):
    return aes128_ctr_encrypt(key, msg, nonce, counter_start_val)


def calc_pretag(key, encrypted_msg, associated_data):
    v = b"\x00" * (16 * ((len(associated_data) + 15) // 16) - len(associated_data))
    u = b"\x00" * (16 * ((len(encrypted_msg) + 15) // 16) - len(encrypted_msg))

    h = bytes_to_num(aes128_encrypt(key, b"\x00" * 16))
    data = (
        associated_data
        + v
        + encrypted_msg
        + u
        + num_to_bytes(len(associated_data) * 8, 8)
        + num_to_bytes(len(encrypted_msg) * 8, 8)
    )
    return num_to_bytes(ghash(h, data), 16)


def aes128_gcm_decrypt(key, msg, nonce, associated_data):
    TAG_LEN = 16

    encrypted_msg, tag = msg[:-TAG_LEN], msg[-TAG_LEN:]

    pretag = calc_pretag(key, encrypted_msg, associated_data)
    check_tag = aes128_ctr_encrypt(key, pretag, nonce, counter_start_val=1)
    if check_tag != tag:
        raise ValueError("Decrypt error, bad tag")
    return aes128_ctr_decrypt(key, encrypted_msg, nonce, counter_start_val=2)


def do_authenticated_decryption(key, nonce_start, seq_num, msg_type, payload):
    nonce = xor(nonce_start, num_to_bytes(seq_num, 12))

    data = msg_type + LEGACY_TLS_VERSION + num_to_bytes(len(payload), 2)
    msg = aes128_gcm_decrypt(key, payload, nonce, associated_data=data)

    msg_type, msg_data = msg[-1:], msg[:-1]
    return msg_type, msg_data


def handle_server_cert(server_cert_data):
    handshake_type = server_cert_data[0]

    CERTIFICATE = 0x0B
    assert handshake_type == CERTIFICATE

    # certificate_payload_len = bytes_to_num(server_cert_data[1:4])
    certificate_list_len = bytes_to_num(server_cert_data[5:8])

    certificates = []

    cert_string_left = server_cert_data[8 : 8 + certificate_list_len]

    while cert_string_left:
        cert_len = bytes_to_num(cert_string_left[0:3])
        certificates.append(cert_string_left[3 : 3 + cert_len])

        cert_string_left = cert_string_left[3 + cert_len + 2 :]

    return certificates


def handle_encrypted_extensions(msg):
    ENCRYPTED_EXTENSIONS = 0x8

    assert msg[0] == ENCRYPTED_EXTENSIONS
    extensions_length = bytes_to_num(msg[1:4])
    assert len(msg[4:]) >= extensions_length
    return msg[4 + extensions_length :]
    # ignore the rest


def recv_tls_and_decrypt(s, key, nonce, seq_num):
    rec_type, encrypted_msg = recv_tls(s)
    assert rec_type == APPLICATION_DATA

    msg_type, msg = do_authenticated_decryption(
        key, nonce, seq_num, APPLICATION_DATA, encrypted_msg
    )
    return msg_type, msg


async def async_recv_tls_and_decrypt(s, key, nonce, seq_num):
    rec_type, encrypted_msg = await async_recv_tls(s)
    assert rec_type == APPLICATION_DATA

    msg_type, msg = do_authenticated_decryption(
        key, nonce, seq_num, APPLICATION_DATA, encrypted_msg
    )
    return msg_type, msg


def recv_num_bytes(s, num):
    ret = bytearray()
    while len(ret) < num:
        data = s.recv(min(4096, num - len(ret)))
        if not data:
            raise BrokenPipeError
        ret += data
    return bytes(ret)


async def async_recv_num_bytes(s, num):
    ret = bytearray()
    while len(ret) < num:
        data = await s.recv(min(4096, num - len(ret)))
        if not data:
            raise BrokenPipeError
        ret += data
    return bytes(ret)


def recv_tls(s):
    rec_type = recv_num_bytes(s, 1)
    tls_version = recv_num_bytes(s, 2)

    assert tls_version == LEGACY_TLS_VERSION

    rec_len = bytes_to_num(recv_num_bytes(s, 2))
    rec = recv_num_bytes(s, rec_len)
    return rec_type, rec


def send_tls(s, rec_type, msg):
    tls_record = rec_type + LEGACY_TLS_VERSION + num_to_bytes(len(msg), 2) + msg
    s.sendall(tls_record)


async def async_recv_tls(s):
    rec_type = await async_recv_num_bytes(s, 1)
    tls_version = await async_recv_num_bytes(s, 2)

    assert tls_version == LEGACY_TLS_VERSION

    rec_len = bytes_to_num(await async_recv_num_bytes(s, 2))
    rec = await async_recv_num_bytes(s, rec_len)
    return rec_type, rec


async def async_send_tls(s, rec_type, msg):
    tls_record = rec_type + LEGACY_TLS_VERSION + num_to_bytes(len(msg), 2) + msg
    await s.sendall(tls_record)


__all__ = (
    "multiply_num_on_ec_point",
    "gen_client_hello",
    "send_tls",
    "recv_tls",
    "handle_server_hello",
    "num_to_bytes",
    "derive_secret",
    "recv_tls_and_decrypt",
    "handle_encrypted_extensions",
    "handle_server_cert",
    "HANDSHAKE",
    "ALERT",
    "CHANGE_CIPHER",
)

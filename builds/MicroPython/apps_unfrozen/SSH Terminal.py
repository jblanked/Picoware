"""
SSH Client/Terminal App for Picoware (work in progress)
Copyright (c) 2026 JBlanked
GPL-3.0 License
https://www.github.com/jblanked/Picoware
Last Updated: 2026-02-16
"""

from micropython import const
import usocket as socket
import struct
import hashlib
import uos as os
import _thread
from gc import collect

# View constants
VIEW_MAIN_MENU = const(0)
VIEW_KEYBOARD_HOST = const(1)
VIEW_KEYBOARD_PORT = const(2)
VIEW_KEYBOARD_USERNAME = const(3)
VIEW_KEYBOARD_PASSWORD = const(4)
VIEW_KEYBOARD_COMMAND = const(5)
VIEW_CONNECTING = const(6)
VIEW_CONNECTED = const(7)
VIEW_OUTPUT = const(8)

# Menu constants
MENU_ITEM_CONNECT = const(0)
MENU_ITEM_SET_HOST = const(1)
MENU_ITEM_SET_PORT = const(2)
MENU_ITEM_SET_USERNAME = const(3)
MENU_ITEM_SET_PASSWORD = const(4)
MENU_ITEM_DISCONNECT = const(5)

# Connection states
STATE_DISCONNECTED = const(0)
STATE_CONNECTING = const(1)
STATE_CONNECTED = const(2)
STATE_EXECUTING = const(3)
STATE_ERROR = const(4)

# Keyboard states
KEYBOARD_WAITING = const(-1)
KEYBOARD_ENTERING = const(0)

# SSH Message Types
SSH_MSG_DISCONNECT = const(1)
SSH_MSG_IGNORE = const(2)
SSH_MSG_UNIMPLEMENTED = const(3)
SSH_MSG_DEBUG = const(4)
SSH_MSG_SERVICE_REQUEST = const(5)
SSH_MSG_SERVICE_ACCEPT = const(6)
SSH_MSG_KEXINIT = const(20)
SSH_MSG_NEWKEYS = const(21)
SSH_MSG_KEXDH_INIT = const(30)
SSH_MSG_KEXDH_REPLY = const(31)
SSH_MSG_KEX_DH_GEX_INIT = const(32)
SSH_MSG_KEX_DH_GEX_REPLY = const(33)
SSH_MSG_KEX_DH_GEX_REQUEST = const(34)
SSH_MSG_USERAUTH_REQUEST = const(50)
SSH_MSG_USERAUTH_FAILURE = const(51)
SSH_MSG_USERAUTH_SUCCESS = const(52)
SSH_MSG_USERAUTH_BANNER = const(53)
SSH_MSG_GLOBAL_REQUEST = const(80)
SSH_MSG_REQUEST_FAILURE = const(82)
SSH_MSG_CHANNEL_OPEN = const(90)
SSH_MSG_CHANNEL_OPEN_CONFIRMATION = const(91)
SSH_MSG_CHANNEL_OPEN_FAILURE = const(92)
SSH_MSG_CHANNEL_WINDOW_ADJUST = const(93)
SSH_MSG_CHANNEL_DATA = const(94)
SSH_MSG_CHANNEL_EXTENDED_DATA = const(95)
SSH_MSG_CHANNEL_EOF = const(96)
SSH_MSG_CHANNEL_CLOSE = const(97)
SSH_MSG_CHANNEL_REQUEST = const(98)
SSH_MSG_CHANNEL_SUCCESS = const(99)
SSH_MSG_CHANNEL_FAILURE = const(100)

# DH Group 14 prime (RFC 3526) - 2048-bit MODP Group
_DH_G = const(2)
_DH_P = int(
    "FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD1"
    "29024E088A67CC74020BBEA63B139B22514A08798E3404DD"
    "EF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245"
    "E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7ED"
    "EE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3D"
    "C2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F"
    "83655D23DCA3AD961C62F356208552BB9ED529077096966D6"
    "70C354E4ABC9804F1746C08CA18217C32905E462E36CE3BE"
    "39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9D"
    "E2BCBF6955817183995497CEA956AE515D2261898FA05101"
    "5728E5A8AACAA68FFFFFFFFFFFFFFFF",
    16,
)

# X25519 constants (RFC 7748)
_X25519_P = (1 << 255) - 19
_X25519_A24 = const(121665)

# Globals
current_view = VIEW_MAIN_MENU
menu_index = MENU_ITEM_CONNECT
keyboard_index = KEYBOARD_WAITING
connection_state = STATE_DISCONNECTED

_menu = None
_loading = None
_ssh_client = None
_textbox = None
_previous_text_len = 0

# SSH connection details
ssh_host = ""
ssh_port = "22"
ssh_username = ""
ssh_password = ""
ssh_command = ""


# --- SSH Protocol Helpers ---


def _ssh_string(data):
    """Pack data as SSH string (uint32 length prefix + data)"""
    if isinstance(data, str):
        data = data.encode()
    return struct.pack(">I", len(data)) + data


def _ssh_mpint(n):
    """Pack integer as SSH mpint (big-endian, sign-extended)"""
    if n == 0:
        return struct.pack(">I", 0)
    # Convert to big-endian bytes
    hex_s = "%x" % n
    if len(hex_s) & 1:
        hex_s = "0" + hex_s
    b = bytes(int(hex_s[i : i + 2], 16) for i in range(0, len(hex_s), 2))
    # Prepend zero byte if high bit set (positive number must not look negative)
    if b[0] & 0x80:
        b = b"\x00" + b
    return struct.pack(">I", len(b)) + b


def _parse_uint32(data, offset):
    """Parse big-endian uint32 from data at offset"""
    return (
        (data[offset] << 24)
        | (data[offset + 1] << 16)
        | (data[offset + 2] << 8)
        | data[offset + 3],
        offset + 4,
    )


def _parse_string(data, offset):
    """Parse SSH string from data at offset, returns (bytes, new_offset)"""
    length, offset = _parse_uint32(data, offset)
    return bytes(data[offset : offset + length]), offset + length


def _parse_mpint(data, offset):
    """Parse SSH mpint from data at offset, returns (int, new_offset)"""
    length, offset = _parse_uint32(data, offset)
    val = 0
    for i in range(length):
        val = (val << 8) | data[offset + i]
    # Two's complement for negative
    if length > 0 and data[offset] & 0x80:
        val -= 1 << (length * 8)
    return val, offset + length


def _parse_name_list(data, offset):
    """Parse SSH name-list, returns (list_of_strings, new_offset)"""
    raw, offset = _parse_string(data, offset)
    if raw:
        return raw.decode().split(","), offset
    return [], offset


# --- HMAC Implementations ---


def _hmac_compute(key, msg, hash_cls, block_size):
    """Compute HMAC with the given hash class and block size"""
    if len(key) > block_size:
        h = hash_cls()
        h.update(key)
        key = h.digest()
    if len(key) < block_size:
        key = key + b"\x00" * (block_size - len(key))
    o_pad = bytes(b ^ 0x5C for b in key)
    i_pad = bytes(b ^ 0x36 for b in key)
    hi = hash_cls()
    hi.update(i_pad)
    hi.update(msg)
    inner = hi.digest()
    ho = hash_cls()
    ho.update(o_pad)
    ho.update(inner)
    return ho.digest()


def _hmac_sha256(key, msg):
    """HMAC-SHA-256"""
    return _hmac_compute(key, msg, hashlib.sha256, 64)


def _hmac_sha1(key, msg):
    """HMAC-SHA-1"""
    return _hmac_compute(key, msg, hashlib.sha1, 64)


# --- X25519 Diffie-Hellman (RFC 7748) ---


def _x25519(k_bytes, u_bytes):
    """X25519 scalar multiplication with aggressive GC"""
    p = _X25519_P
    a24 = _X25519_A24

    # Decode and clamp scalar
    k_list = bytearray(k_bytes)
    k_list[0] &= 248
    k_list[31] &= 127
    k_list[31] |= 64
    scalar = int.from_bytes(bytes(k_list), "little")
    del k_list
    collect()  # Free k_list immediately

    u = int.from_bytes(u_bytes, "little") & ((1 << 255) - 1)

    x_2, z_2 = 1, 0
    x_3, z_3 = u, 1
    swap = 0

    for t in range(254, -1, -1):
        k_t = (scalar >> t) & 1
        swap ^= k_t
        if swap:
            x_2, x_3 = x_3, x_2
            z_2, z_3 = z_3, z_2
        swap = k_t

        A = (x_2 + z_2) % p
        AA = (A * A) % p
        B = (x_2 - z_2) % p
        BB = (B * B) % p
        E = (AA - BB) % p
        C = (x_3 + z_3) % p
        D = (x_3 - z_3) % p
        DA = (D * A) % p
        CB = (C * B) % p
        sum_dc = (DA + CB) % p
        diff_dc = (DA - CB) % p
        x_3 = (sum_dc * sum_dc) % p
        z_3 = (u * ((diff_dc * diff_dc) % p)) % p
        x_2 = (AA * BB) % p
        z_2 = (E * ((AA + (a24 * E) % p) % p)) % p

        # GC every 32 iterations to prevent buildup
        if t % 32 == 0:
            collect()

    if swap:
        x_2, x_3 = x_3, x_2
        z_2, z_3 = z_3, z_2

    # Compute result with immediate cleanup
    result = (x_2 * pow(z_2, p - 2, p)) % p
    del x_2, z_2, x_3, z_3, scalar, u
    collect()

    return result.to_bytes(32, "little")


# X25519 base point (u=9)
_X25519_BASE = b"\x09" + b"\x00" * 31


# --- AES-CTR Cipher ---


class _AES_CTR:
    """AES in Counter mode. Tries native CTR (mode 6) first,
    falls back to manual CTR built on ECB."""

    def __init__(self, key, iv):
        try:
            from cryptolib import aes
        except ImportError:
            from ucryptolib import aes
        self._native = False
        try:
            # Mode 6 = CTR in MicroPython's ucryptolib
            self._aes = aes(key, 6, iv[:16])
            self._native = True
        except Exception:
            # Fallback: manual CTR on top of ECB
            self._ecb = aes(key, 1)  # mode 1 = ECB
            self._ctr = bytearray(iv[:16])
            self._buf = bytearray(16)
            self._pos = 16  # exhausted so first call generates keystream

    def _inc_counter(self):
        """Increment 128-bit big-endian counter by 1"""
        for i in range(15, -1, -1):
            self._ctr[i] = (self._ctr[i] + 1) & 0xFF
            if self._ctr[i]:
                break

    def process(self, data):
        """Encrypt or decrypt data (XOR with AES-CTR keystream)"""
        if self._native:
            # Native CTR mode handles counter increment internally
            return self._aes.encrypt(data)

        # Manual CTR mode
        out = bytearray(len(data))
        for i in range(len(data)):
            if self._pos >= 16:
                ks = self._ecb.encrypt(bytes(self._ctr))
                for j in range(16):
                    self._buf[j] = ks[j]
                self._inc_counter()
                self._pos = 0
            out[i] = data[i] ^ self._buf[self._pos]
            self._pos += 1
        return bytes(out)


# --- Full SSH-2 Client ---


class SSHClient:
    """Full SSH-2 protocol client with multiple KEX algorithms"""

    _CLIENT_VERSION = "SSH-2.0-Picoware_1.6.9"

    # Supported algorithms in preference order
    _KEX_ALGORITHMS = (
        "curve25519-sha256,"
        "curve25519-sha256@libssh.org,"
        "diffie-hellman-group-exchange-sha256,"
        "diffie-hellman-group14-sha256,"
        "diffie-hellman-group14-sha1"
    )
    _HOST_KEY_ALGORITHMS = (
        "ssh-ed25519,rsa-sha2-256,rsa-sha2-512," "ecdsa-sha2-nistp256,ssh-rsa"
    )
    _CIPHERS = "aes128-ctr,aes256-ctr"
    _MACS = "hmac-sha2-256,hmac-sha1"
    _COMPRESSION = "none"

    def __init__(self):
        self._sock = None
        self._connected = False
        self._authenticated = False
        self._error = None
        self._lock = _thread.allocate_lock()
        self._output = []

        # Protocol state
        self._server_version = ""
        self._send_seq = 0
        self._recv_seq = 0
        self._session_id = None

        # Encryption state
        self._encrypted = False
        self._enc_cipher = None
        self._dec_cipher = None
        self._mac_key_c2s = None
        self._mac_key_s2c = None
        self._mac_len = 0
        self._mac_func = None

        # KEX negotiation results
        self._kex_algorithm = None
        self._cipher_c2s = None
        self._cipher_s2c = None
        self._mac_c2s = None
        self._mac_s2c = None
        self._client_kexinit = None
        self._server_kexinit = None

        # Channel state
        self._channel_id = 0
        self._remote_channel = 0
        self._remote_window = 0
        self._remote_max_pkt = 0
        self._channel_eof = False
        self._channel_closed = False

    @property
    def is_connected(self) -> bool:
        with self._lock:
            return self._connected and self._authenticated

    @property
    def error(self) -> str:
        with self._lock:
            return self._error

    @property
    def output(self) -> list:
        with self._lock:
            return self._output.copy()

    # ---- Low-level transport ----

    def _recv_exact(self, n):
        """Receive exactly n bytes"""
        buf = bytearray()
        while len(buf) < n:
            chunk = self._sock.recv(min(n - len(buf), 4096))
            if not chunk:
                raise Exception("Connection closed")
            buf.extend(chunk)
        return bytes(buf)

    def _send_all(self, data):
        """Send all bytes"""
        mv = memoryview(data)
        total = 0
        while total < len(data):
            sent = self._sock.send(mv[total:])
            if sent <= 0:
                raise Exception("Send failed")
            total += sent

    def _read_packet(self):
        """Read one SSH binary packet, decrypting if encryption is active"""
        if self._encrypted:
            # Read and decrypt first 4 bytes to get packet length
            raw4 = self._recv_exact(4)
            dec4 = self._dec_cipher.process(raw4)
            pkt_len, _ = _parse_uint32(dec4, 0)
            if pkt_len > 35000:
                raise Exception("Packet too large")

            # Read and decrypt the rest of the packet
            raw_rest = self._recv_exact(pkt_len)
            dec_rest = self._dec_cipher.process(raw_rest)

            # Read MAC
            mac_recv = self._recv_exact(self._mac_len)

            # Verify MAC: HMAC(key, seq_number || unencrypted_packet)
            seq_b = struct.pack(">I", self._recv_seq)
            mac_calc = self._mac_func(self._mac_key_s2c, seq_b + dec4 + dec_rest)
            if mac_calc[: self._mac_len] != mac_recv:
                raise Exception("MAC verification failed")

            self._recv_seq = (self._recv_seq + 1) & 0xFFFFFFFF
            pad_len = dec_rest[0]
            return bytes(dec_rest[1 : pkt_len - pad_len])
        else:
            # Unencrypted
            raw4 = self._recv_exact(4)
            pkt_len, _ = _parse_uint32(raw4, 0)
            if pkt_len > 35000:
                raise Exception("Packet too large")
            raw_rest = self._recv_exact(pkt_len)
            self._recv_seq = (self._recv_seq + 1) & 0xFFFFFFFF
            pad_len = raw_rest[0]
            return bytes(raw_rest[1 : pkt_len - pad_len])

    def _send_packet(self, payload):
        """Build, optionally encrypt, and send an SSH binary packet"""
        bs = 16 if self._encrypted else 8
        # padding_length + payload; total (4 + 1 + payload + padding) must be multiple of bs
        inner = 1 + len(payload)
        pad_len = bs - ((4 + inner) % bs)
        if pad_len < 4:
            pad_len += bs

        pkt_len = inner + pad_len
        padding = os.urandom(pad_len)
        packet = struct.pack(">IB", pkt_len, pad_len) + payload + padding

        if self._encrypted:
            # MAC over unencrypted packet
            seq_b = struct.pack(">I", self._send_seq)
            mac = self._mac_func(self._mac_key_c2s, seq_b + packet)
            mac = mac[: self._mac_len]
            enc = self._enc_cipher.process(packet)
            self._send_all(enc + mac)
        else:
            self._send_all(packet)

        self._send_seq = (self._send_seq + 1) & 0xFFFFFFFF

    def _read_ssh_packet(self):
        """Read a packet, transparently handling transport-level messages"""
        while True:
            payload = self._read_packet()
            if not payload:
                raise Exception("Empty packet")
            t = payload[0]

            if t == SSH_MSG_DISCONNECT:
                _, off = _parse_uint32(payload, 1)
                desc, _ = _parse_string(payload, off)
                raise Exception("Disconnected: " + desc.decode("utf-8", "ignore"))

            if t in (SSH_MSG_IGNORE, SSH_MSG_DEBUG, SSH_MSG_UNIMPLEMENTED):
                continue

            if t == SSH_MSG_GLOBAL_REQUEST:
                self._send_packet(bytes([SSH_MSG_REQUEST_FAILURE]))
                continue

            return payload

    # ---- Key Exchange ----

    def _build_kexinit(self):
        """Build our SSH_MSG_KEXINIT payload"""
        p = bytearray()
        p.append(SSH_MSG_KEXINIT)
        p.extend(os.urandom(16))  # cookie
        for alg_list in (
            self._KEX_ALGORITHMS,
            self._HOST_KEY_ALGORITHMS,
            self._CIPHERS,
            self._CIPHERS,
            self._MACS,
            self._MACS,
            self._COMPRESSION,
            self._COMPRESSION,
            "",  # languages c2s
            "",  # languages s2c
        ):
            p.extend(_ssh_string(alg_list))
        p.append(0)  # first_kex_packet_follows
        p.extend(b"\x00\x00\x00\x00")  # reserved
        return bytes(p)

    def _negotiate_kexinit(self, server_payload):
        """Parse server KEXINIT and pick algorithms"""
        off = 17  # skip msg type (1) + cookie (16)
        s_kex, off = _parse_name_list(server_payload, off)
        s_host, off = _parse_name_list(server_payload, off)
        s_enc_c2s, off = _parse_name_list(server_payload, off)
        s_enc_s2c, off = _parse_name_list(server_payload, off)
        s_mac_c2s, off = _parse_name_list(server_payload, off)
        s_mac_s2c, off = _parse_name_list(server_payload, off)
        # skip compression and rest

        def pick(client_csv, server_list):
            for a in client_csv.split(","):
                if a in server_list:
                    return a
            return None

        self._kex_algorithm = pick(self._KEX_ALGORITHMS, s_kex)
        if not self._kex_algorithm:
            svr = ",".join(s_kex[:5])
            raise Exception("No common KEX: svr=[%s]" % svr)

        host_alg = pick(self._HOST_KEY_ALGORITHMS, s_host)
        if not host_alg:
            svr = ",".join(s_host[:5])
            raise Exception("No common host key: [%s]" % svr)

        self._cipher_c2s = pick(self._CIPHERS, s_enc_c2s)
        self._cipher_s2c = pick(self._CIPHERS, s_enc_s2c)
        if not self._cipher_c2s or not self._cipher_s2c:
            raise Exception("No common cipher")

        self._mac_c2s = pick(self._MACS, s_mac_c2s)
        self._mac_s2c = pick(self._MACS, s_mac_s2c)
        if not self._mac_c2s or not self._mac_s2c:
            raise Exception("No common MAC algo")

    # ---- KEX dispatcher ----

    def _do_kex(self):
        """Dispatch to the correct key exchange method"""
        alg = self._kex_algorithm
        if alg in ("curve25519-sha256", "curve25519-sha256@libssh.org"):
            return self._do_curve25519_kex()
        elif alg == "diffie-hellman-group-exchange-sha256":
            return self._do_gex_kex()
        elif alg.startswith("diffie-hellman-group14"):
            return self._do_dh_group14_kex()
        else:
            raise Exception("KEX '%s' not implemented" % alg)

    # ---- curve25519-sha256 (RFC 8731) ----

    def _do_curve25519_kex(self):
        """Curve25519 ECDH key exchange"""
        # Generate ephemeral keypair
        priv = os.urandom(32)
        Q_C = _x25519(priv, _X25519_BASE)

        # Send SSH_MSG_KEX_ECDH_INIT (msg 30) with our public key
        self._send_packet(bytes([SSH_MSG_KEXDH_INIT]) + _ssh_string(Q_C))

        # Receive SSH_MSG_KEX_ECDH_REPLY (msg 31)
        reply = self._read_ssh_packet()
        if reply[0] != SSH_MSG_KEXDH_REPLY:
            raise Exception("Expected ECDH_REPLY, got %d" % reply[0])

        off = 1
        K_S, off = _parse_string(reply, off)  # server host key blob
        Q_S, off = _parse_string(reply, off)  # server ephemeral public key
        sig, off = _parse_string(reply, off)  # signature

        if len(Q_S) != 32:
            raise Exception("Invalid server ECDH key len=%d" % len(Q_S))

        # Compute shared secret via X25519
        raw_K = _x25519(priv, Q_S)

        # Verify non-zero
        if raw_K == b"\x00" * 32:
            raise Exception("X25519 zero result")

        # Interpret as big-endian integer (SSH convention)
        K = int.from_bytes(raw_K, "big")

        # Exchange hash: SHA-256
        hash_cls = hashlib.sha256
        h = hash_cls()
        h.update(_ssh_string(self._CLIENT_VERSION))
        h.update(_ssh_string(self._server_version))
        h.update(_ssh_string(self._client_kexinit))
        h.update(_ssh_string(self._server_kexinit))
        h.update(_ssh_string(K_S))
        h.update(_ssh_string(Q_C))  # string (not mpint)
        h.update(_ssh_string(Q_S))  # string (not mpint)
        h.update(_ssh_mpint(K))
        H = h.digest()

        if self._session_id is None:
            self._session_id = H

        del priv, raw_K
        collect()
        return K, H, hash_cls

    # ---- diffie-hellman-group-exchange-sha256 (RFC 4419) ----

    def _do_gex_kex(self):
        """Diffie-Hellman Group Exchange key exchange"""
        gex_min = 2048
        gex_n = 2048
        gex_max = 4096

        # Send SSH_MSG_KEX_DH_GEX_REQUEST (34)
        req = bytearray()
        req.append(SSH_MSG_KEX_DH_GEX_REQUEST)
        req.extend(struct.pack(">III", gex_min, gex_n, gex_max))
        self._send_packet(bytes(req))

        # Receive SSH_MSG_KEX_DH_GEX_GROUP (31): p, g
        grp = self._read_ssh_packet()
        if grp[0] != SSH_MSG_KEXDH_REPLY:  # msg 31 reused
            raise Exception("Expected GEX_GROUP, got %d" % grp[0])

        off = 1
        p, off = _parse_mpint(grp, off)
        g, off = _parse_mpint(grp, off)

        if p < (1 << (gex_min - 1)):
            raise Exception("Server DH prime too small")

        # Generate private exponent (truncate to 128 bits for speed)
        x = int.from_bytes(os.urandom(16), "big")

        # Compute public value e = g^x mod p
        e = pow(g, x, p)

        # Send SSH_MSG_KEX_DH_GEX_INIT (32)
        self._send_packet(bytes([SSH_MSG_KEX_DH_GEX_INIT]) + _ssh_mpint(e))

        # Receive SSH_MSG_KEX_DH_GEX_REPLY (33)
        reply = self._read_ssh_packet()
        if reply[0] != SSH_MSG_KEX_DH_GEX_REPLY:
            raise Exception("Expected GEX_REPLY, got %d" % reply[0])

        off = 1
        K_S, off = _parse_string(reply, off)
        f, off = _parse_mpint(reply, off)
        sig, off = _parse_string(reply, off)

        if f < 2 or f >= p - 1:
            raise Exception("Invalid server GEX value")

        # Shared secret
        K = pow(f, x, p)

        # Exchange hash for GEX includes min, n, max, p, g
        hash_cls = hashlib.sha256
        h = hash_cls()
        h.update(_ssh_string(self._CLIENT_VERSION))
        h.update(_ssh_string(self._server_version))
        h.update(_ssh_string(self._client_kexinit))
        h.update(_ssh_string(self._server_kexinit))
        h.update(_ssh_string(K_S))
        h.update(struct.pack(">III", gex_min, gex_n, gex_max))
        h.update(_ssh_mpint(p))
        h.update(_ssh_mpint(g))
        h.update(_ssh_mpint(e))
        h.update(_ssh_mpint(f))
        h.update(_ssh_mpint(K))
        H = h.digest()

        if self._session_id is None:
            self._session_id = H

        del x, e, f, p, g
        collect()
        return K, H, hash_cls

    # ---- diffie-hellman-group14-sha256/sha1 (RFC 4253 / RFC 8268) ----

    def _do_dh_group14_kex(self):
        """Diffie-Hellman Group 14 fixed-group key exchange"""
        # Use 128-bit exponent for speed (security limited by 2048-bit group)
        x = int.from_bytes(os.urandom(16), "big")
        # Compute public value e = g^x mod p
        e = pow(_DH_G, x, _DH_P)

        # Send SSH_MSG_KEXDH_INIT
        self._send_packet(bytes([SSH_MSG_KEXDH_INIT]) + _ssh_mpint(e))

        # Receive SSH_MSG_KEXDH_REPLY
        reply = self._read_ssh_packet()
        if reply[0] != SSH_MSG_KEXDH_REPLY:
            raise Exception("Expected KEXDH_REPLY, got %d" % reply[0])

        off = 1
        k_s, off = _parse_string(reply, off)  # server host key blob
        f, off = _parse_mpint(reply, off)  # server DH public value
        sig, off = _parse_string(reply, off)  # signature (not verified)

        # Validate f
        if f < 2 or f >= _DH_P - 1:
            raise Exception("Invalid server DH value")

        # Shared secret K = f^x mod p
        K = pow(f, x, _DH_P)

        # Pick hash function for this KEX algorithm
        if "sha256" in self._kex_algorithm:
            hash_cls = hashlib.sha256
        else:
            hash_cls = hashlib.sha1

        # Compute exchange hash H
        h = hash_cls()
        h.update(_ssh_string(self._CLIENT_VERSION))
        h.update(_ssh_string(self._server_version))
        h.update(_ssh_string(self._client_kexinit))
        h.update(_ssh_string(self._server_kexinit))
        h.update(_ssh_string(k_s))
        h.update(_ssh_mpint(e))
        h.update(_ssh_mpint(f))
        h.update(_ssh_mpint(K))
        H = h.digest()

        # First exchange hash becomes session ID
        if self._session_id is None:
            self._session_id = H

        # Free big ints
        del x, e, f
        collect()

        return K, H, hash_cls

    def _derive_keys(self, K, H, hash_cls):
        """Derive encryption, IV, and MAC keys from shared secret"""
        K_enc = _ssh_mpint(K)

        def derive(letter, needed):
            h = hash_cls()
            h.update(K_enc)
            h.update(H)
            h.update(letter.encode())
            h.update(self._session_id)
            key = h.digest()
            while len(key) < needed:
                h = hash_cls()
                h.update(K_enc)
                h.update(H)
                h.update(key)
                key += h.digest()
            return key[:needed]

        # Key sizes
        c2s_key_len = 32 if self._cipher_c2s == "aes256-ctr" else 16
        s2c_key_len = 32 if self._cipher_s2c == "aes256-ctr" else 16

        # MAC parameters
        if self._mac_c2s == "hmac-sha2-256":
            mac_key_len = 32
            self._mac_len = 32
            self._mac_func = _hmac_sha256
        else:
            mac_key_len = 20
            self._mac_len = 20
            self._mac_func = _hmac_sha1

        iv_c2s = derive("A", 16)
        iv_s2c = derive("B", 16)
        key_c2s = derive("C", c2s_key_len)
        key_s2c = derive("D", s2c_key_len)
        self._mac_key_c2s = derive("E", mac_key_len)
        self._mac_key_s2c = derive("F", mac_key_len)

        self._enc_cipher = _AES_CTR(key_c2s, iv_c2s)
        self._dec_cipher = _AES_CTR(key_s2c, iv_s2c)

        del K_enc
        collect()

    # ---- Authentication ----

    def _request_service(self, name):
        """Send SSH_MSG_SERVICE_REQUEST"""
        self._send_packet(bytes([SSH_MSG_SERVICE_REQUEST]) + _ssh_string(name))
        resp = self._read_ssh_packet()
        if resp[0] != SSH_MSG_SERVICE_ACCEPT:
            raise Exception("Service '%s' rejected" % name)

    def _auth_password(self, username, password):
        """Password authentication"""
        p = bytearray()
        p.append(SSH_MSG_USERAUTH_REQUEST)
        p.extend(_ssh_string(username))
        p.extend(_ssh_string("ssh-connection"))
        p.extend(_ssh_string("password"))
        p.append(0)  # FALSE
        p.extend(_ssh_string(password))
        self._send_packet(bytes(p))

        while True:
            resp = self._read_ssh_packet()
            t = resp[0]
            if t == SSH_MSG_USERAUTH_SUCCESS:
                return True
            elif t == SSH_MSG_USERAUTH_BANNER:
                continue
            elif t == SSH_MSG_USERAUTH_FAILURE:
                methods, _ = _parse_string(resp, 1)
                raise Exception("Auth failed (%s)" % methods.decode())
            else:
                raise Exception("Auth unexpected msg %d" % t)

    # ---- Channel operations ----

    def _open_session_channel(self):
        """Open a session channel"""
        self._channel_id = 0
        local_win = 0x200000  # 2 MB
        local_max = 0x8000  # 32 KB

        p = bytearray()
        p.append(SSH_MSG_CHANNEL_OPEN)
        p.extend(_ssh_string("session"))
        p.extend(struct.pack(">III", self._channel_id, local_win, local_max))
        self._send_packet(bytes(p))

        while True:
            resp = self._read_ssh_packet()
            t = resp[0]
            if t == SSH_MSG_CHANNEL_OPEN_CONFIRMATION:
                off = 1
                _, off = _parse_uint32(resp, off)  # recipient
                self._remote_channel, off = _parse_uint32(resp, off)
                self._remote_window, off = _parse_uint32(resp, off)
                self._remote_max_pkt, off = _parse_uint32(resp, off)
                self._channel_eof = False
                self._channel_closed = False
                return
            elif t == SSH_MSG_CHANNEL_OPEN_FAILURE:
                _, off = _parse_uint32(resp, 1)
                code, off = _parse_uint32(resp, off)
                desc, _ = _parse_string(resp, off)
                raise Exception(
                    "Channel open failed: %s" % desc.decode("utf-8", "ignore")
                )
            elif t == SSH_MSG_CHANNEL_WINDOW_ADJUST:
                continue
            else:
                continue  # ignore unexpected messages

    def _send_exec(self, command):
        """Send exec request on the channel"""
        p = bytearray()
        p.append(SSH_MSG_CHANNEL_REQUEST)
        p.extend(struct.pack(">I", self._remote_channel))
        p.extend(_ssh_string("exec"))
        p.append(1)  # want reply
        p.extend(_ssh_string(command))
        self._send_packet(bytes(p))

    def _window_adjust(self, amount):
        """Send window adjust to allow server to send more data"""
        p = bytearray()
        p.append(SSH_MSG_CHANNEL_WINDOW_ADJUST)
        p.extend(struct.pack(">II", self._remote_channel, amount))
        self._send_packet(bytes(p))

    def _collect_output(self):
        """Read channel data until EOF or close, return list of lines"""
        lines = []

        while not self._channel_closed:
            try:
                self._sock.settimeout(15.0)
                resp = self._read_ssh_packet()
            except Exception as e:
                s = str(e)
                if "timed out" in s or "ETIMEDOUT" in s:
                    break
                raise

            t = resp[0]

            if t == SSH_MSG_CHANNEL_SUCCESS:
                continue

            if t == SSH_MSG_CHANNEL_FAILURE:
                lines.append("[Server rejected command]")
                break

            if t == SSH_MSG_CHANNEL_DATA:
                off = 1
                _, off = _parse_uint32(resp, off)
                data, _ = _parse_string(resp, off)
                text = data.decode("utf-8", "ignore")
                for ln in text.split("\n"):
                    lines.append(ln)
                continue

            if t == SSH_MSG_CHANNEL_EXTENDED_DATA:
                off = 1
                _, off = _parse_uint32(resp, off)
                dtype, off = _parse_uint32(resp, off)
                data, _ = _parse_string(resp, off)
                text = data.decode("utf-8", "ignore")
                prefix = "[stderr] " if dtype == 1 else ""
                for ln in text.split("\n"):
                    lines.append(prefix + ln)
                continue

            if t == SSH_MSG_CHANNEL_EOF:
                self._channel_eof = True
                continue

            if t == SSH_MSG_CHANNEL_CLOSE:
                self._channel_closed = True
                # Send close back
                cp = bytearray()
                cp.append(SSH_MSG_CHANNEL_CLOSE)
                cp.extend(struct.pack(">I", self._remote_channel))
                self._send_packet(bytes(cp))
                break

            if t == SSH_MSG_CHANNEL_WINDOW_ADJUST:
                off = 1
                _, off = _parse_uint32(resp, off)
                adj, _ = _parse_uint32(resp, off)
                self._remote_window += adj
                continue

            if t == SSH_MSG_CHANNEL_REQUEST:
                off = 1
                _, off = _parse_uint32(resp, off)
                rtype, off = _parse_string(resp, off)
                want = resp[off] if off < len(resp) else 0
                if want:
                    sp = bytearray()
                    sp.append(SSH_MSG_CHANNEL_SUCCESS)
                    sp.extend(struct.pack(">I", self._remote_channel))
                    self._send_packet(bytes(sp))
                continue

        # Trim trailing empty lines
        while lines and not lines[-1].strip():
            lines.pop()
        return lines

    # ---- Public API ----

    def connect(self, host, port, username, password):
        """Full SSH-2 connect: version exchange, KEX, auth"""
        with self._lock:
            if self._connected:
                self._error = "Already connected"
                return False

        try:
            # TCP connect
            info = socket.getaddrinfo(host, port)[0]
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.settimeout(15.0)
            self._sock.connect(info[-1])

            # --- Version exchange ---
            buf = b""
            while True:
                c = self._sock.recv(1)
                if not c:
                    raise Exception("Connection closed during version exchange")
                buf += c
                if buf.endswith(b"\n"):
                    line = buf.decode("utf-8", "ignore").strip()
                    if line.startswith("SSH-"):
                        self._server_version = line
                        break
                    buf = b""  # skip banner lines
                if len(buf) > 255:
                    raise Exception("Version line too long")

            self._sock.send((self._CLIENT_VERSION + "\r\n").encode())

            # --- Key exchange ---
            # Send our KEXINIT
            kexinit = self._build_kexinit()
            self._client_kexinit = kexinit
            self._send_packet(kexinit)

            # Receive server KEXINIT
            s_kex = self._read_ssh_packet()
            if s_kex[0] != SSH_MSG_KEXINIT:
                raise Exception("Expected KEXINIT, got %d" % s_kex[0])
            self._server_kexinit = s_kex

            # Negotiate algorithms
            self._negotiate_kexinit(s_kex)

            # Perform key exchange
            K, H, hash_cls = self._do_kex()

            # Derive session keys
            self._derive_keys(K, H, hash_cls)
            del K
            collect()

            # Send NEWKEYS
            self._send_packet(bytes([SSH_MSG_NEWKEYS]))

            # Receive NEWKEYS
            nk = self._read_ssh_packet()
            if nk[0] != SSH_MSG_NEWKEYS:
                raise Exception("Expected NEWKEYS, got %d" % nk[0])

            # Switch to encrypted transport
            self._encrypted = True

            # Free kexinit payloads
            self._client_kexinit = None
            self._server_kexinit = None
            collect()

            # --- Authentication ---
            self._request_service("ssh-userauth")
            self._auth_password(username, password)

            with self._lock:
                self._connected = True
                self._authenticated = True
                self._error = None
            return True

        except Exception as e:
            with self._lock:
                self._error = str(e)
                self._connected = False
                self._authenticated = False
            self._close_socket()
            return False

    def execute_command(self, command):
        """Execute a command over the encrypted SSH channel"""
        with self._lock:
            if not self._connected or not self._authenticated:
                self._error = "Not connected"
                return False

        try:
            self._sock.settimeout(15.0)

            # Open a new session channel for this command
            self._open_session_channel()

            # Request exec
            self._send_exec(command)

            # Collect output
            lines = self._collect_output()

            with self._lock:
                self._output.append("$ " + command)
                self._output.extend(lines)

            return True

        except Exception as e:
            with self._lock:
                self._error = str(e)
                self._output.append("$ " + command)
                self._output.append("[Error: %s]" % str(e))
            return False

    def disconnect(self):
        """Send SSH_MSG_DISCONNECT and clean up"""
        with self._lock:
            if self._connected:
                try:
                    p = bytearray()
                    p.append(SSH_MSG_DISCONNECT)
                    p.extend(struct.pack(">I", 11))  # BY_APPLICATION
                    p.extend(_ssh_string("Bye"))
                    p.extend(_ssh_string(""))
                    self._send_packet(bytes(p))
                except Exception:
                    pass

            self._connected = False
            self._authenticated = False
            self._encrypted = False
            self._enc_cipher = None
            self._dec_cipher = None
            self._mac_key_c2s = None
            self._mac_key_s2c = None
            self._session_id = None
            self._send_seq = 0
            self._recv_seq = 0
            self._output.clear()

        self._close_socket()

    def _close_socket(self):
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None

    def __del__(self):
        self.disconnect()


def __load_ssh_credentials(view_manager) -> bool:
    """Load SSH credentials from storage"""
    global ssh_host, ssh_port, ssh_username, ssh_password
    storage = view_manager.storage

    stored_host = storage.read("picoware/ssh/host.txt")
    stored_port = storage.read("picoware/ssh/port.txt")
    stored_username = storage.read("picoware/ssh/username.txt")
    stored_password = storage.read("picoware/ssh/password.txt")

    if stored_host:
        ssh_host = stored_host
    if stored_port:
        ssh_port = stored_port
    else:
        storage.write("picoware/ssh/port.txt", "22")
        ssh_port = "22"
    if stored_username:
        ssh_username = stored_username
    if stored_password:
        ssh_password = stored_password

    return ssh_host != "" and ssh_username != "" and ssh_password != ""


def _keyboard_save(view_manager) -> bool:
    """Keyboard callback function"""
    global ssh_host, ssh_port, ssh_username, ssh_password, ssh_command
    storage = view_manager.storage
    kb = view_manager.keyboard

    if current_view == VIEW_KEYBOARD_COMMAND:
        ssh_command = kb.response
        return True

    # Determine which file to write to based on current view
    file_path = ""
    if current_view == VIEW_KEYBOARD_HOST:
        file_path = "picoware/ssh/host.txt"
        ssh_host = kb.response
    elif current_view == VIEW_KEYBOARD_PORT:
        file_path = "picoware/ssh/port.txt"
        ssh_port = kb.response
    elif current_view == VIEW_KEYBOARD_USERNAME:
        file_path = "picoware/ssh/username.txt"
        ssh_username = kb.response
    elif current_view == VIEW_KEYBOARD_PASSWORD:
        file_path = "picoware/ssh/password.txt"
        ssh_password = kb.response

    if file_path:
        return storage.write(file_path, kb.response)
    return False


def _keyboard_run(view_manager) -> bool:
    """Start the keyboard view"""
    global current_view, keyboard_index, connection_state

    kb = view_manager.keyboard

    # Initialize keyboard based on view
    if keyboard_index == KEYBOARD_WAITING:
        kb.reset()

        if current_view == VIEW_KEYBOARD_HOST:
            kb.title = "Enter SSH Host"
            kb.response = ssh_host
        elif current_view == VIEW_KEYBOARD_PORT:
            kb.title = "Enter SSH Port"
            kb.response = ssh_port if ssh_port else "22"
        elif current_view == VIEW_KEYBOARD_USERNAME:
            kb.title = "Enter Username"
            kb.response = ssh_username
        elif current_view == VIEW_KEYBOARD_PASSWORD:
            kb.title = "Enter Password"
            kb.response = ssh_password
        elif current_view == VIEW_KEYBOARD_COMMAND:
            kb.title = "Enter Command"
            kb.response = ""

        keyboard_index = KEYBOARD_ENTERING
        return kb.run(force=True)

    # Run keyboard
    if keyboard_index == KEYBOARD_ENTERING:
        if not kb.run(force=True):
            kb.reset()
            current_view = (
                VIEW_MAIN_MENU
                if connection_state == STATE_DISCONNECTED
                else VIEW_CONNECTED
            )
            _menu_start(view_manager)
            keyboard_index = KEYBOARD_WAITING
            return False

        if kb.is_finished:
            if _keyboard_save(view_manager):
                kb.reset()

                # Return to appropriate view
                if current_view == VIEW_KEYBOARD_COMMAND:
                    current_view = VIEW_CONNECTED
                else:
                    current_view = VIEW_MAIN_MENU
                    _menu_start(view_manager)

                keyboard_index = KEYBOARD_WAITING
                return True

            view_manager.alert("Failed to save!", False)
            kb.reset()
            current_view = VIEW_MAIN_MENU
            keyboard_index = KEYBOARD_WAITING
            return False

    return True


def _loading_run(view_manager, message: str = "Connecting...") -> None:
    """Display loading screen"""
    from picoware.gui.loading import Loading

    global _loading

    if _loading is None:
        draw = view_manager.draw
        _loading = Loading(draw)
        _loading.text = message
        _loading.animate()
    else:
        _loading.animate()


def _menu_start(view_manager) -> None:
    """Start the menu view"""
    from picoware.gui.menu import Menu
    from picoware.system.colors import TFT_BLUE

    global _menu, connection_state

    if _menu is not None:
        _menu.clear()
        del _menu

    draw = view_manager.draw
    bg = view_manager.background_color
    fg = view_manager.foreground_color

    # Set menu
    _menu = Menu(
        draw,
        "SSH Client",
        0,
        draw.size.y,
        fg,
        bg,
        TFT_BLUE,
        fg,
    )

    # Add items based on connection state
    if connection_state == STATE_DISCONNECTED:
        _menu.add_item("Connect")
        _menu.add_item("Set Host")
        _menu.add_item("Set Port")
        _menu.add_item("Set Username")
        _menu.add_item("Set Password")
    else:
        _menu.add_item("Execute Command")
        _menu.add_item("View Output")
        _menu.add_item("Disconnect")

    _menu.set_selected(0)
    _menu.set_selected(0)


def _textbox_start(view_manager) -> None:
    global _textbox, _ssh_client, _previous_text_len

    if not _ssh_client:
        return

    _output = "\n".join(_ssh_client.output)
    _len = len(_output)
    if _output == "" or _len == _previous_text_len:
        return

    _previous_text_len = _len

    if _textbox is None:
        from picoware.gui.textbox import TextBox

        draw = view_manager.draw
        _textbox = TextBox(draw, 0, draw.size.y)
        _textbox.set_text(_output)
    else:
        _textbox.set_text(_output)

    # move to end of text
    _textbox.set_current_line(_textbox.text_height)


def start(view_manager) -> bool:
    """Start the SSH app"""
    wifi = view_manager.wifi

    # if not a wifi device, return
    if not wifi:
        view_manager.alert("WiFi not available...", False)
        return False

    # if wifi isn't connected, return
    if not wifi.is_connected():
        from picoware.applications.wifi.utils import connect_to_saved_wifi

        view_manager.alert("WiFi not connected yet...", False)
        connect_to_saved_wifi(view_manager)
        return False

    # Create SSH folder if it doesn't exist
    view_manager.storage.mkdir("picoware/ssh")

    # Load credentials
    __load_ssh_credentials(view_manager)

    # Initialize SSH client
    global _ssh_client

    _ssh_client = SSHClient()

    # Start menu
    _menu_start(view_manager)

    return True


def run(view_manager) -> None:
    """Run the SSH app"""
    from picoware.system.buttons import (
        BUTTON_BACK,
        BUTTON_UP,
        BUTTON_DOWN,
        BUTTON_CENTER,
    )

    inp = view_manager.input_manager
    button = inp.button

    global current_view, keyboard_index, connection_state, ssh_command

    if current_view == VIEW_MAIN_MENU:
        if button == BUTTON_BACK:
            inp.reset()
            view_manager.back()
        elif button == BUTTON_UP:
            inp.reset()
            _menu.scroll_up()
        elif button == BUTTON_DOWN:
            inp.reset()
            _menu.scroll_down()
        elif button == BUTTON_CENTER:
            inp.reset()
            selected = _menu.selected_index

            if connection_state == STATE_DISCONNECTED:
                if selected == MENU_ITEM_CONNECT:
                    if not ssh_host or not ssh_username:
                        view_manager.alert("Set host & user!", False)
                        return

                    current_view = VIEW_CONNECTING
                    connection_state = STATE_CONNECTING

                elif selected == MENU_ITEM_SET_HOST:
                    current_view = VIEW_KEYBOARD_HOST
                    keyboard_index = KEYBOARD_WAITING

                elif selected == MENU_ITEM_SET_PORT:
                    current_view = VIEW_KEYBOARD_PORT
                    keyboard_index = KEYBOARD_WAITING

                elif selected == MENU_ITEM_SET_USERNAME:
                    current_view = VIEW_KEYBOARD_USERNAME
                    keyboard_index = KEYBOARD_WAITING

                elif selected == MENU_ITEM_SET_PASSWORD:
                    current_view = VIEW_KEYBOARD_PASSWORD
                    keyboard_index = KEYBOARD_WAITING
            else:
                # Connected menu
                if selected == 0:  # Execute Command
                    current_view = VIEW_KEYBOARD_COMMAND
                    keyboard_index = KEYBOARD_WAITING

                elif selected == 1:  # View Output
                    current_view = VIEW_OUTPUT

                elif selected == 2:  # Disconnect
                    if _ssh_client:
                        _ssh_client.disconnect()
                    connection_state = STATE_DISCONNECTED
                    _menu_start(view_manager)

    elif current_view == VIEW_CONNECTING:
        _loading_run(view_manager, "Connecting to SSH...")

        if _ssh_client:
            try:
                port = int(ssh_port) if ssh_port else 22
                success = _ssh_client.connect(
                    ssh_host, port, ssh_username, ssh_password
                )

                if success:
                    connection_state = STATE_CONNECTED
                    current_view = VIEW_CONNECTED
                    _menu_start(view_manager)
                else:
                    error = _ssh_client.error or "Connection failed"
                    view_manager.alert(error[:30], False)
                    connection_state = STATE_DISCONNECTED
                    current_view = VIEW_MAIN_MENU
            except Exception as e:
                view_manager.alert(f"Error: {str(e)[:20]}", False)
                connection_state = STATE_DISCONNECTED
                current_view = VIEW_MAIN_MENU

    elif current_view == VIEW_CONNECTED:
        if button == BUTTON_BACK:
            inp.reset()
            current_view = VIEW_MAIN_MENU
        elif button == BUTTON_UP:
            inp.reset()
            _menu.scroll_up()

        elif button == BUTTON_DOWN:
            inp.reset()
            _menu.scroll_down()

        elif button == BUTTON_CENTER:
            inp.reset()
            selected = _menu.selected_index

            if selected == 0:  # Execute Command
                current_view = VIEW_KEYBOARD_COMMAND
                keyboard_index = KEYBOARD_WAITING

            elif selected == 1:  # View Output
                current_view = VIEW_OUTPUT

            elif selected == 2:  # Disconnect
                if _ssh_client:
                    _ssh_client.disconnect()
                connection_state = STATE_DISCONNECTED
                current_view = VIEW_MAIN_MENU
                _menu_start(view_manager)

    elif current_view == VIEW_OUTPUT:
        _textbox_start(view_manager)

        if button == BUTTON_BACK:
            inp.reset()
            current_view = VIEW_CONNECTED
            _menu_start(view_manager)

        elif not _textbox:
            return

        elif button == BUTTON_UP:
            inp.reset()
            _textbox.scroll_up()

        elif button == BUTTON_DOWN:
            inp.reset()
            _textbox.scroll_down()

    elif current_view in (
        VIEW_KEYBOARD_HOST,
        VIEW_KEYBOARD_PORT,
        VIEW_KEYBOARD_USERNAME,
        VIEW_KEYBOARD_PASSWORD,
        VIEW_KEYBOARD_COMMAND,
    ):
        if not _keyboard_run(view_manager):
            return

        # If command was entered, execute it
        if current_view == VIEW_CONNECTED and ssh_command and _ssh_client:
            _ssh_client.execute_command(ssh_command)
            ssh_command = ""
            current_view = VIEW_OUTPUT


def stop(view_manager) -> None:
    """Stop the SSH app"""
    global _ssh_client, _menu, _loading, _textbox, _previous_text_len
    global ssh_host, ssh_port, ssh_username, ssh_password, ssh_command

    # Disconnect SSH
    if _ssh_client:
        _ssh_client.disconnect()
        del _ssh_client
        _ssh_client = None

    # Clean up UI elements
    if _menu:
        del _menu
        _menu = None

    if _loading:
        del _loading
        _loading = None

    if _textbox:
        del _textbox
        _textbox = None

    ssh_host = ""
    ssh_port = "22"
    ssh_username = ""
    ssh_password = ""
    ssh_command = ""

    _previous_text_len = 0

    view_manager.keyboard.reset()
    collect()

import socket as pysocket
import struct
import base64
import string
import errno
from random import SystemRandom
from contextlib import contextmanager
from hashlib import sha256
from io import BytesIO


def greet(max_version):
    return 'HELLO VERSION MIN=3.0 MAX=%s' % max_version

def random_name(l=20):
    nick = 'leaflet-'
    rng = SystemRandom()
    for n in range(l):
        nick += rng.choice(string.ascii_letters)
    return nick

name_chars = frozenset(string.ascii_letters + string.digits + string.punctuation)
domain_chars = frozenset(string.ascii_lowercase + string.digits + '.-')
forward_chars = frozenset(string.digits + '.')

def check_invalid_chars(name, char_set):
    if not isinstance(name, str):
        raise TypeError('Expects a str instance, not %s' % name.__class__.__name__)

    for ch in name:
        if ch not in char_set:
            raise ValueError('Invalid character %s. Keep it simple' % repr(ch))

def check_name(name):
    if '=' in name:
        raise ValueError('Invalid character \'=\'. Keep it simple')
    if len(name) > 250:
        raise ValueError('That is a long name. Keep it short')

    check_invalid_chars(name, name_chars)

def check_forward(forward):
    try:
        check_invalid_chars(forward[0], forward_chars)
    except ValueError as e:
        raise ValueError('Invalid IP address') from e

    if not 0 <= forward[1] <= 65535:
        raise ValueError('Invalid port number')

def check_domain(domain):
    if len(domain) > 1000:
        raise ValueError('That is a long domain name. Keep it short')

    check_invalid_chars(domain, domain_chars)

def normalize_domain(domain):
    domain = domain.lower()
    check_domain(domain)
    return domain


########## SAM header parser ##########

def sam_readline(sock, partial = None):
    """read a line from a sam control socket"""
    response = b''
    exception = None
    while True:
        try:
            c = sock.recv(1)
            if not c:
                raise EOFError('SAM connection died. Partial response %r %r' % (partial, response))
            elif c == b'\n':
                break
            else:
                response += c
        except (BlockingIOError, pysocket.timeout) as e:
            if partial is None:
                raise e
            else:
                exception = e
                break

    if partial is None:
        # print('<--', response)
        return response.decode('ascii')
    else:
        # print('<--', repr(partial), '+', response, exception)
        return (partial + response.decode('ascii'), exception)


def make_reply_reader(sock):
    while True:
        yield from line_generator(sock)

def line_generator(sock):
    partial = ''
    partial, exc = sam_readline(sock, partial)
    while exc:
        yield exc
        partial, exc = sam_readline(sock, partial)
    yield partial


class SAMReply(object):
    __slots__ = ('cmd', 'opts')

    def __init__(self, cmd = None, opts = None):
        self.cmd = cmd
        self.opts = opts

    def __getitem__(self, key):
        return self.opts[key]

    def get(self, key, default = None):
        return self.opts.get(key, default)

    def __iter__(self):
        return iter(self.opts)

    def __len__(self):
        return len(self.opts)

    @property
    def ok(self):
        return self.result == 'OK'

    @property
    def result(self):
        return self.opts.get('RESULT')

    @property
    def message(self):
        return self.opts.get('MESSAGE')

    def __repr__(self):
        return '<%s %r %r>' % (self.__class__.__name__, self.result, self.message)


def split_kv(sub_parts):
    for part in sub_parts:
        if '=' in part:
            i = part.index('=')
            yield (part[:i], part[i+1:])

def join_kv(options):
    return ' '.join('%s=%s' % (k, v) for (k, v) in options.items())


def sam_parse_reply(line):
    """parse a reply line into a dict"""
    parts = line.split(' ')
    opts = {k: v for (k, v) in split_kv(parts[2:])}
    return SAMReply(parts[0], opts)

def sam_send(sock, line_and_data):
    """Send a line to the SAM controller, but don't read it"""
    if isinstance(line_and_data, tuple):
        line, data = line_and_data
    else:
        line, data = line_and_data, b''

    line = bytes(line, encoding='ascii') + b' \n'
    # print('-->', line, data)
    sock.sendall(line + data)

def sam_cmd(sock, line, parse=True):
    """Send a line to the SAM controller, returning the parsed response"""
    sam_send(sock, line)
    reply_line = sam_readline(sock)
    if parse:
        return sam_parse_reply(reply_line)
    else:
        return reply_line


########## handshake ##########

class HandshakeError(OSError):
    def __init__(self, msg):
        super().__init__(errno.ENOTCONN, msg)

class NSError(OSError):
    def __init__(self, msg):
        super().__init__(errno.EAGAIN, msg)

class CreateDestError(OSError):
    def __init__(self, msg):
        super().__init__(errno.EADDRNOTAVAIL, msg)

class ReachError(OSError):
    def __init__(self, msg):
        super().__init__(errno.EHOSTUNREACH, msg)

class AcceptError(OSError):
    def __init__(self, msg):
        super().__init__(errno.EADDRNOTAVAIL, msg)

def controller_connect(sam_api, timeout):
    sam_sock = pysocket.create_connection(sam_api)
    sam_sock.setsockopt(pysocket.IPPROTO_TCP, pysocket.SO_KEEPALIVE, 1)
    sam_sock.settimeout(timeout)
    return sam_sock

def handshake(timeout, sam_api, max_version):
    """handshake with sam via a socket.socket instance"""
    sock = controller_connect(sam_api, timeout=timeout)
    response = sam_cmd(sock, greet(max_version))
    if response.ok:
        return sock
    else:
        raise HandshakeError("Failed to handshake with SAM: %s" % repr(response))

@contextmanager
def context_handshake(timeout, sam_api, max_version):
    sock = None
    try:
        sock = handshake(timeout=timeout, sam_api=sam_api, max_version=max_version)
        yield sock
    finally:
        if sock:
            sock.close()


########## SAM socket commands ##########

def lookup_cache(domain, cache):
    if isinstance(domain, Dest):
        return domain
    domain = normalize_domain(domain)
    dest = cache.get(domain)
    if dest:
        return dest

def lookup(sock, domain, cache = None):
    """lookup an I2P domain name, returning a Destination instance"""
    domain = normalize_domain(domain)

    # cache miss, perform lookup
    reply = sam_cmd(sock, "NAMING LOOKUP NAME=%s" % domain)

    b64_dest = reply.get('VALUE')
    if b64_dest:
        dest = Dest(b64_dest, encoding='base64')
        if cache:
            cache[dest.base32 + '.b32.i2p'] = dest
        return dest
    else:
        raise NSError('Domain name %r not resolved because %r' % (domain, reply))


def session_create(sock, sock_type, sig_type, name, i2cp_options = None):
    i2cp = i2cp_options or {}
    sock_type = sock_type.upper()
    if sock_type not in ('STREAM', 'DATAGRAM'):
        raise NotImplementedError('Socket type %s is not implemented' % repr(sock_type))

    cmd = 'SESSION CREATE STYLE=%s DESTINATION=TRANSIENT SIGNATURE_TYPE=%d ID=%s ' % (sock_type, sig_type, name)
    cmd += join_kv(i2cp)
    reply = sam_cmd(sock, cmd)

    # parse reply
    if reply.ok:
        return reply['DESTINATION']
    else:
        raise CreateDestError('Failed to create destination. %s' % repr(reply))

def bind_datagram(binding):
    dgram_sock = pysocket.socket(type=pysocket.SOCK_DGRAM)
    dgram_sock.bind(binding)
    # port = dgram_sock.getsockname()[1]
    # return (dgram_sock, binding[0], port)
    return dgram_sock


########## stream generators ##########

def stream_connect(nickname, dest):
    line = yield ('STREAM CONNECT ID=%s DESTINATION=%s SILENT=false' % (nickname, dest.base64))
    reply = sam_parse_reply(line)
    if reply.ok:
        yield reply
    else:
        raise ReachError('Cannot reach %r because %r' % (dest, reply))

def stream_accept(nickname):
    line = yield ('STREAM ACCEPT ID=%s SILENT=false' % nickname)
    reply = sam_parse_reply(line)
    if reply.ok:
        yield from accept_dest_generator()
    else:
        raise AcceptError('Failed to accept %r because %r' % (nickname, reply))

def accept_dest_generator():
    line = yield None
    yield parse_reply_dest(line)

def parse_reply_dest(line):
    space_index = line.find(' ')
    if space_index >= 0:
        line = line[0:space_index]
    return Dest(line, encoding='base64')



########## datagram stuff ##########

def datagram_send(data, dest):
    header = 'DATAGRAM SEND DESTINATION=%s SIZE=%s' % (dest.base64, str(len(data)))
    line = yield (header, data)
    reply = sam_parse_reply(line)
    yield Dest(reply['DESTINATION'], encoding='base64'), int(reply['SIZE'])

def pack_datagram(data, max_version, nickname, dest, options):
    header = ' '.join((max_version, nickname, dest.base64, join_kv(options))).rstrip() + '\n'
    return bytes(header, encoding='ascii') + data

class Dest(object):
    ECDSA_SHA256_P256 = 1
    ECDSA_SHA384_P384 = 2
    ECDSA_SHA512_P521 = 3
    EdDSA_SHA512_Ed25519 = 7

    default_sig_type = EdDSA_SHA512_Ed25519
    sskey_len_dict = {
        ECDSA_SHA256_P256: 32,
        ECDSA_SHA384_P384: 48,
        ECDSA_SHA512_P521: 66,
        EdDSA_SHA512_Ed25519: 32,
    }

    __slots__ = ('secret_key', 'signing_secret_key', 'keys_cert', 'sig_type')

    def __init__(self, keyfile, encoding, sig_type = None, private=False):
        if encoding not in ('base64', 'raw'):
            raise ValueError('Unknown Destination encoding %s' % repr(encoding))
        if private:
            if sig_type not in self.sskey_len_dict.keys():
                raise NotImplementedError('Signing key type %s not implemented' % repr(sig_type))
            self.sig_type = sig_type

        if encoding == 'base64':
            keyfile = self.__class__.b64decode(keyfile)
        keyfile = BytesIO(keyfile)

        self.keys_cert = self.__class__.read_keys_cert(keyfile)
        if private:
            self.secret_key = self.__class__.read_secret_key(keyfile)
            self.signing_secret_key = self.__class__.read_signing_secret_key(keyfile, sig_type)

        if keyfile.read(1):
            raise ValueError('Found extra bytes at the end of keyfile')

    def __repr__(self):
        return '<%s %r>' % (self.__class__.__name__, self.base32)

    @property
    def is_private(self):
        return hasattr(self, 'secret_key')

    @property
    def base64(self):
        return self.__class__.b64encode(self.keys_cert)

    @property
    def base32(self):
        digest = sha256(self.keys_cert).digest()
        return base64.b32encode(digest).rstrip(b'=').lower().decode('ascii')

    @staticmethod
    def b64encode(arg):
        return base64.b64encode(arg, b'-~').decode('ascii')

    @staticmethod
    def b64decode(arg):
        return base64.b64decode(arg + '=' * (-len(arg) % 4), '-~')

    @staticmethod
    def _read(keyfile, read_len, throw='Keyfile truncated'):
        data = keyfile.read(read_len)
        if len(data) != read_len:
            raise ValueError(throw + ' %d < %d' % (len(data), read_len))
        return data

    @classmethod
    def read_keys_cert(cls, keyfile):
        fixed_len = 256 + 128 + 3
        keys_cert_header = cls._read(keyfile, fixed_len, throw='KeysAndCert header truncated')

        body_len = struct.unpack('!H', keys_cert_header[-2:])[0]
        body = cls._read(keyfile, body_len, throw='Certificate body truncated')

        return keys_cert_header + body

    @classmethod
    def read_secret_key(cls, keyfile):
        key_len = 256
        secret_key = cls._read(keyfile, key_len, throw='Secret key truncated')
        return secret_key

    @classmethod
    def read_signing_secret_key(cls, keyfile, sig_type):
        key_len = cls.sskey_len_dict[sig_type]
        secret_signing = cls._read(keyfile, key_len, throw='Secret signing key truncated')
        return secret_signing



__all__ = (
    'HandshakeError', 'NSError', 'CreateDestError', 'ReachError', 'Dest',
)

from . import samtools
from .usersocket import WrappedSocket
from socket import SHUT_RDWR

def sam_handshake(func):
    def f(self, *args, **kwargs):
        sock = samtools.handshake(*self.handshake_args)
        return func(self, sock, *args, **kwargs)
    return f

def transient_handshake(func):
    def f(self, *args, **kwargs):
        with samtools.context_handshake(*self.handshake_args) as sock:
            return func(self, sock, *args, **kwargs)
    return f

class Controller(object):
    __slots__ = ('sam_timeout', 'sam_api', 'dgram_api', 'max_version', 'ns_cache')

    def __init__(self,
                 sam_timeout=60.0,
                 sam_api=samtools.default_sam_api,
                 dgram_api=samtools.default_dgram_api,
                 max_version=samtools.default_max_version):
        self.sam_timeout = sam_timeout
        self.sam_api = sam_api
        self.dgram_api = dgram_api
        self.max_version = max_version
        self.ns_cache = dict()

        self.check_api()

    @property
    def handshake_args(self):
        return (self.sam_timeout, self.sam_api, self.max_version)

    @transient_handshake
    def check_api(self, sam_sock):
        pass

    def lookup(self, name):
        dest = samtools.lookup_cache(name, self.ns_cache)
        if dest:
            return dest
        else:
            return self._lookup(name)

    @transient_handshake
    def _lookup(self, sam_sock, name):
        return samtools.lookup(sam_sock, name, self.ns_cache)

    @sam_handshake
    def create_dest(self, sam_sock, name = None, sock_type='stream', i2cp = None):
        if sock_type not in ('stream',):
            raise NotImplementedError('Socket type %s is not implemented' % repr(sock_type))
        if not name:
            name = samtools.random_name()
        else:
            samtools.check_name(name)
        if sock_type == 'dgram':
            if not i2cp or 'PORT' not in i2cp:
                raise ValueError('For datagram, you must bind to a port')
        return OurDest(self, sock_type, name, i2cp or {})


class OurDest(samtools.Dest):
    __slots__ = ('name', 'sam_sock', 'controller')

    def __init__(self, controller, sock_type, nickname, i2cp_options):
        self.name = nickname
        self.controller = controller

        sig_type = self.default_sig_type
        sock = samtools.handshake(*controller.handshake_args)
        keyfile = samtools.session_create(sock, sock_type, sig_type, nickname, i2cp_options)
        self.sam_sock = sock

        super().__init__(keyfile, sig_type=sig_type, encoding='base64', private=True)


    @property
    def handshake_args(self):
        return self.controller.handshake_args

    def connect(self, other):
        dest = self.controller.lookup(other)
        s = samtools.handshake(*self.handshake_args)
        parser = samtools.stream_connect(self.name, dest)
        return WrappedSocket(s, self.controller, parser)

    def register_accept(self):
        s = samtools.handshake(*self.handshake_args)
        parser = samtools.stream_accept(self.name)
        return WrappedSocket(s, self.controller, parser)

    def close(self):
        if self.sam_sock:
            self.sam_sock.shutdown(SHUT_RDWR)
            self.sam_sock.close()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()


__all__ = ('Controller',)

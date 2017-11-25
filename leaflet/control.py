from . import samtools
from .usersocket import StreamSocket, DatagramSocket
from socket import SHUT_RDWR

default_sam_api = ('127.0.0.1', 7656)
default_dgram_api = ('127.0.0.1', 7655)
default_max_version = '3.0'
default_timeout = 60.0

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
                 sam_timeout=default_timeout,
                 sam_api=default_sam_api,
                 dgram_api=default_dgram_api,
                 max_version=default_max_version):
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

    def create_dest(self, name = None, style='stream', forward = None, i2cp = None):
        return OurDest(controller=self, name=name, style=style, forward=forward, i2cp=i2cp)


class OurDest(samtools.Dest):
    __slots__ = ('name', 'sam_sock', 'controller', 'style', 'forward')

    def __init__(self, controller, name, style, forward, i2cp):
        if style not in ('stream', 'datagram', 'dgram'):
            raise NotImplementedError('Socket type %s is not implemented' % repr(style))

        if not name:
            name = samtools.random_name()
        else:
            samtools.check_name(name)

        if style == 'dgram':
            style = 'datagram'

        if forward is not None:
            if isinstance(forward, int):
                forward = ('127.0.0.1', forward)
            else:
                samtools.check_forward(forward)

        self.__real_init(controller=controller, name=name, style=style, forward=forward, i2cp=i2cp or {})


    def __real_init(self, controller, name, style, forward, i2cp):
        self.controller = controller
        self.name = name
        self.style = style
        self.forward = forward

        if forward:
            i2cp['HOST'], i2cp['PORT'] = forward
        sig_type = self.default_sig_type
        sock = samtools.handshake(*controller.handshake_args)
        keyfile = samtools.session_create(sock, style, sig_type, name, i2cp)
        self.sam_sock = sock

        super().__init__(keyfile, sig_type=sig_type, encoding='base64', private=True)


    @property
    def handshake_args(self):
        return self.controller.handshake_args

    def connect(self, other):
        dest = self.controller.lookup(other)
        s = samtools.handshake(*self.handshake_args)
        parser = samtools.stream_connect(self.name, dest)
        return StreamSocket(s, self.controller, parser)

    def register_accept(self):
        s = samtools.handshake(*self.handshake_args)
        parser = samtools.stream_accept(self.name)
        return StreamSocket(s, self.controller, parser)

    def bind(self):
        if self.forward:
            return self._bind_datagram()
        else:
            return self._bind_legacy_datagram()

    def _bind_datagram(self):
        sock = samtools.bind_datagram(self.forward)
        return DatagramSocket(sock, self.controller, self.name, parser=None)

    def _bind_legacy_datagram(self):
        raise NotImplementedError('Legacy DATAGRAM SEND is not implemented')

    def close(self):
        if self.sam_sock:
            self.sam_sock.shutdown(SHUT_RDWR)
            self.sam_sock.close()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()


__all__ = ('Controller',)

from . import samtools
import socket

class IncompleteIOError(BlockingIOError):
    pass

class SourceError(socket.error):
    pass

def it_leaks(func):
    def f(self, *args, **kwargs):
        human_error = func(self, *args, **kwargs) +  \
            ' Calling the original method will leak your packets.'
        raise AttributeError(human_error)
    return f

def alt_func(alt_name):
    def decorator(func):
        def f(self, *args, **kwargs):
            human_error = 'This is dangerous! Instead, use %s.%s %s' % (
                self.__class__.__name__, alt_name, func(self, *args, **kwargs))
            raise AttributeError(human_error)
        return f
    return decorator

class WrappedSocket(object):
    """A python socket wrapped to expose I2P addreses instead of IP addresses"""

    __passthru = ('type', 'proto', 'send', 'recv', 'sendall', 'sendfile',
        'fileno', 'shutdown', 'detach', 'makefile', 'setsockopt',
        'getsockopt','setblocking', 'settimeout')

    __slots__ = ('sock', 'controller', 'thing_generator')

    def __init__(self, sock, controller, parser):
        sock.settimeout(None)
        self.sock = sock
        self.controller = controller

        reader = samtools.make_reply_reader(sock)
        self.thing_generator = self._make_loop(parser, reader)

    def __getattr__(self, name):
        if name not in self.__passthru:
            raise AttributeError('%r object has no attribute %r' % (self.__class__.__name__, name))
        return getattr(self.sock, name)

    def __setattr__(self, name, value):
        if name in self.__passthru:
            return setattr(self.sock, name, value)
        else:
            return super().__setattr__(name, value)


    def listen(self, *args, **kwargs):
        human_error = 'There is nothing to listen to. Instead, ask the controller to notify you when a stream comes.'
        raise AttributeError(human_error)

    def accept(self, *args, **kwargs):
        human_error = 'There is nothing to accept. Just use %s.recv and strip the SAM response.' % self.__class__.__name__
        raise AttributeError(human_error)

    def connect(self, *args, **kwargs):
        human_error = 'This %s instance is connected to %s.' % (self.__class__.__name__, repr(self.sam_api))
        human_error += ' To reach an I2P address, ask the controller to do it for you.'
        raise AttributeError(human_error)

    @it_leaks
    def gethostbyname(self, *args, **kwargs):
        return 'Use %s.lookup or controller.lookup instead.' % self.__class__.__name__

    @it_leaks
    def gethostbyname_ex(self, *args, **kwargs):
        return 'Use %s.lookup controller.lookup instead.' % self.__class__.__name__

    @alt_func('transmit')
    def sendto(self, *args, **kwargs):
        return 'to send a message to an I2P destination.'

    @alt_func('collect')
    def recvfrom(self, *args, **kwargs):
        return 'to receive a message from the I2P UDP port.'

    @property
    def sam_api(self):
        return self.controller.sam_api

    @property
    def dgram_api(self):
        return self.controller.dgram_api

    def transmit(self, *args):
        return self.sock.sendto(*args, self.dgram_api)

    def collect(self, *args, **kwargs):
        data, address = self.sock.recvfrom(*args, **kwargs)
        if address != self.dgram_api:
            raise SourceError(repr(address))
        return (data, address)

    def lookup(self, name):
        return self.controller.lookup(name)

    def _make_loop(self, parser, reader):
        reply = None
        while True:
            parser_yields = parser.send(reply)
            # if not request, but a parsed result
            if not isinstance(parser_yields, str):
                yield parser_yields
            else:
                if parser_yields:
                    samtools.sam_send(self.sock, parser_yields)
                while True:
                    reader_yields = reader.__next__()
                    # if not reply, but an exception
                    if not isinstance(reader_yields, str):
                        yield reader_yields
                    else:
                        reply = reader_yields
                        break

    def parse_headers(self):
        loop_yields = next(self.thing_generator)
        if isinstance(loop_yields, BaseException):
            raise loop_yields
        else:
            return loop_yields

    def _close_me(self):
        self.thing_generator.close()

    def close(self):
        self._close_me()
        self.sock.close()

    def __enter__(self):
        self.sock.__enter__(self)
        return self

    def __exit__(self, *args):
        self._close_me()
        return self.sock.__exit__(self, *args)


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
            self.sam_sock.shutdown(socket.SHUT_RDWR)
            self.sam_sock.close()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()


__all__ = ('Controller', 'IncompleteIOError', 'SourceError', )

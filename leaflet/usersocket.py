from .samtools import make_reply_reader, sam_send, pack_datagram, parse_reply_dest
from errno import EACCES

class SourceError(OSError):
    def __init__(self, message):
        super().__init__(EACCES, message)

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
    """A python socket wrapped to expose I2P addresses instead of IP addresses"""

    __passthru = ('type', 'proto', 'send', 'recv', 'sendall', 'sendfile',
        'fileno', 'shutdown', 'detach', 'makefile', 'setsockopt',
        'getsockopt','setblocking', 'settimeout')

    __slots__ = ('sock', 'controller', 'reply_generator')

    def __init__(self, sock, controller, parser):
        self.__class__._send_data(sock, parser)
        sock.settimeout(None)
        self.sock = sock
        self.controller = controller

        reader = make_reply_reader(sock)
        self.reply_generator = self._make_loop(parser, reader)

    @staticmethod
    def _send_data(sock, generator):
        if generator:
            request_line = next(generator)
            sam_send(sock, request_line)
        # print('End of sending SAM data')

    def __getattr__(self, name):
        if name not in self.__passthru:
            raise AttributeError('%r object has no attribute %r' % (self.__class__.__name__, name))
        return getattr(self.sock, name)

    def __setattr__(self, name, value):
        if name in self.__passthru:
            return setattr(self.sock, name, value)
        else:
            return super().__setattr__(name, value)

    def bind(self, *args, **kwargs):
        human_error = 'Bind what? Use controller.register_accept instead'
        raise AttributeError(human_error)

    def listen(self, *args, **kwargs):
        human_error = 'Use controller.register_accept instead'
        raise AttributeError(human_error)

    def accept(self, *args, **kwargs):
        human_error = 'SAM socket is different. ' + \
            'Use controller.register_accept to strip the SAM response, ' + \
            'and %s.recv to receive data' % self.__class__.__name__
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

    @property
    def sam_api(self):
        return self.controller.sam_api

    def lookup(self, name):
        return self.controller.lookup(name)

    def _close_me(self):
        self.reply_generator.close()

    def close(self):
        self._close_me()
        self.sock.close()

    def __enter__(self):
        self.sock.__enter__(self)
        return self

    def __exit__(self, *args):
        self._close_me()
        self.sock.__exit__(self, *args)

    def _make_loop(self, parser, reader):
        parser_result = None
        while True:
            if parser_result is not None:
                yield parser_result
                break
            else:
                # parser did not yield result, feed with more data
                reply = None
                while reply is None:
                    reader_result = next(reader)
                    if not isinstance(reader_result, str):
                        # if not a reply line, but an exception
                        yield reader_result
                    else:
                        reply = reader_result
                parser_result = parser.send(reply)

    def parse_headers(self):
        loop_result = next(self.reply_generator)
        if isinstance(loop_result, BaseException):
            raise loop_result
        else:
            return loop_result


dgram_header_len = 2048

class StreamSocket(WrappedSocket):
    pass

class DatagramSocket(WrappedSocket):
    __slots__ = ('name', 'forward_mode')
    __blocked = ('recv', 'send', 'sendall', 'sendfile')

    def __init__(self, sock, controller, name, parser):
        self.name = name
        self.forward_mode = False if parser else True
        super().__init__(sock, controller, parser)

    def __getattr__(self, name):
        if name in self.__blocked:
            raise AttributeError('%r object has no attribute %r' % (self.__class__.__name__, name))
        return super().__getattr__(name)

    @alt_func('transmit')
    def sendto(self, *args, **kwargs):
        return 'to send a message to an I2P destination.'

    @alt_func('collect')
    def recvfrom(self, *args, **kwargs):
        return 'to receive a message from the I2P UDP port.'

    @property
    def dgram_api(self):
        return self.controller.dgram_api

    def transmit(self, *args):
        data = args[0]
        dest = self.lookup(args[-1])
        real_data = pack_datagram(data, self.controller.max_version, self.name, dest, {})
        real_args = (real_data,) + args[1:-1] + (self.dgram_api,)
        return self.sock.sendto(*real_args)

    def collect(self, bufsize=32*1024, *args):
        if self.forward_mode:
            return self._datagram_collect(bufsize, *args)
        else:
            return self._stream_collect(bufsize, *args)

    def _stream_collect(self, bufsize, *args):
        raise NotImplementedError()

    def _datagram_collect(self, bufsize, *args):
        real_bufsize = bufsize + dgram_header_len
        data, address = self.sock.recvfrom(real_bufsize, *args)
        if address != self.dgram_api:
            raise SourceError('Packet src=%r not from SAM UDP API %r' % (address, self.dgram_api))

        # parse SAM reply header
        lf_index = data.index(b'\n')
        line, real_data = data[0:lf_index].decode('ascii'), data[1+lf_index:]
        real_address = parse_reply_dest(line)

        return (real_data, real_address)


__all__ = ('SourceError',)

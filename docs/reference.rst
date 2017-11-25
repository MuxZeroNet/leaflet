Class reference
===============

Leaflet defines the following public classes and functions.


Controller and our Destination
------------------------------

.. class:: Controller(object)

    .. method:: __init__(self, sam_timeout=60.0, sam_api=('127.0.0.1', 7656), dgram_api=('127.0.0.1', 7655), max_version='3.0')

        Make a SAM Controller instance using the given information, and test SAM connection.

    .. method:: check_api(self)

        Check SAM API connection. This method will be automatically called when the constructor is called.

        :raises OSError: if failed to connect to SAM API.

    .. method:: lookup(self, name)

        Lookup and return the full Destination of the I2P domain name. If `name` is a :class:`Dest` instance, return it directly.

        :param name: the ``.b32.i2p`` domain name.
        :type name: str or Dest
        :return: A :class:`Dest` instance.
        :raises NSError: if lookup failed.

    .. method:: create_dest(self, name = None, style='stream', forward = None, i2cp = None)

        Create an ephemeral Destination. The Destination will be destroyed when dereferenced.

        :param name: a human-readable "nickname" of our Destination, must be unique and cannot contain whitespaces. If the name is not provided, a random name will be generated.
        :type name: str or None
        :param str style: the Destination type, can be either ``stream`` or ``datagram``.
        :param forward: for ``datagram`` Destinations only. The port number or endpoint which SAM will forward incoming datagram to.
        :type forward: int, tuple or None
        :param i2cp: additional I2CP options.
        :type i2cp: dict or None

        :return: An :class:`OurDest` instance.
        :raises CreateDestError: if failed to create an ephemeral Destination.
        :raises HandshakeError: if handshake failed.


.. class:: OurDest(Dest)

    Internal class returned when calling :meth:`Controller.create_dest`. It inherits methods from the :class:`Dest` class. It also defines the following methods.

    .. method:: connect(self, other)

        For ``stream`` Destinations only.

        Ask SAM to connect to a remote I2P peer, and write to the returned wrapped socket object when the connection is successful.

        Because of how the SAM protocol is designed, this method simply sends a ``STREAM CONNECT`` request to the SAM port. This method will not block. To receive and parse the SAM reply headers, use :meth:`StreamSocket.parse_headers` immediately.

        :param other: the remote I2P peer to connect to.
        :type other: str or Dest
        :returns: a :class:`StreamSocket` instance.
        :raises HandshakeError: if handshake failed.

    .. method:: register_accept(self)

        For ``stream`` Destinations only.

        Ask SAM to accept connections to this destination, and write to the returned wrapped socket object when a data stream is available.

        Because of how the SAM protocol is designed, this method simply sends a ``STREAM ACCEPT`` request to the SAM port. This method will not block. To receive and parse the SAM reply headers, use :meth:`StreamSocket.parse_headers` immediately.

        :returns: a :class:`StreamSocket` instance.
        :raises HandshakeError: if handshake failed.
        :raises AcceptError: if failed to accept connections.

    .. method:: bind(self)

        For ``datagram`` Destinations only.

        Make a datagram socket, and bind the datagram socket to the endpoint specified in the `forward` parameter, in the constructor, returning the datagram socket.

        :returns: a :class:`DatagramSocket` instance.
        :raises OSError: when failed to bind to the given endpoint.

    .. method:: close(self)

        Close the SAM connection and free resources, destroying the ephemeral Destination.

    .. method:: __enter__(self)
    .. method:: __exit__(self, *args, **kwargs)

        Allows you to use :meth:`Controller.create_dest` inside a ``with`` statement suite.

        .. code-block:: Python

            controller = Controller()
            with controller.create_dest() as our_dest:
                do_stuff()


Wrapped socket
--------------

.. class:: WrappedSocket(object)
.. class:: StreamSocket(WrappedSocket)

    A wrapped socket object that exposes I2P concepts instead of IP concepts. It defines the following methods.

    .. method:: parse_headers(self)

        Receive and parse SAM reply headers. This method will block or raise BlockingIOError or raise socket.timeout depending on your socket settings.

        When this method is used immediately after :meth:`OurDest.connect`, the return value and exception type are the following.

        :return: a :class:`SAMReply` instance.
        :raises ReachError: when the remote peer was unreachable.

        When this method is used immediately after :meth:`OurDest.register_accept`, the return value and exception type are the following.

        :return: a :class:`Dest` instance, indicating the source of the packet.
        :raises ValueError: if the Destination in the SAM reply headers cannot be parsed.

    .. method:: lookup(self, name)

        The alternative to the `gethostbyname` method.

        See :meth:`Controller.lookup`

    .. method:: close(self)
    .. method:: __enter__(self)
    .. method:: __exit__(self, *args, **kwargs)

    .. note::

        It has the following passthru methods.

        ``type  proto  send  recv  sendall  sendfile  fileno  shutdown  detach  makefile  setsockopt  getsockopt  setblocking  settimeout``

    Notably, the following methods are not available. Calling any of them results in an AttributeError. Instead, their alternatives should be used.

        .. method:: bind
        .. method:: listen
        .. method:: accept
        .. method:: connect
        .. method:: gethostbyname
        .. method:: gethostbyname_ex

.. class:: DatagramSocket(WrappedSocket)

    A wrapped datagram socket object that exposes I2P concepts instead of IP concepts. It defines the following methods.

    .. class:: transmit(self, data, [flags,] dest)

        The alternative to the `sendto` method.

        :param bytes data: the payload, excluding the SAM datagram header.
        :param dest: where to send the payload to.
        :type dest: str or Dest
        :raises NSError: if naming lookup failed.
        :raises OSError: if a socket error ocurred.

        .. note:: The maximum acceptable payload size is ~31 KB. However, it is recommended to keep the payload size under 15 KB.

    .. class:: collect(self, bufsize=32*1024, *args)

        The alternative to the `recvfrom` method.

        :param int bufsize: the number of bytes you want to receive, excluding the SAM datagram header.
        :returns: a ``(data, address)`` -> (bytes, :class:`Dest`) tuple.
        :raises SourceError: if the packet is not forwarded by SAM.

    Notably, the following methods are not available. Calling any of them results in an AttributeError. Instead, their alternatives should be used.

        .. method:: sendto
        .. method:: recvfrom


SAM data structure
------------------

.. class:: Dest(object)

    A parsed Destination or KeyFile.

    :var bool is_private: `True` if the Destination contains private keys.
    :var str base64: Base-64 representation of the public component of the Destination.
    :var str base32: Base-32 representation of the SHA-256 hash of the public component of the Destination.

    .. method:: __init__(self, keyfile, encoding, sig_type = None, private=False)

.. class:: SAMReply(object)


Exceptions
----------

.. class:: HandshakeError(OSError)
.. class:: NSError(OSError)
.. class:: CreateDestError(OSError)
.. class:: ReachError(OSError)
.. class:: AcceptError(OSError)
.. class:: SourceError(OSError)

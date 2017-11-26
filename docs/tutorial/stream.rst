Writing a server using stream sockets
=====================================

Make a Controller object.

.. code-block:: Python
    :linenos:

    controller = Controller()

Create our Destination. Our Destination is our "IP Address" in the I2P network.

Our Destination instance will be discarded once it gets garbage collected, so we should keep the reference to it, and use it in a context manager.

.. code-block:: Python
    :lineno-start: 2

    with controller.create_dest() as our_dest:
        print('Server address: ' + our_dest.base32 + '.b32.i2p')

Tell SAM we need to accept connections. The method ``our_dest.register_accept`` tells SAM to accept connections. The return value ``conn`` is a socket object. This method will not block.

.. code-block:: Python
    :lineno-start: 4

        conn = our_dest.register_accept()

SAM will write to the ``conn`` socket only when a data stream comes in. Wait until a message comes in. When a message came in, read and strip the SAM response headers.

The method ``conn.parse_headers`` will block until a message comes in.

Now a message comes in, but first we need to strip the SAM headers.

.. code-block:: Python
    :lineno-start: 5

        addr = conn.parse_headers()

Now we have the connection and the address. Pass them to a handler.

.. code-block:: Python
    :lineno-start: 6

        handler(addr, conn)

Write the handler.

.. code-block:: Python

    def handler(addr, conn):
        # now we can read the real message
        request = conn.recv(4096)
        print('Received a message from %r: %r' % (addr, request))
        # reply
        conn.sendall(b'Hello, how are you?')
        conn.close()

Write our client:

.. code-block:: Python

    def send(server_addr):
        # test SAM connection
        controller = Controller()

        with controller.create_dest() as our_dest:
            # connect to a remote destination and send our message
            sock = our_dest.connect(server_addr)
            # SAM will give us response headers
            # when the connection is successful
            sam_reply = sock.parse_headers()
            # now we can send data
            sock.sendall(b'Hello, there!')
            real_reply = sock.recv(4096)

            print(sam_reply, real_reply)
            sock.close()

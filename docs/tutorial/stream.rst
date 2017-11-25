Tutorial: Writing a server using stream sockets
===============================================

Make a Controller object.

.. code-block:: Python

    controller = Controller()

Create our Destination. Our Destination is our "IP Address" in the I2P network. Our Destination will be thrown away if it gets garbage collected, so we should keep the reference to our destination instance, and use it in a context manager.

.. code-block:: Python

    with controller.create_dest() as our_dest:
        print('Server address: ' + our_dest.base32 + '.b32.i2p')

Tell SAM we need to accept connections. ``our_dest.register_accept`` returns a socket object.

.. code-block:: Python

    with controller.create_dest() as our_dest:
        print('Server address: ' + our_dest.base32 + '.b32.i2p')
        # SAM will write to the conn socket
        # when a data stream comes in
        # this line will not block
        conn = our_dest.register_accept()

Wait until a message comes in. When a message came in, strip the SAM response headers.

Now we have the connection and the address. Pass them to a handler.

.. code-block:: Python

    with controller.create_dest() as our_dest:
        print('Server address: ' + our_dest.base32 + '.b32.i2p')
        # SAM will write to the conn socket
        # when a data stream comes in
        # this line will not block
        conn = our_dest.register_accept()
        # `conn.parse_headers` will block
        # until a message comes in
        # now a message comes in, but first we need to
        # strip the SAM headers
        addr = conn.parse_headers()
        # pass them to a handler
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

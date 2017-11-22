leaflet
=======

Dead simple I2P SAM library. Download now and enjoy Garlic Routing today.

How to use
----------

`Learn how to create identities, connect to a remote destination and accept data streams. <https://github.com/MuxZeroNet/leaflet/blob/master/leaflet/examples/basic.py>`_

How to play
-----------

Make sure you have two terminal windows open.

Script for terminal window #1.

::

    from leaflet.examples import basic
    basic.accept()
    # it will print out its server address

Script for terminal window #2.

::


    from leaflet.examples import basic
    basic.their_b32 = 'PUT THE SERVER ADDRESS HERE' + '.b32.i2p'
    basic.hi_there()


Caveat
------

- Python 3 only. Nobody writes new code in Python 2 in 2017.

- If you like to monkey-patch your modules, then you are on your own.

- Leaflet is based on i2p.socket but it is no longer a drop-in socket module replacement.

- Stream/TCP sockets only at this moment. Support for datagram and raw socket is under construction.

- Could freak out if used with non-blocking sockets. I probably over-engineered the API.

# leaflet
Dead simple I2P SAM library. Download now and enjoy Garlic Routing today.

## How to use

[Learn how to create identities, connect to a remote destination and accept data streams.](leaflet/examples/basic.py)

## An example to play with

Make sure you have two terminal windows open.

Script for terminal window #1.

```python
from leaflet.examples import basic
basic.accept()
# it will print out its server address
```

Script for terminal window #2.

```python
from leaflet.examples import basic
basic.their_b32 = 'PUT THE SERVER ADDRESS HERE' + '.b32.i2p'
basic.hi_there()
```

## Caveat

- Python 3 only. Nobody writes new code in Python 2 in 2017.

- Leaflet is based on `i2p.socket` but it is no longer a drop-in socket module replacement. If you like to monkey-patch your modules, then you are on your own.

- Stream/TCP sockets only at this moment. Support for datagram and raw socket is under construction.

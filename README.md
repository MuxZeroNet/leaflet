# leaflet
Dead simple I2P SAM library. Download now and enjoy Garlic Routing today!

## How to use

[Create identities, connect to a remote destination and accept data streams.](leaflet/examples/basic.py)

[Write a datagram client and a datagran server.](leaflet/examples/datagram.py)

[Class reference](https://leaflet.readthedocs.io/)

## Examples to play with

To run the demo, make sure you have two terminal windows open.

__Hello, how are you?__

Script for terminal window #1.

```bash
python3 -m leaflet.examples.basic server
# it will print out its server address
```

Script for terminal window #2.

```python
python3 -m leaflet.examples.basic client serveraddress.b32.i2p
```

__Nevermind, you probably wouldn't get it.__

Script for terminal window #1

```python
python3 -m leaflet.examples.datagram server
# wait until it prints out its server address
```

Script for terminal window #2:

```python
python3 -m leaflet.examples.datagram client serveraddress.b32.i2p
```

## Caveat

- Python 3 only. Nobody writes new code in Python 2 in 2017.

- Leaflet is based on `i2p.socket` but it is no longer a drop-in socket module replacement. If you like to monkey-patch your modules, then you are on your own.

- No RAW socket support. You aren't gonna need it anyway.

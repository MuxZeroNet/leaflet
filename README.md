# leaflet
Dead simple I2P SAM library. Download now and enjoy Garlic Routing today.

## How to use

[Learn how to create identities, connect to a remote destination and accept data streams.](leaflet/examples/basic.py)

## Examples to play with

To run the demo, make sure you have two terminal windows open.

__Hello, how are you?__

Script for terminal window #1.

```python
from leaflet.examples import basic
basic.accept()
# it will print out its server address
```

Script for terminal window #2.

```python
from leaflet.examples import basic
basic.hi_there('PUT THE SERVER ADDRESS HERE' + '.b32.i2p')
```

__Nevermind, you probably wouldn't get it.__

Script for terminal window #1

```python
from leaflet.examples import datagram
datagram.serve()
# wait until it prints out its server address
```

Script for terminal window #2:

```python
from leaflet.examples import datagram
datagram.hi_there('PUT THE SERVER ADDRESS HERE' + '.b32.i2p')
```

## Caveat

- Python 3 only. Nobody writes new code in Python 2 in 2017.

- Leaflet is based on `i2p.socket` but it is no longer a drop-in socket module replacement. If you like to monkey-patch your modules, then you are on your own.

- No RAW socket support. You aren't gonna need it anyway.

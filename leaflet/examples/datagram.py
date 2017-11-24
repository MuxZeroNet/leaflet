from leaflet import Controller
from socket import timeout as SocketTimeout
from time import sleep
import sys

their_b32 = 'ob2xiidzn52xeicjgjicazlfobzws5dfebqwizdsebugk4tffyxa.b32.i2p'

def hi_there(server_addr = None):
    # test SAM connection
    controller = Controller()
    # create our "IP Address" so we can receive a reply
    # ask SAM to forward incoming datagram to 127.0.0.1:48000
    with controller.create_dest(style='datagram', forward=48000) as our_dest:
        print('Our address is ' + our_dest.base32)
        # bind our datagram socket to 127.0.0.1:48000
        sock = our_dest.bind()
        sock.settimeout(2.0)

        for i in range(100):
            try:
                _send_loop(sock, server_addr or their_b32, i)
            except SocketTimeout:
                pass
            sleep(0.5)

def _send_loop(sock, server_addr, i):
    print('Sending message %d...' % i)
    # send a message to the server
    data = b"Nevermind, you probably wouldn't get it. " + bytes(str(i), 'utf-8')
    sock.transmit(data, server_addr)
    # receive the response
    data, addr = sock.collect()
    print('Received datagram from %r: %r' % (addr, data))


def serve():
    # test SAM connection
    controller = Controller()
    # create our "IP Address" so that people can find us
    # ask SAM to forward incoming datagram to 127.0.0.1:8080
    with controller.create_dest(style='datagram', forward=8080) as our_dest:
        print('Server address: ' + our_dest.base32 + '.b32.i2p')
        # bind our datagram socket to 127.0.0.1 8080
        sock = our_dest.bind()
        while True:
            # receive a message
            data, addr = sock.collect()
            print('Received datagram from %r: %r' % (addr, data))
            # send the response back
            sock.transmit(b'I got ...' + data[-5:], addr)


if __name__ == '__main__':
    help_doc = '\n'.join((
        'Usage:',
        '    python3 -m leaflet.examples.datagram server',
        '    python3 -m leaflet.examples.datagram client <server.b32.i2p>',))
    if len(sys.argv) == 1:
        print(help_doc)
    else:
        action = sys.argv[1]
        if action == 'server':
            serve()
        elif action == 'client':
            hi_there(sys.argv[2])
        else:
            print(help_doc)

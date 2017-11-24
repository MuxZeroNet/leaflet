from leaflet import Controller
import sys


their_b32 = 'ob2xiidzn52xeicjgjicazlfobzws5dfebqwizdsebugk4tffyxa.b32.i2p'


def create_id():
    # connect to SAM
    controller = Controller()

    # create our I2P "IP Address"
    # but it is formally called a "Destination"
    our_dest = controller.create_dest('name_of_my_destination')
    return our_dest
    # when our Destination gets garbage-collected, it is shutdown and unreachable


def hi_there(server_addr = None):
    # connect to SAM
    controller = Controller(sam_api=('127.0.0.1', 7656))
    # create our "IP Address" so that they can reply
    our_dest = controller.create_dest()
    print('Our address: ' + our_dest.base32)
    # perform NS lookup to get their full Destination (optional)
    their_dest = controller.lookup(server_addr or their_b32)
    print('Their full destination: ' + their_dest.base64)

    # connect to their server
    sock = our_dest.connect(their_dest)
    # strip the SAM response headers
    sam_reply = sock.parse_headers()
    # send message and receive the reply
    sock.sendall(b'Hello, there!')
    real_reply = sock.recv(4096)

    print(sam_reply, real_reply)

    # clean up
    sock.close()
    our_dest.close()


def send_and_disappear(server_addr = None):
    # test SAM connection
    controller = Controller()

    # `create_dest` can be used in a `with` statement
    # to create throw-away Destinations
    with controller.create_dest() as our_dest:
        # connect to a remote destination and send our message
        sock = our_dest.connect(server_addr or their_b32)
        # SAM will give us response headers when the connection is successful
        sam_reply = sock.parse_headers()
        # now we can send data
        sock.sendall(b'Hello, there!')
        real_reply = sock.recv(4096)

        print(sam_reply, real_reply)
        sock.close()


def accept():
    # test SAM connection
    controller = Controller()

    # create our "IP Address" so that people can find us
    with controller.create_dest() as our_dest:
        print('Server address: ' + our_dest.base32 + '.b32.i2p')
        while True:
            # SAM will write to the conn socket when a message is available
            # this line will not block
            conn = our_dest.register_accept()
            # `conn.parse_headers` will block until a message comes in
            # now a message comes in, but first we need to strip the SAM headers
            addr = conn.parse_headers()
            _handler(addr, conn)

def _handler(addr, conn):
    # now we can read the real message
    request = conn.recv(4096)
    print('Received a message from %r: %r' % (addr, request))
    # reply
    conn.sendall(b'Hello, how are you?')
    conn.close()



if __name__ == '__main__':
    help_doc = '\n'.join((
        'Usage:',
        '    python3 -m leaflet.examples.basic server',
        '    python3 -m leaflet.examples.basic client <server.b32.i2p>',))
    if len(sys.argv) == 1:
        print(help_doc)
    else:
        action = sys.argv[1]
        if action == 'server':
            accept()
        elif action == 'client':
            hi_there(sys.argv[2])
        else:
            print(help_doc)

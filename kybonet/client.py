import argparse
import json
import zmq
import logging
from .crypto import import_private_key, decrypt
from .input_devices import PseudoEvent, FakeDevice

logger = logging.getLogger(__name__)


def parse_args(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('ip', type=str, help='ip')
    parser.add_argument('-p', '--port', type=int, default=5555, help='port')
    parser.add_argument('-i', '--id-rsa', type=str, default='~/id_rsa',
                        help='rsa private key path')
    parser.add_argument('-sim', '--simulate', action='store_true',
                        help='Simulate, don\'t press/release any key.')
    verbosity = parser.add_mutually_exclusive_group(required=False)
    verbosity.add_argument('-q', '--quiet', action='store_true',
                           help='Reduce output messages.')
    verbosity.add_argument('-v', '--verbose', action='store_true',
                           help='Increment output messages.')
    return parser.parse_args(args)


def main(args=None):
    args = parse_args(args=args)

    if args.quiet:
        logging.basicConfig(level=logging.ERROR)
    elif args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    ip = args.ip
    port = args.port
    id_rsa = args.id_rsa
    simulate = args.simulate
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.connect("tcp://{}:{}".format(ip, port))
    socket.subscribe('')
    logger.debug('running zmq subscriber on {}:{}'.format(ip, port))

    device = FakeDevice(name='my-fake-device')

    with open(id_rsa, 'rb') as f:
        private_key = import_private_key(f.read())

    while True:
        rcv = socket.recv()
        try:
            decrypted = decrypt(message=rcv, private_key=private_key)
        except ValueError:
            txt = 'Unable to decode message... May be it wasn\'t for you?'
            logger.debug(txt)
            continue
        message = decrypted.decode('utf-8')
        decoded_event = json.loads(message)
        event = PseudoEvent(**decoded_event)
        if not simulate:
            device.write_event(event)


if __name__ == '__main__':
    main()

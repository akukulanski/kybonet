import argparse
import json
import zmq
import os
import logging
from .crypto import import_private_key, decrypt
from .input_devices import PseudoEvent, FakeDevice

logger = logging.getLogger(__name__)


def parse_args(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('ip', type=str, help='ip')
    parser.add_argument('-p', '--port', type=int, default=5555, help='port')
    parser.add_argument('-i', '--id-rsa', type=str, default=None,
                        required=True, help='Private key path (generate one '
                        'with kybonet-generate)')
    parser.add_argument('-sim', '--simulate', action='store_true',
                        help='Simulate, don\'t press/release any key.')
    verbosity = parser.add_mutually_exclusive_group(required=False)
    verbosity.add_argument('-q', '--quiet', action='store_true',
                           help='Reduce output messages.')
    verbosity.add_argument('-v', '--verbose', action='store_true',
                           help='Increment output messages.')
    return parser.parse_args(args)


class KybonetClient:
    def __init__(self):
        # zmq
        self._context = None
        self._socket = None

    def connect(self, ip, port):
        self._context = zmq.Context()
        self._socket = self._context.socket(zmq.SUB)
        self._socket.connect("tcp://{}:{}".format(ip, port))
        self._socket.subscribe('')

    def run(self, key, simulate=False):
        device = FakeDevice(name='my-fake-device')
        while True:
            rcv = self._socket.recv()
            try:
                decrypted = decrypt(message=rcv, private_key=key)
            except ValueError:
                txt = 'Unable to decode message... May be it wasn\'t for you?'
                logger.debug(txt)
                continue
            message = decrypted.decode('utf-8')
            decoded_event = json.loads(message)
            event = PseudoEvent(**decoded_event)
            if not simulate:
                device.write_event(event)


def main(args=None):
    args = parse_args(args=args)

    if args.quiet:
        log_level = logging.ERROR
    elif args.verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    if os.getenv('DEBUG', False):
        log_fmt = '%(levelname)s - %(name)s: %(message)s'
    else:
        log_fmt = '%(levelname)s - %(message)s'

    logging.basicConfig(level=log_level, format=log_fmt)

    client = KybonetClient()
    client.connect(ip=args.ip, port=args.port)

    with open(args.id_rsa, 'rb') as f:
        private_key = import_private_key(f.read())

    logger.info('Connected to {}:{}'.format(args.ip, args.port))
    try:
        client.run(key=private_key, simulate=args.simulate)
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()

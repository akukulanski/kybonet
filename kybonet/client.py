import argparse
import json
import zmq
import logging
import os
from crypto import import_private_key, decrypt
from input_devices import PseudoEvent, FakeDevice

if __name__ == '__main__':
    debug = os.getenv('DEBUG', None)
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=level)
    logger = logging.getLogger()
else:
    logger = logging.getLogger(__name__)


def parse_args(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('ip', type=str, help='ip')
    parser.add_argument('-p', '--port', type=int, default=5555, help='port')
    parser.add_argument('-i', '--id-rsa', type=str, default='~/id_rsa',
                        help='rsa private key path')
    parser.add_argument('-sim', '--simulate', action='store_true',
                        help='Simulate, don\'t press/release any key.')
    return parser.parse_args(args)


def main(args=None):
    args = parse_args(args=args)

    ip = args.ip
    port = args.port
    id_rsa = args.id_rsa
    simulate = args.simulate
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.connect("tcp://{}:{}".format(ip, port))
    socket.subscribe('')
    logger.info('running zmq subscriber on {}:{}'.format(ip, port))

    device = FakeDevice(name='my-fake-mouse')

    with open(id_rsa, 'rb') as f:
        private_key = import_private_key(f.read())

    logger.info('key event subscriber is now active')
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

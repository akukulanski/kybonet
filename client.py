import argparse
import keyboard
import json
import zmq
import gnupg
import time
import logging
import os
from keyboard import KeyboardEvent

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
    parser.add_argument('--gpghome', type=str, default='/root/.gnupg/',
                        help='gpg home directory')
    parser.add_argument('--speed', type=float, default=2.0,
                        help='Playback speed')
    parser.add_argument('-sim', '--simulate', action='store_true',
                        help='Simulate, don\'t press/release any key.')
    return parser.parse_args(args)


def main(args=None):
    args = parse_args(args=args)

    ip = args.ip
    port = args.port
    speed = args.speed
    simulate = args.simulate
    context = zmq.Context()         
    socket = context.socket(zmq.SUB)
    socket.connect ("tcp://{}:{}".format(ip, port))
    socket.subscribe('')
    logger.info('running zmq subscriber on {}:{}'.format(ip, port))

    gpg = gnupg.GPG(gnupghome=args.gpghome)
    gpg.encoding = 'utf-8'
    logger.debug('available keys: {}'.format(gpg.list_keys()))

    logger.info('key event subscriber is now active')
    while True:
        rcv = socket.recv_string()
        decrypted = gpg.decrypt(rcv)
        if decrypted.ok:
            message = str(decrypted)
            decoded_events = json.loads(message)
            # logger.info('decoded: {}'.format(decoded_events))  ## TO DO: remove
            if not simulate:
                events = [KeyboardEvent(**event) for event in decoded_events]
                keyboard.play(events, speed_factor=speed)
        else:
            logger.debug('Unable to decode message... ({})'.format(
                                decrypted.stderr))


if __name__ == '__main__':
    main()
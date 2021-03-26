import argparse
import keyboard
import json
import zmq
import time
import logging
import os
from keyboard import KeyboardEvent
from crypto import import_private_key, decrypt
import mouse_dev


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
    parser.add_argument('--speed', type=float, default=2.0,
                        help='Playback speed')
    parser.add_argument('-sim', '--simulate', action='store_true',
                        help='Simulate, don\'t press/release any key.')
    return parser.parse_args(args)


def create_event_from_dict(event_dict):
    keyboard_fields = ['scan_code', 'name', 'event_type', 'time']
    mouse_fields = ['etype', 'code', 'value', 'time']
    for class_, fields in zip([keyboard.KeyboardEvent, mouse_dev.MouseEvent],
                              [keyboard_fields, mouse_fields]):
        fields_present = [f in event_dict for f in fields]
        if all(fields_present):
            return class_(**event_dict)
    return None


def main(args=None):
    args = parse_args(args=args)

    ip = args.ip
    port = args.port
    id_rsa = args.id_rsa
    speed = args.speed
    simulate = args.simulate
    context = zmq.Context()         
    socket = context.socket(zmq.SUB)
    socket.connect ("tcp://{}:{}".format(ip, port))
    socket.subscribe('')
    logger.info('running zmq subscriber on {}:{}'.format(ip, port))

    device = mouse_dev.FakeMouse(name='my-fake-mouse')

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
        event = create_event_from_dict(decoded_event)
        if not simulate:
            if isinstance(event, keyboard.KeyboardEvent):
                # event = KeyboardEvent(**decoded_event)
                keyboard.play([event], speed_factor=speed)
            elif isinstance(event, mouse_dev.MouseEvent):
                device.write_event(event)
            else:
                logger.error('Unknown event type: {}'.format(decoded_event))
                continue


if __name__ == '__main__':
    main()
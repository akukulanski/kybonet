import argparse
import keyboard
import json
import yaml
import zmq
import queue
import time
import logging
import os
from crypto import import_public_key, encrypt


if __name__ == '__main__':
    debug = os.getenv('DEBUG', None)
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=level)
    logger = logging.getLogger()
else:
    logger = logging.getLogger(__name__)


def parse_args(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', type=int, default=5555, help='port')
    parser.add_argument('-c', '--config', type=str, default='./config.yml',
                        help='YML configuration file')
    return parser.parse_args(args)


def load_subscribers(subs):
    """
    Reads the public key of every subscriber and stores it in the field
    'public_key'.
    """
    for s in subs:
        try:
            n = s['name']
            with open(s['key'], 'rb') as f:
                key = import_public_key(f.read())
            s['public_key'] = key
        except Exception as e:
            logger.error(e)
            logger.warning('Error importing key for "{}"'.format(s['name']))
            subs.remove(s)
            continue
        logger.info('Successfully imported key for "{}"'.format(s['name']))


class HookContext:
    """
    Profilactic Context Manager:
    The hook returns a destructor. If you forget to use it and lose the object
    reference, the hook will continue 'hooking' forever.
    """
    def __init__(self, callback):
        self._callback = callback

    def __enter__(self):
        self._h = keyboard.hook(self._callback)
        return self._h

    def __exit__(self, type, value, traceback):
        self._h()


class State:
    """
    Class to track the current state.
    """
    def __init__(self, subscribers):
        self._subscribers = subscribers
        self.current_sub = 0
        self.last_event = None

    def next(self):
        self.current_sub += 1
        self.current_sub %= len(self._subscribers)
        logger.info('Current sub: {} ({})'.format(
                self.current_sub,
                self._subscribers[self.current_sub]['name']))

    def switch(self, sub):
        if sub < len(self._subscribers):
            self.current_sub = sub
            logger.info('Jumped to sub: {} ({})'.format(
                self.current_sub,
                self._subscribers[self.current_sub]['name']))
        else:
            logger.warning('Ignoring invalid sub: {}'.format(sub))


def main(args=None):
    args = parse_args(args=args)

    port = args.port
    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.bind("tcp://*:{}".format(port))
    logger.info('running zmq publisher on port {}'.format(port))
    # socket.bind("tcp://127.0.0.1:{}".format(port))

    with open(args.config, 'r') as f:
        config = yaml.load(f.read(), Loader=yaml.FullLoader)

    fields_to_send = ['scan_code', 'name', 'event_type', 'time']

    subs = config['subscribers']
    load_subscribers(subs)
    assert len(subs), 'No subscribers available'

    state = State(subs)
    ignore_list = []

    # assign hotkeys
    if 'switch_hotkey' in config:
        keyboard.add_hotkey(config['switch_hotkey'], state.next, args=())
        ignore_list.append(config['switch_hotkey'])
        logger.info('Switch key is: {}'.format(config['switch_hotkey']))
    else:
        logger.warning('Ignoring switch key due to missing "switch_hotkey" field in config.')

    for i in range(len(subs)):
        s = subs[i]
        if 'hotkey' in s and s['hotkey']:
            keyboard.add_hotkey(s['hotkey'], state.switch, args=(i,))
            ignore_list.append(s['hotkey'])
            logger.info('Hotkey for {} is {}'.format(s['name'],
                                                     s['hotkey']))

    def is_the_same_event(event_a, event_b):
        if (    event_a['event_type'] == event_b['event_type'] and
                event_a['scan_code'] == event_b['scan_code'] and
                event_a['name'] == event_b['name']):
            return True
        else:
            return False

    def key_event_arrived(event):
        """
        args:
            event   type: keyboard.KeyboardEvent
        """
        if event.name in ignore_list:
            logger.debug('Ignored hotkey event ({}).'.format(event.name))
            return
        event_dict = {k: getattr(event, k) for k in fields_to_send}
        # check if it's the same as the previous one
        if state.last_event and is_the_same_event(event_dict, state.last_event):
            return

        logger.debug('Current subscriber: "{}"'.format(
                            subs[state.current_sub]['name']))

        state.last_event = event_dict
        to_send_str = json.dumps(event_dict)
        encrypted = encrypt(message=to_send_str.encode('utf-8'),
                            public_key=subs[state.current_sub]['public_key'])
        socket.send(encrypted)

    with HookContext(key_event_arrived) as _hook:
        logger.info('Key event publisher is now active.')
        logger.info('Current subscriber: {}'.format(
                            subs[state.current_sub]['name']))
        try:
            while True:
                time.sleep(1e6)
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()

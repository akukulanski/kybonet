import argparse
import keyboard
import json
import yaml
import zmq
import gnupg
import time
import logging
import os


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


def subscriber_str(sub):
    return '{} <{}>'.format(sub['name'], sub['key_id'])


class State:
    """
    Class to track the current state.
    """
    def __init__(self, subscribers):
        self._subscribers = subscribers
        self.current_sub = 0

    def next(self):
        self.current_sub += 1
        self.current_sub %= len(self._subscribers)
        logger.info('Current sub: {} ({})'.format(
                self.current_sub,
                subscriber_str(self._subscribers[self.current_sub])))

    def switch(self, sub):
        if sub < len(self._subscribers):
            self.current_sub = sub
            logger.info('Jumped to sub: {} ({})'.format(
                self.current_sub,
                subscriber_str(self._subscribers[self.current_sub])))
        else:
            logger.warning('Ignoring invalid sub: {}'.format(sub))


_fields_to_send = ['scan_code', 'name', 'event_type', 'time']


def get_key_by_id(keys_list, key_id):
    for k in keys_list:
        for uid in k['uids']:
            if key_id == uid or '<' + key_id + '>' in uid:
                return k
    return None


def remove_invalid_subs(subs, keys_list):
    """
    Checks that key_id is an available key, and deletes the subscriber
    otherwise. Also adds the fingerprint to the subscriber dict.
    """
    for s in subs:
        key_id = s['key_id']
        key = get_key_by_id(keys_list=keys_list, key_id=key_id)
        if not key:
            logger.warning('Key {} not found. Ignoring.'.format(key_id))
            del subs[s]
            continue
        s['fp'] = key['fingerprint']


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

    gpg = gnupg.GPG(gnupghome=config['gnugp_dir'])
    gpg.encoding = 'utf-8'
    keys_list = gpg.list_keys()
    # logger.debug('Available keys: {}'.format(keys_list))

    subs = config['subscribers']

    remove_invalid_subs(subs, keys_list)
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
            logger.info('Hotkey for {} is {}'.format(subscriber_str(s),
                                                     s['hotkey']))

    def send_key_zmq(event):
        """
        send key event over zmq
        args:
            event   type: keyboard._KeyboardEvent
        """
        if event.name in ignore_list:
            logger.debug('Ignored hotkey event ({}).'.format(event.name))
            return
        event_dict = {k: getattr(event, k) for k in _fields_to_send}
        event_text = json.dumps(event_dict)
        logger.debug('Current subscriber: {}'.format(state.current_sub))
        logger.debug('Encrypting for {} (fingerprint: {})'.format(
                            subs[state.current_sub]['key_id'],
                            subs[state.current_sub]['fp']))
        encrypted = gpg.encrypt(event_text, subs[state.current_sub]['fp'],
                                always_trust=True)
        assert encrypted.ok
        logger.debug('Send: {}'.format(str(encrypted)))
        socket.send_string(str(encrypted))

    with HookContext(send_key_zmq) as _h_:
        logger.info('Key event publisher is now active.')
        try:
            keyboard.wait()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()

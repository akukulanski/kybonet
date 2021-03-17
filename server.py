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


_fields_to_send = ['scan_code', 'name', 'event_type', 'time']


def get_key_by_id(keys_list, key_id):
    for k in keys_list:
        for uid in k['uids']:
            if key_id == uid or '<' + key_id + '>' in uid:
                return k
    return None


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

    subs = config['subscribers']
    n_subs = len(subs)
    current_sub = 0

    gpg = gnupg.GPG(gnupghome=config['gnugp_dir'])
    gpg.encoding = 'utf-8'
    keys_list = gpg.list_keys()
    logger.debug('Available keys: {}'.format(keys_list))

    # check key_id exist and add field fingerprint tp have easier access later.
    for s in subs:
        key_id = s['key_id']
        key = get_key_by_id(keys_list=keys_list, key_id=key_id)
        if not key:
            logger.warning('Key {} not found'.format(key_id))
            del subs[s]
            continue
        s['fp'] = key['fingerprint']

    assert len(subs), 'No subscribers available'

    def send_key_zmq(event):
        """
        send key event over zmq
        args:
            event   type: keyboard._KeyboardEvent
        """
        logger.debug(event)
        event_dict = {k: getattr(event, k) for k in _fields_to_send}
        event_text = json.dumps(event_dict)
        logger.debug('Current subscriber: {}'.format(current_sub))
        logger.debug('Encrypting for {} (fingerprint: {})'.format(
                            subs[current_sub]['key_id'],
                            subs[current_sub]['fp']))
        encrypted = gpg.encrypt(event_text, subs[current_sub]['fp'],
                                always_trust=True)
        assert encrypted.ok
        logger.debug('Send: {}'.format(str(encrypted)))
        socket.send_string(str(encrypted))

    with HookContext(send_key_zmq) as _h_:
        logger.info('key event publisher is now active')
        try:
            keyboard.wait()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()

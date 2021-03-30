import argparse
import json
import yaml
import zmq
import logging
import shutil
import sys
import os
from collections import defaultdict
from selectors import DefaultSelector, EVENT_READ
import kybonet
from .input_devices import find_devices, RelativeMovement, PseudoEvent, \
                           is_mouse, keycode_from_str
from .crypto import import_public_key, encrypt


logger = logging.getLogger(__name__)


class DeviceNotFound(Exception):
    pass


class UnknownHotkey(Exception):
    pass


def parse_args(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', type=int, default=5555, help='Port.')
    parser.add_argument('-c', '--config', type=str,
                        default=None,
                        help='YML configuration file.')
    verbosity = parser.add_mutually_exclusive_group(required=False)
    verbosity.add_argument('-q', '--quiet', action='store_true',
                           help='Reduce output messages.')
    verbosity.add_argument('-v', '--verbose', action='store_true',
                           help='Increment output messages.')
    return parser.parse_args(args)


class KybonetServer:

    def __init__(self):
        # zmq
        self._context = None
        self._socket = None
        # subs
        self._subs = []
        # devices
        self._devices_connected = []
        self._devices = []
        # hotkeys
        self._hotkeys = self._empty_hotkeys()
        # run
        self._selector = DefaultSelector()
        # state
        self._current_idx = 0
        self._pressed_keys = defaultdict(lambda: False)
        self._grabbed = False

    @property
    def subs(self):
        return self._subs

    @property
    def devices(self):
        return self._devices

    def connect(self, port):
        self._context = zmq.Context()
        self._socket = self._context.socket(zmq.PUB)
        self._socket.bind("tcp://*:{}".format(port))

    def add_subscriber(self, name, id_file=None, hotkey=None):
        new_sub = {'name': name, 'public_key': None, 'is_local': False,
                   'hotkey': None}
        if id_file is not None:
            with open(id_file, 'rb') as f:
                key = import_public_key(f.read())
            new_sub['public_key'] = key
            new_sub['is_local'] = False
        else:
            new_sub['is_local'] = True
        if hotkey:
            new_sub['hotkey'] = hotkey
            k = 'switch_' + name
            self._hotkeys[k] = {'key': keycode_from_str(hotkey),
                                'callback': self.switch,
                                'args': (len(self._subs),)}
        self._subs.append(new_sub)
        logger.debug('Client added: {}.'.format(name))

    def scan_devices(self):
        self._devices_connected = find_devices()

    def add_device(self, name):
        for d in self._devices_connected:
            if name == d.name:
                self._devices.append(d)
                logger.debug('Found device "{}"'.format(name))
                return
        raise DeviceNotFound('Device "{}" not present.'.format(name))

    def _empty_hotkeys(self):
        return {'switch': {'key': None,
                           'callback': self.next,
                           'args': ()},
                'exit': {'key': None,
                         'callback': self.exit_program,
                         'args': ('Exit key pressed',)},}

    def assign_hotkey(self, name, key):
        assert name in self._hotkeys, 'Unknown hotkey: "{}"'.format(name)
        if isinstance(key, int):
            keycode = key
        elif isinstance(key, str):
            keycode = keycode_from_str(key)
        assert isinstance(keycode, int), 'Invalid key: "{}"'.format(key)
        self._hotkeys[name]['key'] = keycode

    def teardown(self):
        logger.debug('Teardown')
        for k, pressed in self._pressed_keys.items():
            if pressed:
                new_event = PseudoEvent.KeyRelease(k)
                self.send_event(new_event)
        self.ungrab_all()
        for d in self._devices:
            self._selector.unregister(d)
        self._selector.close()

    def exit_program(self, reason='-'):
        self.teardown()
        logger.info('Exit')
        os._exit(0)

    def next(self):
        next_idx = (self._current_idx + 1) % len(self._subs)
        self.switch(next_idx)

    def switch(self, idx):
        if idx < len(self._subs):
            self._current_idx = idx
            if self.current_sub['is_local']:
                self.ungrab_all()
            else:
                self.grab_all()
            logger.info('Current sub: {} ({})'.format(
                self.current_sub['name'], self._current_idx,))
        else:
            logger.warning('Ignoring invalid sub: {}'.format(idx))

    @property
    def current_sub(self):
        return self._subs[self._current_idx]

    def grab_all(self):
        if self._grabbed:
            return
        self._grabbed = True
        for d in self._devices:
            d.grab()

    def ungrab_all(self):
        if not self._grabbed:
            return
        self._grabbed = False
        for d in self._devices:
            d.ungrab()

    def merge_events(self, events):
        merged_events = []
        rel_movement = RelativeMovement()
        for e in events:
            if e.is_rel_movement():
                x, y, wheel = e.get_rel_movement()
                if rel_movement.is_mergeable(x, y, wheel):
                    rel_movement.merge(x, y, wheel)
                else:
                    merged_events += rel_movement.generate_events()
                    rel_movement.set(x, y, wheel)
            else:
                merged_events += rel_movement.generate_events()
                rel_movement.set(0, 0, 0)
                merged_events.append(e)
        merged_events += rel_movement.generate_events()
        rel_movement.set(0, 0, 0)
        return merged_events

    def event_is_hotkey(self, event):
        for name, hotkey in self._hotkeys.items():
            if hotkey['key'] == event.code:
                return True
        return False

    def run_hotkey_callback(self, event):
        for name, hotkey in self._hotkeys.items():
            # key, callback, args
            if hotkey['key'] == event.code:
                hotkey['callback'](*hotkey['args'])
                return
        raise UnknownHotkey('Key code {} is not a valid hotkey'.format(
                                                                event.ecode))

    def parse_events(self, device, events):
        events = [PseudoEvent.from_event(e) for e in events]
        if is_mouse(device):
            events = [e for e in events if e.is_valid_mouse_event()]
            events = self.merge_events(events)
        else:
            events = [e for e in events if e.is_valid_keyboard_event()]
            events = [e for e in events if (
                        not(e.is_key_pressed() and self.event_is_hotkey(e)))]
        for event in events:
            if self.event_is_hotkey(event) and event.is_key_released():
                logger.debug('Hotkey detected ({})'.format(event.code))
                for k, pressed in self._pressed_keys.items():
                    if pressed:
                        new_event = PseudoEvent.KeyRelease(k)
                        self._send_event(new_event)
                self.run_hotkey_callback(event)
            else:
                self._send_event(event)
        return

    def _send_event(self, event):
        if self.current_sub['is_local']:
            logger.debug('Local user, nothing done...')
            return

        if event.is_key_pressed() and self._pressed_keys[event.code]:
            return

        if event.is_key_pressed():
            self._pressed_keys[event.code] = True
        elif event.is_key_released():
            self._pressed_keys[event.code] = False

        fields = ['etype', 'code', 'value', 'time']
        event_dict = {k: getattr(event, k) for k in fields}
        to_send_str = json.dumps(event_dict)
        encrypted = encrypt(message=to_send_str.encode('utf-8'),
                            public_key=self.current_sub['public_key'])
        self._socket.send(encrypted)

    def run(self):
        for d in self._devices:
            self._selector.register(d, EVENT_READ)

        self.switch(idx=0)
        try:
            while True:
                for key, mask in self._selector.select():
                    device = key.fileobj
                    events = list(device.read())
                    self.parse_events(device, events)
        except KeyboardInterrupt:
            pass


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

    if args.config:
        config_file = args.config
    else:
        logger.info('Config file not specified. Using default.')
        config_file = os.path.expanduser("~") + '/.local/kybonet/config.yml'
        dir_name = os.path.dirname(config_file)
        if not os.path.isdir(dir_name):
            os.makedirs(dir_name)
        if not os.path.isfile(config_file):
            default_config_file = kybonet.__path__[0] + '/config.yml'
            shutil.copyfile(default_config_file, config_file)
    assert os.path.isfile(config_file), 'File not found: {}'.format(config_file)
    logger.info('Loading config file: {}'.format(config_file))
    with open(config_file, 'r') as f:
        config = yaml.load(f.read(), Loader=yaml.FullLoader)

    server = KybonetServer()
    server.connect(port=args.port)

    for s in config['subscribers']:
        server.add_subscriber(**s)

    if len(server.subs) == 0:
        logger.error('No subscribers available')
        sys.exit(1)

    server.scan_devices()
    for d in config['devices']:
        try:
            server.add_device(d)
        except DeviceNotFound as e:
            logger.warning(e)

    if len(server.devices) == 0:
        logger.error('No devices available')
        sys.exit(1)

    for name, key in config['hotkeys'].items():
        if key:
            server.assign_hotkey(name, key)

    logger.info('Kybonet server running on port {}'.format(args.port))
    server.run()


if __name__ == '__main__':
    main()

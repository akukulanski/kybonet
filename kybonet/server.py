import argparse
import json
import yaml
import zmq
import logging
import os
from collections import defaultdict
from selectors import DefaultSelector, EVENT_READ
import kybonet
from .input_devices import find_devices, RelativeMovement, PseudoEvent, \
                           is_mouse, keycode_from_str
from .crypto import import_public_key, encrypt


logger = logging.getLogger(__name__)


def parse_args(args=None):
    default_config_file = kybonet.__path__[0] + '/config.yml'
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', type=int, default=5555, help='port')
    parser.add_argument('-c', '--config', type=str,
                        default=default_config_file,
                        help='YML configuration file')
    return parser.parse_args(args)


def load_subscribers(subs):
    """
    Reads the public key of every subscriber and stores it in the field
    'public_key'.
    """
    loaded_subs = []
    for s in subs:
        if 'key' not in s or not s['key']:
            s['public_key'] = None
            s['is_local'] = True
            loaded_subs.append(s)
            logger.info('Client with no key: local usage of the devices')
        else:
            try:
                with open(s['key'], 'rb') as f:
                    key = import_public_key(f.read())
                s['public_key'] = key
                s['is_local'] = False
                loaded_subs.append(s)
                logger.info('Successfully imported key for "{}"'.format(s['name']))
            except Exception as e:
                logger.error(e)
                logger.warning('Error importing key for "{}"'.format(s['name']))
    return loaded_subs


class State:
    """
    Class to track the current state.
    """
    def __init__(self, subscribers, devices):
        self._subscribers = subscribers
        self.current_idx = 0
        self.last_event = None
        self.pressed_keys = defaultdict(lambda: False)
        self.devices = devices
        self.grabbed = False
        self.switch(idx=0)

    def next(self):
        next_idx = (self.current_idx + 1) % len(self._subscribers)
        self.switch(next_idx)

    def switch(self, idx):
        if idx < len(self._subscribers):
            self.current_idx = idx
            if self.current_sub['is_local']:
                self.ungrab_all()
            else:
                self.grab_all()
            logger.info('Jumped to sub: {} ({})'.format(
                self.current_idx,
                self.current_sub['name']))
        else:
            logger.warning('Ignoring invalid sub: {}'.format(idx))

    @property
    def current_sub(self):
        return self._subscribers[self.current_idx]

    def grab_all(self):
        if self.grabbed:
            return
        logger.debug('grab()')
        self.grabbed = True
        for d in self.devices:
            d.grab()

    def ungrab_all(self):
        if not self.grabbed:
            return
        logger.debug('ungrab()')
        self.grabbed = False
        for d in self.devices:
            d.ungrab()

    def __del__(self):
        self.ungrab_all()


def main(args=None):
    debug = os.getenv('DEBUG', None)
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=level)
    logger = logging.getLogger()

    args = parse_args(args=args)
    port = args.port
    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.bind("tcp://*:{}".format(port))
    logger.info('running zmq publisher on port {}'.format(port))

    with open(args.config, 'r') as f:
        config = yaml.load(f.read(), Loader=yaml.FullLoader)

    subs = config['subscribers']
    subs = load_subscribers(subs)
    assert len(subs), 'No subscribers available'

    devices = []
    for d in find_devices():
        if d.name in config['devices']:
            logger.info('Found device: {}'.format(d.name))
            devices.append(d)
            d.read()
    assert len(devices), 'No devices found'
    selector = DefaultSelector()
    for d in devices:
        selector.register(d, EVENT_READ)

    state = State(subs, devices=devices)
    hotkeys = []

    def add_hotkey(key, callback, args):
        if isinstance(key, int):
            keycode = key
        elif isinstance(key, str):
            keycode = keycode_from_str(key)
        assert isinstance(keycode, int), 'Invalid key: "{}"'.format(key)
        new_hotkey = (keycode, callback, args)
        hotkeys.append(new_hotkey)
        return new_hotkey

    def exit_program(reason='-'):
        logger.info('Exit ({})'.format(reason))
        for k, pressed in state.pressed_keys.items():
            if pressed:
                new_event = PseudoEvent.KeyRelease(k)
                send_event(new_event)
        state.ungrab_all()
        for d in devices:
            selector.unregister(d)
        exit(0)

    # assign hotkeys
    _hotkeys_config = [
        ('switch_hotkey', state.next, ()),
        ('exit_hotkey', exit_program, ('Exit key pressed',)),
    ]

    _hotkeys_to_assign = []

    for name, callback, args in _hotkeys_config:
        if name in config and config[name]:
            _hotkeys_to_assign.append((config[name], callback, args))
        else:
            logger.warning('No key assigned for "{}"'.format(name))

    for i in range(len(subs)):
        s = subs[i]
        if 'hotkey' in s and s['hotkey']:
            _hotkeys_to_assign.append((s['hotkey'], state.switch, (i,)))

    for key, callback, args in _hotkeys_to_assign:
        try:
            add_hotkey(key=key, callback=callback, args=args)
        except AssertionError as e:
            logger.error(e)
            exit_program(reason=str(e))
        fmt = 'Key assigned for "{}": "{}"'
        logger.info(fmt.format(config[name], config[name]))

    def merge_events(events):
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

    def matches_hotkey(event):
        for key, _, __ in hotkeys:
            if key == event.code:
                return True
        return False

    def is_hotkey_down(event):
        return event.is_key_pressed() and matches_hotkey(event)

    def is_hotkey_up(event):
        return event.is_key_released() and matches_hotkey(event)

    def remove_hostkey_press(events):
        return [e for e in events if not(is_hotkey_down(e))]

    def run_hotkey_callback(event):
        for key, callback, args in hotkeys:
            if key == event.code:
                callback(*args)
                return
        keys = [h[0] for h in hotkeys]
        logger.warning('Key {} not found in hotkeys {}'.format(key, keys))

    def parse_events(device, events):
        events = [PseudoEvent.from_event(e) for e in events]
        if is_mouse(device):
            events = [e for e in events if e.is_valid_mouse_event()]
            events = merge_events(events)
        else:
            events = [e for e in events if e.is_valid_keyboard_event()]
            events = remove_hostkey_press(events)
        for event in events:
            if is_hotkey_up(event):
                logger.debug('Hotkey detected ({}).'.format(event.code))
                for k, pressed in state.pressed_keys.items():
                    if pressed:
                        new_event = PseudoEvent.KeyRelease(k)
                        send_event(new_event)
                run_hotkey_callback(event)
            else:
                send_event(event)
        return

    def send_event(event):
        if state.current_sub['is_local']:
            logger.debug('Local user, nothing done.')
            return

        if event.is_key_pressed() and state.pressed_keys[event.code]:
            return

        if event.is_key_pressed():
            state.pressed_keys[event.code] = True
        elif event.is_key_released():
            state.pressed_keys[event.code] = False

        fields = ['etype', 'code', 'value', 'time']
        event_dict = {k: getattr(event, k) for k in fields}
        to_send_str = json.dumps(event_dict)
        encrypted = encrypt(message=to_send_str.encode('utf-8'),
                            public_key=state.current_sub['public_key'])
        socket.send(encrypted)

    logger.info('Key event publisher is now active.')
    logger.info('Current subscriber: {}'.format(state.current_sub['name']))

    try:
        while True:
            for key, mask in selector.select():
                device = key.fileobj
                events = list(device.read())
                parse_events(device, events)
    except KeyboardInterrupt:
        pass

    state.ungrab_all()


if __name__ == '__main__':
    main()

import evdev
import time
from evdev import UInput, ecodes

_ev_key_codes = {ecodes.BTN_MOUSE: 'left',
                 ecodes.BTN_RIGHT: 'right',
                 ecodes.BTN_MIDDLE: 'middle',
                 ecodes.BTN_SIDE: 'side',
                 ecodes.BTN_EXTRA: 'extra'}

_ev_key_types = {0: 'up',
                 1: 'down'}

_ev_rel_codes = {ecodes.REL_X: 'deltaX',
                 ecodes.REL_Y: 'deltaY',
                 ecodes.REL_WHEEL: 'deltaWheel'}


class MouseEvent:
    def __init__(self, etype, code, value, time):
        self.etype = etype
        self.code = code
        self.value = value
        self.time = time

    @classmethod
    def from_event(cls, event):
        return cls(event.type, event.code, event.value, time.time())

    def is_valid(self):
        if self.etype == ecodes.EV_REL:
            if self.code in _ev_rel_codes:
                return True
        if self.etype == ecodes.EV_KEY:
            if (self.code in _ev_key_codes and self.value in _ev_key_types):
                return True
        return False

    def __str__(self):
        if self.etype == ecodes.EV_REL:
            fmt = 'MouseRelative(x={}, y={}, wheel={}, time={})'
            x, y, wheel = self.get_rel_movement()
            return fmt.format(x, y, wheel, self.time)
        elif self.etype == ecodes.EV_KEY:
            fmt = 'MouseKey(button="{}", action="{}", time={})'
            button = _ev_key_codes[self.code]
            action = _ev_key_types[self.value]
            return fmt.format(button, action, self.time)
        return 'MouseUnknown()'

    def is_rel_movement(self):
        return self.etype == ecodes.EV_REL

    def get_rel_movement(self):
        if self.etype == ecodes.EV_REL:
            x = self.value if self.code == ecodes.REL_X else 0
            y = self.value if self.code == ecodes.REL_Y else 0
            wheel = self.value if self.code == ecodes.REL_WHEEL else 0
        else:
            x, y, wheel = (0, 0, 0)
        return (x, y, wheel)


class RelativeMovement:
    def __init__(self):
        self.x = 0
        self.y = 0
        self.wheel = 0
        self.time = time.time()

    def set(self, x, y, wheel):
        self.x = x
        self.y = y
        self.wheel = wheel
        self.time = time.time()

    def is_mergeable(self, x, y, wheel):
        # a new relative movement can be merged if there is no change in any
        # of the directions.
        # (a * b) is less than 0 if the signs of (a) and (b) differ.
        if x * self.x < 0 or y * self.y < 0 or wheel * self.wheel < 0:
            return False
        else:
            return True

    def merge(self, x, y, wheel):
        self.x += x
        self.y += y
        self.wheel += wheel

    def generate_events(self):
        events = []
        if self.x != 0:
            events.append(MouseEvent(etype=ecodes.EV_REL, code=ecodes.REL_X,
                                     value=self.x, time=self.time))
        if self.y != 0:
            events.append(MouseEvent(etype=ecodes.EV_REL, code=ecodes.REL_Y,
                                     value=self.y, time=self.time))
        if self.wheel != 0:
            events.append(MouseEvent(etype=ecodes.EV_REL, code=ecodes.REL_WHEEL,
                                     value=self.wheel, time=self.time))
        return events


class FakeMouse:
    _cap = {ecodes.EV_KEY: [*_ev_key_codes.keys()],
            ecodes.EV_REL: [*_ev_rel_codes.keys()]}

    def __init__(self, name, version=0x1):
        self.name = name
        self.ui = UInput(self._cap, name=name, version=version)

    def write(self, etype, code, value):
        self.ui.write(etype, code, value)
        self.ui.syn()

    def write_event(self, event):
        self.write(event.etype, event.code, event.value)


def _is_mouse(device):
    c = device.capabilities()
    if ecodes.EV_KEY in c:
        if ecodes.BTN_MOUSE in c[ecodes.EV_KEY]:
            return True
    return False


def find_devices():
    _devices = [evdev.InputDevice(fn) for fn in evdev.list_devices()]
    _mouses = [d for d in _devices if _is_mouse(d)]
    return _mouses

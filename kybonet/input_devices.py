import evdev
import time
from evdev import UInput, ecodes

_ev_key_codes = {ecodes.BTN_MOUSE: 'left',
                 ecodes.BTN_RIGHT: 'right',
                 ecodes.BTN_MIDDLE: 'middle',
                 ecodes.BTN_SIDE: 'side',
                 ecodes.BTN_EXTRA: 'extra'}

_ev_key_values = {0: 'up',
                  1: 'down'}

_ev_rel_codes = {ecodes.REL_X: 'deltaX',
                 ecodes.REL_Y: 'deltaY',
                 ecodes.REL_WHEEL: 'deltaWheel'}


class PseudoEvent:
    def __init__(self, etype, code, value, time):
        self.etype = etype
        self.code = code
        self.value = value
        self.time = time

    @classmethod
    def from_event(cls, event):
        return cls(event.type, event.code, event.value, time.time())

    @classmethod
    def KeyPress(cls, code):
        return cls(etype=ecodes.EV_KEY, code=code, value=1, time=time.time())

    @classmethod
    def KeyRelease(cls, code):
        return cls(etype=ecodes.EV_KEY, code=code, value=0, time=time.time())

    @property
    def type(self):
        return self.etype

    def is_valid_mouse_event(self):
        if self.etype == ecodes.EV_REL:
            if self.code in _ev_rel_codes:
                return True
        if self.etype == ecodes.EV_KEY:
            if (self.code in _ev_key_codes and self.value in _ev_key_values):
                return True
        return False

    def is_valid_keyboard_event(self):
        if self.is_valid_mouse_event():
            return False
        return self.is_key_pressed() or self.is_key_released()

    def is_key_pressed(self):
        if self.etype != ecodes.EV_KEY:
            return False
        if self.value != 1:
            return False
        return True

    def is_key_released(self):
        if self.etype != ecodes.EV_KEY:
            return False
        if self.value != 0:
            return False
        return True

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

    def __str__(self):
        try:
            if self.is_valid_mouse_event():
                if self.is_rel_movement():
                    fmt = 'MouseMove(x={}, y={}, wheel={}, time={})'
                    x, y, wheel = self.get_rel_movement()
                    return fmt.format(x, y, wheel, self.time)
                elif self.etype == ecodes.EV_KEY:
                    fmt = 'MouseButton(button="{}", action="{}", time={})'
                    button = _ev_key_codes[self.code]
                    action = _ev_key_values[self.value]
                    return fmt.format(button, action, self.time)
        except KeyError:
            pass
        fmt = 'Event(type={}, code={}, value={})'
        return fmt.format(self.etype, self.code, self.value)


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
            events.append(PseudoEvent(etype=ecodes.EV_REL, code=ecodes.REL_X,
                                      value=self.x, time=self.time))
        if self.y != 0:
            events.append(PseudoEvent(etype=ecodes.EV_REL, code=ecodes.REL_Y,
                                      value=self.y, time=self.time))
        if self.wheel != 0:
            events.append(PseudoEvent(etype=ecodes.EV_REL,
                                      code=ecodes.REL_WHEEL, value=self.wheel,
                                      time=self.time))
        return events


class FakeDevice:
    _cap = {ecodes.EV_KEY: [*ecodes.keys.keys()],
            ecodes.EV_REL: [ecodes.REL_X, ecodes.REL_Y, ecodes.REL_WHEEL]}

    def __init__(self, name, version=0x1):
        self.name = name
        self.ui = UInput(self._cap, name=name, version=version)

    def write(self, etype, code, value):
        self.ui.write(etype, code, value)
        self.ui.syn()

    def write_event(self, event):
        self.write(event.etype, event.code, event.value)


def is_mouse(device):
    c = device.capabilities()
    if ecodes.EV_KEY in c:
        if ecodes.BTN_MOUSE in c[ecodes.EV_KEY]:
            return True
    return False


def is_keyboard(device):
    c = device.capabilities()
    if ecodes.EV_KEY in c:
        if ecodes.KEY_A in c[ecodes.EV_KEY]:
            return True
    return False


def find_devices():
    devices = [evdev.InputDevice(fn) for fn in evdev.list_devices()]
    devices = [d for d in devices if is_mouse(d) or is_keyboard(d)]
    return devices


def keycode_from_str(key_str):
    attr = 'KEY_' + key_str.upper()
    if hasattr(ecodes, attr):
        return getattr(ecodes, attr)
    else:
        return None


def main():
    devices = find_devices()
    print('Found {} devices.'.format(len(devices)))
    for d in devices:
        print('Device: "{}"'.format(d.name))


if __name__ == '__main__':
    main()

# Kybonet - software KM switch with encryption!

### Description


Share your keyboard and mouse connected to a computer over the network!

This tool allows to share your input devices with many computers in the same
network (one at a time). You can switch from one computer to the next one
with a configurable hotkey (by default *F7*).

*How does it work?*

The host computer (the one with the keyboard/mouse) runs the server, and every
computer where you want to use that keyboard run the client.

To keep things easy, there is no point-to-point connection here, but a zmq
publish/subscribe scheme. The server'll publish the keyboard events encrypted
with the public key of the selected client, so only that client'll be able to
decode them. When pressing the hotkey, the server'll start using the public key
of the 2nd client to encrypt the events. Now only the 2nd client'll be able to
decode them.


### Setup the client

* 0. (optional) Create a venv.

```bash
python3 -m venv venv
. venv/bin/activate
```

* 1. Install the required packages.

```bash
pip install kybonet
```

* 2. Generate public/private keys pair (one in each client).

```bash
# generate
kybonet-keygen
# Copy public key to the server
scp <public-key.pub> <user>@<server>:<path>/
```

* 3. Run.

```bash
kybonet-client <server-ip> -p <port> -i <private-key>
```


### Setup the server

* 0. (optional) Create a venv.

```bash
python3 -m venv venv
. venv/bin/activate
```

* 1. Install the required packages.

```bash
pip install kybonet
```

* 2. List the available devices and identify the ones you want to be shared:

```bash
kybonet-devices
```

**Note:** It's likely that you need to add your user to the *input* group in
order to have access to the input devies. Check that with `ls -las /dev/input`
and add it with `usermod -aG <group> <user>`. **You'll have to login again so
the change take effect.**

* 3. Open the default config file or get a copy of it
(*~/.local/kybonet/config.yml*). Add as many clients as you want, with at
least a name and the path to their public key (the hotkey field is optional).
In case you don't like the default values, you can also assign the hotkeys you
want to switch between clients and to exit the program.

* 4. Run.

```bash
kybonet-server -p <PORT> -c <config-file>
```

**Note:** If the config-file is ommited, it'll be loaded from
*~/.local/kybonet/config.yml*. If you want a fresh start, remove it and when
you run `kybonet-server` a new one'll be created.

### Info

Please report any issues [here](https://github.com/akukulanski/kybonet/issues).

Start typing, and have fun!

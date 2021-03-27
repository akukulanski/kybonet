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


### Setup

0. (optional) Create a venv.

```bash
python3 -m venv venv
. venv/bin/activate
```

1. Install the required packages in both the server and the clients.

```bash
git clone https://github.com/akukulanski/kybonet.git
python3 -m pip install ./kybonet
```

2. Generate public/private keys pair (one in each client).

```bash
# generate
kybonet-keygen
# Copy public key to the server
scp <filename.pub> <user>@<host>:<path>/
```

3. In the server side, add the path of every client's public key in a config
file like [this example](./kybonet/config.yml).

4. In the server side, check the permissions of the input devices with
`ls -las /dev/input` and if necessary add your user to the corresponding group
(`usermod -aG <group> <user>`).

5. Check the available devices in the server with `kybonet-devices`. Add the
ones you want to capture to the list of devices in the config file.


### Run

1. Run the server in the computer with the keyboard/mouse.

```bash
kybonet-server -p <PORT> -c <config-file>
```

2. Run the clients in the other computers.

```bash
kybonet-client <SERVER-IP> -p <PORT> -i <PATH_PRIVATE_KEY>
```


3. Start typing!

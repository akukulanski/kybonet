# Kybonet - software KVM switch with encryption!

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

1. Install the required packages in both the server and the clients.

```bash
apt install python3 python3-pip
python3 -m pip install -r requirements.txt
```

2. Generate public/private keys pair.

```bash
# generate
python3 crypto.py
# Copy public key to the server
scp <filename.pub> <user>@<host>:<path>/
```

3. In the server side, add the path of every client's public key in the config
file *config.yml*:

Example of *config.yml*:
```yaml
subscribers:
  - name: 'client-1'
    key: '/root/id_client1.pub'
    hotkey: False
  - name: 'client-2'
    key: '/root/id_client2.pub'
    hotkey: 'f8'
switch_hotkey: 'f7'
```

### Run

**NOTE:** The *keyboard* package used by this tool requires root privileges to
capture the keyboard. It makes sense, since this is esencially a keylogger.
Nevertheless, always take a look at the code before running random code from
github! I take no responsibility for any damage it can cause... `/(·_·)\`

**Tip:** To avoid duplicating every Python package for the *root* user, just set
the PYTHONPATH acordingly. For example, if you have python3.7, you'll probably
have the packages installed in `/home/<YOUR-USER>/.local/lib/python3.7/site-packages/`.
If you are using a virtual env, even better!

* Run the server in the computer with the keyboard.

```bash
sudo su -c "PYTHONPATH=path/to/python/packages python3 server.py -p <PORT>"
```

* Run the clients in the other computers.

```bash
sudo su -c "PYTHONPATH=path/to/python/packages python3 client.py <SERVER-IP> -p <PORT> -i <PATH_PRIVATE_KEY>"
```

5. Start typing!

**NOTE:** since this'll run with root, it's better to create the keys also
with root so the private key is not visible to less privileged users.

**NOTE:** To increment the verbosity set the env `DEBUG`.

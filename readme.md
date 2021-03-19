# keyboard over network (with encryption!)

### Description

This tool allows to share a keyboard connected to a computer with many clients
(one at a time) over the network. You can switch from one computer to the next
one with a configurable hotkey (by default *F7*).

How does it work?

The host computer (the one with the keyboard) runs the server, and every
computer where you want to use that keyboard run the client.

To keep things easy, there is no point-to-point connection here, but a zmq
publish/subscribe scheme. The server'll publish the keyboard events encrypted
with the public key of the selected client, so only that client'll be able to
decode them.

When pressing the hotkey, the server'll start using the public key of the 2nd
client to encrypt the events. Now only the 2nd client'll be able to decode
them.


### Setup

1. Install the required packages (all python packages installable with pip
   except for *GPG*).

2. set-up the gpg keys.

3. run the server in the computer with the keyboard.

4. run the clients in the other computers.

5. start typing

**NOTE:** The *keyboard* package used by this tool requires root privileges to
capture the keyboard. It makes sense, since this is esencially a keylogger.
Nevertheless, always take a look at the code before running random code from
github! I take no responsibility for any damage it can cause...

### Requirements

* python3
* python3-pip
* gpg
* python packages listed in *requirements.txt*

Install requirements:
```
apt install python3 python3-pip gpg
python3 -m pip install -r requirements.txt
```

### Generate keys for encryption

(**NOTE:** all with root, since it's already required for capturing the
keyboard input)

In the client side: 

* Log in as root:
```bash
sudo su
```

* Generate public/private keys pair: (no passphrase)
```bash
gpg --full-generate-key
```

* Export the public key:
```bash
gpg --export --armor --output <filename>.pub
```

* Copy the public key in the server:
```bash
scp <filename.pub> <user>@<host>:<path>/
```

In the server side:

* Log in as root:
```bash
sudo su
```

* Import the generated public key:
```bash
gpg --import <path>/<filename.pub>
```

* Add the key to the config file (`config.yml`) including the key *ID* and a
name. Also a hotkey can be assigned to switch the keyboard to that client.
Example config file with two keys:
```yaml
subscribers:
  - name: 'a-meaningful-name'
    key_id: 'one@email.com'  # the same one used to generate the key!
    hotkey: False
  - name: 'another-meaningful-name'
    key_id: 'another@email.com'  # the same one used to generate the key!
    hotkey: 'f8'
gnugp_dir: '/root/.gnupg/'
switch_hotkey: 'f7'
```

### Misc

* about PATHs...

To avoid duplicating every Python package for the *root* user, just set
the PYTHONPATH acordingly. For example, if you have python3.7, probably you'll
have the packages installed in `/home/<YOUR-USER>/.local/lib/python3.7/site-packages/`.
So you can ran:

server:
```bash
sudo su -c "PYTHONPATH=/home/<YOUR-USER>/.local/lib/python3.7/site-packages/ python3 server.py -p <PORT>"
```

client:
```bash
sudo su -c "PYTHONPATH=/home/<YOUR-USER>/.local/lib/python3.9/site-packages/ DEBUG=1 python3 client.py <SERVER-IP> -p <PORT>"
```

* Debug: To increment the verbosity set the env `DEBUG`.
# keyboard over network (with encryption!)

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
* Log in as root: `sudo su`
* Generate public/private keys pair: `gpg --full-generate-key` (no passphrase).
* Export the public key: `gpg --export --armor --output <filename>.pub`.
* Copy the public key in the server: `scp <filename.pub> <user>@<host>:<path>/`.

In the server side:
* Log in as root: `sudo su`
* Import the generated public key: `gpg --import <path>/<filename.pub>`.
* Add the key to the config file (`config.yml`) including the key *ID* and a name.
Example config file with two keys:
```yaml
subscribers:
  - name: 'a-meaningful-name'
    key_id: 'one@email.com'  # the same one used to generate the key!
  - name: 'another-meaningful-name'
    key_id: 'another@email.com'  # the same one used to generate the key!
```

### Tip about PATHs...

To avoid duplicating every Python package for the *root* user, just set
the PYTHONPATH acordingly. For example, if you have python3.7, probably you'll
have the packages installed in `/home/<YOUR-USER>/.local/lib/python3.7/site-packages/`.
So you can ran:
* server: `sudo su -c "PYTHONPATH=/home/<YOUR-USER>/.local/lib/python3.7/site-packages/ python3 server.py -p <PORT>"`
* client: `sudo su -c "PYTHONPATH=/home/<YOUR-USER>/.local/lib/python3.9/site-packages/ DEBUG=1 python3 client.py <SERVER-IP> -p <PORT>"`

### Debug

To increment the verbosity set the env `DEBUG`. For example,
* server: `sudo su -c "PYTHONPATH=/home/<YOUR-USER>/.local/lib/python3.7/site-packages/ DEBUG=1 python3 server.py"`
* client: `sudo su -c "PYTHONPATH=/home/<YOUR-USER>/.local/lib/python3.9/site-packages/ DEBUG=1 python3 client.py <SERVER-IP> -p <PORT>"`


### To do...

Keystrokes actions are being ommited so far, to test only the communication and
encription. Stay tuned!
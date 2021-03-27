from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from collections import namedtuple
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

KeysPair = namedtuple('KeysPair', ['private', 'public'])


def generate_keys():
    private = rsa.generate_private_key(public_exponent=65537,
                                       key_size=2048,
                                       backend=default_backend())
    public = private.public_key()
    return KeysPair(private=private, public=public)


def serialize_public_key(public_key):
    return public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo)


def serialize_private_key(private_key):
    return private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption())


def import_public_key(key):
    return serialization.load_pem_public_key(key, backend=default_backend())


def import_private_key(key):
    return serialization.load_pem_private_key(key, password=None,
                                              backend=default_backend())


def encrypt(message, public_key):
    encrypted = public_key.encrypt(
                    message,
                    padding.OAEP(
                        mgf=padding.MGF1(algorithm=hashes.SHA256()),
                        algorithm=hashes.SHA256(),
                        label=None))
    return encrypted


def decrypt(message, private_key):
    decrypted = private_key.decrypt(
                    message,
                    padding.OAEP(
                        mgf=padding.MGF1(algorithm=hashes.SHA256()),
                        algorithm=hashes.SHA256(),
                        label=None))
    return decrypted


def main():
    import os
    import os.path
    default_dir = os.path.expanduser("~")
    default_name = 'id_rsa'
    txt = 'Directory where keys\'ll be generated [{}]:'
    while True:
        path = input(txt.format(default_dir))
        if not path:
            path = default_dir
        if os.path.isdir(path):
            break
        print('Non-existing directory.')
    while True:
        txt = 'Name of the keys [{}]:'
        name = input(txt.format(default_name))
        if not name:
            name = default_name
        full_path_priv = path + '/' + name
        full_path_pub = path + '/' + name + '.pub'
        if os.path.isfile(full_path_priv):
            print('File {} already exists.'.format(full_path_priv))
        elif os.path.isfile(full_path_pub):
            print('File {} already exists.'.format(full_path_pub))
        else:
            break

    keys_pair = generate_keys()
    private = serialize_private_key(keys_pair.private)
    public = serialize_public_key(keys_pair.public)
    flags = os.O_CREAT | os.O_WRONLY
    with open(os.open(full_path_pub, flags, 0o444), 'wb') as f:
        f.write(public)
    print('Generated public key in "{}".'.format(full_path_pub))
    with open(os.open(full_path_priv, flags, 0o400), 'wb') as f:
        f.write(private)
    print('Generated private key in "{}".'.format(full_path_priv))


if __name__ == '__main__':
    main()

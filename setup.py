from setuptools import setup, find_packages

install_requires = []
with open('./requirements.txt', 'r') as f:
    for line in f.readlines():
        install_requires.append(line.replace('\n', ''))

packages = find_packages()

setup(name='kybonet',
      version='0.1.0',
      description='kybonet',
      packages=packages,
      install_requires=install_requires,
      include_package_data=True,
      entry_points={'console_scripts': [
                        'kybonet-server=kybonet.server:main',
                        'kybonet-client=kybonet.client:main',
                        'kybonet-keygen=kybonet.crypto:main',
                        'kybonet-devices=kybonet.input_devices:main']},
      )

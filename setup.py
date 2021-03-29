from setuptools import setup, find_packages


def install_requires():
    with open('./requirements.txt', 'r') as f:
        return [line.replace('\n', '') for line in f.readlines()]


def long_description():
    with open("README.rst") as f:
        return f.read()


setup(name='kybonet',
      version='0.1.0',
      author='Ariel Kukulanski',
      author_email='akukulanski@gmail.com',
      description='Software KVM switch over the network with encryption (keyboard and mouse only, no video).',
      packages=find_packages(),
      license='BSD',
      python_requires="~=3.6",
      url='https://github.com/akukulanski/kybonet',
      # download_url=,
      keywords=['keyboard', 'mouse', 'kvm', 'switch', 'encrypt'],
      install_requires=install_requires(),
      include_package_data=True,
      entry_points={'console_scripts': [
                        'kybonet-server=kybonet.server:main',
                        'kybonet-client=kybonet.client:main',
                        'kybonet-keygen=kybonet.crypto:main',
                        'kybonet-devices=kybonet.input_devices:main']},
      project_urls={
          "Source Code": "https://github.com/akukulanski/kybonet",
          "Bug Tracker": "https://github.com/akukulanski/kybonet/issues",
      },
      classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: BSD License',
        'Operating System :: POSIX :: Linux',
        'Topic :: Utilities'])

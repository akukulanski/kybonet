from setuptools import setup, find_packages


def install_requires():
    with open('./requirements.txt', 'r') as f:
        return [line.replace('\n', '') for line in f.readlines()]


def long_description():
    with open("readme.md") as f:
        return f.read()


def get_version():
    import setuptools_scm
    import setuptools_scm.git
    return setuptools_scm.get_version(root='.',
                                      parse=setuptools_scm.git.parse)


version = get_version()
print('version={}'.format(version))

setup(name='kybonet',
      version=version,
      author='Ariel Kukulanski',
      author_email='akukulanski@gmail.com',
      description='Software KVM switch over the network with encryption (keyboard and mouse only, no video).',
      long_description=long_description(),
      long_description_content_type='text/markdown',
      packages=find_packages(),
      license='BSD',
      python_requires="~=3.6",
      url='https://github.com/akukulanski/kybonet',
      # download_url=,
      keywords=['keyboard', 'mouse', 'kvm', 'switch', 'encrypt'],
      setup_requires=['setuptools_scm', 'wheel'],
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

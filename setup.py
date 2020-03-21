""" Setup """

import re
from setuptools import setup, find_packages

with open('README.md', 'rb') as f:
    DESCRIPTION = f.read().decode('utf-8')

with open('timeflux_brainflow/__init__.py') as f:
    VERSION = re.search('^__version__\s*=\s*\'(.*)\'', f.read(), re.M).group(1)

DEPENDENCIES = [
    'brainflow',
    'timeflux @ git+https://github.com/timeflux/timeflux'
]

setup(
    name='timeflux-brainflow',
    packages=find_packages(),
    version=VERSION,
    description='Timeflux BrainFlow plugin',
    long_description=DESCRIPTION,
    author='Pierre Clisson',
    author_email='contact@timeflux.io',
    url='https://timeflux.io',
    install_requires=DEPENDENCIES
)

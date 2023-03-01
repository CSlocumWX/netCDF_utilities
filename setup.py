# -*- coding: utf-8 -*-

from setuptools import setup, find_packages


with open('README.md') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='netCDF_utilities',
    version='1.4c',
    description='Utilities to use with the Unidata netCDF4 module',
    long_description=readme,
    author='Chris Slocum',
    author_email='Christopher.Slocum@colostate.edu',
    url='https://github.com/CSlocumWX/netCDF_utilities',
    license=license,
    packages=find_packages(exclude=('test', 'docs'))
)

#! /usr/env/bin python
from setuptools import setup
import Smartscope
setup(
    name='Smartscope',
    version=Smartscope.__version__,
    description='Smartscope module for automatic CryoEM grid screening',
    author='Jonathan Bouvette',
    author_email='jonathan.bouvette@nih.gov',
    packages=['Smartscope'],
    scripts=['Smartscope/bin/smartscope.py','Smartscope/bin/manage.py','Smartscope/bin/smartscope.sh'],  # same as name
    install_requires=['numpy', 'pandas', 'matplotlib', 'mrcfile', 'scipy',
                      'imutils', 'scikit-image', 'pyampd'],  # external packages as dependencies
)

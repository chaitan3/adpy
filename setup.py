import numpy as np
import os
import sys
from setuptools import setup, Extension, Command

class CleanCommand(Command):
    """Custom clean command to tidy up the project root."""
    user_options = []
    def initialize_options(self):
        pass
    def finalize_options(self):
        pass
    def run(self):
        os.system('rm -vrf ./build ./dist ./*.pyc ./*.tgz ./*.egg-info')



#compile_args = ['-std=c++11', '-O3']#, '-march=native']

setup(name='adpy',
      version='0.1.1',
      description='adpy',
      author='Chaitanya Talnikar',
      author_email='talnikar@mit.edu',
      packages=['adpy'],
      package_data={
       'adpy': ['gencode/*', 'cpp/*.cpp', 'cpp/*.py', 'cpp/include/*'],
      },
      include_package_data=True,
      install_requires=[ 
          'numpy >= 1.8.2',
          'scipy >= 0.13.3',
          #'mpi4py >= 0.13.1',
          #'h5py >= 2.6.0',
          #'matplotlib >= 1.3.1'
      ],
      cmdclass={
        'clean': CleanCommand,
      }
    )

import numpy as np
import os

gpu = False
gpu_double = False
precision = np.float64
profile = False
gc = False
compile = True
openmp = False
codeExt = 'cpp'

def set_config(config):
    globals()['gpu']  = config.gpu
    globals()['gpu_double']  = config.gpu_double
    globals()['precision']  = config.precision
    globals()['profile']  = config.profile
    globals()['gc']  = config.gc
    globals()['compile'] = config.compile
    globals()['openmp'] = config.openmp
    globals()['codeExt'] = config.codeExt

from . import cpp
    
def get_sources():
    cppDir = os.path.realpath(os.path.dirname(cpp.__file__))
    includeDir = os.path.join(cppDir, 'include')
    #headers = [os.path.join(includeDir, header) for headers in ['common.hpp', 'gpu.hpp', 'interface.hpp']]
    sources = [os.path.join(cppDir, src) for src in ['interface.cpp']]
    print includeDir, sources
    return includeDir, sources

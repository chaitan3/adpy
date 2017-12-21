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
cppDir = os.path.realpath(os.path.dirname(cpp.__file__))
includeDir = os.path.join(cppDir, 'include')
moduleDir = os.path.join(cppDir, 'module')

def get_include_dirs(external=True):
    if external:
        return [includeDir, moduleDir]
    else:
        return [includeDir]
    
def get_sources():
    #headers = [os.path.join(includeDir, header) for headers in ['common.hpp', 'gpu.hpp', 'interface.hpp']]
    return ['interface.cpp']

def get_module_sources(external=True):
    if external:
        sources = ['graph.cpp', 'external.cpp']
    else:
        sources = ['graph.cpp']
    return [os.path.join(moduleDir, x) for x in sources]

def get_gen_sources():
    codeFile = 'code.{}'.format(codeExt)
    kernelCodeFile = 'kernel.{}'.format(codeExt)
    kernelHeaderFile = 'kernel.hpp'
    return codeFile, kernelCodeFile, kernelHeaderFile

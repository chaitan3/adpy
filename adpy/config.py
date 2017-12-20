import numpy as np

gpu = False
gpu_double = False
precision = np.float64
profile = False
gc = False
compile = False
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
    

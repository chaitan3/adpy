from __future__ import print_function

import os
import numpy as np
import subprocess
import multiprocessing.pool

from distutils.sysconfig import get_python_inc

from . import config

def compile_gencode(codeDir, compiler='ccache gcc', linker='g++', incdirs=[], libdirs=[], libs=[], sources=[]):
    codeDir = os.path.realpath(codeDir)
    openmp = config.openmp
    gpu = config.gpu
    gpu_double = config.gpu_double
    codeExt = 'cu' if gpu else 'cpp'

    if gpu:
        #compiler = 'ccache nvcc -x cu'
        compiler = 'nvcc -x cu'
        linker = 'nvcc --shared'

    home = os.path.expanduser("~")
    external = (len(sources) == 0)
    incdirs += [get_python_inc(), np.get_include(), codeDir] + config.get_include_dirs(external)
    sources += config.get_module_sources(external)
    sources += [os.path.join(config.cppDir, x) for x in config.get_sources()]
    sources += [x.format(codeExt) for x in ['kernel.{}', 'code.{}']]

    compile_args = ['-std=c++11', '-O3', '-g']
    link_args = []
    if openmp:
        compile_args += ['-fopenmp']
        link_args = ['-lgomp']
    if gpu:
        #cmdclass = {}
        nv_arch="-gencode=arch=compute_52,code=\"sm_52,compute_52\""
        compile_args += [nv_arch, '-Xcompiler=-fPIC']
        compile_args += ['-DGPU']
        if gpu_double:
            compile_args += ['-DGPU_DOUBLE']
        
        libs += ['gomp']
    else:
        compile_args += ['-fPIC', '-Wall', '-march=native']
        compile_args += ['-Wfatal-errors']
        link_args += ['-shared']

    module = 'graph.so'
    incdirs = ['-I'+inc for inc in incdirs]
    libdirs = ['-L'+lib for lib in libdirs]
    compiler = compiler.split(' ')
    linker = linker.split(' ')
    libs = ['-l' + lib for lib in libs]
    objects = [os.path.basename(src).split('.')[0] + '.o' for src in sources]

    def single_compile(src):
        cmd = compiler + compile_args + incdirs + [src, '-c']
        print(' '.join(cmd))
        subprocess.check_call(cmd, stderr=subprocess.STDOUT, cwd=codeDir)

    n = len(sources)
    #n = 4
    n = 1
    res = list(multiprocessing.pool.ThreadPool(n).imap(single_compile, sources))

    cmd = linker + link_args + objects + libdirs + libs + ['-o', module]
    print(' '.join(cmd))
    subprocess.check_call(cmd, stderr=subprocess.STDOUT, cwd=codeDir)
    print()

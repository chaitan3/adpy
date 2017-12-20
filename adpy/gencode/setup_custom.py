#!/usr/bin/python2

from __future__ import print_function

import os
import numpy as np
import subprocess
import multiprocessing.pool

from distutils.sysconfig import get_python_inc

from adpy import config

openmp = 'WITH_OPENMP' in os.environ
matop = 'WITH_MATOP' in os.environ
gpu = 'WITH_GPU' in os.environ
gpu_double = 'WITH_GPU_DOUBLE' in os.environ
codeExt = 'cu' if gpu else 'cpp'

compiler = 'ccache mpicc'
linker = 'mpicxx'
if gpu:
    #compiler = 'ccache nvcc -x cu'
    compiler = 'nvcc -x cu'
    linker = 'nvcc --shared'

home = os.path.expanduser("~")
incdirs = [get_python_inc(), np.get_include(), config.includeDir]
libdirs = []
libs = []
sources = config.get_sources() + config.get_module_sources()
sources += [x.format(codeExt) for x in ['kernel.{}', 'code.{}']]

compile_args = ['-std=c++11', '-O3', '-g']
link_args = []
if openmp:
    compile_args += ['-fopenmp']
    link_args = ['-lgomp']
if matop:
    sources += [cppDir + 'matop.cpp']
    compile_args += ['-DMATOP']
    if gpu and not gpu_double:
        compile_args += ['-DPETSC_USE_REAL_SINGLE']
        home = os.path.expanduser('~') + '/sources/petsc_single/'
    else:
        home = os.path.expanduser('~') + '/sources/petsc/'
    build = 'arch-linux2-c-debug'
    incdirs += ['{}/{}/include'.format(home, build), home + '/include', os.path.expanduser('~') + '/sources/cusp/']
    #incdirs += [home + '/linux-gnu-c-opt/include']
    libdirs += ['{}/{}/lib'.format(home, build)]
    libs += ['petsc']
if gpu:
    #cmdclass = {}
    nv_arch="-gencode=arch=compute_52,code=\"sm_52,compute_52\""
    compile_args += [nv_arch, '-Xcompiler=-fPIC']
    compile_args += ['-DGPU']
    if gpu_double:
        compile_args += ['-DGPU_DOUBLE']
    mpi_incdirs = subprocess.check_output('mpicc --showme | egrep -o -e "-I[a-z\/\.]*"', shell=True)
    incdirs += [d[2:] for d in mpi_incdirs.split('\n')[:-1]]
    mpi_libdirs = subprocess.check_output('mpicc --showme | egrep -o -e "-L[a-z\/\.]*"', shell=True)
    libdirs += [d[2:] for d in mpi_libdirs.split('\n')[:-1]]
    libs += ['mpi', 'cublas', 'cusolver', 'gomp']
else:
    libs += ['lapack']
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
    subprocess.check_call(cmd, stderr=subprocess.STDOUT)

n = len(sources)
#n = 4
#n = 1
res = list(multiprocessing.pool.ThreadPool(n).imap(single_compile, sources))

cmd = linker + link_args + objects + libdirs + libs + ['-o', module]
print(' '.join(cmd))
subprocess.check_call(cmd, stderr=subprocess.STDOUT)
print()

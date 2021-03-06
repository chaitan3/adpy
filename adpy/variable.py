
import os, sys, subprocess, shutil
scriptDir = os.path.dirname(os.path.realpath(__file__))

from . import config
from .scalar import *
from .compile import compile_gencode

import numpy as np
import time
import sys
try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO

_dtype = dtype

def graphGetChildren(outputs):
    children = {}
    inputs = []

    def _childrenFunc(out):
        if len(out.args) == 0:
            inputs.append(out)
        for inp in out.args:
            if inp in children:
                children[inp] += 1
            else:
                children[inp] = 1
                _childrenFunc(inp)

    output = Container()
    output.args = tuple(outputs)
    _childrenFunc(output)
    for out in outputs:
        children[out] -= 1
    return children, inputs

def graphTopologicalSort(outputs, children):
    output = Container()
    output.args = tuple(outputs)
    for out in outputs:
        children[out] += 1
    children[output] = 0
    sortedOps = []
    def _sort(out):
        sortedOps.append(out)
        for inp in out.args:
            children[inp] -= 1
            if children[inp] == 0:
                _sort(inp)
    _sort(output)
    return sortedOps[1:][::-1]

class Variable(ArithBase):
    _index = 0
    def __init__(self, shape, dtype=_dtype):
        index = Variable._index
        Variable._index += 1
        self.name = 'Variable_{}'.format(index)
        self.shape = shape
        self.dtype = dtype
        self.args = ()
        self.index = 0
        self.outputIndex = None
        self.static = False
        assert dtype in ['integer', 'scalar']
        assert isinstance(shape, tuple)
        assert all([isinstance(x, int) or isinstance(x, IntegerScalar) for x in shape])

    def __getitem__(self, index):
        #print self.index
        #assert self.index == 0
        var = self.getReference()
        var.index = index
        return var

    def getReference(self):
        var = Variable(self.shape, self.dtype)
        var.args = (self,)
        var.name = self.name
        var.static = self.static
        return var

    def grad(self, grad):
        assert isinstance(grad, tuple)
        assert len(grad) == 1
        gradIndex = 0
        for out in grad:
            assert self.shape == out.shape
            assert self.dtype == out.dtype
        if len(self.args) == 0:
            return tuple()
        assert len(self.args) == 1
        index = 0
        if isinstance(self.args[0], Variable):
            index = self.args[0].index
        gradArgs = (grad[gradIndex][index],)
        if isinstance(self.args[0], FunctionOp):
            gradArgs[0].outputIndex = self.outputIndex
        return gradArgs

    def staticId(self):
        if self.static:
            return hash(self.name)
        else:
            return 0

class Zeros(Variable):
    pass

class IntegerVariable(Variable):
    def __init__(self, shape):
        super(IntegerVariable, self).__init__(shape, 'integer')

class StaticVariable(Variable):
    def __init__(self, shape, dtype=_dtype):
        super(StaticVariable, self).__init__(shape, dtype)
        self.static = True

class StaticIntegerVariable(StaticVariable):
    def __init__(self, shape):
        super(StaticIntegerVariable, self).__init__(shape, 'integer')

import inspect
class FunctionOp(object):
    def _init(self, name, args, outputs):
        self.name = name
        args = args + outputs
        self.args = args
        self.outputs = []
        for index, out in enumerate(outputs):
            self.outputs.append(out.getReference())
            self.outputs[-1].args = (self,)
            self.outputs[-1].outputIndex = index
        self.outputs = tuple(self.outputs)

    def _grad(self, grad):
        outputRefs = self.outputs
        n = len(outputRefs)
        _inputs, _outputs = self.args[:-n], self.args[-n:]
        inputs = []
        indices = set([x.outputIndex for x in grad])
        assert all([x.outputIndex is not None for x in grad])
        for out1, out2 in zip(grad, [_outputs[i] for i in indices]):
            inputs.append(out1[out2.index])
            inputs[-1].outputIndex = out1.outputIndex
        extraIndices = set(range(0, n))-indices
        for index in extraIndices:
            out = _outputs[index]
            zero = Zeros(out.shape, out.dtype)
            zero.name = out.name + '_adj'
            inputs.append(zero[out.index])
            inputs[-1].outputIndex = index
            FunctionOp.insert_cache([inputs[-1]])
        inputs = list(sorted(inputs, key=lambda x: x.outputIndex))
        gradOutputs = tuple(inputs)
        assert len(inputs) == n
        for out1, out2 in zip(inputs, _outputs):
            assert out1.shape == out2.shape
            assert out1.dtype == out2.dtype
            assert out1.index == out2.index
        inputs = _inputs + gradOutputs
        outputs = []
        for inp in _inputs:
            name = inp.name + '_adj'
            out = FunctionOp.get_cache(name, inp)
            outputs.append(out)
        outputs = tuple(outputs)
        assert len(inputs) == len(self.args)
        assert len(outputs) == len(_inputs)
        return inputs, outputs, gradOutputs

    def _gradOutputRefs(self, gradOutputs):
        gradOutputs = list(gradOutputs)
        for index, out in enumerate(gradOutputs):
            outRef = out[out.index]
            outRef.args = (self,)
            gradOutputs[index] = outRef
        return tuple(gradOutputs)

    @classmethod
    def clear_cache(cls):
        FunctionOp._gradCache = {}

    @classmethod
    def insert_cache(cls, gradInputs):
        cache = FunctionOp._gradCache
        for out in gradInputs:
            cache[out.name] = out

    @classmethod
    def get_cache(cls, name, inp=None):
        cache = FunctionOp._gradCache
        if name in cache:
            out = cache[name]
        elif inp:
            out = Zeros(inp.shape, inp.dtype)
            out.static = inp.static
            out.name = name
        else:
            raise Exception("not found in cache")
        if inp:
            return out[inp.index]
        else:
            return out

class TensorFunctionOp(FunctionOp):
    _gradCache = {}
    
    def __init__(self, func, args, outputs, indices):
        assert isinstance(indices, IntegerScalar) or isinstance(indices, int)
        self.func = func
        self._init(func.name, args, outputs)
        self.indices = indices
        self.info = inspect.stack()[2:]
        
    def getCallString(self):
        #callString = '\n/* ' + str(self.info) + ' */\n'
        callString = ''
        for inp in self.args:
            if isinstance(inp.index, int):
                offset = '({})'.format(inp.index)
            else:
                offset = '({})'.format(inp.index.name)
            callString += '&{}{}, '.format(inp.name, offset)
            #if hasattr(inp, 'dtype'):
            #    callString += '/* {} */  '.format(inp.dtype)
        #for out in self.outputs:
        #    callString += '{}, '.format(out.name)
        return callString[:-2]
    
    def grad(self, grad):
        n = len(self.outputs)
        args, outputs, gradOutputs = self._grad(grad)
        gradOp = TensorFunctionOp(self.func.grad, args, outputs, self.indices)
        gradInputs, gradOutputs = gradOp.outputs, gradOp._gradOutputRefs(gradOutputs)
        FunctionOp.insert_cache(gradInputs)
        gradInputs[0].args[0].info = ['grad'] + self.info
        return gradInputs + gradOutputs


class ExternalFunctionOp(FunctionOp):
    def __init__(self, name, args, outputs, empty=False):
        self._init('Function_' + name, args, outputs)
        self.empty = empty
        self.arrType = None

    def getCallString(self):
        if self.empty:
            return ''
        inp = self.args[0]
        shape = ','.join([str(x) for x in inp.shape[1:]])
        pointer = '{}<{},{}>*'.format(self.arrType, inp.dtype, shape)
        callString = 'std::vector<{}>{{'.format(pointer)
        for inp in self.args:
            callString += '({})&{},'.format(pointer, inp.name)
        callString = callString[:-1] + '}'
        return callString

    def grad(self, grad):
        n = len(self.outputs)
        args, outputs, gradOutputs = self._grad(grad)
        name = self.name[len('Function_'):] + '_grad'
        gradOp = ExternalFunctionOp(name, args, outputs, self.empty)
        gradInputs, gradOutputs = gradOp.outputs, gradOp._gradOutputRefs(gradOutputs)
        FunctionOp.insert_cache(gradInputs)
        return gradInputs + gradOutputs

class Function(object):
    _index = 0
    _init = False

    _module = None
    codeDir = None
    codeFile = None
    kernelCodeFile = None
    kernelHeaderFile = None
    funcs = None

    defaultOptions = {'return_static': True, 
                      'zero_static': False,
                      'replace_static': False,
                      'return_reusable': True,
                      'replace_reusable': False,
                     }

    def __init__(self, name, inputs, outputs, **kwargs):
        if not Function._init:
            Function.reset()
        self._io_map = kwargs.get('io_map', {})
        if config.gpu:
            self.arrType = 'gpuArrType'
        else:
            self.arrType = 'arrType'
            #self.arrType = 'gpuArrType'
        self.name = name
        if isinstance(inputs, list):
            inputs = tuple(inputs)
        elif isinstance(inputs, Variable):
            inputs = (inputs,)
        if isinstance(outputs, list):
            outputs = tuple(outputs)
        elif isinstance(outputs, Variable):
            outputs = (outputs,)
        assert isinstance(inputs, tuple)
        assert isinstance(outputs, tuple)
        assert all([isinstance(x, Variable) or isinstance(x, IntegerScalar) for x in inputs])
        assert all([isinstance(x, Variable) for x in outputs])
        self._inputs = inputs
        self._outputs = outputs
        _outputs = [x for x in self._outputs if x is not None]
        self._children, discoveredInputs = graphGetChildren(_outputs)
        discoveredInputs = [x for x in discoveredInputs if not isinstance(x, Zeros)]
        assert set(discoveredInputs).issubset(set(inputs))
        
        self._genCode(_outputs)
        FunctionOp.clear_cache()
        Function.funcs.append(self.name)

    def grad(self):
        #gradOutputs = []
        #for out in self._outputTensors:
        #    gradOutputs.append(Tensor(out.shape))
        #    gradOutputs[-1].cellTensor = out.cellTensor

        #scalarOutput = sum([x.dot(y) for x, y in zip(self._outputTensors, gradInputs)])
        gradients = {}
        gradOutputs = []
        for out in self._outputs:
            name = out.name + '_adj'
            grad = Variable(out.shape, out.dtype)
            grad.name = name
            gradients[out] = (grad,)
            gradOutputs.append(grad)
        FunctionOp.insert_cache(gradOutputs)
        gradInputs = self._diff(self._outputs, self._inputs, gradients)
        assert len(gradInputs) == len(self._inputs)
        for inp1, inp2 in zip(self._inputs, gradInputs):
            if isinstance(inp1, Variable):
                inp2.static = inp1.static
        return gradOutputs, gradInputs

    def getAdjoint(self):
        gradOutputs, gradInputs = self.grad()
        adj_io_map = {v + len(self._inputs): k for k, v in self._io_map.items()}
        return Function(self.name + '_grad', self._inputs + tuple(gradOutputs), tuple(gradInputs), io_map=adj_io_map)

    def _getName(self, op):
        if isinstance(op, int):
            name = op
        else:
            name = op.name
        return name

    def _reuseId(self, index):
        return '{}_{}'.format(self.name, index)
        
    def _genCode(self, outputs):
        codeFile = Function.codeFile
        codeFile.write('\nstatic PyObject* Function_{}(PyObject *self, PyObject *args, PyObject *kwargs) {{\n'.format(self.name))
        codeFile.write('\tmap<string, int> options = PyOptions_Parse(kwargs);\n')
        if config.profile:
            codeFile.write('\tlong long start, end;\n')
        #for out in self._outputs:
        #    memString += '{}* {}, '.format(out.dtype, out.name)
        memoryInit = {}
        keepMemory = {True: 'true', False: 'false'}[not config.gc]
        codeFile.write('\tassert(PyTuple_Size(args) == {});\n'.format(len(self._inputs)))
        for index, inp in enumerate(self._inputs):
            if isinstance(inp, IntegerScalar):
                codeFile.write('\tinteger {} = (integer) PyInt_AsLong(PyTuple_GetItem(args, {}));\n'.format(inp.name, index))

        for index, inp in enumerate(self._inputs):
            if isinstance(inp, IntegerScalar):
                continue
            memoryInit[inp.name] = 1
            codeFile.write('\tPyObject* Py_{} = PyTuple_GetItem(args, {});\n'.format(inp.name, index))
            shape = ','.join([str(x) for x in inp.shape[1:]])
            codeFile.write('\t{}<{}, {}> {};\n'.format(self.arrType, inp.dtype, shape, inp.name))
            if index in self._io_map:
                reuseId = self._reuseId(index)
                codeFile.write('\tif (options["replace_reusable"] || {}.get_mem()->reuse.count("{}") == 0) {{\n'.format(inp.name, reuseId))
                codeFile.write('\t\tgetArray((PyArrayObject*) Py_{0}, {0}, {2}, {1}L);\n'.format(inp.name, inp.staticId(), keepMemory))
                codeFile.write('\t} else {\n')
                codeFile.write('\t\t{}.reuse_acquire("{}", {}, {});\n'.format(inp.name, reuseId, self._getName(inp.shape[0]), keepMemory))
                codeFile.write('\t}\n') 
            else:
                codeFile.write('\tgetArray((PyArrayObject*) Py_{0}, {0}, {2}, {1}L);\n'.format(inp.name, inp.staticId(), keepMemory))
        codeFile.write('\n')

        varChildren = {}
        for op, off in self._children.items():
            name = op.name
            if name not in varChildren:
                varChildren[name] = 0
            varChildren[name] += off
        inputNames = list(memoryInit.keys())
        outputNames = [out.name for out in outputs]

        sortedOps = graphTopologicalSort(outputs, self._children.copy())
        prevOp = Container()
        prevOp.args = []
        for op in sortedOps:

            for arg in prevOp.args:
                varName = arg.name
                assert varChildren[varName] > 0
                varChildren[varName] -= 1
                if isinstance(arg, Variable) and varName not in outputNames and varChildren[varName] == 0:
                    if varName in inputNames and ((not config.gpu) or arg.static):
                        continue
                    codeFile.write('\t{}.destroy();\n'.format(varName))
            
            for arg in op.args:
                varName = arg.name
                if isinstance(arg, Variable) and varName not in memoryInit:
                    shape = ','.join([str(x) for x in arg.shape[1:]])
                    arrType = '{}<{}, {}>'.format(self.arrType, arg.dtype, shape)
                    #codeFile.write('\t{} {}({}, true);\n'.format(arrType, varName, self._getName(arg.shape[0]))) 
                    codeFile.write('\t{} {}({}, true, {}, {}L);\n'.format(arrType, varName, self._getName(arg.shape[0]), keepMemory, arg.staticId())) 
                    memoryInit[varName] = 1

            # fix garbage collection
            #for key, ref in memoryPool.items():
            #    if config.gc:
            #        codeFile.write('\t{}.destroy();\n'.format(ref.name))

            if isinstance(op, TensorFunctionOp):
                codeFile.write('\t/* {} */\n'.format(op.info))

                #for index, inp in enumerate(op.args[:-len(op.outputs)]):
                #    if not isinstance(inp.shape[0], int) and op.func._inputsUsed[index]:
                #        codeFile.write('\tassert({}.shape >= ({} + {}));\n'.format(inp.name, _getName(op.indices), _getName(inp.index)))
                name = self._getName(op.indices)
                if config.profile:
                    #codeFile.write('\tMPI_Barrier(MPI_COMM_WORLD);\n')
                    codeFile.write('\tstart = current_timestamp();\n')
                if config.gpu:
                    #codeFile.write('\tinteger nBlocks = {}/GPU_THREADS_PER_BLOCK + 1;\n'.format(name))
                    #codeFile.write('\tdim3 blocks(nBlocks / GPU_MAX_BLOCKS + 1, min(nBlocks, GPU_MAX_BLOCKS));\n')
                    #codeFile.write('\tdim3 threads(min(GPU_THREADS_PER_BLOCK, {}));\n'.format(name))
                    #codeFile.write('\t\t{}<<<blocks, threads>>>({}, {});\n'.format(op.name, name, op.getCallString()))
                    codeFile.write('\t{}<<<GPU_BLOCKS_PER_GRID, GPU_THREADS_PER_BLOCK>>>({}, {});\n'.format(op.name, name, op.getCallString()))
                    if config.profile:
                        codeFile.write('\tgpuErrorCheck(cudaDeviceSynchronize());\n')
                    codeFile.write('\tgpuErrorCheck(cudaPeekAtLastError());\n')
                else:
                    codeFile.write('\t{}({}, {});\n'.format(op.name, name, op.getCallString()))
                if config.profile:
                    #codeFile.write('\tMPI_Barrier(MPI_COMM_WORLD);\n')
                    codeFile.write('\tend = current_timestamp();\n')
                    codeFile.write('\tif (meshp->rank == 0) cout << "{} Kernel time: " << end-start << "us" << endl;\n'.format(op.name))
                    
                    codeFile.write('\t{\n')
                    codeFile.write('\t\tdouble global, local;\n')
                    codeFile.write('\t\tdouble local_time;\n')
                    codeFile.write('\t\tlocal_time = (double)(end-start);\n')

                    rate = '\t\tcout << "{} {}: " << global << endl;\n'
                    for msg, nops in zip(['Mload bandwidth', 'Mstore bandwidth', 'Mflops'], [op.func._loads, op.func._stores, op.func._flops]):
                        codeFile.write('\t\tglobal = 0;\n'.format(name, nops))
                        codeFile.write('\t\tlocal = {}*{}/local_time;\n'.format(name, nops))
                        codeFile.write('\t\tMPI_Reduce(&local, &global, 1, MPI_DOUBLE, MPI_SUM, 0, MPI_COMM_WORLD);\n')
                        codeFile.write('\t\tif (meshp->rank == 0) ' +  rate.format(op.name, msg))
                    codeFile.write('\t}\n')
            elif isinstance(op, ExternalFunctionOp):
                op.arrType = self.arrType
                codeFile.write('\t{}({});\n'.format(op.name, op.getCallString()))
            elif isinstance(op, Variable):
                pass
            else:
                raise Exception('op not recognised', op)

            #if hasattr(op, 'outputs'):
            #    for arg in op.outputs:
            #        if isinstance(arg, Variable):
            #            codeFile.write('\tif ({}.checkNAN()) throw 20;\n'.format(arg.name))
            prevOp = op
            
        codeFile.write('\n\tPyObject* outputs = PyTuple_CreateNone({});\n'.format(len(outputs)))
        for index, out in enumerate(outputs):
            if isinstance(out, Variable) and out.static:
                codeFile.write('\tif (options["return_static"]) {\n');
                codeFile.write('\t\tPyTuple_SetItem(outputs, {}, putArray({}, false));\n'.format(index, out.name))
                codeFile.write('\t}\n');
                codeFile.write('\tif (options["zero_static"]) {\n');
                codeFile.write('\t\t{}.zero();\n'.format(out.name))
                codeFile.write('\t}\n');
            elif index in self._io_map.values():
                key =  list(self._io_map.keys())[list(self._io_map.values()).index(index)]
                codeFile.write('\t{}.reuse_release("{}");\n'.format(out.name, self._reuseId(key)))
                codeFile.write('\tif (options["return_reusable"]) {\n');
                codeFile.write('\t\tPyTuple_SetItem(outputs, {}, putArray({}, false));\n'.format(index, out.name))
                codeFile.write('\t}\n');
            else:
                codeFile.write('\tPyTuple_SetItem(outputs, {}, putArray({}, false));\n'.format(index, out.name))
        if len(outputs) == 1:
            codeFile.write('\treturn PyTuple_GetItem(outputs, 0);')
        else:
            codeFile.write('\treturn outputs;')
        codeFile.write('\n')
        codeFile.write('}\n\n')

    def _diff(self, outputs, inputs, gradients=None):
        children = self._children.copy()
        #print children.values()
        # TODO: better handling of None, change integer grad to None
        def _diffFunc(out):
            #assert children[out] == 0
            grads = out.grad(gradients[out])
            assert len(grads) == len(out.args)
            for grad, inp in zip(grads, out.args):
                if inp not in gradients:
                    gradients[inp] = tuple()
                if not isinstance(inp, Variable):
                    gradients[inp] += (grad,)
                else:
                    gradients[inp] = (FunctionOp.get_cache(grad.name),)
                children[inp] -= 1
                if children[inp] == 0:
                    _diffFunc(inp)
        for out in outputs:
            if children[out] == 0:
                _diffFunc(out)
        #print children.values()
        #exit(1)
        #print(self.name, [len(gradients.get(inp, (None,))) for inp in inputs])
        #return [gradients.get(inp, (None,))[-1] for inp in inputs]
        return [gradients.get(inp, (None,))[0] for inp in inputs]

    def __call__(self, *args, **kwargs):
        func = getattr(Function._module, self.name)
        options = self.defaultOptions.copy()
        options.update(kwargs)
        #print options
        return func(*args, **options)

    @classmethod
    def createCodeDir(cls, case, replace=True):
        cls.codeDir = case + 'gencode/'
        if replace:
            if os.path.exists(cls.codeDir):
                shutil.rmtree(cls.codeDir)
            os.makedirs(cls.codeDir)

    @classmethod
    def reset(cls):
        cls._module = None
        cls.codeDir = None
        cls.codeFile = StringIO()
        cls.kernelCodeFile = StringIO()
        cls.kernelHeaderFile = StringIO()
        cls.funcs = []
        cls.codeFile.write('#include "code.hpp"\n')
        cls.kernelCodeFile.write('#include "code.hpp"\n')
        cls._init = True
        cls._index += 1

    @classmethod
    def compile(cls, case='./', init=True, replace=True, compiler_args={}):
        if cls.codeDir is None:
            cls.createCodeDir(case, replace=replace)

        cls.codeFile.write("PyMethodDef ExtraMethods[] = {\n")
        for name in Function.funcs:
            cls.codeFile.write('\t{{"{0}",(PyCFunction)Function_{0}, METH_VARARGS | METH_KEYWORDS, "boo"}},\n'.format(name))
        cls.codeFile.write("\n\t\t{NULL, NULL, 0, NULL}        /* Sentinel */\n\t};\n")

        moduleName = 'graph_{}'.format(cls._index)
        #moduleName = 'graph{}'.format(cls._index)

        if replace:
            for name, string in zip(config.get_gen_sources(), [cls.codeFile, cls.kernelCodeFile, cls.kernelHeaderFile]):
                with open (os.path.join(cls.codeDir, name), 'w') as f:
                    string.seek(0)
                    shutil.copyfileobj(string, f)
                    string.close()

            compile_gencode(cls.codeDir, moduleName, **compiler_args)

        sys.path.append(cls.codeDir)
        while True:
            import importlib
            Function._module = importlib.import_module(moduleName)
            try:
                #Function._module = __import__(moduleName)
                import importlib
                Function._module = importlib.import_module(moduleName)
                break
            #except ImportError:
            except NotImplemented:
                time.sleep(1)
                continue
        
        if init:
            cls.initialize()
        cls._init = False

    @classmethod
    def initialize(cls, *args, **kwargs):
        cls._module.initialize(*args, **kwargs)

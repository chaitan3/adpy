from adpy.variable import Variable, Function
from adpy.tensor import Kernel

import numpy as np

a = Variable((1,1))

def func(a):
    return 2*a

Function.createCodeDir('./')

b = Kernel(func)()(a)[0]
f = Function('test', (a,), (b,))

Function.compile()

Function._module.initialize(0)

print f(np.ones((1,1)))

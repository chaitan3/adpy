from adpy.variable import Variable, Function
from adpy.tensor import Kernel

import numpy as np

a = Variable((1,1))

def func(a):
    return 2*a + 3, a*5

b, c = Kernel(func)()(a)
f = Function('test', a, b)

Function.compile()

print(f(np.ones((1,1))))

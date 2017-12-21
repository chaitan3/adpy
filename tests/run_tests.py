#!/usr/bin/python2 

from adpy.variable import Variable, Function
from adpy.tensor import Kernel

import numpy as np

def test_arithmetic():

    n = 100
    a = Variable((n, 1))
    b = Variable((n, 1))
    c = Variable((n, 1))
    d = Variable((n, 1))

    def func(a, b, c, d):
        x = 2*a + 3*b - c
        y = x/d
        return x, y


    x, y = Kernel(func)()(a, b, c, d)
    f = Function('test_arithmetic', (a, b, c, d), (x, y))

    Function.compile()

    ar = np.random.rand(n, 1)
    br = np.random.rand(n, 1)
    cr = np.random.rand(n, 1)
    dr = np.random.rand(n, 1)
    dr += 2
    xr, yr = func(ar, br, cr, dr)
    x, y = f(ar, br, cr, dr)

    print x.sum(), xr.sum()
    assert np.allclose(x, xr)
    assert np.allclose(y, yr)
 

if __name__ == '__main__':
    test_arithmetic()

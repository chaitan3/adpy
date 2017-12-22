from adpy.variable import Variable, Function, Zeros, IntegerVariable
from adpy.tensor import Kernel, Tensor

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

    assert np.allclose(x, xr)
    assert np.allclose(y, yr)
 
def test_reduction():

    n = 100
    a = Variable((n, 1))
    b = Variable((n, 1))

    def func(a, b):
        return (a*b).sum(), (a+b).reduce_max()

    def np_func(a, b):
        return (a*b).sum(), (a+b).max()

    x, y = Zeros((1, 1)), Zeros((1,1))
    x, y = Kernel(func)(n, (x, y))(a, b)
    f = Function('test_reduction', (a, b), (x, y))

    Function.compile()

    ar = np.random.rand(n, 1)
    br = np.random.rand(n, 1)
    xr, yr = np_func(ar, br)
    x, y = f(ar, br)

    assert np.allclose(x, xr)
    assert np.allclose(y, yr)

def test_indirect_access():

    n = 100
    m = 20
    a = Variable((n, 1))
    b = IntegerVariable((m, 1))
    c = Variable((m, 1))

    def func(a, b, c):
        return a.extract(b), Tensor.collate(c, b)

    def np_func(a, b, c):
        b = b.flatten()
        x = a[b]
        y = np.zeros_like(a)
        np.add.at(y, b, c)
        return x, y

    x, y = Zeros((m, 1)), Zeros((n, 1))
    x, y = Kernel(func)(m, (x, y))(a, b, c)
    f = Function('test_indirect_access', (a, b, c), (x, y))

    Function.compile()

    ar = np.random.rand(n, 1)
    br = np.random.randint(0, n, (m, 1)).astype(np.int32)
    cr = np.random.rand(m, 1)
    xr, yr = np_func(ar, br, cr)
    x, y = f(ar, br, cr)

    assert np.allclose(x, xr)
    assert np.allclose(y, yr)

def test_matvec():

    n = 100
    a = Variable((n, 1))
    b = Variable((n, 3))
    c = Variable((n, 3, 3))

    def func(a, b, c):
        return a*b, b.dot(b), c.tensordot(b)

    def np_func(a, b, c):
        return a*b, (b*b).sum(axis=1, keepdims=1), np.matmul(c, b.reshape((n, 3, 1))).reshape((n, 3))

    x, y, z = Kernel(func)()(a, b, c)
    f = Function('test_matvec', (a, b, c), (x, y, z))

    Function.compile()

    ar = np.random.rand(n, 1)
    br = np.random.rand(n, 3)
    cr = np.random.rand(n, 3, 3)
    xr, yr, zr = np_func(ar, br, cr)
    x, y, z = f(ar, br, cr)

    assert np.allclose(x, xr)
    assert np.allclose(y, yr)
    assert np.allclose(z, zr)

def test_gradient():
    n = 100
    a = Variable((n, 1))
    b = Variable((n, 1))
    c = Variable((n, 1))
    y = IntegerVariable((n, 1))

    def func(a, b, c, y):
        return a*b + c, Tensor.collate(c, y)

    def func2(x, y, z):
        return ((z.extract(y)/(x + 2))).sqrt().sum()

    x, z = Kernel(func)()(a, b, c, y)
    res = Zeros((1, 1))
    res = Kernel(func2)(n, (res,))(x, y, z)
    f = Function('test_gradient', (a, b, c, y), (res,))
    g = f.getAdjoint()

    Function.compile()

    ar = np.random.rand(n, 1)
    br = np.random.rand(n, 1)
    cr = np.random.rand(n, 1)
    yr = np.random.randint(0, n, (n, 1)).astype(np.int32)
    res = f(ar, br, cr, yr)[0]
    for eps in [1e-6, 1e-7, 1e-8]:
        ap = 2*eps*(np.random.rand(n, 1)-0.5)
        bp = 2*eps*(np.random.rand(n, 1)-0.5)
        cp = 2*eps*(np.random.rand(n, 1)-0.5)
        res2 = f(ar + ap, br + bp, cr + cp, yr)[0]
        fd = res2-res
        ag, bg, cg, yg = g(ar, br, cr, yr, np.ones((1, 1)))
        ad = (ag*ap + bg*bp + cg*cp).sum()
        assert np.allclose(fd, ad)

if __name__ == '__main__':
    test_arithmetic()
    import shutil
    shutil.rmtree('gencode')
    test_reduction()
    #test_indirect_access()
    #test_matvec()
    #test_gradient()

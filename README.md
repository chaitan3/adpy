## Introduction

adpy is a library useful for defining operations of a numerical simulation tool in the form of a computational graph. The graph can be executed on CPUs and GPUs and the adjoint graph can be derived using automatic differentiation provided by the library.

## Installation
Build and install adpy using the following commands 
```
python setup.py build
python setup.py install --prefix=/path/you/want
```


## Testing
To run unit tests for adpy
```
cd tests
./run_tests.sh
cd ..
```

## Examples
An example of how to use the adpy library can be found in the tmp.py
file in the tests folder.

## Contributors

Chaitanya Talnikar and Professor Qiqi Wang

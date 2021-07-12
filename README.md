# Cee EXtensions Interpolation

cexi aims to facilitate developing of [C extension](https://docs.python.org/3/extending/extending.html) for [CPython](https://github.com/python/cpython)
main goal is to allow one to mix python an C code within single file

currently lib is WIP, unstable, undocumented & not nearly polished and
not extensively, yet you can enjoy some fancy examples below


### Fancy example
```python
from time import sleep
from cexi import define, to


@define
def fun(x, y):
    return x


# defaults to python implementation
assert fun(4, 2) == 4


# once cee implementation is defined background compilation
# process starts, generates code, compiles extension and notifies
# foreground process that .so file is available
@fun.cee
def fun_cee(module, args: to(x=int, y=int)):
    "return PyLong_FromLong(y);"


# this expression may fail if your CPU is super fast
assert fun(4, 2) == 4

# wait for background process to finish
sleep(1)

# now cee implementation is used
assert fun(4, 2) == 2
```
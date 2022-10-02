# Cee EXtensions Interpolation


### Rationale
cexi aims to facilitate developing of [C extension](https://docs.python.org/3/extending/extending.html) for [CPython](https://github.com/python/cpython). In particular interfacing between python and C.

### Code
```python
from cexi import Module, s


class Foo(Module):

    class options:
        flags = ['-O3']

    """
    #include "stdio.h"
    """

    @s.cee
    def foo(x: int) -> int:
        """
        return x + 1;
        """

    @s.share
    def bar(self, x: int) -> int:
        return x ** 2

    @s.py
    def baz(x: int, y: int) -> (int, int):
        """
        printf("baz\\n");
        int ret = x + y;
        bar(ret, &ret);
        return(foo(x + y), ret);
        """

    def wrapped_baz(self, x, y):
        print(f'calling {self.baz}')
        return self.baz(x, y)

print(Foo().wrapped_baz(3, 4)
```


### Explanation
```python
from cexi import Module, s


# cexi extensively uses docstrings to generate module's code
class Foo(Module):

    # compilation options
    class options:
        flags = ['-O3']

    # module's docs directly inserted at the beginning of cee extension
    """
    #include "stdio.h"
    """

    # s object is used to assign different tags to methods

    # .cee is a plain cee function, it's useful to organize plain cee routines
    # .cee functions aren't available for use in python, they're simply excluded from
    # final class namespace
    @s.cee
    def foo(x: int) -> int:
        """
        return x + 1;
        """

    # .share is a plain python function that is added to module to be used in cee code
    # it's signature is transformed as such
    # func(<input parameters>) -> <output parameters> => int func(<input parameters>, <pointers to output parameters>)
    # e.g. bar here becomes
    # int bar(int x, int *a), it returns non-zero value on failure & modify pointer to the return value, here x ** x
    @s.share
    def bar(self, x: int) -> int:
        return x ** 2

    # .py is a cee extension function. it's available from python & can use both .cee & .share functions at will
    @s.py
    def baz(x: int, y: int) -> (int, int):
        """
        printf("baz\\n");
        int ret = x + y;
        bar(ret, &ret);
        return(foo(x + y), ret);
        """

    # untagged functions are untouched, i.e. they're just instance's methods
    def wrapped_baz(self, x, y):
        print(f'calling {self.baz}')
        return self.baz(x, y)

# cexi.Module children act as singletones - on instantiation they're get loaded/compiled
# by default they are built inside temporaty directories, but users are able to make modules persistent
Foo()

ret = Foo().wrapped_baz(3, 4) # => prints
                              # calling <cexi.proxy.Proxy object at 0x7f4bae56cf10>
                              # baz

print(ret)  # => prints (8, 49)


# there are two main options to make modules persistent

# 1 - using `near` parameter. This will create a directory at __file__/../foo_cexi_module
# and store object & shared files there

class Foo(Module, near=__file__):
    pass


# 2 - using `directory` class attributeerror
class Foo(Module):
    directory = Path('/some/path')


# persistent extensions compiled on-demand. if extension is persistent cexi first loads it's module.
# then it compares revisions, which are hashed module's contents. thus if class definition is changed
# since last compilation it will be re-compiled and re-loaded

# you can also compile persistent extensions with command
python -mcexi <module path>:<class name>
```
import pytest

from time import sleep, time
from unittest.mock import patch

from cexi.core import DynamicExtension
from cexi import to, define
from cexi.exceptions import TooLate


def test_background():
    ext = DynamicExtension()

    @ext.py
    def choose(module: object, args: object) -> object:
        "return PyLong_FromLong(42);"

    ext._DynamicExtension__spawn()

    for _ in range(1000):
        if ext._check():
            break
        sleep(.01)

    assert choose() == 42


def test_define():
    orig = DynamicExtension.compile

    def f(*args, **kwargs):
        sleep(1)
        return orig(*args, **kwargs)

    patch.object(DynamicExtension, 'compile', f)

    @define
    def choose(x, y):
        return x

    @choose.cee
    def cee_choose(module, args: to(x=int, y=int)):
        "return PyLong_FromLong(y);"

    assert choose(2, 3) == 2
    sleep(1.1)
    assert choose(2, 3) == 3

    with pytest.raises(TooLate):
        choose.cee(lambda: 42)

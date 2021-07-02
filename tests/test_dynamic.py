import pytest

from cexi import Extension, to
from time import sleep


@pytest.mark.skip(reason='not yet implemented')
def test_dynamic():
    ext = Extension(dynamic=True)

    @ext.define
    def choose(x: int, y: int) -> int:
        return x

    @f.sub
    def _(x, y):
        "return PyLong_FromLong(y);"


    ret = None
    for _ in range(5):
        ret = choose(0, 1)
        sleep(.5)
    assert ret

import pytest


@pytest.mark.skip(reason='not yet implemented')
def test_single():
    from cexi import py, to

    @py.define
    def add(x: int, y: int) -> int:
        return x + y

    @add.sub
    def cee_add(x, y):
        """
        return PyLong_FromLong(x + y);
        """

    @py.defer
    def pyf(module: object, args: to(x=int, y=int)) -> int:
        "return PyLong_FromLong(x + y);"

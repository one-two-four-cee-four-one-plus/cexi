from cexi import Extension, to


def test_inverse():
    mix = Extension()

    @mix.pyc
    def add(a: int, b: int) -> int:
        return a + b


    @mix.pyc
    def add_and_mul(a: int, b: int) -> (int, int):
        return (a + b, a * b)

    @mix.py
    def test(self, args: to(left=int, right=int)):
        """
        int r1 = 0, r2 = 0, r3 = 0; // results
        add(left, right, &r1);
        add_and_mul(left, right, &r2, &r3);
        PyObject* result = Py_BuildValue("iii", r1, r2, r3);
        Py_XINCREF(result);
        return result;
        """

    with mix.ensured:
        assert (5, 5, 6) == test(2, 3) == (add(2, 3), *add_and_mul(2, 3))

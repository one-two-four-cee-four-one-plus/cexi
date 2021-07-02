from cexi import Extension


def test_pur_ce():
    mix = Extension()

    @mix.cee
    def add(a: int, b: int):
        'return a + b;'

    @mix.py
    def add2(self, args):
        """
        int right = 0, ret = 0;
        PyObject* ret_obj = NULL;

        if (!PyArg_ParseTuple(args, "i", &right))
            return NULL;

        ret = add(2, right);

        ret_obj = Py_BuildValue("i", ret);
        Py_INCREF(ret_obj);
        return ret_obj;
        """


    with mix.ensured:
        assert 4 == add2(2)

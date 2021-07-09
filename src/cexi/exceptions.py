class CodeDiverged(Exception):
    def __init__(
            self, module_name=None, member_name=None, attr=None,
            *args, **kwargs
    ):
        arguments = (module_name, member_name, attr)
        if all(arguments):
            super().__init__(
                (f'for "{member_name}" from "{module_name}", '
                 f'failed to retrieve "{attr}"'),
                *args,
                **kwargs
            )
        else:
            args = (*tuple(i for i in arguments if i), *args)
            super().__init__(*args, **kwargs)


class NotInitialized(Exception):
    def __init__(self, module=None, *args, **kwargs):
        if module:
            msg = f"module {module} not compiled/loaded"
            super().__init__(msg, *args, **kwargs)
        else:
            super().__init__(*args, **kwargs)


class TooLate(Exception):
    pass


class TooEarly(Exception):
    pass


class BackgroundCompileError(Exception):
    pass

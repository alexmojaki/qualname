"""
Tests for the qualname module.
"""
import functools
import inspect

from qualname import qualname


# These examples are based on the examples from
# https://www.python.org/dev/peps/pep-3155/

class C(object):
    @staticmethod
    def f():
        pass

    class D(object):
        @staticmethod
        def g():
            pass

        @staticmethod
        def h():
            def i():
                def j():
                    pass
                return j
            return i()


def f():
    def g():
        pass
    return g


def _test_cache(test_func):
    """
    This ensures that the cache works by running the test twice, where the second
    run should raise an error if qualname tries to use inspect.getsourcefile
    which comes after the cache checks.
    """

    def error():
        raise Exception()

    @functools.wraps(test_func)
    def wrapper():
        test_func()
        original = inspect.getsourcefile
        inspect.getsourcefile = error
        try:
            test_func()
        finally:
            inspect.getsourcefile = original

    return wrapper


@_test_cache
def test_nested_classes():
    assert qualname(C) == 'C'
    assert qualname(C.D) == 'C.D'


@_test_cache
def test_methods_in_nested_classes():
    assert qualname(C.f) == 'C.f'
    assert qualname(C.D.g) == 'C.D.g'


@_test_cache
def test_nested_functions():
    assert qualname(f) == 'f'
    assert qualname(f()) == 'f.<locals>.g'
    assert qualname(C.D.h()) == 'C.D.h.<locals>.i.<locals>.j'


@_test_cache
def test_directly_constructed_type():
    new_type = type('NewCls', (object,), {})
    assert qualname(new_type) == 'NewCls'


@_test_cache
def test_builtins():
    assert qualname(int) == 'int'
    assert qualname(len) == 'len'

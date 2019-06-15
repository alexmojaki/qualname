"""
Module to find out the qualified name of a class.
"""

import ast
import inspect
import types

from collections import defaultdict

__all__ = ['qualname']

_cache = {}
_file_cache = {}


class _Visitor(ast.NodeVisitor):
    def __init__(self):
        super(_Visitor, self).__init__()
        self.stack = []

        # The keys here are line numbers of a method/function
        self.function_qualnames = {}

        # The keys here are unqualified names of classes
        self.class_qualnames = defaultdict(set)

    def current_qualname(self):
        return ".".join(self.stack)

    def visit_FunctionDef(self, node):
        self.stack.append(node.name)
        self.function_qualnames[node.lineno] = self.current_qualname()
        self.stack.append('<locals>')
        self.generic_visit(node)
        self.stack.pop()
        self.stack.pop()

    def visit_ClassDef(self, node):
        self.stack.append(node.name)
        self.class_qualnames[node.name].add(self.current_qualname())
        self.generic_visit(node)
        self.stack.pop()


def _fallback_to_name(obj):
    name = obj.__name__
    if inspect.isclass(obj):
        _cache[obj] = name
    else:
        try:
            obj.__qualname__ = name
        except (AttributeError, TypeError):
            _cache[obj] = name

    return name


def qualname(obj):
    """Find out the qualified name for a class or function."""

    # For Python 3.3+, this is straight-forward.
    # This attribute is also set where possible on functions processed
    # for the first time as a simple cache
    if hasattr(obj, '__qualname__'):
        return obj.__qualname__

    # This is for objects that can't have an attribute set on them
    # (e.g. builtins) and classes (to prevent inheritance issues)
    # See _fallback_to_name
    if obj in _cache:
        return _cache[obj]

    code = None
    if isinstance(obj, (types.FunctionType, types.MethodType)):
        # Extract function from unbound method (Python 2)
        obj = getattr(obj, 'im_func', obj)
        try:
            code = obj.__code__
        except AttributeError:
            code = obj.func_code

        # Different instances of the same local function share the same code object, so this
        # can be used to look them up in the cache
        if code in _cache:
            return _cache[code]
    elif not (inspect.isclass(obj) or inspect.isroutine(obj)):
        return obj.__qualname__  # This object isn't meant to have a qualname. Raise a sensible error

    # For older Python versions, things get complicated.
    # Obtain the filename where the
    # class/method/function is defined.
    try:
        filename = inspect.getsourcefile(obj)
    except TypeError:
        return _fallback_to_name(obj)

    # Re-parse the source file to figure out what the
    # __qualname__ should be by analysing the abstract
    # syntax tree. Use a cache to avoid doing this more
    # than once for the same file.
    visitor = _file_cache.get(filename)
    if visitor is None:
        with open(filename, 'r') as fp:
            source = fp.read()
        node = ast.parse(source, filename)
        visitor = _Visitor()
        visitor.visit(node)
        _file_cache[filename] = visitor

        # For classes accessible from the top level, directly associate
        # each class with its qualname
        module = inspect.getmodule(obj)
        for k, qname_set in visitor.class_qualnames.items():

            # iterate over a copy since we're going to modify it
            for qname in list(qname_set):
                val = module
                for attr in qname.split('.'):
                    val = getattr(val, attr, None)

                    # Ensure that we're getting the right thing
                    if not (
                            inspect.isclass(val)
                            and val.__name__ == attr
                            and inspect.getmodule(val) == module
                    ):
                        break
                else:
                    _cache[val] = qname
                    qname_set.discard(qname)

        # Check if that worked for the current argument
        if obj in _cache:
            assert _cache[obj].endswith(obj.__name__)
            return _cache[obj]

    if code:
        result = _cache[code] = obj.__qualname__ = visitor.function_qualnames[code.co_firstlineno]
    else:
        results = visitor.class_qualnames[obj.__name__]
        if not results:
            return _fallback_to_name(obj)

        if len(results) == 1:
            result = list(results)[0]
        else:  # This means several local classes in the file have the same short name

            # Since the qualname of a method is unambiguous, the qualname
            # of this class can be guessed pretty reliably from its methods.
            # Since you could theoretically take a method from one class and
            # assign it as an attribute on another class, we look for the most
            # common prefix.
            counts = defaultdict(int)
            for method in obj.__dict__.values():
                if not isinstance(method, types.FunctionType):
                    continue
                method_qualname = qualname(method)
                suffix = '.' + method.__name__
                owner_class_qualname = method_qualname[:-len(suffix)]
                if owner_class_qualname in results:
                    counts[owner_class_qualname] += 1

            if counts:
                result = max(counts.items(), key=lambda item: item[1])[0]
            else:
                result = list(results)[0]

        if '.<locals>.' not in result:  # avoid overloading the cache with local classes
            _cache[obj] = result

    assert result.endswith(obj.__name__)
    return result

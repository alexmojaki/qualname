"""
Module to find out the qualified name of a class.
"""

import ast
import inspect
import types

__all__ = ['qualname']

_cache = {}
_file_cache = {}
_processed_modules = set()


def _assign_qualnames(module, parent, prefix=''):
    for name, child in inspect.getmembers(parent,
                                          lambda m: inspect.isclass(m) and inspect.getmodule(m) == module):
        qname = prefix + name
        if not hasattr(child, '__qualname__'):
            child.__qualname__ = qname
        _assign_qualnames(module, child, qname + '.')


class _Visitor(ast.NodeVisitor):
    def __init__(self):
        super(_Visitor, self).__init__()
        self.stack = []
        self.qualnames = {}

    def store_qualname(self, lineno):
        qn = ".".join(n for n in self.stack)
        self.qualnames[lineno] = qn

    def visit_FunctionDef(self, node):
        self.stack.append(node.name)
        self.store_qualname(node.lineno)
        self.stack.append('<locals>')
        self.generic_visit(node)
        self.stack.pop()
        self.stack.pop()

    def visit_ClassDef(self, node):
        self.stack.append(node.name)
        self.store_qualname(node.lineno)
        self.generic_visit(node)
        self.stack.pop()


def _fallback_to_name(obj):
    name = obj.__name__
    try:
        obj.__qualname__ = name
    except (AttributeError, TypeError):
        _cache[obj] = name
    return name


def qualname(obj):
    """Find out the qualified name for a class or function."""

    # For Python 3.3+, this is straight-forward.
    # This attribute is also set where possible on objects processed
    # for the first time as a simple cache
    if hasattr(obj, '__qualname__'):
        return obj.__qualname__

    # This is for objects that can't have an attribute set on them,
    # e.g. builtins.
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

    # For older Python versions, things get complicated.
    # Obtain the filename and the line number where the
    # class/method/function is defined.
    try:
        filename = inspect.getsourcefile(obj)
    except TypeError:
        return _fallback_to_name(obj)
    if inspect.isclass(obj):
        # For classes, several approaches are used, and the combination should work
        # for the vast majority of cases.

        # First, assign a __qualname__ to all accessible classes in the module
        module = inspect.getmodule(obj)
        if module not in _processed_modules:
            _assign_qualnames(module, module)

            # Check if that worked for this class
            if hasattr(obj, '__qualname__'):
                return obj.__qualname__

        try:
            _, lineno = inspect.getsourcelines(obj)
        except (OSError, IOError):
            return _fallback_to_name(obj)
    elif code:
        lineno = code.co_firstlineno
    else:
        return _fallback_to_name(obj)

    # Re-parse the source file to figure out what the
    # __qualname__ should be by analysing the abstract
    # syntax tree. Use a cache to avoid doing this more
    # than once for the same file.
    qualnames = _file_cache.get(filename)
    if qualnames is None:
        with open(filename, 'r') as fp:
            source = fp.read()
        node = ast.parse(source, filename)
        visitor = _Visitor()
        visitor.visit(node)
        _file_cache[filename] = qualnames = visitor.qualnames

    try:
        result = qualnames[lineno]
    except KeyError:
        return _fallback_to_name(obj)

    obj.__qualname__ = result
    if code:
        _cache[code] = result

    return result

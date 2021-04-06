"""Predicate factories for list-like object filters, e.g. Collection.where.

Functions in this method generate predicates that take
a field name and a Collection object and return True or False
depending on whether they fit the condition specified at generation.

See the docstring of Collection.where for examples
that illustrate why this unusual syntax is used.
"""
def _hasvalue(obj, attr):
    """True if the attribute `attr` of `obj` exists and is not None."""
    return getattr(obj, attr, None) != None

def eq(val):
    return lambda attr, obj: _hasvalue(obj, attr) and getattr(obj, attr) == val
def lt(val):
    return lambda attr, obj: _hasvalue(obj, attr) and getattr(obj, attr) < val
def lte(val):
    return lambda attr, obj: _hasvalue(obj, attr) and getattr(obj, attr) <= val
def gt(val):
    return lambda attr, obj: _hasvalue(obj, attr) and getattr(obj, attr) > val
def gte(val):
    return lambda attr, obj: _hasvalue(obj, attr) and getattr(obj, attr) >= val
def key(val):
    """Check if the attr is a dict and contains a key with name == val."""
    def keypred(field_name, obj):
        if hasattr(obj, field_name):
            attr = getattr(obj, field_name)
            if hasattr(attr, 'keys'):
                if val in attr.keys():
                    return True
        return False
    return keypred
def in_(val):
    """Check if `val` is in the value of `attr`.
    >>> from dnd5edb.test import s
    >>> s.where(components=in_('pearl')).sorted('level').print()
    Identify (rit.) 1m/T/I (1:A+B+Wz)
    Identify* (rit.) 1m/T/I (1:CF+CK)
    Identify (Ritual Only) (rit.) 1m/T/I (1:Rit)
    Circle of Death A/150'/I (6:S+Wl+Wz)
    """
    return lambda attr, obj: _hasvalue(obj, attr) and val in getattr(obj, attr)

def or_(*preds):
    """Check if any of the passed predicates return true.

    >>> from dnd5edb.test import aobj
    >>> numor = or_(in_(1), in_(2), in_(3))
    >>> numor('a', aobj([1, 2, 3]))
    True
    >>> numor('a', aobj([4, 5, 6]))
    False
    >>> numor('a', aobj([1, 5, 6]))
    True
    >>> numor('a', aobj([6, 2, 6]))
    True
    >>> numor('a', aobj([8, 7, 1]))
    True
    >>> numor('a', aobj([]))
    False
    >>> numor('a', aobj([3, 2, 1]))
    True

    >>> ranges = or_(lt(4), gt(7)) #tests that numbers are outside of the 4-7 range
    >>> ranges('a', aobj(4))
    False
    >>> ranges('a', aobj(3))
    True
    >>> ranges('a', aobj(-4.7))
    True
    >>> ranges('a', aobj(7))
    False
    >>> ranges('a', aobj(8))
    True
    """
    def or_closure(*args, **kwargs):
        for p in preds:
            if p(*args, **kwargs):
                return True
        return False

    return or_closure

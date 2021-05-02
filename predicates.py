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
def contains(val):
    """Check if `attr` contains `val`.
    >>> from dnd5edb.test import s
    >>> s.where(components=contains('pearl')).sorted('level').print()
    Identify (rit.) 1m/T/I (1:A+B+CF+CK+Wz)
    Fortune's Favor 1m/T/1h (2:WzC+WzG)
    Circle of Death A/150'/I (6:S+Wl+Wz)
    """
    return lambda attr, obj: _hasvalue(obj, attr) and val in getattr(obj, attr)

def in_(val):
    """Check if `val` is in the value of `attr`.

    >>> from dnd5edb.repltools import s
    >>> s.where(classes=contains("Wizard"), level=in_([2, 3, 4]), text=contains('spell attack')).print()
    Melf's Acid Arrow A/90'/I (2:AAl+DL+Wz)
    Ray of Enfeeblement A/60'/C<=1m (2:CD+CG+Wl+Wz)
    Scorching Ray A/120'/I (2:AArt+CLt+DW+S+WlF+WlGe+Wz)
    Vampiric Touch A/S/C<=1m (3:CD+CG+Wl+Wz)
    Storm Sphere A/150'/C<=1m (4:S+Wz)
    """
    return lambda attr, obj: _hasvalue(obj, attr) and getattr(obj, attr) in val

def or_(*preds):
    """Check if any of the passed predicates return true.

    >>> from dnd5edb.test import aobj
    >>> numor = or_(contains(1), contains(2), contains(3))
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

def and_(*preds):
    """Check if all of the passed predicates are true.

    >>> from dnd5edb.test import aobj
    >>> numand = and_(contains(1), contains(2), contains(3))
    >>> numand('a', aobj([1, 2, 3]))
    True
    >>> numand('a', aobj([4, 5, 6]))
    False
    >>> numand('a', aobj([1, 5, 6]))
    False
    >>> numand('a', aobj([6, 2, 6]))
    False
    >>> numand('a', aobj([8, 7, 1]))
    False
    >>> numand('a', aobj([]))
    False
    >>> numand('a', aobj([3, 2, 1]))
    True

    >>> ranges = and_(gte(4), lte(7)) #tests that numbers are within the range 4-7
    >>> ranges('a', aobj(4))
    True
    >>> ranges('a', aobj(3))
    False
    >>> ranges('a', aobj(-4.7))
    False
    >>> ranges('a', aobj(7))
    True
    >>> ranges('a', aobj(8))
    False
    """
    def and_closure(*args, **kwargs):
        for p in preds:
            if not p(*args, **kwargs):
                return False
        return True

    return and_closure

def not_(*preds):
    """Check if none of the passed predicates are true.

    >>> from dnd5edb.test import aobj
    >>> not_(lt(4))('a', aobj(7))
    True
    >>> not_(lt(4))('a', aobj(2))
    False
    >>> numnot = not_(contains(1), contains(2), contains(3))
    >>> numnot('a', aobj([1, 2, 3]))
    False
    >>> numnot('a', aobj([4, 5, 6]))
    True
    >>> numnot('a', aobj([1, 6, 9]))
    False
    """
    def not_closure(*args, **kwargs):
        for p in preds:
            if p(*args, **kwargs):
                return False
        return True

    return not_closure

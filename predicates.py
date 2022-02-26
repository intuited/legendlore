"""Predicate factories for list-like object filters, e.g. Collection.where.

Functions in this method generate predicates that take
a field name and a Collection object and return True or False
depending on whether they fit the condition specified at generation.

See the docstring of Collection.where for examples
that illustrate why this unusual syntax is used.

>>> from util import Generic
>>> testpred = lambda attrval, pred: pred('test', Generic(test=attrval))
>>> testpred(4, eq(5))
False
>>> testpred(6, eq(6))
True
>>> testpred('test string', contains("test string"))
True
>>> testpred([1, 2, 3, 4], contains(6))
False
>>> testpred('Testing', startswith('test'))
True
>>> testpred('Testing', startswith('test', ignorecase=False))
False
"""
def _hasvalue(obj, attr):
    """True if the attribute `attr` of `obj` exists and is not None."""
    return getattr(obj, attr, None) != None

def eq(val):
    return lambda attr, obj: _hasvalue(obj, attr) and getattr(obj, attr) == val
def ne(val):
    return lambda attr, obj: _hasvalue(obj, attr) and getattr(obj, attr) != val
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
    >>> from legendlore.test import s
    >>> s.where(components=dictvalue('M', contains('pearl'))).sorted('level').print()
    Identify (rit.) 1m/T/I [V/S/M@100gp] (1:A+Bd+CF+CK+Wz)
    Fortune's Favor 1m/T/1h [V/S/M@!100!gp] (2:WzC+WzG)
    Circle of Death A/150'/I [V/S/M@500gp] (6:S+Wl+Wz)
    """
    return lambda attr, obj: _hasvalue(obj, attr) and val in getattr(obj, attr)

def in_(val):
    """Check if `val` is in the value of `attr`.

    >>> from legendlore.repltools import s
    >>> s.where(classes=contains("Wizard"), level=in_([2, 3, 4]), text=contains('spell attack')).print()
    Melf's Acid Arrow A/90'/I [V/S/M] (2:AAl+DL+Wz)
    Ray of Enfeeblement A/60'/C<=1m [V/S] (2:CD+CG+Wl+Wz)
    Scorching Ray A/120'/I [V/S] (2:AArt+CLt+DW+S+WlFi+WlGe+Wz)
    Vampiric Touch A/S/C<=1m [V/S] (3:CD+CG+Wl+Wz)
    Storm Sphere A/150'/C<=1m [V/S] (4:S+Wz)
    """
    return lambda attr, obj: _hasvalue(obj, attr) and getattr(obj, attr) in val

def apply(fn, val):
    """Returned predicate passes (attr, val) to fn, returns result.

    >>> from legendlore.repltools import m
    >>> len(m.where(type='humanoid'))
    17
    >>> len(m.where(type=apply(str.startswith, 'humanoid')))
    778
    """
    return lambda attr, obj: _hasvalue(obj, attr) and fn(getattr(obj, attr), val)

def startswith(val, ignorecase=True):
    if ignorecase:
        return lambda attr, obj: _hasvalue(obj, attr) and getattr(obj, attr).lower().startswith(val.lower())
    else:
        return apply(str.startswith, val)

def or_(*preds):
    """Check if any of the passed predicates return true.

    >>> from legendlore.test import aobj
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

    >>> from legendlore.test import aobj
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

    >>> from legendlore.test import aobj
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

def dictvalue(key, pred):
    """Test the predicate on the value of `key` in the dictionaries passed to the returned closure.

    Find spells whose value of used material components equals 100
    >>> from legendlore.repltools import s
    >>> s.where(components=dictvalue('used', eq(100))).print()
    Identify (rit.) 1m/T/I [V/S/M@100gp] (1:A+Bd+CF+CK+Wz)
    Warding Bond A/T/1h [V/S/M@100gp] (2:ABS+C+CPe+P+PCr)
    Clairvoyance 10m/1mi/C<=10m [V/S/M@100gp] (3:BbAG+Bd+C+S+WlGOO+Wz)
    Dawn A/60'/C<=1m [V/S/M@100gp] (5:C+Wz)
    Find the Path 1m/S/C<=1d [V/S/M@100gp] (6:Bd+C+D)
    Soul Cage R/60'/8h [V/S/M@100gp] (6:Wl+Wz)
    """
    from legendlore.test import obj_fromdict
    
    def dictvalue_closure(attr, obj):
        if _hasvalue(obj, attr):
            dictionary = getattr(obj, attr)
            # predicate is expecting the value to be in an attribute, not a key
            return pred(key, obj_fromdict(dictionary))
        return False

    return dictvalue_closure

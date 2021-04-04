"""Predicate factories for list-like object filters, e.g. Collection.where.

Functions in this method generate predicates that take
a field name and a Collection object and return True or False
depending on whether they fit the condition specified at generation.

See the docstring of Collection.where for examples
that illustrate why this unusual syntax is used.
"""
def eq(val):
    return lambda attr, obj: hasattr(obj, attr) and getattr(obj, attr) == val
def lt(val):
    return lambda attr, obj: hasattr(obj, attr) and getattr(obj, attr) < val
def lte(val):
    return lambda attr, obj: hasattr(obj, attr) and getattr(obj, attr) <= val
def gt(val):
    return lambda attr, obj: hasattr(obj, attr) and getattr(obj, attr) > val
def gte(val):
    return lambda attr, obj: hasattr(obj, attr) and getattr(obj, attr) >= val
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
    """Check if `val` is in the value of `attr`."""
    return lambda attr, obj: hasattr(obj, attr) and val in getattr(obj, attr)

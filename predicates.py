"""Predicate factories for list-like object filters, e.g. Monsters.where.

Functions in this method generate predicates that take
a field name and a Monster object and return True or False
depending on whether they fit the condition specified at generation.

See the docstring of Monsters.where for examples
that illustrate why this unusual syntax is used.
"""
def eq(val):
    return lambda field, m: hasattr(m, field) and getattr(m, field) == val
def lt(val):
    return lambda field, m: hasattr(m, field) and getattr(m, field) < val
def lte(val):
    return lambda field, m: hasattr(m, field) and getattr(m, field) <= val
def gt(val):
    return lambda field, m: hasattr(m, field) and getattr(m, field) >= val
def gte(val):
    return lambda field, m: hasattr(m, field) and getattr(m, field) > val
def key(val):
    """Check if the field is a dict and contains a key with name == val."""
    def keypred(field_name, m):
        if hasattr(m, field_name):
            field = getattr(m, field_name)
            if hasattr(field, 'keys'):
                if val in field.keys():
                    return True
        return False
    return keypred
def in_(val):
    """Check if `val` is in the value of `field`."""
    return lambda field, m: hasattr(m, field) and val in getattr(m, field)

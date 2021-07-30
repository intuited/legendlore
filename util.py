"""Utility classes and functions.

>>> test = Generic(attrib1='testing', __doc__='Test object docstring.')
>>> test.attrib1
'testing'
>>> help(test)
Help on Generic in module util:
<BLANKLINE>
<util.Generic object>
    Test object docstring.
<BLANKLINE>
"""
def dictify(fn):
    """Used as a wrapper for generator functions that produce dicts."""
    return lambda *args, **kwargs: dict(fn(*args, **kwargs))

class Generic:
    """Generic class used as basis for attribute-based structures."""
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

careful_list_sum = lambda l: None if None in l else sum(l)
careful_sum = lambda l: careful_list_sum(list(l))

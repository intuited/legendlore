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

class Generic:
    """Generic class used as basis for attribute-based structures."""
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

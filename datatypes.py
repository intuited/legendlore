"""Various items of data used by both parse.py and higher level code."""
from functools import total_ordering
from logging import warning

@total_ordering
class SpellRange:
    def __init__(self, string):
        if string not in self._ranges.keys():
            string = self._range_aliases[string]
        self.string = string

    def __repr__(self):
        return self.string

    def __eq__(self, other):
        """`True` if this range is equal to `other`.

        `other` can be either another SpellRange object or a string.
        
        >>> SpellRange('Self') == SpellRange('Self')
        True
        >>> SpellRange('Self') == 'Self'
        True
        >>> SpellRange('Self') == 'Self (10-foot radius)'
        False
        """
        if type(other) is not SpellRange:
            other = SpellRange(other)
        return self._ord() == other._ord()

    def __lt__(self, other):
        """`True` if this range is lower in the sort order than `other`.

        `other` can be either another SpellRange object or a string.

        >>> SpellRange('Touch') < SpellRange('60 feet')
        True
        >>> SpellRange('15 feet') < SpellRange('Self (15-foot cone)')
        False
        >>> SpellRange('Self (60-foot cone)') < 'Touch'
        True
        """
        if type(other) is not SpellRange:
            other = SpellRange(other)
        return self._ord() < other._ord()

    def abbr(self):
        """Returns the abbreviation used for this range in one-line descriptions."""
        return self._ranges[self.string]

    def _ord(self):
        """Returns the ordinal position of this range in the full set of ranges.

        Used by rich comparison methods.

        >>> SpellRange('Self')._ord()
        1
        >>> SpellRange('90 feet')._ord()
        23
        """
        for i, r in enumerate(self._ranges.keys()):
            if r == self.string:
                return i
        raise ValueError(f'SpellRange._ord: self.string "{self.string}" not found in _ranges')

    # Ordered set of all ranges and their abbreviated form.
    _ranges = {
        None: "N",
        'Self': 'S',
        "Self (5-foot radius)": "S(5'r)",
        'Self (10-foot radius)': "S(10'r)",
        'Self (10-foot-radius sphere)': "S(10'r-sphere)",
        'Self (10-foot-radius hemisphere)': "S(10'r-hemisphere)",
        "Self (15-foot radius)": "S(15'r)",
        'Self (15-foot cone)': "S(15'cone)",
        'Self (15-foot cube)': "S(15'cube)",
        'Self (30-foot radius)': "S(30'r)",
        'Self (30-foot cone)': "S(30'cone)",
        "Self (30-foot line)": "S(30'line)",
        'Self (60-foot line)': "S(60'line)",
        'Self (60 foot cone)': "S(60'cone)",
        'Self (60-foot cone)': "S(60'cone)",
        'Self (100-foot line)': "S(100'line)",
        'Self (5-mile radius)': "S(5mi.r)",
        'Touch': "T",
        'Special': "Special",
        'Sight': "Sight",
        '5 feet': "5'",
        '10 feet': "10'",
        '15 feet': "15'",
        "20 feet": "20'",
        '30 feet': "30'",
        '60 feet': "60'",
        '90 feet': "90'",
        '100 feet': "100'",
        '120 feet': "120'",
        '150 feet': "150'",
        '300 feet': "300'",
        '500 feet': "500'",
        "1000 feet": "1000'",
        '1 mile': "1mi",
        '500 miles': "500mi",
        'Unlimited': "Unlimited"}

    _range_aliases = {
            "Self (10-foot sphere)": "Self (10-foot-radius sphere)",
            "Self (15-foot-radius)": "Self (15-foot radius)",
            "Self (10-foot hemisphere)": "Self (10-foot-radius hemisphere)",
            }

#TODO: delet this
spell_ranges = {
    'Unlimited',
    '60 feet',
    '120 feet',
    '300 feet',
    'Self (15-foot radius)',
    'Self (30-foot radius)',
    'Self (5-foot radius)',
    '20 feet',
    'Self (10-foot sphere)',
    'Self (10-foot radius)',
    '500 miles',
    '150 feet',
    'Self (10-foot hemisphere)',
    'Self (30-foot line)',
    'Self (60-foot cone)',
    '500 feet',
    'Touch',
    'Self',
    '100 feet',
    '90 feet',
    '5 feet',
    'Self (15-foot cone)',
    '1 mile',
    'Self (60-foot line)',
    '10 feet',
    '30 feet',
    'Self (30-foot cone)',
    'Self (5-mile radius)',
    'Sight',
    'Self (15-foot cube)',
    'Self (100-foot line)',
    'Special',
    '1000 feet',
    }

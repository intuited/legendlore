"""Various items of data used by both parse.py and higher level code."""
from functools import total_ordering
from logging import warning

@total_ordering
class OrderedField:
    """Base class for fields which have a predefined set of values with a predefined order.

    Also provides abbreviation functionality.
    """
    def __init__(self, value):
        """Attempt to remap the value if it's not in our known value set.

        >>> SpellRange('Self (10-foot sphere)')
        SpellRange('Self (10-foot-radius sphere)')
        >>> SpellRange('Total gibberish.') # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        KeyError: "SpellRange: unknown value 'Total gibberish.' could not be instantiated."
        """
        if value in self._value_aliases:
            value = self._value_aliases[value]
        if value not in self._values:
            raise KeyError(f'{type(self).__name__}: unknown value {repr(value)} could not be instantiated.')
        self.value = value

    def __repr__(self):
        """Make it look offical.

        >>> SpellRange('90 feet')
        SpellRange('90 feet')
        """
        return f'{type(self).__name__}({repr(self.value)})'
    def __str__(self):
        """Just converts the underlying data to a string.

        This is apparently Not The Way you're supposed to handle this, but it seems like it should work.

        >>> str(SpellRange('90 feet'))
        '90 feet'
        """
        return str(self.value)

    def __eq__(self, other):
        """`True` if this range is equal to `other`.

        `other` can be either another SpellRange object
        or a value of a type compatible with that of self.value.
        
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

        `other` can be either another SpellRange object
        or a value of a type compatible with that of self.value.

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
        return self._values[self.value]

    def _ord(self):
        """Returns the ordinal position of this range in the full set of ranges.

        Used by rich comparison methods.

        >>> SpellRange('Self')._ord()
        1
        >>> SpellRange('90 feet')._ord()
        26
        """
        for i, r in enumerate(self._values.keys()):
            if r == self.value:
                return i
        raise ValueError(f'SpellRange._ord: self.value "{self.value}" not found in self._values')

class SpellRange(OrderedField):
    """Ordered set of all ranges and their abbreviated form."""
    _values = {
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

    _value_aliases = {
            "Self (10-foot sphere)": "Self (10-foot-radius sphere)",
            "Self (15-foot-radius)": "Self (15-foot radius)",
            "Self (10-foot hemisphere)": "Self (10-foot-radius hemisphere)",
            }

class CastingTime(OrderedField):
    _values = {
        None: 'N',
        'None': 'N',
        '1 action': 'A',
        'part of the Attack action to fire a magic arrow': 'A*',
        '1 bonus action': 'B',
        '1 reaction': 'R',
        '1 reaction, which you take when you take acid, cold, fire, lightning, or thunder damage': 'R*',
        '1 reaction, which you take when a humanoid you can see within 60 feet of you dies': 'R*',
        '1 minute': '1m',
        '10 minutes': '10m',
        '1 hour': '1h',
        '8 hours': '8h',
        '1 action or 8 hours': 'A/8h',
        '1 action, 8 hours': 'A/8h',
        '12 hours': '12h',
        '24 hours': '24h'}


# Maps caster classes as found in <spell> tags to abbreviations used in one-line descriptions.
# Abbreviations are subject to change as ambiguities are introduced with new class archetypes.
caster_classes = {
    'Artificer': "A",
    'Artificer (Alchemist)': 'AAl',
    'Artificer (Armorer)': "AArm",
    'Artificer (Artillerist)': "AArt",
    'Artificer (Battle Smith)': "ABS",
    'Bard (Glamour)': 'BdG',
    'Bard': "Bd",
    'Barbarian (Ancestral Guardian)': 'BbAG',
    'Barbarian (Totem Warrior)': 'BbTW',
    'Barbarian': 'Bb',
    'Cleric (Arcana)': "CA",
    'Cleric (Death)': "CD",
    'Cleric (Forge)': "CF",
    'Cleric (Grave)': "CG",
    'Cleric (Knowledge)': "CK",
    'Cleric (Life)': "CLf",
    'Cleric (Light)': "CLt",
    'Cleric (Nature)': "CN",
    'Cleric (Order)': "CO",
    'Cleric (Protection)': "CPr",
    'Cleric (Peace)': "CPe",
    'Cleric (Tempest)': "CTm",
    'Cleric (Twilight)': "CTw",
    'Cleric (Trickery)': "CTr",
    'Cleric (War)': "CW",
    'Cleric': "C",
    'Druid (Arctic)': "DLA",
    'Druid (Coast)': "DLC",
    'Druid (Desert)': "DLD",
    'Druid (Forest)': "DLF",
    'Druid (Grassland)': "DLG",
    'Druid (Mountain)': "DLM",
    'Druid (Swamp)': "DLS",
    'Druid (Underdark)': "DLU",
    'Druid (Land)': "DL",
    'Druid (Moon)': "DM",
    'Druid (Spores)': "DS",
    'Druid (Wildfire)': "DW",
    'Druid': "D",
    'Eldritch Invocations': "EI",
    'Fighter': "F",
    'Fighter (Arcane Archer)': "FAA",
    'Fighter (Battle Master)': "FBM",
    'Fighter (Eldritch Knight)': "FEK",
    'Martial Adept': "MA",
    'Monk': "M",
    'Monk (Way of the Four Elements)': "M4",
    'Paladin (Ancients)': "PA",
    'Paladin (Conquest)': "PCo",
    'Paladin (Crown)': "PCr",
    'Paladin (Devotion)': "PD",
    'Paladin (Glory)': "PG",
    'Paladin (Oathbreaker)': "PO",
    'Paladin (Redemption)': "PR",
    'Paladin (Treachery)': "PT",
    'Paladin (Vengeance)': "PV",
    'Paladin (Watchers)': "PW",
    'Paladin': "P",
    'Ranger (Fey Wanderer)': "RaFW",
    'Ranger (Gloom Stalker)': "RaGS",
    'Ranger (Horizon Walker)': "RaHW",
    'Ranger (Monster Slayer)': "RaMS",
    'Ranger (Primeval Guardian)': "RaPG",
    'Ranger (Swarmkeeper)': "RaS",
    'Ranger (No Spells)': "Ra",
    'Ranger': "Ra",
    'Ritual Caster': "Rit",
    'Rogue (Arcane Trickster)': "RoAT",
    'Rogue': "Ro",
    'Sorcerer (Aberrant Mind)': "SAM",
    'Sorcerer (Clockwork Soul)': "SCS",
    'Sorcerer (Divine Soul)': "SDS",
    'Sorcerer (Shadow)': "SSh",
    'Sorcerer (Stone Sorcery)': "SSS",
    'Sorcerer': "S",
    'Warlock (Archfey)': "WlA",
    'Warlock (Celestial)': "WlC",
    'Warlock (Fathomless)': "WlFa",
    'Warlock (Fiend)': "WlFi",
    'Warlock (Genie)': "WlGe",
    'Warlock (Great Old One)': "WlGOO",
    'Warlock (Hexblade)': "WlH",
    'Warlock (Raven Queen)': "WlR",
    'Warlock (Seeker)': "WlS",
    'Warlock (Undying)': "WlU",
    'Warlock': "Wl",
    'Wizard (Chronurgy)': "WzC",
    'Wizard (Graviturgy)': "WzG",
    'Wizard (Illusion)': "WzI",
    'Wizard': "Wz"}

# Spell durations mapped to their abbreviations.
spell_durations = {
        None: 'N',
        'Instantaneous': 'I',
        'Instantaneous or 1 hour (see below)': 'I/1h',
        'Special': "S",
        '1 turn': '1t',
        'up to 1 round': '<=1r',
        '1 round': '1r',
        'up to 6 rounds': '<=6r',
        'up to 1 minute': "<=1m",
        'Up to 1 minute': '<=1m',
        '1 minute': '1m',
        'up to 10 minutes': "<=10m",
        '10 minutes': '10m',
        'up to 1 hour': "<=1h",
        'Up to 1 hour': '<=1h',
        '1 hour': "1h",
        'up to 2 hours': '<=2h',
        '6 hours': '6h',
        'up to 8 hours': '<=8h',
        'Up to 8 hours': '<=8h',
        '8 hours': "8h",
        'up to 1 day': '<=1d',
        '1 day': '1d',
        '10 days': "10d",
        '24 hours': "24h",
        'up to 24 hours': "<=24h",
        '30 days': '30d',
        '7 days': '7d',
        'Until dispelled or triggered': 'UD/T',
        'Until dispelled': "UD",
        'special': 'S',
        }
